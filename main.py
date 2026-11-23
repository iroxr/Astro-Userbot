# Astro Userbot
# © جميع الحقوق محفوظة
import asyncio
import logging
import os
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("astro")

REQUIRED = ("API_ID", "API_HASH", "SESSION", "GITHUB_TOKEN", "GITHUB_REPO")


async def run():
    from core import bot, client, eventlog, keepalive, lang, loader, registry, runtime
    from core import settings, state, storage
    import core.dispatcher  # noqa: F401

    await keepalive.start_server()
    sync_error = None
    try:
        await storage.sync_plugins()
    except Exception as exc:
        sync_error = exc
        log.exception("plugin sync failed")
    await settings.load()
    if not settings.get("core", "setup_date"):
        settings.set("core", "setup_date", date.today().isoformat())

    failed = loader.load_all()

    await client.connect()
    if not await client.is_user_authorized():
        sys.exit("SESSION is invalid or expired")
    state.me = await client.get_me()
    await eventlog.ensure()

    problems = []
    if sync_error is not None:
        problems.append((lang.UPDATE_FAILED, sync_error, lang.UPDATE_ABORT))
    try:
        await bot.start()
    except Exception as exc:
        log.exception("companion bot failed to start")
        problems.append((lang.BOT_START_FAILED, exc, lang.BOT_START_HINT))
    for hook in list(registry.start_hooks):
        try:
            await hook()
        except Exception as exc:
            log.exception("start hook failed")
            name = (getattr(hook, "__module__", "") or "").split(".")[-1] or "?"
            problems.append((lang.HOOK_FAILED.format(name=name), exc, None))

    await runtime.announce_start()
    for text in failed:
        await eventlog.post(text)
    for title, exc, hint in problems:
        await eventlog.fail(title, exc, hint=hint)

    log.info("online as %s", state.me.id)
    try:
        await client.run_until_disconnected()
    finally:
        await settings.flush()


if __name__ == "__main__":
    missing = [k for k in REQUIRED if not os.getenv(k)]
    if missing:
        sys.exit("Missing env: " + ", ".join(missing))
    asyncio.run(run())
