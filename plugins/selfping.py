# Mukhtarat Userbot — مختارات
# © جميع الحقوق محفوظة
import asyncio
import html
import logging
import os
import time

import aiohttp

from core import state
from core.api import command, group, notify, on_start, reason, ui

STATUS = "حالة البينغ الذاتي"

T_DOWN = "⚠️ فشل البينغ الذاتي {n} مرات متتالية، الخدمة ممكن تنام على Render\nالسبب: {reason}\nالرابط: {url}"
T_UP = "✅ رجع البينغ الذاتي للعمل بعد {n} محاولات فاشلة"

S_TITLE = "حالة البينغ الذاتي"
S_URL = "الرابط"
S_EVERY = "كل كم"
S_EVERY_TEXT = "كل {n} دقائق"
S_OK = "نجاح البينغ"
S_FAIL = "فشل البينغ"
S_LAST = "آخر محاولة"
S_RESULT = "نتيجة آخر محاولة"
S_RESULT_OK = "✅ ناجحة (رد الخادم {code})"
S_RESULT_BAD = "❌ فاشلة"
S_WHY = "سبب الفشل"
S_PURPOSE = "الغرض"
S_PURPOSE_TEXT = "منع خدمة Render المجانية من النوم بعد 15 دقيقة بدون زيارات"
S_WAITING = "⏳ لم يبدأ بعد، ينتظر جاهزية الرابط"

URL = (
    os.getenv("KEEPALIVE_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or "https://astro-userbot-nns4.onrender.com/"
)
INTERVAL = 300
ALERT_AFTER = 3

group("البينغ الذاتي")
log = logging.getLogger("mukhtarat.selfping")
stats = {"ok": 0, "fail": 0, "streak": 0, "last": 0.0, "code": None, "reason": None, "good": None}


async def _loop():
    # wait until the public URL is live after a fresh start
    await asyncio.sleep(20)

    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    }

    while True:
        try:
            # a changing query string defeats caches so Render always counts the visit
            ping_url = f"{URL.rstrip('/')}/?t={int(time.time())}"
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(ping_url, ssl=False) as resp:
                    await resp.read()
                    stats["code"] = resp.status
                    log.info("ping %s", resp.status)
            stats["ok"] += 1
            stats["good"] = True
            stats["last"] = time.time()
            if stats["streak"] >= ALERT_AFTER:
                await notify(T_UP.format(n=stats["streak"]))
            stats["streak"] = 0
        except Exception as exc:
            log.warning("ping failed: %r", exc)
            stats["fail"] += 1
            stats["streak"] += 1
            stats["good"] = False
            stats["last"] = time.time()
            stats["reason"] = reason(exc)
            if stats["streak"] == ALERT_AFTER:
                await notify(T_DOWN.format(n=ALERT_AFTER, reason=html.escape(stats["reason"]), url=html.escape(URL)))

        await asyncio.sleep(INTERVAL)


@on_start
async def start():
    state.tasks.append(asyncio.create_task(_loop()))


@command(STATUS, order=10)
async def status(event, args):
    if stats["good"] is None:
        result = S_WAITING
    elif stats["good"]:
        result = S_RESULT_OK.format(code=stats["code"])
    else:
        result = S_RESULT_BAD
    rows = [
        (S_URL, html.escape(URL)),
        (S_EVERY, S_EVERY_TEXT.format(n=INTERVAL // 60)),
        (S_RESULT, result),
        (S_LAST, ui.ago(stats["last"])),
        (S_OK, stats["ok"]),
        (S_FAIL, stats["fail"]),
    ]
    if stats["reason"] and not stats["good"]:
        rows.append((S_WHY, html.escape(stats["reason"])))
    rows.append((S_PURPOSE, S_PURPOSE_TEXT))
    await event.edit(ui.card(S_TITLE, rows), link_preview=False)
