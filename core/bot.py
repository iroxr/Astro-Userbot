# Astro Userbot
# © جميع الحقوق محفوظة
"""Optional companion bot, private to the account owner.

Enabled by the BOT_TOKEN environment variable. It answers only the account that runs the
userbot and ignores everyone else. Plugins add commands with @bot_command and can message
the owner through the bot with bot_notify().
"""
import asyncio
import logging
import os
import re

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault, InputPeerUser

from . import eventlog, lang, panel, registry, settings, state
from . import errors as err
from .errors import PluginError

log = logging.getLogger("astro.bot")

TOKEN = os.getenv("BOT_TOKEN", "").strip()
RETRY_DELAY = 60  # seconds between background login attempts after a failed start
bot = None
username = None
error = None

_CMD = re.compile(r"^/([A-Za-z0-9_]+)(?:@(\w+))?(?:\s+(.*))?$", re.S)


def enabled():
    return bool(TOKEN)


def running():
    return bot is not None


def linked():
    """True once the owner has written /start to the bot (Telegram forbids bots from writing first)."""
    return bool(settings.get("core", "bot_owner"))


async def start():
    """Log the bot in, attach the router and publish the command menu."""
    global bot, username, error
    if not TOKEN:
        return
    error = None
    client = TelegramClient(
        StringSession(),
        int(os.environ["API_ID"]),
        os.environ["API_HASH"],
        connection_retries=-1,
        retry_delay=2,
    )
    client.parse_mode = "html"
    try:
        await client.start(bot_token=TOKEN)
        me = await client.get_me()
        client.add_event_handler(_route, events.NewMessage(incoming=True))
        client.add_event_handler(panel.on_callback, events.CallbackQuery())
        bot = client
        username = me.username
        await sync_menu()
    except Exception as exc:
        error = exc
        bot = None
        try:
            await client.disconnect()
        except Exception:
            pass
        raise


async def keep_trying(delay=RETRY_DELAY):
    """Background retry for a failed login (Telegram sometimes answers "internal issues").

    Runs until the bot is up, so no restart is needed once Telegram recovers.
    """
    attempts = 0
    while bot is None and TOKEN:
        await asyncio.sleep(delay)
        attempts += 1
        try:
            await start()
        except Exception as exc:
            log.warning("companion bot retry %s failed: %s", attempts, type(exc).__name__)
            continue
        log.info("companion bot is up after %s background attempt(s)", attempts)
        try:
            await eventlog.post(lang.BOT_RECOVERED.format(n=attempts))
        except Exception:
            log.exception("could not announce the bot recovery")
        return


async def stop():
    global bot
    if bot is not None:
        try:
            await asyncio.wait_for(bot.disconnect(), 5)
        except Exception:
            pass
        bot = None


async def sync_menu():
    """Publish the registered bot commands to Telegram's "/" menu. Best effort."""
    cmds = []
    for cmd in registry.bot_commands.values():
        desc = cmd.desc or cmd.name
        if len(desc) < 3:
            desc += " command"
        cmds.append(BotCommand(command=cmd.name, description=desc[:256]))
    try:
        await bot(SetBotCommandsRequest(scope=BotCommandScopeDefault(), lang_code="", commands=cmds[:100]))
    except Exception:
        log.exception("could not publish the bot command menu")


async def notify(text):
    """Send a message to the owner through the bot. Raises a readable error when it cannot."""
    if bot is None:
        raise PluginError(lang.BOT_NOT_ENABLED)
    saved = settings.get("core", "bot_owner")
    if not saved:
        raise PluginError(lang.BOT_NOT_STARTED)
    peer = InputPeerUser(user_id=int(saved[0]), access_hash=int(saved[1]))
    return await bot.send_message(peer, text, link_preview=False)


async def _remember_owner(event):
    sender = await event.get_input_sender()
    saved = [state.me.id, getattr(sender, "access_hash", 0)]
    if settings.get("core", "bot_owner") != saved:
        settings.set("core", "bot_owner", saved)


async def _route(event):
    if not event.is_private or event.sender_id != state.me.id:
        return  # private to the owner: everyone else is ignored silently
    text = (event.raw_text or "").strip()
    found = _CMD.match(text)
    if not found:
        try:
            await panel.take_text(event)  # the text a "run with text" button is waiting for
        except Exception:
            log.exception("panel text input failed")
        return
    panel.clear()
    if found[2] and username and found[2].lower() != username.lower():
        return
    try:
        await _remember_owner(event)
    except Exception:
        log.exception("could not remember the owner")
    cmd = registry.bot_commands.get(found[1].lower())
    if cmd is None:
        await event.respond(lang.BOT_UNKNOWN)
        return
    try:
        await cmd.handler(event, (found[3] or "").strip())
    except Exception as exc:
        log.exception("bot command failed: %s", cmd.name)
        title = lang.BOT_CMD_FAILED.format(cmd=f"/{cmd.name}")
        try:
            await event.respond(f"{title}\n{err.describe(exc, lang.CMD_FAILED_HINT)}")
        except Exception:
            pass
        await eventlog.fail(title, exc, hint=lang.CMD_FAILED_HINT)
