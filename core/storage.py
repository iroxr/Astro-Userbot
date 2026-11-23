# Astro Userbot
# © جميع الحقوق محفوظة
import asyncio
import base64
import hashlib
import logging
import os

import aiohttp

from . import PLUGINS_DIR

log = logging.getLogger("astro.storage")

API = "https://api.github.com"
TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPO"]
BRANCH = os.getenv("GITHUB_BRANCH", "main")

_session = None
_lock = asyncio.Lock()


class StorageError(RuntimeError):
    pass


def _http():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            base_url=API,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "astro-userbot",
            },
        )
    return _session


async def _call(method, path, **kw):
    url = f"/repos/{REPO}/contents/{path}"
    last = None
    for attempt in range(3):
        try:
            async with _http().request(method, url, **kw) as resp:
                if resp.status < 500:
                    return resp.status, await resp.json(content_type=None)
                last = StorageError(f"HTTP {resp.status}")
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last = exc
        await asyncio.sleep(2 ** attempt)
    raise StorageError(str(last))


async def close():
    """Close the shared HTTP session so no connection is left open on exit or restart."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


async def read(path):
    """Return (bytes, sha) or (None, None) when the file does not exist."""
    status, js = await _call("GET", path, params={"ref": BRANCH})
    if status == 404:
        return None, None
    if status != 200:
        raise StorageError(f"read {path}: HTTP {status}")
    return base64.b64decode(js["content"]), js["sha"]


async def write(path, data, message):
    async with _lock:
        for _ in range(3):
            current, sha = await read(path)
            if current == data:
                return
            body = {
                "message": message,
                "content": base64.b64encode(data).decode(),
                "branch": BRANCH,
            }
            if sha:
                body["sha"] = sha
            status, js = await _call("PUT", path, json=body)
            if status in (200, 201):
                return
            if status not in (409, 422):
                raise StorageError(f"write {path}: HTTP {status}")
        raise StorageError(f"write {path}: conflict")


async def listdir(path):
    status, js = await _call("GET", path, params={"ref": BRANCH})
    if status == 404:
        return []
    if status != 200 or not isinstance(js, list):
        raise StorageError(f"list {path}: HTTP {status}")
    return js


def _blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


async def sync_plugins():
    """Pull plugin files from the repo. Returns (changed names, total files)."""
    changed, total = [], 0
    for item in await listdir("plugins"):
        name = item["name"]
        if item["type"] != "file" or not name.endswith(".py") or name.startswith("_"):
            continue
        total += 1
        local = PLUGINS_DIR / name
        if local.exists() and _blob_sha(local.read_bytes()) == item["sha"]:
            continue
        data, _ = await read(f"plugins/{name}")
        if data is not None:
            local.write_bytes(data)
            changed.append(name)
    return changed, total
