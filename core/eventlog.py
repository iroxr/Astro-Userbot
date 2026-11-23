# Astro Userbot
# © جميع الحقوق محفوظة
"""The events channel: every command result and notification is written here."""
import asyncio
import logging

from telethon import errors, utils
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.types import Channel

from . import client, lang, settings
from . import errors as err

log = logging.getLogger("astro.events")

LIMIT = 3900
CHANNEL_PROBLEMS = {
    "ChannelPrivateError",
    "ChannelInvalidError",
    "ChannelBannedError",
    "ChatWriteForbiddenError",
    "ChatAdminRequiredError",
    "PeerIdInvalidError",
    "UserBannedInChannelError",
}

_peer = None
_pid = None
_lock = asyncio.Lock()
_problem = None  # last reason the channel could not be used

_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_MARKS = dict.fromkeys([*range(0x064B, 0x0653), 0x0640])


def _norm(text):
    text = (text or "").translate(_MAP).translate(_MARKS)
    return " ".join(text.split()).casefold()


def info():
    """(peer id, problem) for the status card."""
    return _pid, _problem


async def _resolve(ref):
    try:
        return await client.get_input_entity(ref)
    except ValueError:
        await client.get_dialogs()
        return await client.get_input_entity(ref)


async def _usable(ref):
    peer = await _resolve(ref)
    ent = await client.get_entity(peer)
    if not isinstance(ent, Channel) or getattr(ent, "left", False) or getattr(ent, "deactivated", False):
        return None
    return peer


async def _find():
    want = _norm(lang.EVENTS_TITLE)
    other = None
    async for dialog in client.iter_dialogs():
        ent = dialog.entity
        if isinstance(ent, Channel) and ent.broadcast and _norm(ent.title) == want:
            if getattr(ent, "creator", False):
                return ent
            other = other or ent
    return other


async def _create():
    res = await client(CreateChannelRequest(title=lang.EVENTS_TITLE, about=lang.EVENTS_ABOUT, broadcast=True))
    return res.chats[0]


async def ensure(force=False):
    """Find the events channel by name, or create it. Returns True when usable."""
    global _peer, _pid, _problem
    created = False
    async with _lock:
        if _peer is not None and not force:
            return True
        _peer = None
        try:
            cached = None if force else settings.get("core", "events_channel")
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
                settings.set("core", "events_channel", _pid)
            _problem = None
        except Exception as exc:
            _peer = None
            _problem = err.reason(exc)
            log.exception("events channel unavailable")
            return False
    if created:
        await post(lang.EVENTS_CREATED)
    return True


def _chunks(text):
    out, part, size = [], [], 0
    for line in text.split("\n"):
        while len(line) > LIMIT:
            if part:
                out.append("\n".join(part))
                part, size = [], 0
            out.append(line[:LIMIT])
            line = line[LIMIT:]
        if part and size + len(line) + 1 > LIMIT:
            out.append("\n".join(part))
            part, size = [], 0
        part.append(line)
        size += len(line) + 1
    if part:
        out.append("\n".join(part))
    return out or [""]


async def _send(text):
    """Send one chunk. Returns (message, chat reference) or (None, None)."""
    for attempt in (0, 1):
        if _peer is None and not await ensure():
            break
        try:
            return await client.send_message(_peer, text, link_preview=False), _pid
        except errors.FloodWaitError as exc:
            await asyncio.sleep(min(exc.seconds, 60) + 1)
        except Exception as exc:
            log.warning("events send failed: %s", type(exc).__name__)
            if attempt == 0 and (err.kind(exc) in CHANNEL_PROBLEMS or isinstance(exc, ValueError)):
                await ensure(force=True)
                continue
            break
    try:
        note = lang.EVENTS_FALLBACK.format(reason=_problem or lang.LBL_UNKNOWN)
        return await client.send_message("me", note + text, link_preview=False), "me"
    except Exception:
        log.exception("fallback send failed")
        return None, None


class Entry:
    """A logged message that can be edited as the work progresses."""

    def __init__(self, ids, chat):
        self.ids = list(ids)
        self.chat = chat

    @property
    def msg_id(self):
        return self.ids[0] if self.ids else None

    async def _peer_for(self):
        if self.chat == "me":
            return "me"
        if self.chat == _pid and _peer is not None:
            return _peer
        return await _resolve(self.chat)

    async def update(self, text):
        parts = _chunks(text)
        try:
            peer = await self._peer_for()
        except Exception:
            peer = None
        for i, part in enumerate(parts):
            if i < len(self.ids) and peer is not None:
                try:
                    await client.edit_message(peer, self.ids[i], part, link_preview=False)
                    continue
                except errors.MessageNotModifiedError:
                    continue
                except errors.FloodWaitError as exc:
                    await asyncio.sleep(min(exc.seconds, 30) + 1)
                    continue
                except Exception:
                    log.warning("events edit failed, sending a new message")
            msg, chat = await _send(part)
            if msg is not None:
                if i < len(self.ids):
                    self.ids[i] = msg.id
                else:
                    self.ids.append(msg.id)
                self.chat = chat
        if peer is not None and len(self.ids) > len(parts):
            extra, self.ids = self.ids[len(parts):], self.ids[:len(parts)]
            try:
                await client.delete_messages(peer, extra)
            except Exception:
                log.warning("events cleanup failed")
        return self

    @classmethod
    async def attach(cls, chat, msg_id):
        return cls([msg_id], chat)


async def post(text):
    """Write a new message to the events channel."""
    parts = _chunks(text)
    ids, chat = [], None
    for part in parts:
        msg, where = await _send(part)
        if msg is not None:
            ids.append(msg.id)
            chat = where
    return Entry(ids, chat)


async def fail(title, exc, entry=None, hint=None):
    """Write a detailed failure: title, cause, technical detail and hint."""
    text = f"{title}\n{err.describe(exc, hint)}"
    if entry is not None:
        return await entry.update(text)
    return await post(text)


class Job:
    """Progress message of one command: first show posts, later shows edit it."""

    def __init__(self):
        self.entry = None

    async def show(self, text=None, *args, **kwargs):
        if not text:
            return self.entry
        if self.entry is None:
            self.entry = await post(text)
        else:
            await self.entry.update(text)
        return self.entry
