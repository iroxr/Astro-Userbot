# Astro Userbot — Plugin Guide

This file is the complete reference for writing plugins for **Astro Userbot**.
It is written for both humans and AI models. If you are an AI model asked to write a plugin,
read this whole file first, then produce **one self-contained `.py` file** that follows every rule below.

The core ships with **no plugins**. Every feature is a single file in `plugins/`.

---

## 1. How the bot works (the 60-second version)

- Telethon userbot running as the owner's own Telegram account.
- A plugin is one file in `plugins/`. The loader imports every `plugins/*.py` (except files starting with `_`) at startup.
- Importing the file is how it registers itself: decorators add commands, listeners and start hooks.
- If the file raises **any** exception while importing, everything it registered is rolled back, the plugin is marked failed, an Arabic error is posted to the events channel, and the rest of the bot keeps running.
- Commands are **outgoing messages** that start with the prefix (default `.`). Example: `.example on`.
- The command message is **deleted immediately**. All output goes to a Telegram channel called **`قناة الاحداث`** (the events channel). The bot finds it by name or creates it.
- Menus are generated automatically from registered commands. Nothing needs to be edited in the core when a plugin is added or removed.
- Persistent data is stored in `data/settings.json` in the GitHub repo through `scope(...)`. The host filesystem is ephemeral, so **never rely on local files**.

Startup order (matters for what you may do at import time):

1. keepalive HTTP server starts
2. `plugins/` is synced from GitHub
3. settings are loaded from GitHub (`scope()` data is available)
4. **all plugin files are imported** (client is **not connected yet**)
5. client connects, events channel is ensured
6. the companion bot starts if `BOT_TOKEN` is set, then `@on_start` hooks run (client and bot are connected here)
7. start message and status card are posted

---

## 2. The rules (checklist)

A plugin is correct only if **all** of these hold:

1. **One file**, name matches `^[A-Za-z][A-Za-z0-9_]*\.py$`, under 512 KB, UTF-8.
2. First two lines are exactly:
   ```python
   # Astro Userbot
   # © جميع الحقوق محفوظة
   ```
3. Imports from the core come **only** from `core.api` (plus `core.state` if you need `state.me` or `state.tasks`). Never import from other plugins. Never edit core files.
4. Calls `group("<Arabic menu name>")` once, at the top level, before any `@command`.
5. Has a **status command** named `حالة <feature>` that shows detailed rows (see section 8).
6. **All user-facing text is Arabic**, defined as constants at the top of the file (see section 9). No hard-coded strings inside handlers.
7. Every command handler has the signature `async def handler(event, args)`.
8. Output is written only with `event.edit(...)` / `notify(...)` / `fail(...)`. Never `print`.
9. Messages use **HTML** parse mode. Escape any user/external text with `html.escape` (or `ui.esc`).
10. Errors are reported with `fail(title, exc, event.job.entry, hint)` so the cause is shown in Arabic. Never swallow an exception silently and never let one escape from a listener or background task without handling it.
11. State that must survive a restart goes in `scope("<plugin name>")`. Lists/dicts are **re-assigned with `store.set`** after changing them.
12. Everything is `async`. No blocking calls (`time.sleep`, `requests`, heavy CPU loops). Use `asyncio.sleep`, `aiohttp`, `asyncio.to_thread`.
13. Command names are unique across **all** plugins and the core. Use feature-specific names.
14. No code at import time that needs the network or the connected client. Use `@on_start` for that.
15. Only dependencies in `requirements.txt` (`telethon`, `aiohttp`, `tzdata`) and the standard library. If a new package is truly needed, say so explicitly in your reply so it can be added to `requirements.txt`.

---

## 3. The only import you need: `core.api`

```python
from core.api import PREFIX, bot_command, bot_notify, client, command, events, fail, group, listener, notify, on_start, reason, scope, ui
```

| Name | What it is |
|------|------------|
| `PREFIX` | command prefix string, default `"."` |
| `client` | the shared connected Telethon `TelegramClient` (HTML parse mode by default) |
| `events` | `telethon.events` |
| `group(name, order=100)` | sets the plugin's menu name; call once at top level |
| `command(name, desc="", aliases=(), order=100, hidden=False, group=None, keep=False)` | decorator, registers a command |
| `bot_command(name, desc="")` | decorator, registers a command of the private companion bot (section 15) |
| `bot_notify(text)` | sends a message to the owner through the companion bot (section 15) |
| `listener(builder)` | decorator, registers a Telethon event handler, e.g. `@listener(events.NewMessage(incoming=True))` |
| `on_start` | decorator, async hook that runs once after the client connects |
| `scope(ns)` | persistent key-value store, returns an object with `get(key, default)`, `set(key, value)`, `delete(key)` |
| `notify(text)` | writes a **new** message to the events channel, returns an `Entry` |
| `fail(title, exc, entry=None, hint=None)` | writes a detailed Arabic failure (title, cause, technical detail, hint). If `entry` is given, edits it instead of posting a new one |
| `reason(exc)` | short Arabic cause for an exception (use to store "last failure reason" in stats) |
| `describe(exc, hint=None)` | the Arabic cause/details/hint block as text |
| `kind(exc)` | class name of the most specific known error, for grouping failures |
| `ui` | formatting helpers (section 7) |

Extra, allowed when needed: `from core import state` → `state.me` (the logged-in user, available after connect), `state.tasks` (list to append your background `asyncio.Task`s to).

---

## 4. Commands

```python
@command("example on", order=10)
async def example_on(event, args):
    ...
```

- `name` is matched against the text after the prefix. Words are separated by single spaces; matching is whole-word. **The longest matching name wins**, so `example on` beats `example`.
- `args` is everything after the command name, stripped. Empty string if none.
- `order` sorts the command inside its menu (lower first).
- `aliases=("x", "y")` registers extra names for the same handler.
- `hidden=True` hides it from menus and counts (still works).
- `group="..."` overrides the plugin's group for one command.
- `keep=True` keeps the command message until the handler finishes (required when the command message carries a file/media you need to download). It is deleted afterwards.
- Names are Arabic by convention, without hamza forms and diacritics (`اضافة`, not `إضافة`). A plugin author may choose English names if the owner asks.

### What `event` is inside a command

`event` is a thin wrapper (`Ctx`) around the real Telethon event. Everything is delegated (`event.message`, `event.chat_id`, `event.is_reply`, `event.is_private`, `await event.get_reply_message()`, …) **except**:

- `await event.edit(text)` — does **not** edit the command message (it is already deleted). The first call posts a message to the events channel; **later calls update that same message**. Use it for progress → result flows.
- `await event.respond(text)` / `event.reply(text)` — post a **new** message to the events channel.
- `event.job.entry` — the `Entry` of that progress message (or `None` before the first `edit`). Pass it to `fail(...)` so the failure replaces the progress message.

To send something **into the chat where the command was typed**, use the client explicitly:

```python
await client.send_message(event.chat_id, "text", reply_to=reply_msg_id)
```

The command message is gone by the time the handler runs. Reading the replied-to message with `await event.get_reply_message()` still works (the dispatcher caches it first).

### Dispatcher behavior you can rely on

- Only the owner's **outgoing** messages starting with the prefix are routed.
- If a handler raises, the dispatcher posts `❌ فشل تنفيذ الامر ...` with the Arabic cause. You still should handle expected failures yourself with `fail(...)` and a useful hint.

---

## 5. Persistent storage: `scope`

```python
store = scope("example")           # namespace = plugin name
store.set("enabled", True)
store.get("enabled", False)
store.delete("enabled")
```

- Data is saved to `data/settings.json` on GitHub, batched (about 3 seconds after the last change) and flushed on restart.
- Values must be **JSON serializable**. After a restart, **dict keys come back as strings** (`{5: "x"}` becomes `{"5": "x"}`), tuples become lists, sets are not allowed. Convert on load, e.g. `items = set(store.get("items", []))`.
- `store.get` returns the live object. If you mutate it in place nothing is saved. Always call `store.set(key, value)` again:
  ```python
  items = store.get("items", [])
  items.append(x)
  store.set("items", items)
  ```
- Read stored data at module level (import time) is fine: settings are loaded before plugins are imported.
- Keep each namespace to the plugin's own name. Never read another plugin's namespace.
- Do not store secrets or large blobs.

---

## 6. Listeners, start hooks and background tasks

### Listener

```python
@listener(events.NewMessage(incoming=True))
async def on_message(event):
    if not event.is_private or not store.get("enabled", False):
        return
    ...
```

- Here `event` is the **raw Telethon event** (not `Ctx`). `event.edit` really edits the message; to log something use `notify(...)` / `fail(...)`.
- Always return early on the cheap checks first (enabled flag, chat type). Listeners run for every matching message.
- Wrap risky work in `try/except` and report with `fail(...)`. An unhandled exception inside a listener is only logged to the server console and the owner never sees it.

### Start hook and background loop

```python
import asyncio
from core import state

async def _loop():
    while True:
        try:
            ...  # do the work
        except Exception as exc:
            await fail("❌ ...", exc)
        await asyncio.sleep(300)

@on_start
async def start():
    state.tasks.append(asyncio.create_task(_loop()))
```

- `@on_start` runs after the client is connected. Start loops here, not at import time.
- A loop must never die from an exception: catch inside the loop body.
- Handle Telegram flood limits: catch `telethon.errors.FloodWaitError` and `await asyncio.sleep(exc.seconds + 1)`.

### Resolving chats by id

Private channel/group ids may fail to resolve right after a restart until dialogs are cached. Use this helper pattern:

```python
async def _resolve(ref):
    try:
        return await client.get_input_entity(ref)
    except ValueError:
        await client.get_dialogs()
        return await client.get_input_entity(ref)
```

---

## 7. `ui` helpers

| Helper | Purpose |
|--------|---------|
| `ui.card(title, rows)` | status card. A row is `(label, value)`, a plain string, or `""` for a blank line. Values must already be HTML-safe |
| `ui.frame(title, rows)` | numbered list card (used for menus) |
| `ui.flag(bool)` | `✅ مفعل` / `⛔ متوقف` |
| `ui.esc(x)` | `html.escape(str(x))` |
| `ui.span(seconds)` | Arabic duration, e.g. `5 دقيقة`, `2 ساعة و10 دقيقة` |
| `ui.stamp(ts)` | formatted local time from a unix timestamp |
| `ui.ago(ts)` | `2026-11-23 13:40 (قبل 5 دقيقة)`, or `لم يحدث بعد` if `ts` is falsy |
| `ui.until(ts)` | same, for a future time |
| `ui.clip(rows, limit)` | shortens a long list and appends `... (+N)` |
| `ui.TZ` | timezone used for display (`POST_TZ` env var, default `Asia/Jerusalem`) |

Telegram messages are limited to 4096 chars. The events channel splits long text automatically at ~3900, but keep status cards compact (use `ui.clip` for long lists).

When mentioning a command inside a message, write it with the prefix and in `<code>` so it is tappable:
`f"<code>{PREFIX}{CMD}</code>"`.

---

## 8. The status command (mandatory)

Every plugin has a command named `حالة <feature>`. It shows enough rows that the owner can tell whether the feature works without reading logs. Typical rows:

- whether the feature is on/off (`ui.flag`)
- key configuration values
- counters since last start (sent, failed)
- last activity time (`ui.ago`)
- last failure reason (only if there was one)
- a one-line explanation of the rule/purpose

```python
@command(STATUS, order=90)
async def status(event, args):
    rows = [
        (S_STATE, ui.flag(store.get("enabled", False))),
        (S_COUNT, stats["count"]),
        (S_LAST, ui.ago(stats["last"])),
    ]
    if stats["reason"]:
        rows.append((S_LAST_FAIL, html.escape(stats["reason"])))
    await event.edit(ui.card(S_TITLE, rows), link_preview=False)
```

Keep runtime counters in a module-level `stats` dict (they reset on restart, which is expected and the card says "since last start"). Persist only what must survive restarts.

---

## 9. Text and naming conventions

- All messages are **Arabic**, short and direct, in a simple colloquial (Levantine/Palestinian-leaning) tone: `ما في`, `رح`, `مش`, `جرب مرة ثانية`.
- Write Arabic without hamza forms and without diacritics, matching the core: `اضافة`, `اعادة`, `ايقاف`, `الاوامر`.
- Define strings as constants at the top of the file with fixed prefixes:
  - `T_*` command/notification texts
  - `S_*` status card labels
  - `R_*` report labels
  - plain upper-case names (`ON`, `OFF`, `STATUS`, `SET`, …) for **command names**
- Status emoji: `✅` success, `❌` failure, `⏳` in progress, `⚠️` warning, `ℹ️` info, `⛔` stopped, `↩️` automatic reply sent.
- Failure messages have three parts: what failed (title), `السبب:` (cause), `الحل:` (hint). `fail()` builds the last two for you.
- Usage errors show the correct syntax: `"الصيغة الصحيحة:\n<code>{cmd} ...</code>"`.
- Menu name (`group(...)`) is a short Arabic noun. The owner opens it with `.اوامر <group name>`; `.الاوامر` lists all groups.
- Standard command set for a toggleable feature: `<feature> تفعيل`, `<feature> ايقاف`, `حالة <feature>`.
- Logger (optional, for server console only): `logging.getLogger("astro.<plugin>")`.

---

## 10. Minimal plugin (copy and adapt)

`plugins/_template.py` is the same thing. Files starting with `_` are never loaded.

```python
# Astro Userbot
# © جميع الحقوق محفوظة
import html

from core.api import PREFIX, command, fail, group, scope, ui

ON = "مثال تفعيل"
OFF = "مثال ايقاف"
SET = "مثال رسالة"
STATUS = "حالة مثال"

T_ON = "✅ تم تفعيل المثال"
T_OFF = "⛔ تم ايقاف المثال"
T_SET_USAGE = "الصيغة الصحيحة:\n<code>{cmd} النص</code>"
T_SET = "✅ تم حفظ النص: {text}"

S_TITLE = "حالة مثال"
S_STATE = "الحالة"
S_TEXT = "النص المحفوظ"
S_NO_TEXT = "⚠️ غير محدد"

group("مثال")
store = scope("example")


@command(ON, order=10)
async def example_on(event, args):
    store.set("enabled", True)
    await event.edit(T_ON)


@command(OFF, order=20)
async def example_off(event, args):
    store.set("enabled", False)
    await event.edit(T_OFF)


@command(SET, order=30)
async def example_set(event, args):
    if not args:
        await event.edit(T_SET_USAGE.format(cmd=f"{PREFIX}{SET}"))
        return
    store.set("text", args)
    await event.edit(T_SET.format(text=html.escape(args)))


@command(STATUS, order=90)
async def example_status(event, args):
    text = store.get("text")
    rows = [
        (S_STATE, ui.flag(store.get("enabled", False))),
        (S_TEXT, html.escape(text) if text else S_NO_TEXT),
    ]
    await event.edit(ui.card(S_TITLE, rows))
```

## 11. Fuller example: listener + stats + failure handling

```python
# Astro Userbot
# © جميع الحقوق محفوظة
import html
import time

from telethon import utils

from core.api import PREFIX, client, command, events, fail, group, listener, notify, reason, scope, ui

ON = "ترحيب تفعيل"
OFF = "ترحيب ايقاف"
STATUS = "حالة الترحيب"

T_ON = "✅ تم تفعيل الترحيب"
T_OFF = "⛔ تم ايقاف الترحيب"
T_SENT = "👋 تم ارسال الترحيب الى {name}"
T_FAILED = "❌ فشل ارسال الترحيب الى {name}"
T_FAILED_HINT = "تأكد ان الشخص ما حاظر حسابك"

S_TITLE = "حالة الترحيب"
S_STATE = "الحالة"
S_SENT = "الترحيبات المرسلة منذ آخر تشغيل"
S_LAST = "آخر ترحيب"
S_FAILS = "مرات الفشل منذ آخر تشغيل"
S_LAST_FAIL = "سبب آخر فشل"
S_RULE = "الشرط"
S_RULE_TEXT = "اول رسالة من شخص جديد في الخاص"

group("الترحيب")
store = scope("welcome")
greeted = set(store.get("greeted", []))
stats = {"sent": 0, "last": 0.0, "fails": 0, "reason": None}


@command(ON, order=10)
async def welcome_on(event, args):
    store.set("enabled", True)
    await event.edit(T_ON)


@command(OFF, order=20)
async def welcome_off(event, args):
    store.set("enabled", False)
    await event.edit(T_OFF)


@command(STATUS, order=90)
async def welcome_status(event, args):
    rows = [
        (S_STATE, ui.flag(store.get("enabled", False))),
        (S_SENT, stats["sent"]),
        (S_LAST, ui.ago(stats["last"])),
        (S_FAILS, stats["fails"]),
    ]
    if stats["reason"]:
        rows.append((S_LAST_FAIL, html.escape(stats["reason"])))
    rows.append((S_RULE, S_RULE_TEXT))
    await event.edit(ui.card(S_TITLE, rows))


@listener(events.NewMessage(incoming=True))
async def on_message(event):
    if not event.is_private or not store.get("enabled", False):
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False) or sender.id in greeted:
        return
    greeted.add(sender.id)
    store.set("greeted", sorted(greeted))
    name = f'<a href="tg://user?id={sender.id}">{html.escape(utils.get_display_name(sender))}</a>'
    try:
        await client.send_message(event.chat_id, "أهلا وسهلا")
    except Exception as exc:
        stats["fails"] += 1
        stats["reason"] = reason(exc)
        await fail(T_FAILED.format(name=name), exc, hint=T_FAILED_HINT)
    else:
        stats["sent"] += 1
        stats["last"] = time.time()
        await notify(T_SENT.format(name=name))
```

---

## 12. Installing a plugin

Two ways, both end with a restart so the new plugin loads:

1. **From Telegram (no git):** send the `.py` file to any chat with the caption `.اضافة ملف` (or reply to the file with that command). The core checks the name, size and Python syntax, saves it to the GitHub repo, then run `.تحديث` to pull and restart.
2. **From the repo:** commit the file to `plugins/` on GitHub, then run `.تحديث`.

Notes:
- The syntax check catches only syntax errors. Runtime import errors are caught by the loader on restart: the plugin is rolled back and an Arabic error is posted. Fix and resend the file.
- Sending a file with the same name replaces the old version.
- To remove a plugin, delete it from `plugins/` in the repo and run `.تحديث`. Its menu and commands disappear automatically. Its data stays in `data/settings.json` under its namespace.

---

## 13. Common mistakes to avoid

| Mistake | Why it breaks | Do this instead |
|---------|---------------|-----------------|
| `await event.edit(...)` expecting the command message to change | the command message is deleted; text goes to the events channel | that is intended: use it for progress/results; use `client.send_message` to write in the chat |
| Mutating `store.get("x")` in place | not saved | call `store.set("x", value)` |
| Using int dict keys in stored dicts | become strings after restart | use string keys from the start |
| Writing files to disk for persistence | host filesystem is wiped on redeploy | use `scope()` |
| Network or `client` calls at import time | client is not connected yet | do it in `@on_start` or a command |
| `time.sleep`, `requests` | blocks the whole bot | `asyncio.sleep`, `aiohttp` |
| Markdown (`**bold**`) in messages | parse mode is HTML | `<b>`, `<code>`, `<a href="...">` |
| Putting raw user text in a message | can break HTML or inject tags | `html.escape(text)` |
| Reusing a command name from another plugin or the core | plugin fails to load with `DUP_COMMAND` | pick feature-specific names |
| Registering commands/listeners outside import time (e.g. inside a handler) | registration is only allowed while the plugin is loading | register at top level |
| Letting a background loop crash | the feature silently stops | try/except inside the loop and `fail(...)` |
| Forgetting `group(...)` | plugin fails with "no menu name" | call `group("...")` at the top |
| Hard-coded Arabic strings inside handlers | hard to maintain and diverges from the convention | constants at the top (`T_*`, `S_*`) |
| Importing another plugin | plugins can be removed at any time | duplicate the small helper instead |

---

## 14. Reserved core commands (do not reuse)

| Command | Action |
|---------|--------|
| `الاوامر` | main menu |
| `اوامر <name>` | commands of one group |
| `الحالة` | status card |
| `حالة النظام` | detailed system status |
| `اضافة ملف` | install a plugin from an attached `.py` |
| `تحديث` | pull plugins from the repo and restart |
| `اعادة تشغيل` | restart |

Bot commands reserved by the core: `/start`, `/status`, `/commands`.

---

## 15. Companion bot commands

Astro can run a second Telegram client: a **bot** created with @BotFather, enabled when the `BOT_TOKEN` environment variable is set. It is **private**: it only answers the account that runs the userbot and silently ignores everyone else. Plugins can use it, but it is optional, so a plugin must still work when the bot is disabled.

Built-in bot commands: `/start`, `/status`, `/commands`. Do not reuse those names.

### Registering a bot command

```python
from core.api import bot_command

@bot_command("ping", "Check that the bot answers")
async def bot_ping(event, args):
    await event.respond("pong")
```

- `name`: lowercase English letters, digits and `_`, starts with a letter, max 32 chars (Telegram's rule). Invalid or duplicate names make the plugin fail to load.
- `desc`: short description (3-256 chars). It appears in Telegram's `/` menu and in `/commands`. Write it in Arabic like everything else.
- Handler signature is `async def handler(event, args)`. `event` is the **raw Telethon event of the bot**: reply with `await event.respond(text)` (HTML parse mode). `args` is the text after the command.
- Only the owner reaches the handler, so no permission check is needed inside it.
- Registered like any other decorator: at the top level of the plugin file. Removing the plugin removes its bot commands; the `/` menu refreshes on the next restart.
- Unhandled exceptions are reported to the owner in the bot chat and in the events channel. Still prefer handling expected failures yourself.

### Pushing a message to the owner

```python
from core.api import bot_notify, fail, notify

try:
    await bot_notify("✅ تم ...")
except Exception as exc:
    await fail("❌ تعذر ارسال اشعار البوت", exc)
    await notify("✅ تم ...")   # fall back to the events channel
```

- `bot_notify` raises a readable Arabic error when the bot is not enabled (no `BOT_TOKEN`) or when the owner has not sent `/start` to the bot yet (Telegram does not allow bots to write first). Always catch it and fall back to `notify(...)`.
- It is meant for important alerts. Routine command output still goes through `event.edit(...)` to the events channel.

### Status

The system status card (`.حالة النظام`) shows whether the bot is enabled, connected and linked to the account. A plugin that depends on the bot should mention that in its own `حالة <feature>` rows.

---

## 16. Prompt to give an AI model

Paste this together with this guide:

> You are writing a plugin for Astro Userbot. Follow `PLUGIN_GUIDE.md` exactly. Output **one** complete Python file, ready to send to the bot with `.اضافة ملف`, with no explanations inside the file. Use Arabic for every user-facing message, define texts as constants at the top, include `group(...)`, the on/off commands where it makes sense, and a detailed `حالة <feature>` command. Use `scope()` for persistence, `fail()` for errors, and never import from other plugins. At the end, tell me the file name to use and list every command the plugin adds.
>
> The plugin should: *(describe the feature here)*

Before finishing, the model should verify against the checklist in section 2 and confirm the file compiles (`python -m py_compile file.py`).
