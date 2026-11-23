# Astro Userbot
# © جميع الحقوق محفوظة
import time

me = None
started = time.time()
tasks = []

loaded = {}   # plugin name -> number of visible commands
failed = []   # (plugin name, html reason)
