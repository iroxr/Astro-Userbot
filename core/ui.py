# Astro Userbot
# © جميع الحقوق محفوظة
import html
import os
import time
from datetime import datetime, timedelta, timezone

from . import lang

try:
    from zoneinfo import ZoneInfo

    TZ_NAME = os.getenv("POST_TZ", "Asia/Jerusalem")
    TZ = ZoneInfo(TZ_NAME)
except Exception:
    TZ_NAME = "UTC+4"
    TZ = timezone(timedelta(hours=4))

# Right-to-left mark: forces a line to be RTL so numbers and decoration sit on the right.
RLM = "‏"


def esc(value):
    return html.escape(str(value))


def frame(title, rows):
    """Numbered menu card."""
    lines = [RLM + lang.DECO_TITLE.format(esc(title)), RLM + lang.DECO_LINE]
    lines += [f"{RLM}{i} {lang.DECO_BULLET} {row}" for i, row in enumerate(rows, 1)]
    lines.append(RLM + lang.DECO_LINE)
    return "\n".join(lines)


def card(title, rows):
    """Status card. A row is (label, value), a plain line, or '' for a blank line.

    Values must already be HTML-safe; use esc() on user supplied text.
    """
    lines = [RLM + lang.DECO_TITLE.format(esc(title)), RLM + lang.DECO_LINE]
    for row in rows:
        if row is None:
            continue
        if isinstance(row, tuple):
            lines.append(f"{RLM}{lang.DECO_BULLET} {row[0]}: {row[1]}")
        elif row == "":
            lines.append("")
        else:
            lines.append(f"{RLM}{row}")
    lines.append(RLM + lang.DECO_LINE)
    return "\n".join(lines)


def flag(on):
    return lang.LBL_ON if on else lang.LBL_OFF


def span(seconds):
    s = max(int(seconds), 0)
    if s < 60:
        return f"{s} {lang.UNIT_SECOND}"
    if s < 3600:
        return f"{s // 60} {lang.UNIT_MINUTE}"
    hours, minutes = s // 3600, s % 3600 // 60
    out = f"{hours} {lang.UNIT_HOUR}"
    if minutes:
        out += f" {lang.AND}{minutes} {lang.UNIT_MINUTE}"
    return out


def stamp(ts):
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d %H:%M")


def ago(ts):
    if not ts:
        return lang.NEVER
    return f"{stamp(ts)} ({lang.AGO.format(span(time.time() - ts))})"


def until(ts):
    delta = ts - time.time()
    if delta <= 0:
        return stamp(ts)
    return f"{stamp(ts)} ({lang.IN.format(span(delta))})"


def clip(rows, limit, more="..."):
    """Keep a long list short for a status card."""
    rows = list(rows)
    if len(rows) <= limit:
        return rows
    return rows[:limit] + [f"{more} (+{len(rows) - limit})"]
