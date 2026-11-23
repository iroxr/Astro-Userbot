# Astro Userbot
# © جميع الحقوق محفوظة
import asyncio
import json
import logging
import time

from . import storage

log = logging.getLogger("astro.settings")

PATH = "data/settings.json"
DELAY = 3

_data = {}
_dirty = False
_task = None
last_flush = 0.0
last_error = None


async def load():
    global _data
    raw, _ = await storage.read(PATH)
    _data = json.loads(raw) if raw else {}


def get(ns, key, default=None):
    return _data.get(ns, {}).get(key, default)


def set(ns, key, value):
    _data.setdefault(ns, {})[key] = value
    _touch()


def delete(ns, key):
    if _data.get(ns, {}).pop(key, None) is not None:
        _touch()


def _touch():
    global _dirty, _task
    _dirty = True
    if _task is None or _task.done():
        _task = asyncio.get_running_loop().create_task(_later())


async def _later():
    while True:
        await asyncio.sleep(DELAY)
        await flush()
        if not _dirty:
            return


def pending():
    return _dirty


async def flush():
    global _dirty, last_flush, last_error
    if not _dirty:
        return
    _dirty = False
    payload = json.dumps(_data, ensure_ascii=False, indent=1, sort_keys=True)
    try:
        await storage.write(PATH, payload.encode(), "settings")
        last_flush = time.time()
        last_error = None
    except Exception as exc:
        _dirty = True
        last_error = exc
        log.exception("settings flush failed")


class Scope:
    """Per-plugin view of the shared settings store."""

    def __init__(self, ns):
        self.ns = ns

    def get(self, key, default=None):
        return get(self.ns, key, default)

    def set(self, key, value):
        set(self.ns, key, value)

    def delete(self, key):
        delete(self.ns, key)


def scope(ns):
    return Scope(ns)
