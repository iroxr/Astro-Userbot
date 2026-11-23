# Astro Userbot
# © جميع الحقوق محفوظة
import asyncio
import html
import tempfile
import time

from telethon import errors, utils

from core.api import command, events, fail, group, listener, notify, reason, scope, ui, vault_send

ON = "الذاتيات تفعيل"
OFF = "الذاتيات ايقاف"
STATUS = "حالة الذاتيات"

T_ON = "✅ تم تفعيل حفظ الذاتيات\nاي صورة او فيديو او بصمة صوتية ذاتية التدمير توصلك في الخاص رح تنحفظ في قناة التخزين"
T_OFF = "⛔ تم ايقاف حفظ الذاتيات"
T_SAVING = "⏳ جاري حفظ {kind} ذاتية من {name}..."
T_SAVED = "✅ تم حفظ {kind} ذاتية التدمير من {name}\nالمكان: قناة التخزين"
T_FAILED = "❌ فشل حفظ {kind} ذاتية التدمير من {name}"
T_FAILED_HINT = "الوسائط الذاتية بتنحذف بعد ما تنفتح، فاذا فشل الحفظ ممكن تكون ضاعت. جرب تتأكد ان الاتصال ثابت"
T_CAPTION = (
    "📥 <b>وسائط ذاتية التدمير</b>\n"
    "المرسل: {name}\n"
    "النوع: {kind}\n"
    "مدة الظهور: {ttl}\n"
    "وقت الاستلام: {time}"
)

K_PHOTO = "صورة"
K_VIDEO = "فيديو"
K_VOICE = "بصمة صوتية"
K_NOTE = "فيديو دائري"
K_FILE = "ملف"
TTL_ONCE = "مرة واحدة"

S_TITLE = "حالة الذاتيات"
S_STATE = "الحالة"
S_PLACE = "مكان الحفظ"
S_PLACE_TEXT = "قناة التخزين"
S_SESSION = "المحفوظ منذ آخر تشغيل"
S_TOTAL = "اجمالي المحفوظ"
S_LAST = "آخر حفظ"
S_FAILS = "مرات الفشل منذ آخر تشغيل"
S_LAST_FAIL = "سبب آخر فشل"
S_RULE = "ما يتم حفظه"
S_RULE_TEXT = "الصور والفيديوهات والبصمات الصوتية الذاتية التدمير في المحادثات الخاصة فقط"

ONCE = 2147483647  # Telegram uses this ttl for "view once" media

group("الذاتيات")
store = scope("selfdestruct")
stats = {"saved": 0, "last": 0.0, "fails": 0, "reason": None}
seen = set()


def _kind(msg):
    if msg.voice:
        return K_VOICE
    if msg.video_note:
        return K_NOTE
    if msg.video:
        return K_VIDEO
    if msg.photo:
        return K_PHOTO
    return K_FILE


def _ttl(media):
    ttl = getattr(media, "ttl_seconds", None) or 0
    return TTL_ONCE if ttl >= ONCE else ui.span(ttl)


def _name(user):
    full = utils.get_display_name(user) or str(user.id)
    return f'<a href="tg://user?id={user.id}">{html.escape(full)}</a>'


async def _save(msg, sender, kind):
    caption = T_CAPTION.format(
        name=_name(sender),
        kind=kind,
        ttl=_ttl(msg.media),
        time=ui.stamp(msg.date.timestamp()),
    )
    with tempfile.TemporaryDirectory() as tmp:
        for attempt in (0, 1):
            try:
                path = await msg.download_media(file=tmp + "/")
                if not path:
                    raise ValueError("empty download")
                await vault_send(
                    caption,
                    path,
                    voice_note=bool(msg.voice),
                    video_note=bool(msg.video_note),
                    supports_streaming=bool(msg.video),
                )
                return
            except errors.FloodWaitError as exc:
                if attempt:
                    raise
                await asyncio.sleep(min(exc.seconds, 60) + 1)


@command(ON, order=10)
async def selfdestruct_on(event, args):
    store.set("enabled", True)
    await event.edit(T_ON)


@command(OFF, order=20)
async def selfdestruct_off(event, args):
    store.set("enabled", False)
    await event.edit(T_OFF)


@command(STATUS, order=30)
async def selfdestruct_status(event, args):
    rows = [
        (S_STATE, ui.flag(store.get("enabled", False))),
        (S_PLACE, S_PLACE_TEXT),
        (S_SESSION, stats["saved"]),
        (S_TOTAL, store.get("total", 0)),
        (S_LAST, ui.ago(stats["last"])),
        (S_FAILS, stats["fails"]),
    ]
    if stats["reason"]:
        rows.append((S_LAST_FAIL, html.escape(stats["reason"])))
    rows.append((S_RULE, S_RULE_TEXT))
    await event.edit(ui.card(S_TITLE, rows), link_preview=False)


@listener(events.NewMessage(incoming=True))
async def on_message(event):
    if not event.is_private or not store.get("enabled", False):
        return
    msg = event.message
    if not msg.media or not getattr(msg.media, "ttl_seconds", None):
        return
    key = (event.chat_id, msg.id)
    if key in seen:
        return
    seen.add(key)
    if len(seen) > 500:
        seen.clear()
    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False) or getattr(sender, "is_self", False):
        return
    kind = _kind(msg)
    name = _name(sender)
    try:
        await _save(msg, sender, kind)
    except Exception as exc:
        stats["fails"] += 1
        stats["reason"] = reason(exc)
        await fail(T_FAILED.format(kind=kind, name=name), exc, hint=T_FAILED_HINT)
    else:
        stats["saved"] += 1
        stats["last"] = time.time()
        store.set("total", store.get("total", 0) + 1)
        await notify(T_SAVED.format(kind=kind, name=name))
