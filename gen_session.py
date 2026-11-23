# Astro Userbot
# © جميع الحقوق محفوظة
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

api_id = int(input("API_ID: "))
api_hash = input("API_HASH: ").strip()
with TelegramClient(StringSession(), api_id, api_hash) as tg:
    print("\nSESSION:\n" + tg.session.save())
