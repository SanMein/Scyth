# bot.py — единая точка создания экземпляра бота
import logging

import discord
from discord.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger('scyth')

intents = discord.Intents.all()
# Префикс оставляем на случай будущих команд; сейчас команд нет.
bot = commands.Bot(command_prefix='//', intents=intents)