# Astro Userbot
# © جميع الحقوق محفوظة
"""Button panel of the companion bot.

The same commands as `.الاوامر`, but run by tapping buttons in the bot chat. Nothing is
registered here: groups and commands are read from the registry every time a menu is drawn,
so a plugin that is added or removed appears or disappears from the buttons by itself.
Text commands in any chat keep working exactly as before.
"""
import asyncio
import hashlib
import html
import logging
import time
from datetime import datetime, timezone

from telethon import Button, errors

from . import PREFIX, client as userbot, eventlog, lang, registry, state, ui
from .eventlog import _chunks as chunks

log = logging.getLogger("astro.panel")

PER_PAGE = 20  # buttons per page (Telegram allows 100 per message)
COLS = 2
ASK_TTL = 300  # seconds the bot waits for the text of "run with text"

_tasks = set()
_pending = None  # {"cid", "chat", "msg", "until"} while the bot waits for the text of a command


# ---- ids (callback data is limited to 64 bytes, names are Arabic) -------------

def _id(name):
    return hashlib.blake2s(name.encode("utf-8"), digest_size=4).hexdigest()


def _find_group(gid):
    for name in registry.groups():
        if _id(name) == gid:
            return name
    return None


def _find_cmd(cid):
    for name in registry.groups():
        for cmd in registry.by_group(name):
            if _id(cmd.name) == cid:
                return cmd
    return None


# ---- drawing ------------------------------------------------------------------

def _grid(buttons):
    return [buttons[i:i + COLS] for i in range(0, len(buttons), COLS)]


def _paginate(buttons, page, nav):
    pages = max(1, -(-len(buttons) // PER_PAGE))
    page = min(max(page, 0), pages - 1)
    rows = _grid(buttons[page * PER_PAGE:(page + 1) * PER_PAGE])
    if pages > 1:
        rows.append([
            Button.inline(lang.PANEL_PREV, data=f"{nav}:{page - 1}" if page > 0 else "n"),
            Button.inline(lang.PANEL_PAGE.format(page=page + 1, pages=pages), data="n"),
            Button.inline(lang.PANEL_NEXT, data=f"{nav}:{page + 1}" if page < pages - 1 else "n"),
        ])
    return rows


def main(page=0):
    """(text, buttons) of the main menu: one button per group."""
    names = registry.groups()
    if not names:
        return ui.card(lang.PANEL_TITLE, [lang.PANEL_EMPTY]), None
    total = sum(len(registry.by_group(n)) for n in names)
    text = ui.card(lang.PANEL_TITLE, [
        (lang.PANEL_GROUPS, len(names)),
        (lang.PANEL_COUNT, total),
        "",
        lang.PANEL_PICK,
    ])
    buttons = [Button.inline(n, data=f"g:{_id(n)}:0") for n in names]
    return text, _paginate(buttons, page, "m")


def group_menu(gid, page=0):
    name = _find_group(gid)
    if name is None:
        return None
    cmds = registry.by_group(name)
    text = ui.card(f"{lang.GROUP_TITLE} {name}", [
        (lang.PANEL_COUNT, len(cmds)),
        "",
        lang.PANEL_GROUP_HINT,
        lang.PANEL_TEXT_HINT,
    ])
    buttons = [Button.inline(c.name, data=f"c:{_id(c.name)}") for c in cmds]
    rows = _paginate(buttons, page, f"g:{gid}")
    rows.append([Button.inline(lang.PANEL_HOME, data="m:0")])
    return text, rows


def _gone():
    return lang.PANEL_GONE, [[Button.inline(lang.PANEL_HOME, data="m:0")]]


def _after(cmd):
    """Buttons under the result of a command."""
    cid = _id(cmd.name)
    first = [Button.inline(lang.PANEL_AGAIN, data=f"c:{cid}")]
    if not cmd.confirm:
        first.append(Button.inline(lang.PANEL_WITH_TEXT, data=f"a:{cid}"))
    return [
        first,
        [
            Button.inline(lang.PANEL_BACK, data=f"g:{_id(cmd.group)}:0"),
            Button.inline(lang.PANEL_HOME, data="m:0"),
        ],
    ]


def _name(cmd):
    return f"<code>{PREFIX}{html.escape(cmd.name)}</code>"


# ---- running a command from a button --------------------------------------------

class _Msg:
    """Stand-in for the command message: there is no real message when a button is pressed."""

    id = 0
    file = None
    media = None
    photo = None
    reply_to = None
    out = True

    def __init__(self, text):
        self.text = self.raw_text = self.message = text
        self.date = datetime.now(timezone.utc)

    def __getattr__(self, name):
        raise AttributeError(f"message.{name} is not available when a command runs from a button")


class ButtonCtx:
    """Stand-in for the event a command handler receives (same shape as dispatcher.Ctx).

    Output goes to the events channel exactly like a typed command, and is also remembered
    so the panel can show it in the bot chat under the buttons.
    """

    is_private = True
    is_group = False
    is_channel = False
    is_reply = False
    out = True

    def __init__(self, text):
        self.job = eventlog.Job()
        self.extra = []
        self.client = userbot
        self.message = _Msg(text)
        self.raw_text = self.text = text
        self.chat_id = self.sender_id = state.me.id

    def __getattr__(self, name):
        raise AttributeError(f"event.{name} is not available when a command runs from a button")

    async def edit(self, text=None, *args, **kwargs):
        return await self.job.show(text)

    async def respond(self, text=None, *args, **kwargs):
        if text:
            entry = await eventlog.post(text)
            self.extra.append(entry)
            return entry

    reply = respond

    async def get_reply_message(self):
        return None

    async def get_sender(self):
        return state.me

    get_chat = get_sender

    async def delete(self, *args, **kwargs):
        return None


def _result(ctx, cmd):
    seen, texts = set(), []
    for entry in (ctx.job.entry, *ctx.extra):
        if entry is not None and id(entry) not in seen and entry.text:
            seen.add(id(entry))
            texts.append(entry.text)
    return "\n\n".join(texts) or lang.PANEL_DONE.format(cmd=_name(cmd))


async def _show(bot, chat, msg_id, text, buttons=None):
    """Write text to the bot chat: edit the panel message, send extra parts as new messages."""
    parts = chunks(text)
    last = len(parts) - 1
    for i, part in enumerate(parts):
        keys = buttons if i == last else None
        if i == 0 and msg_id:
            try:
                await bot.edit_message(chat, msg_id, part, buttons=keys, link_preview=False)
            except errors.MessageNotModifiedError:
                pass
            continue
        await bot.send_message(chat, part, buttons=keys, link_preview=False)


async def _execute(bot, chat, msg_id, cmd, args):
    ctx = ButtonCtx(f"{PREFIX}{cmd.name} {args}".strip())
    try:
        await cmd.handler(ctx, args)
    except Exception as exc:
        log.exception("command failed from a button: %s", cmd.name)
        try:
            ctx.extra.append(await eventlog.fail(
                lang.CMD_FAILED.format(cmd=f"{PREFIX}{cmd.name}"), exc, ctx.job.entry, lang.CMD_FAILED_HINT
            ))
        except Exception:
            log.exception("could not report the failure")
    try:
        await _show(bot, chat, msg_id, _result(ctx, cmd), _after(cmd))
    except Exception:
        log.exception("could not show the result in the bot chat")


async def _start_run(bot, chat, msg_id, cmd, args):
    """Mark the panel message as running, then run the command without blocking the bot."""
    try:
        await _show(bot, chat, msg_id, lang.PANEL_RUNNING.format(cmd=_name(cmd)))
    except Exception:
        log.warning("could not show the running state")
    task = asyncio.create_task(_execute(bot, chat, msg_id, cmd, args))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


# ---- text input: "run with text" and /run -----------------------------------------

def clear():
    global _pending
    _pending = None


async def take_text(event):
    """Called by the bot router for a plain (non-slash) owner message. True when it was used."""
    global _pending
    pend, _pending = _pending, None
    if pend is None or time.time() > pend["until"]:
        return False
    text = (event.raw_text or "").strip()
    if not text:
        _pending = pend  # keep waiting: the message had no text (a sticker, a photo...)
        await event.respond(lang.PANEL_ASK_EMPTY)
        return True
    cmd = _find_cmd(pend["cid"])
    if cmd is None:
        text, buttons = _gone()
        await _show(event.client, pend["chat"], pend["msg"], text, buttons)
        return True
    await _start_run(event.client, pend["chat"], pend["msg"], cmd, text)
    return True


async def run_text(event, text):
    """`/run <command text>`: run any command, with arguments, from the bot chat."""
    text = text.strip()
    if text.startswith(PREFIX):
        text = text[len(PREFIX):].strip()
    hit = registry.match(text) if text else None
    if hit is None:
        if text:
            await event.respond(lang.PANEL_RUN_UNKNOWN)
        else:
            await event.respond(lang.PANEL_RUN_USAGE.format(
                example=html.escape(f"{lang.CMD_STATUS}"), sample=html.escape(lang.CMD_SYSTEM_STATUS)
            ))
        return
    cmd, args = hit
    sent = await event.respond(lang.PANEL_RUNNING.format(cmd=_name(cmd)))
    await _start_run(event.client, event.chat_id, sent.id, cmd, args)


# ---- callbacks --------------------------------------------------------------------

async def _edit(event, text, buttons=None):
    try:
        await event.edit(text, buttons=buttons, link_preview=False)
    except errors.MessageNotModifiedError:
        pass


async def _answer(event, text=None, alert=False):
    try:
        await event.answer(text, alert=alert)
    except Exception:
        pass  # the query may already be old: the screen still updates


async def on_callback(event):
    """Handler of every button press of the bot. Only the owner gets a reaction."""
    if event.sender_id != state.me.id:
        return
    try:
        await _dispatch(event, (event.data or b"").decode("utf-8", "ignore"))
    except Exception:
        log.exception("button failed")
        await _answer(event, lang.PANEL_ERROR, alert=True)


async def _dispatch(event, data):
    global _pending
    kind, _, rest = data.partition(":")
    if kind == "n":
        await _answer(event)
        return
    if kind == "m":
        _pending = None
        await _answer(event)
        text, buttons = main(int(rest or 0))
        await _edit(event, text, buttons)
        return
    if kind == "g":
        _pending = None
        gid, _, page = rest.partition(":")
        await _answer(event)
        shown = group_menu(gid, int(page or 0))
        text, buttons = shown if shown else _gone()
        await _edit(event, text, buttons)
        return

    cmd = _find_cmd(rest)
    if cmd is None:
        await _answer(event)
        text, buttons = _gone()
        await _edit(event, text, buttons)
        return

    if kind == "c" and cmd.confirm:
        await _answer(event)
        await _edit(event, lang.PANEL_CONFIRM.format(cmd=_name(cmd)), [[
            Button.inline(lang.PANEL_YES, data=f"y:{rest}"),
            Button.inline(lang.PANEL_NO, data=f"g:{_id(cmd.group)}:0"),
        ]])
    elif kind in ("c", "y"):
        _pending = None
        await _answer(event, lang.PANEL_ANSWER_RUNNING)
        await _start_run(event.client, event.chat_id, event.message_id, cmd, "")
    elif kind == "a" and not cmd.confirm:
        _pending = {
            "cid": rest,
            "chat": event.chat_id,
            "msg": event.message_id,
            "until": time.time() + ASK_TTL,
        }
        await _answer(event)
        await _edit(event, lang.PANEL_ASK.format(cmd=_name(cmd), minutes=ASK_TTL // 60), [[
            Button.inline(lang.PANEL_NO, data=f"g:{_id(cmd.group)}:0"),
        ]])
    else:
        await _answer(event)
