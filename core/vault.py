# Astro Userbot
# © جميع الحقوق محفوظة
"""The storage channel: where plugins archive things worth keeping (self-destructing media,
deleted and edited messages). It is found by name or created, like the events channel."""
import asyncio
import logging

from telethon import errors, utils
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.types import Channel

from . import client, eventlog, lang, settings
from . import errors as err
from .eventlog import CHANNEL_PROBLEMS, _norm, _resolve, _usable

log = logging.getLogger("astro.vault")

_peer = None
_pid = None
_lock = asyncio.Lock()
_problem = None


def info():
    """(peer id, problem) for the status card."""
    return _pid, _problem


async def _find():
    names = {_norm(lang.VAULT_TITLE), _norm(lang.VAULT_ALT)}
    best = None
    async for dialog in client.iter_dialogs():
        ent = dialog.entity
        if not isinstance(ent, Channel) or getattr(ent, "left", False):
            continue
        title = _norm(ent.title)
        if title not in names:
            continue
        score = (bool(getattr(ent, "creator", False)), title == _norm(lang.VAULT_TITLE))
        if best is None or score > best[0]:
            best = (score, ent)
    return best[1] if best else None


async def _create():
    res = await client(CreateChannelRequest(title=lang.VAULT_TITLE, about=lang.VAULT_ABOUT, broadcast=True))
    return res.chats[0]


async def ensure(force=False):
    """Find the storage channel by name, or create it. Returns True when usable."""
    global _peer, _pid, _problem
    created = False
    async with _lock:
        if _peer is not None and not force:
            return True
        _peer = None
        try:
            cached = None if force else settings.get("core", "vault_channel")
            if cached:
                try:
                    _peer = await _usable(cached)
                    _pid = cached if _peer else None
                except Exception:
                    _peer = None
            if _peer is None:
                ent = await _find()
                if ent is None:
                    ent = await _create()
                    created = True
                _peer = utils.get_input_peer(ent)
                _pid = utils.get_peer_id(ent)
                settings.set("core", "vault_channel", _pid)
            _problem = None
        except Exception as exc:
            _peer = None
            _problem = err.reason(exc)
            log.exception("storage channel unavailable")
            return False
    if created:
        await eventlog.post(lang.VAULT_CREATED)
    return True


async def send(text=None, file=None, **kwargs):
    """Send text or a file to the storage channel. Falls back to Saved Messages if it is unreachable."""
    for attempt in (0, 1):
        if _peer is None and not await ensure():
            break
        try:
            if file is None:
                return await client.send_message(_peer, text, link_preview=False)
            return await client.send_file(_peer, file, caption=text, **kwargs)
        except errors.FloodWaitError as exc:
            await asyncio.sleep(min(exc.seconds, 60) + 1)
        except Exception as exc:
            log.warning("storage send failed: %s", type(exc).__name__)
            if attempt == 0 and (err.kind(exc) in CHANNEL_PROBLEMS or isinstance(exc, ValueError)):
                await ensure(force=True)
                continue
            break
    note = lang.VAULT_FALLBACK.format(reason=_problem or lang.LBL_UNKNOWN)
    if file is None:
        return await client.send_message("me", note + (text or ""), link_preview=False)
    return await client.send_file("me", file, caption=note + (text or ""), **kwargs)
