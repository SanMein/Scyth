# cogs/mention_react.py — реакция бота на упоминание
import random

import discord
from discord.ext import commands

from bot import logger
from config import GUILD_ID


REPLIES = [
    "Булка 200",
    "Старый 200",
    "Скрипт 200",
]


class MentionReact(commands.Cog, name="Реакция на упоминание"):
    """Отвечает на упоминание бота тремя рандомными фразами."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != GUILD_ID:
            return
        if self.bot.user not in message.mentions:
            return

        # Не реагируем на ответы боту, чтобы не было петли
        if (
            message.reference
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author.id == self.bot.user.id
        ):
            return

        reply = random.choice(REPLIES)
        try:
            await message.reply(reply, mention_author=False)
        except discord.Forbidden:
            logger.warning(f"Нет прав ответить в канале {message.channel.id}")
        except Exception as e:
            logger.exception(f"Ошибка ответа на упоминание: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MentionReact(bot))