# Astro Userbot
# © جميع الحقوق محفوظة
# Files starting with an underscore are never loaded. Copy this file to start a plugin.
# Full rules and examples: see PLUGIN_GUIDE.md in the repo root.
#
# group() names this plugin's menu. The menu, its entry in the main list and its
# commands appear automatically when the plugin loads and vanish when it is removed.
#
# Rules every plugin follows:
# - event.edit(...) does not edit the command message: the command message is deleted and
#   the text goes to the events channel. Call it again to update the same log message.
# - every plugin has a status command named "حالة <feature>" with detailed rows.
# - errors are reported with fail(title, exc, event.job.entry): it prints the cause in Arabic.
from core.api import PREFIX, command, fail, group, scope, ui

ON = "example on"
OFF = "example off"
STATUS = "حالة example"

group("example")

store = scope("example")  # persisted to the GitHub repo automatically


@command(ON, order=10)
async def example_on(event, args):
    store.set("enabled", True)
    await event.edit("✅ on")


@command(OFF, order=20)
async def example_off(event, args):
    store.set("enabled", False)
    await event.edit("⛔ off")


@command(STATUS, order=30)
async def example_status(event, args):
    rows = [("example", ui.flag(store.get("enabled", False)))]
    await event.edit(ui.card("حالة example", rows))
