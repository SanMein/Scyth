# utils/helpers.py — общие вспомогательные функции
from datetime import datetime

import discord

from config import FOOTER_TEXT, FOOTER_ICON

def create_embed(description: str, color: int = 0xff0000) -> discord.Embed:
    embed = discord.Embed(description=description, color=color, timestamp=datetime.now())
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed