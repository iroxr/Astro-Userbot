# Astro Userbot
# © جميع الحقوق محفوظة
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins"
DATA_DIR = ROOT / "data"
PLUGINS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

PREFIX = os.getenv("PREFIX", ".")

client = TelegramClient(
    StringSession(os.environ["SESSION"]),
    int(os.environ["API_ID"]),
    os.environ["API_HASH"],
    connection_retries=-1,
    retry_delay=2,
)
client.parse_mode = "html"
