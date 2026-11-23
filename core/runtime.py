# Astro Userbot
# © جميع الحقوق محفوظة
import asyncio
import json
import logging
import os
import sys
import time

from . import DATA_DIR, PREFIX, bot, client, eventlog, lang, settings, state, storage

log = logging.getLogger("astro.runtime")

MARK = DATA_DIR / "restart.json"


async def restart(event, kind="restart"):
    """Write the restart marker, flush settings and re-exec the process."""
    job = getattr(event, "job", None)
    entry = job.entry if job is not None else None
    if entry is None:
        entry = await eventlog.post(lang.RESTARTING)
    info = {"t": time.time(), "kind": kind, "chat": entry.chat, "msg": entry.msg_id}
    MARK.write_text(json.dumps(info))
    await settings.flush()
    for task in list(state.tasks):
        task.cancel()
    if state.tasks:
        await asyncio.gather(*state.tasks, return_exceptions=True)
    await bot.stop()
    try:
        await asyncio.wait_for(client.disconnect(), 5)
    except Exception:
        pass
    try:
        await storage.close()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable, *sys.argv])


def _marker():
    if not MARK.exists():
        return None
    try:
        info = json.loads(MARK.read_text())
    except Exception:
        info = None
    try:
        MARK.unlink()
    except OSError:
        pass
    return info


async def announce_start():
    """After a restart: finish the pending message, then send the status card."""
    from . import builtin

    info = _marker()
    if info:
        text = lang.UPDATE_DONE if info.get("kind") == "update" else lang.RESTART_DONE
        text += f"\n{lang.TOOK}: {time.time() - info['t']:.1f} {lang.SECONDS}"
        entry = None
        if info.get("chat") is not None and info.get("msg"):
            entry = await eventlog.Entry.attach(info["chat"], info["msg"])
        if entry is not None:
            await entry.update(text)
        else:
            await eventlog.post(text)
    else:
        await eventlog.post(lang.START_DONE)
    try:
        await eventlog.post(await builtin.status_text())
    except Exception as exc:
        log.exception("status card failed")
        await eventlog.fail(lang.CMD_FAILED.format(cmd=f"{PREFIX}{lang.CMD_STATUS}"), exc)
