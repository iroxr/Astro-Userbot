# Astro Userbot
# © جميع الحقوق محفوظة
import os

from aiohttp import web

PORT = int(os.getenv("PORT", "10000"))


async def _health(_request):
    return web.Response(text="ok")


async def start_server():
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
  
