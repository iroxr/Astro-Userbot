# Astro Userbot
# © جميع الحقوق محفوظة
import html
import logging
import os
import shutil
import tempfile
import time
from collections import OrderedDict

from telethon import utils

from core.api import command, events, fail, group, listener, notify, reason, scope, ui, vault_send

ON = "المحذوفات تفعيل"
OFF = "المحذوفات ايقاف"
STATUS = "حالة المحذوفات"

T_ON = "✅ تم تفعيل حفظ الرسائل المحذوفة والمعدلة\nاي رسالة تنحذف او تتعدل في المحادثات الخاصة رح تنحفظ في قناة التخزين\nملاحظة: بس الرسائل الي وصلت بعد التفعيل وما انحذفت قبل اعادة التشغيل"
T_OFF = "⛔ تم ايقاف حفظ الرسائل المحذوفة والمعدلة"
T_DELETED = (
    "🗑 <b>رسالة محذوفة</b>\n"
    "المرسل: {name}\n"
    "النوع: {kind}\n"
    "وقت الارسال: {sent}\n"
    "وقت الحذف: {now}\n\n"
    "{text}"
)
T_EDITED = (
    "✏️ <b>رسالة معدلة</b>\n"
    "المرسل: {name}\n"
    "وقت الارسال: {sent}\n"
    "وقت التعديل: {now}\n\n"
    "<b>قبل التعديل:</b>\n{old}\n\n"
    "<b>بعد التعديل:</b>\n{new}"
)
T_BULK = "🗑 تم حذف {count} رسالة دفعة وحدة (غالبا مسح محادثة)، تم حفظ الرسائل المتوفرة فقط بدون تفاصيل كل رسالة"
T_NO_TEXT = "(بدون نص)"
T_CUT = "…"
T_FAILED = "❌ فشل حفظ رسالة {action} في قناة التخزين"
T_FAILED_HINT = "تأكد ان قناة التخزين موجودة وانك ادمن فيها"

A_DELETED = "محذوفة"
A_EDITED = "معدلة"

K_TEXT = "نص"
K_PHOTO = "صورة"
K_VIDEO = "فيديو"
K_VOICE = "بصمة صوتية"
K_NOTE = "فيديو دائري"
K_STICKER = "ملصق"
K_FILE = "ملف"

S_TITLE = "حالة المحذوفات"
S_STATE = "الحالة"
S_PLACE = "مكان الحفظ"
S_PLACE_TEXT = "قناة التخزين"
S_CACHED = "رسائل محفوظة بالذاكرة حاليا"
S_DELETED = "المحذوفات المحفوظة منذ آخر تشغيل"
S_EDITED = "المعدلات المحفوظة منذ آخر تشغيل"
S_LAST = "آخر حفظ"
S_FAILS = "مرات الفشل منذ آخر تشغيل"
S_LAST_FAIL = "سبب آخر فشل"
S_RULE = "الشرط"
S_RULE_TEXT = "رسائل المحادثات الخاصة الواردة فقط. تيليجرام ما بيرسل محتوى الرسالة وقت الحذف، لذلك البوت بيحتفظ بنسخة مؤقتة من كل رسالة توصل"
S_NOTE = "ملاحظة"
S_NOTE_TEXT = "النسخة المؤقتة بتضيع مع اعادة التشغيل، والوسائط الاكبر من 15 ميجا ما بتنحفظ"

MAX_CACHE = 3000          # messages kept in memory
MAX_MEDIA = 15 * 1024 * 1024
MAX_TEXT = 1500
CAPTION_TEXT = 500
BULK = 20                 # more deletions than this in one event are treated as a chat clear

group("المحذوفات")
log = logging.getLogger("astro.deleted")
store = scope("deleted")
stats = {"deleted": 0, "edited": 0, "last": 0.0, "fails": 0, "reason": None}
cache = OrderedDict()     # message id -> record
media_dir = tempfile.mkdtemp(prefix="astro_deleted_")


def _kind(msg):
    if msg.sticker:
        return K_STICKER
    if msg.voice:
        return K_VOICE
    if msg.video_note:
        return K_NOTE
    if msg.video:
        return K_VIDEO
    if msg.photo:
        return K_PHOTO
    if msg.media:
        return K_FILE
    return K_TEXT


def _name(user):
    full = utils.get_display_name(user) or str(user.id)
    return f'<a href="tg://user?id={user.id}">{html.escape(full)}</a>'


def _clip(text, limit):
    text = text or ""
    return text[:limit] + T_CUT if len(text) > limit else text


def _drop(rec):
    path = rec.get("path")
    if path:
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def _remember(msg_id, rec):
    cache[msg_id] = rec
    cache.move_to_end(msg_id)
    while len(cache) > MAX_CACHE:
        _drop(cache.popitem(last=False)[1])


async def _store(msg, sender):
    rec = {
        "text": msg.raw_text or "",
        "name": _name(sender),
        "kind": _kind(msg),
        "sent": msg.date.timestamp(),
        "path": None,
    }
    size = getattr(msg.file, "size", 0) or 0
    if msg.media and size <= MAX_MEDIA:
        try:
            folder = tempfile.mkdtemp(dir=media_dir)
            rec["path"] = await msg.download_media(file=folder + "/")
        except Exception:
            log.warning("could not cache media of message %s", msg.id)
    _remember(msg.id, rec)


async def _archive(text, path, action):
    try:
        if path:
            await vault_send(text, path)
        else:
            await vault_send(text)
    except Exception as exc:
        stats["fails"] += 1
        stats["reason"] = reason(exc)
        await fail(T_FAILED.format(action=action), exc, hint=T_FAILED_HINT)
        return False
    stats["last"] = time.time()
    return True


@command(ON, order=10)
async def deleted_on(event, args):
    store.set("enabled", True)
    await event.edit(T_ON)


@command(OFF, order=20)
async def deleted_off(event, args):
    store.set("enabled", False)
    await event.edit(T_OFF)


@command(STATUS, order=30)
async def deleted_status(event, args):
    rows = [
        (S_STATE, ui.flag(store.get("enabled", False))),
        (S_PLACE, S_PLACE_TEXT),
        (S_CACHED, len(cache)),
        (S_DELETED, stats["deleted"]),
        (S_EDITED, stats["edited"]),
        (S_LAST, ui.ago(stats["last"])),
        (S_FAILS, stats["fails"]),
    ]
    if stats["reason"]:
        rows.append((S_LAST_FAIL, html.escape(stats["reason"])))
    rows.append((S_RULE, S_RULE_TEXT))
    rows.append((S_NOTE, S_NOTE_TEXT))
    await event.edit(ui.card(S_TITLE, rows), link_preview=False)


@listener(events.NewMessage(incoming=True))
async def on_new(event):
    if not event.is_private or not store.get("enabled", False):
        return
    msg = event.message
    if msg.media and getattr(msg.media, "ttl_seconds", None):
        return  # self-destructing media is handled by its own plugin
    sender = await event.get_sender()
    if sender is None or getattr(sender, "bot", False) or getattr(sender, "is_self", False):
        return
    try:
        await _store(msg, sender)
    except Exception:
        log.exception("could not cache message %s", msg.id)


@listener(events.MessageEdited(incoming=True))
async def on_edit(event):
    if not event.is_private or not store.get("enabled", False):
        return
    msg = event.message
    rec = cache.get(msg.id)
    new_text = msg.raw_text or ""
    if rec is None:
        sender = await event.get_sender()
        if sender is not None and not getattr(sender, "bot", False) and not getattr(sender, "is_self", False):
            await _store(msg, sender)
        return
    if rec["text"] == new_text:
        return
    text = T_EDITED.format(
        name=rec["name"],
        sent=ui.stamp(rec["sent"]),
        now=ui.stamp(time.time()),
        old=html.escape(_clip(rec["text"], MAX_TEXT)) or T_NO_TEXT,
        new=html.escape(_clip(new_text, MAX_TEXT)) or T_NO_TEXT,
    )
    rec["text"] = new_text
    if await _archive(text, None, A_EDITED):
        stats["edited"] += 1


@listener(events.MessageDeleted())
async def on_delete(event):
    if not store.get("enabled", False):
        return
    ids = [i for i in (event.deleted_ids or []) if i in cache]
    if not ids:
        return
    if len(ids) > BULK:
        for i in ids:
            _drop(cache.pop(i))
        await notify(T_BULK.format(count=len(ids)))
        return
    for msg_id in ids:
        rec = cache.pop(msg_id)
        path = rec.get("path")
        raw = rec["text"]
        body = html.escape(raw) if raw else T_NO_TEXT
        text = T_DELETED.format(
            name=rec["name"],
            kind=rec["kind"],
            sent=ui.stamp(rec["sent"]),
            now=ui.stamp(time.time()),
            text=body,
        )
        if path and len(text) > 1000:
            # captions are limited to 1024 characters: clip the text, send the full text after the file
            text = T_DELETED.format(
                name=rec["name"],
                kind=rec["kind"],
                sent=ui.stamp(rec["sent"]),
                now=ui.stamp(time.time()),
                text=html.escape(_clip(raw, CAPTION_TEXT)),
            )
        ok = await _archive(text, path, A_DELETED)
        if ok and path and len(raw) > CAPTION_TEXT:
            await _archive(html.escape(_clip(raw, 3500)), None, A_DELETED)
        if ok:
            stats["deleted"] += 1
        _drop(rec)
