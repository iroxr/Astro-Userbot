# Astro Userbot
# © جميع الحقوق محفوظة
import html
import os
import platform
import random
import re
import time

from telethon import __version__ as TELETHON_VERSION
from telethon.tl.functions import PingRequest

from . import PLUGINS_DIR, PREFIX, bot, client, eventlog, lang, panel, registry, runtime, settings, state, storage, ui, vault
from . import errors as err
from .registry import bot_command, command, group

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.py$")
MAX_PLUGIN_BYTES = 512 * 1024

group(lang.GROUP_SYSTEM, order=900)


# ---- menus (built from whatever is registered) -------------------------------

def _title(name):
    return f"{lang.MENU_WORD} {name}"


@command(lang.CMD_MENU, hidden=True)
async def menu_root(event, args):
    rows = [f"<code>{PREFIX}{html.escape(_title(g))}</code>" for g in registry.groups()]
    await event.edit(ui.frame(lang.ROOT_TITLE, rows))


@command(lang.MENU_WORD, hidden=True)
async def menu_group(event, args):
    name = " ".join(args.split())
    if not name:
        await menu_root(event, "")
        return
    cmds = registry.by_group(name)
    if not cmds:
        await event.edit(lang.NOT_FOUND.format(menu=f"{PREFIX}{lang.CMD_MENU}"))
        return
    rows = [f"<code>{PREFIX}{html.escape(c.name)}</code>" for c in cmds]
    await event.edit(ui.frame(f"{lang.GROUP_TITLE} {name}", rows))


# ---- system ----------------------------------------------------------------

@command(lang.CMD_ADD_FILE, "Add a plugin file", order=10, keep=True)
async def add_file(event, args):
    msg = event.message
    if not msg.file:
        reply = await event.get_reply_message()
        msg = reply if reply is not None and reply.file else None
    if msg is None:
        await event.edit(lang.ADD_ATTACH)
        return

    name = os.path.basename(args.strip() or msg.file.name or "")
    if name and not name.endswith(".py"):
        name += ".py"
    if not NAME_RE.match(name):
        await event.edit(lang.ADD_BAD_NAME.format(name=html.escape(name or "-"), example="<code>name.py</code>"))
        return
    size = msg.file.size or 0
    if size > MAX_PLUGIN_BYTES:
        await event.edit(lang.ADD_TOO_BIG.format(size=size // 1024, limit=MAX_PLUGIN_BYTES // 1024))
        return

    await event.edit(lang.ADD_CHECKING.format(name=html.escape(name)))
    data = await msg.download_media(file=bytes)
    try:
        compile(data.decode("utf-8"), name, "exec")
    except UnicodeDecodeError:
        await event.edit(lang.ADD_REJECTED.format(name=html.escape(name), reason=lang.ADD_UTF8))
        return
    except SyntaxError as exc:
        reason = lang.ADD_SYNTAX.format(line=exc.lineno or "?", text=html.escape(str(exc.msg)))
        await event.edit(lang.ADD_REJECTED.format(name=html.escape(name), reason=reason))
        return

    local = PLUGINS_DIR / name
    existed = local.exists()
    await event.edit(lang.ADD_SAVING.format(name=html.escape(name)))
    try:
        await storage.write(f"plugins/{name}", data, f"plugin: {name}")
    except Exception as exc:
        await eventlog.fail(lang.ADD_SAVE_FAILED.format(name=html.escape(name)), exc, event.job.entry)
        return
    local.write_bytes(data)
    text = lang.ADD_UPDATED if existed else lang.ADD_ADDED
    await event.edit(text.format(name=f"<code>{html.escape(name)}</code>", update=f"{PREFIX}{lang.CMD_UPDATE}"))


@command(lang.CMD_UPDATE, "Pull plugins and restart", order=20, confirm=True)
async def update(event, args):
    await event.edit(lang.UPDATING)
    try:
        changed, total = await storage.sync_plugins()
    except Exception as exc:
        hint = lang.UPDATE_ABORT
        await eventlog.fail(lang.UPDATE_FAILED, exc, event.job.entry, hint)
        return
    if changed:
        names = "\n".join(f"• <code>{html.escape(n)}</code>" for n in changed)
        text = lang.UPDATE_SYNCED.format(changed=len(changed), total=total) + "\n" + names
    else:
        text = lang.UPDATE_NOTHING
    await event.edit(text + "\n\n" + lang.RESTARTING)
    await runtime.restart(event, "update")


@command(lang.CMD_RESTART, "Restart the bot", order=30, confirm=True)
async def restart(event, args):
    await event.edit(lang.RESTARTING)
    await runtime.restart(event, "restart")


def _hours(seconds):
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


async def _ping_ms():
    start = time.perf_counter()
    await client(PingRequest(ping_id=random.getrandbits(32)))
    return (time.perf_counter() - start) * 1000


def _account_name():
    me = state.me
    return " ".join(p for p in (me.first_name, me.last_name) if p) or me.username or "Userbot"


async def status_text():
    ping = await _ping_ms()
    link = settings.get("core", "group_link") or os.getenv("GROUP_LINK")
    title = "𝐀𝐬𝐭𝐫𝐨 𝐈𝐬 𝐖𝐨𝐫𝐤𝐢𝐧𝐠"
    if link:
        title = f'<a href="{html.escape(link, quote=True)}">{title}</a>'
    name = f'<a href="tg://user?id={state.me.id}">{html.escape(_account_name())}</a>'
    return (
        f"⋆ ✦ {title} ✓ ✦ ⋆\n\n"
        f"⊛ 𝐍𝐚𝐦𝐞 ↬ {name}\n"
        f"⊛ 𝐏𝐲𝐭𝐡𝐨𝐧 ↬ {platform.python_version()}\n"
        f"⊛ 𝐕𝐞𝐫𝐬𝐢𝐨𝐧 ↬ {TELETHON_VERSION}\n"
        f"⊛ 𝐔𝐩𝐭𝐢𝐦𝐞 ↬ {_hours(time.time() - state.started)}\n"
        f"⊛ 𝐏𝐢𝐧𝐠 ↬ {ping:.2f} ms\n"
        f"⊛ 𝐒𝐞𝐭𝐮𝐩 ↬ {settings.get('core', 'setup_date', '-')}\n\n"
        f"╰─ 𓆩 Astro Userbot 𓆪 ─╯\n\n"
        + lang.HELP_LINE.format(cmd=f"<code>{PREFIX}{lang.CMD_MENU}</code>")
    )


@command(lang.CMD_STATUS, "Show bot status", order=40)
async def status(event, args):
    await event.edit(await status_text())


@command(lang.CMD_SYSTEM_STATUS, "Detailed system status", order=50)
async def system_status(event, args):
    pid, problem = eventlog.info()
    rows = [
        (lang.SYS_STATE, lang.SYS_RUNNING),
        (lang.SYS_UPTIME, ui.span(time.time() - state.started)),
        (lang.SYS_EVENTS, lang.SYS_EVENTS_OK + f" <code>{pid}</code>" if pid and not problem else lang.SYS_EVENTS_BAD),
    ]
    if problem:
        rows.append((lang.LBL_REASON, html.escape(problem)))
    vid, vproblem = vault.info()
    rows.append((lang.SYS_VAULT, lang.SYS_VAULT_OK + f" <code>{vid}</code>" if vid and not vproblem else lang.SYS_VAULT_BAD))
    if vproblem:
        rows.append((lang.LBL_REASON, html.escape(vproblem)))
    if not bot.enabled():
        rows.append((lang.SYS_BOT, lang.SYS_BOT_OFF))
    elif bot.running():
        rows.append((lang.SYS_BOT, lang.SYS_BOT_ON.format(username=f"@{html.escape(bot.username or '?')}")))
        rows.append((lang.SYS_BOT_OWNER, lang.SYS_BOT_OWNER_OK if bot.linked() else lang.SYS_BOT_OWNER_NO))
    else:
        rows.append((lang.SYS_BOT, lang.SYS_BOT_BAD))
        if bot.error is not None:
            rows.append((lang.LBL_REASON, html.escape(err.reason(bot.error))))
    rows.append((lang.SYS_SETTINGS, lang.SYS_PENDING if settings.pending() else lang.SYS_SAVED))
    rows.append((lang.SYS_LAST_SAVE, ui.ago(settings.last_flush)))
    if settings.last_error is not None:
        rows.append((lang.SYS_SAVE_ERROR, html.escape(err.reason(settings.last_error))))
    rows.append((lang.SYS_COMMANDS, sum(len(v) for v in registry.by_plugin().values())))
    rows.append((lang.SYS_PLUGINS, len(state.loaded)))
    rows += [f"• {lang.SYS_PLUGIN_ROW.format(name=html.escape(n), count=c)}" for n, c in sorted(state.loaded.items())]
    if state.failed:
        rows.append((lang.SYS_FAILED, len(state.failed)))
        rows += [f"• <code>{html.escape(n)}</code>: {html.escape(r)}" for n, r in state.failed]
    await event.edit(ui.card(lang.SYS_TITLE, rows))


# ---- companion bot (only reachable when BOT_TOKEN is set) -------------------------

@bot_command("start", lang.BOT_DESC_START)
async def bot_start(event, args):
    _, buttons = panel.main()
    await event.respond(lang.BOT_WELCOME.format(name=html.escape(_account_name())), buttons=buttons)


@bot_command("menu", lang.BOT_DESC_MENU)
async def bot_menu(event, args):
    text, buttons = panel.main()
    await event.respond(text, buttons=buttons)


@bot_command("run", lang.BOT_DESC_RUN)
async def bot_run(event, args):
    await panel.run_text(event, args)


@bot_command("status", lang.BOT_DESC_STATUS)
async def bot_status(event, args):
    await event.respond(await status_text(), link_preview=False)


@bot_command("commands", lang.BOT_DESC_LIST)
async def bot_commands_list(event, args):
    rows = [
        f"/{c.name}" + (f" — {html.escape(c.desc)}" if c.desc else "")
        for c in registry.bot_commands.values()
    ]
    await event.respond(ui.frame(lang.BOT_LIST_TITLE, rows))
