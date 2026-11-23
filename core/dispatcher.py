# Astro Userbot
# © جميع الحقوق محفوظة
import logging

from telethon import events

from . import PREFIX, client, eventlog, lang, registry

log = logging.getLogger("astro.dispatch")


class Ctx:
    """The event handed to command handlers.

    Everything is delegated to the real Telethon event, except the reply methods:
    they write to the events channel instead of editing the command message.
    """

    def __init__(self, event, job):
        self._event = event
        self.job = job

    def __getattr__(self, name):
        return getattr(self._event, name)

    async def edit(self, text=None, *args, **kwargs):
        return await self.job.show(text)

    async def respond(self, text=None, *args, **kwargs):
        if text:
            return await eventlog.post(text)

    reply = respond


async def _drop(event):
    try:
        await event.delete()
    except Exception as exc:
        log.warning("could not delete the command message: %s", type(exc).__name__)


@client.on(events.NewMessage(outgoing=True))
async def route(event):
    text = event.raw_text
    if not text or not text.startswith(PREFIX):
        return
    hit = registry.match(text[len(PREFIX):])
    if hit is None:
        return
    cmd, args = hit
    job = eventlog.Job()
    ctx = Ctx(event, job)
    if event.is_reply:
        try:
            await event.get_reply_message()  # cache it before the command message disappears
        except Exception:
            pass
    if not cmd.keep:
        await _drop(event)
    try:
        await cmd.handler(ctx, args)
    except Exception as exc:
        log.exception("command failed: %s", cmd.name)
        await eventlog.fail(
            lang.CMD_FAILED.format(cmd=f"{PREFIX}{cmd.name}"), exc, job.entry, lang.CMD_FAILED_HINT
        )
    finally:
        if cmd.keep:
            await _drop(event)
