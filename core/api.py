# Astro Userbot
# © جميع الحقوق محفوظة
"""Everything a plugin needs, in one import."""
from telethon import events

from . import PREFIX, client, ui
from .errors import describe, kind, reason
from .bot import notify as bot_notify
from .eventlog import fail, post as notify
from .vault import send as vault_send
from .registry import bot_command, command, group, listener, on_start
from .settings import scope

__all__ = [
    "events", "PREFIX", "client", "command", "bot_command", "group", "listener", "on_start", "scope",
    "bot_notify", "vault_send",
    "ui", "describe", "kind", "reason", "fail", "notify",
]
