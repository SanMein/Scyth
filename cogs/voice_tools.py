# cogs/voice_tools.py — автоочистка голосовых каналов + пересылка медиа из VC-чатов
from datetime import time as dtime, timezone, timedelta

import discord
from discord.ext import commands, tasks

from bot import bot, logger
from config import (
    GUILD_ID,
    VOICE_MEDIA_FORWARD_CHANNEL_ID,
    VOICE_CLEANUP_EXCLUDED_IDS,
    VOICE_MEDIA_EXCLUDED_IDS,
    MSK_OFFSET_HOURS,
    JOIN_LOG_ACCENT_COLOR,
)
from utils.containers import build_container


MSK = timezone(timedelta(hours=MSK_OFFSET_HOURS))

# Медиа-расширения, которые пересылаем
MEDIA_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.webp', '.gif',
    '.mp4', '.mov', '.webm', '.mkv',
}

# Голосовые сообщения Discord тоже приходят как вложения
VOICE_MESSAGE_CONTENT_TYPES = {
    'audio/ogg', 'audio/mpeg', 'audio/wav', 'audio/mp4',
}


class VoiceTools(commands.Cog, name="Голосовые"):
    """Автоочистка VC в 6:00 МСК и пересылка медиа из VC-чатов."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_clear_voice.start()

    def cog_unload(self):
        self.auto_clear_voice.cancel()

    # ---------- Автоочистка в 6:00 МСК ----------

    @tasks.loop(time=dtime(hour=6, minute=0, tzinfo=MSK))
    async def auto_clear_voice(self):
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            logger.warning("Гильдия не найдена — автоочистка VC пропущена.")
            return

        moved_total = 0
        channels_touched = 0

        for vc in guild.voice_channels:
            if vc.id in VOICE_CLEANUP_EXCLUDED_IDS:
                continue
            if not vc.members:
                continue

            channels_touched += 1
            for member in list(vc.members):
                try:
                    await member.move_to(None, reason="Плановая очистка голосовых каналов (6:00 МСК)")
                    moved_total += 1
                except discord.Forbidden:
                    logger.warning(f"Нет прав выгнать {member} из {vc.name}")
                except discord.HTTPException as e:
                    logger.exception(f"Ошибка при выгоне {member}: {e}")

        logger.info(
            f"Автоочистка VC в 6:00 МСК завершена: "
            f"каналов={channels_touched}, участников={moved_total}"
        )

    @auto_clear_voice.before_loop
    async def before_auto_clear(self):
        await self.bot.wait_until_ready()

    # ---------- Пересылка медиа из VC-чатов ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != GUILD_ID:
            return
        if not message.attachments:
            return

        # Проверяем, что канал — это текстовый чат голосового канала
        parent = getattr(message.channel, "parent", None)
        if parent is None or not isinstance(parent, discord.VoiceChannel):
            return
        if parent.id in VOICE_MEDIA_EXCLUDED_IDS:
            return

        target = self.bot.get_channel(VOICE_MEDIA_FORWARD_CHANNEL_ID)
        if target is None:
            return

        # Отбираем медиа-вложения
        media = [
            a for a in message.attachments
            if self._is_media(a)
        ]
        if not media:
            return

        # Скачиваем и пересылаем
        files: list[discord.File] = []
        for a in media:
            try:
                files.append(await a.to_file())
            except Exception as e:
                logger.exception(f"Не удалось скачать вложение {a.filename}: {e}")

        if not files:
            return

        text = (
            f"# 📎 Медиа из голосового чата\n"
            f"> **Отправитель:** {message.author.display_name} | {message.author.mention}\n"
            f"> **Канал:** {parent.mention}\n"
            f"> **Сообщение:** [перейти]({message.jump_url})\n"
            f"> **Файлов:** {len(files)}"
        )
        view = build_container(
            text,
            thumb_url=None,
            accent_color=JOIN_LOG_ACCENT_COLOR,
        )

        try:
            await target.send(view=view, files=files)
        except Exception as e:
            logger.exception(f"Ошибка пересылки медиа: {e}")

    @staticmethod
    def _is_media(attachment: discord.Attachment) -> bool:
        """Определяет, является ли вложение медиа."""
        name = (attachment.filename or "").lower()
        _, _, ext = name.rpartition(".")
        if f".{ext}" in MEDIA_EXTENSIONS:
            return True
        if attachment.content_type in VOICE_MESSAGE_CONTENT_TYPES:
            return True
        return False


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceTools(bot))