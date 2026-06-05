# utils.py - вспомогательные функции
import os, json, aiofiles
from datetime import datetime, timedelta
import discord
from config import *
from discord.ui import Modal, TextInput

async def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        async with aiofiles.open(WARNINGS_FILE, 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    return {}

async def save_warnings(data):
    async with aiofiles.open(WARNINGS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))

async def load_moderation_logs():
    if os.path.exists(MODERATION_LOGS_FILE):
        async with aiofiles.open(MODERATION_LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    return {}

async def save_moderation_logs(data):
    async with aiofiles.open(MODERATION_LOGS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))

def parse_duration(duration_str: str) -> timedelta:
    if not duration_str or not duration_str[-1].isalpha():
        return timedelta(minutes=5)
    try:
        value = int(duration_str[:-1])
        unit = duration_str[-1].lower()
        units = {
            'm': timedelta(minutes=value), 'h': timedelta(hours=value),
            'd': timedelta(days=value), 'w': timedelta(weeks=value),
            'y': timedelta(days=value * 365)
        }
        return units.get(unit, timedelta(minutes=5))
    except:
        return timedelta(minutes=5)

def create_embed(description, color=0xff0000):
    embed = discord.Embed(description=description, color=color, timestamp=datetime.now())
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed