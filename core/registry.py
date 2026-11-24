# Astro Userbot
# © جميع الحقوق محفوظة
import re
from dataclasses import dataclass
from itertools import count

from . import client, lang
from .errors import PluginError


@dataclass
class Command:
    name: str
    group: str
    desc: str
    handler: object
    plugin: str
    order: int
    hidden: bool
    seq: int
    keep: bool = False
    confirm: bool = False


@dataclass
class BotCmd:
    name: str
    desc: str
    handler: object
    plugin: str


commands = {}
bot_commands = {}
start_hooks = []
current = None  # plugin being loaded, set by the loader

_owned = {}
_defaults = {}
_group_order = {}
_seq = count()
_patterns = None
BOT_NAME = re.compile(r"^[a-z][a-z0-9_]{0,31}$")


def _own():
    if current is None:
        raise PluginError(lang.REG_LOCKED)
    return _owned.setdefault(current, {"names": [], "handlers": [], "hooks": [], "bot": []})


def _invalidate():
    global _patterns
    _patterns = None


def _norm(text):
    return " ".join(text.split())


def group(name, order=100):
    """Set the menu group for every command of the plugin being loaded."""
    _own()
    name = _norm(name)
    _defaults[current] = name
    _group_order.setdefault(name, order)


def command(name, desc="", aliases=(), order=100, hidden=False, group=None, keep=False, confirm=False):
    def wrap(fn):
        owned = _own()
        grp = _norm(group or _defaults.get(current) or "")
        if not grp:
            raise PluginError(lang.NO_GROUP)
        _group_order.setdefault(grp, 100)
        cmd = Command(_norm(name), grp, desc, fn, current, order, hidden, next(_seq), keep, confirm)
        for key in (name, *aliases):
            key = _norm(key)
            if key in commands:
                raise PluginError(lang.DUP_COMMAND.format(name=key, plugin=commands[key].plugin))
            commands[key] = cmd
            owned["names"].append(key)
        _invalidate()
        return fn

    return wrap


def bot_command(name, desc=""):
    """Register a command of the owner's companion bot (used as /name in the bot chat)."""

    def wrap(fn):
        owned = _own()
        key = name.strip().lstrip("/").lower()
        if not BOT_NAME.match(key):
            raise PluginError(lang.BOT_BAD_NAME.format(name=name))
        if key in bot_commands:
            raise PluginError(lang.BOT_DUP.format(name=key, plugin=bot_commands[key].plugin))
        bot_commands[key] = BotCmd(key, desc, fn, current)
        owned["bot"].append(key)
        return fn

    return wrap


def listener(builder):
    def wrap(fn):
        owned = _own()
        client.add_event_handler(fn, builder)
        owned["handlers"].append((fn, builder))
        return fn

    return wrap


def on_start(fn):
    _own()["hooks"].append(fn)
    start_hooks.append(fn)
    return fn


def rollback(plugin):
    _defaults.pop(plugin, None)
    owned = _owned.pop(plugin, None)
    if not owned:
        return
    for key in owned["names"]:
        commands.pop(key, None)
    for key in owned["bot"]:
        bot_commands.pop(key, None)
    for fn, builder in owned["handlers"]:
        client.remove_event_handler(fn, builder)
    for hook in owned["hooks"]:
        if hook in start_hooks:
            start_hooks.remove(hook)
    _invalidate()


def groups():
    """Menu groups that currently have at least one visible command."""
    first = {}
    for cmd in commands.values():
        if not cmd.hidden:
            first.setdefault(cmd.group, cmd.seq)
    return sorted(first, key=lambda g: (_group_order.get(g, 100), first[g]))


def by_group(name):
    seen, out = set(), []
    for cmd in commands.values():
        if cmd.group == name and not cmd.hidden and id(cmd) not in seen:
            seen.add(id(cmd))
            out.append(cmd)
    return sorted(out, key=lambda c: (c.order, c.seq))


def match(text):
    global _patterns
    if _patterns is None:
        built = [
            (re.compile(r"\s+".join(map(re.escape, key.split())) + r"(?=\s|$)"), key)
            for key in commands
        ]
        _patterns = sorted(built, key=lambda p: -len(p[1]))
    for pattern, key in _patterns:
        found = pattern.match(text)
        if found:
            return commands[key], text[found.end():].strip()
    return None


def by_plugin():
    """Visible command names per plugin, in registration order."""
    out = {}
    seen = set()
    for cmd in sorted(commands.values(), key=lambda c: c.seq):
        if id(cmd) in seen or cmd.hidden:
            continue
        seen.add(id(cmd))
        out.setdefault(cmd.plugin, []).append(cmd.name)
    return out
