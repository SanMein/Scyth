# cogs/slash_commands.py — слэш-команды: /ping, /help, /stats, /cleanup, /remind
import asyncio
import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot import bot, logger
from config import (
    GUILD_ID,
    AUDIT_LOG_CHANNEL_ID,
    CLEANUP_LOG_CHANNEL_ID,
    FOOTER_TEXT,
    FOOTER_ICON,
)
from utils.containers import build_container
from utils.time_utils import (
    parse_remind_time,
    format_delta,
)
from utils import reminders as reminders_db


class SlashCommands(commands.Cog, name="Слэш-команды"):
    """Слэш-команды сервера."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reminder_loop.start()

    def cog_unload(self):
        self._reminder_loop.cancel()

    # /ping
    @app_commands.command(name="ping", description="Проверить задержку бота")
    @app_commands.guild_only()
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        status = "🟢 Онлайн" if latency_ms < 200 else ("🟡 Замедлен" if latency_ms < 500 else "🔴 Высокая")
        text = (
            f"# 🏓 Pong!\n"
            f"> **Задержка:** `{latency_ms} мс`\n"
            f"> **Статус:** {status}"
        )
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x2ECC71)
        await interaction.response.send_message(view=view)

    # /help
    @app_commands.command(name="help", description="Список всех команд")
    @app_commands.guild_only()
    async def help_cmd(self, interaction: discord.Interaction):
        # Собираем команды по когам
        by_cog: dict[str, list[app_commands.Command]] = {}
        for cmd in self.bot.tree.get_commands():
            if isinstance(cmd, app_commands.Command):
                cog_name = cmd.binding.__cog_name__ if cmd.binding else "Прочее"
                by_cog.setdefault(cog_name, []).append(cmd)

        lines = ["# 📚 Команды Скифа", "-# Слэш-команды Discord-сервера ЧВК «MSF-043»", ""]
        for cog_name, cmds in by_cog.items():
            lines.append(f"## {cog_name}")
            for cmd in cmds:
                lines.append(f"`/{cmd.name}` — {cmd.description}")
            lines.append("")

        lines.append("*Все команды доступны только на этом сервере.*")
        text = "\n".join(lines)

        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        await interaction.response.send_message(view=view, ephemeral=True)

    # /stats
    @app_commands.command(name="stats", description="Статистика Discord-сервера")
    @app_commands.guild_only()
    async def stats(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Только для сервера.", ephemeral=True)
            return

        # Базовое
        members = guild.members
        humans = [m for m in members if not m.bot]
        bots = [m for m in members if m.bot]
        online = [m for m in members if m.status != discord.Status.offline]
        idle = [m for m in members if m.status == discord.Status.idle]
        dnd = [m for m in members if m.status == discord.Status.dnd]

        # Владелец (может быть не в кеше — берём по ID)
        if guild.owner:
            owner_str = guild.owner.mention
        else:
            owner_str = f"<@{guild.owner_id}>"

        # Время буста (первый бустер)
        if guild.premium_subscribers:
            first_booster = min(guild.premium_subscribers, key=lambda m: m.premium_since or datetime.now(timezone.utc))
            boost_since = (
                discord.utils.format_dt(first_booster.premium_since, 'R')
                if first_booster.premium_since else "—"
            )
        else:
            boost_since = "—"

        # Топ-3 роли по количеству участников
        role_counts = []
        for role in guild.roles:
            if role.is_default():
                continue
            cnt = len([m for m in members if role in m.roles])
            if cnt:
                role_counts.append((role, cnt))
        role_counts.sort(key=lambda x: x[1], reverse=True)
        top_roles_str = "\n".join(
            f"> • {r.mention} — {c}" for r, c in role_counts[:3]
        ) or "> —"

        # Каналы
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        forum_channels = len(guild.forums)

        # Контент
        roles = len(guild.roles)
        emojis = len(guild.emojis)
        emoji_limit = guild.emoji_limit
        stickers = len(guild.stickers)
        sticker_limit = guild.sticker_limit

        # Бусты
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count

        # Даты
        created = discord.utils.format_dt(guild.created_at, 'D')

        text = (
            f"# Частная Военная Компания «Military Special Forces — 043»\n"
            f"-# статистика Discord-сервера\n\n"
            f"## 📌 Основное\n"
            f"> **Название:** {guild.name}\n"
            f"> **ID:** `{guild.id}`\n"
            f"> **Владелец:** {owner_str}\n"
            f"> **Создан:** {created}\n\n"
            f"## 👥 Участники\n"
            f"> **Всего:** {len(members)}\n"
            f"> **Людей:** {len(humans)}\n"
            f"> **Ботов:** {len(bots)}\n"
            f"> **Онлайн:** {len(online)} (🟢 {len(online) - len(idle) - len(dnd)} | 🌙 {len(idle)} | ⛔ {len(dnd)})\n\n"
            f"## 💬 Каналы\n"
            f"> **Текстовых:** {text_channels}\n"
            f"> **Голосовых:** {voice_channels}\n"
            f"> **Форумов:** {forum_channels}\n"
            f"> **Категорий:** {categories}\n\n"
            f"## 🎭 Контент\n"
            f"> **Ролей:** {roles}\n"
            f"> **Эмодзи:** {emojis}/{emoji_limit}\n"
            f"> **Стикеров:** {stickers}/{sticker_limit}\n\n"
            f"## 🏆 Топ-3 роли по составу\n"
            f"{top_roles_str}\n\n"
            f"## 🚀 Бустеры\n"
            f"> **Уровень:** {boost_level}\n"
            f"> **Бустеров:** {boost_count}\n"
            f"> **Первый буст:** {boost_since}\n"
        )

        gallery = discord.ui.MediaGallery(
            discord.ui.MediaGalleryItem("https://i.imgur.com/9kKUxJZ.jpeg"),
            discord.ui.MediaGalleryItem("https://i.imgur.com/VPlclnJ.jpeg"),
        )

        view = build_container(
            text,
            thumb_url="https://i.imgur.com/m62M7hK.png",
            accent_color=0x9B59B6,
            extra_items=[gallery],
        )

        await interaction.response.send_message(view=view)

    # /cleanup
    @app_commands.command(name="cleanup", description="Удалить N сообщений в текущем канале (1–1000)")
    @app_commands.describe(amount="Количество сообщений для удаления (1–1000)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def cleanup(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 1000:
            await interaction.response.send_message(
                "❌ Количество должно быть от 1 до 1000.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        deleted = await interaction.channel.purge(limit=amount)
        count = len(deleted)

        text = (
            f"# Очистка чата\n"
            f"> **Модератор:** {interaction.user.mention}\n"
            f"> **Канал:** <#{interaction.channel_id}>\n"
            f"> **Количество сообщений:** {count}"
        )

        # Отправляем в оба канала
        for ch_id in (CLEANUP_LOG_CHANNEL_ID, AUDIT_LOG_CHANNEL_ID):
            ch = self.bot.get_channel(ch_id)
            if not ch:
                continue
            try:
                # ВАЖНО: view одноразовый → создаём новый на каждый канал
                v = build_container(
                    text,
                    thumb_url="https://i.imgur.com/j1ubPNG.png",
                    accent_color=0x9B59B6,
                )
                await ch.send(view=v)
            except Exception as e:
                logger.exception(f"Ошибка отправки лога очистки в {ch_id}: {e}")

        await interaction.followup.send(
            f"✅ Удалено **{count}** сообщений.", ephemeral=True
        )

    # /remind add
    remind_group = app_commands.Group(name="remind", description="Управление напоминаниями")
    @remind_group.command(name="add", description="Установить напоминание")
    @app_commands.describe(
        time="30s / 5m / 2h / 1d / 1w или unix timestamp",
        text="Текст напоминания",
    )
    @app_commands.guild_only()
    async def remind_add(self, interaction: discord.Interaction, time: str, text: str):
        delta, error = parse_remind_time(time)
        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        if delta.total_seconds() > 30 * 86400:
            await interaction.response.send_message(
                "❌ Максимальный срок — 30 дней.", ephemeral=True
            )
            return

        fire_at = datetime.now(timezone.utc) + delta
        reminder_id = uuid.uuid4().hex[:8]

        await reminders_db.add_reminder(
            reminder_id=reminder_id,
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            fire_at=fire_at,
            text=text,
        )

        human = format_delta(delta)
        ts = discord.utils.format_dt(fire_at, 'f')
        await interaction.response.send_message(
            f"⏰ Напоминание `{reminder_id}` установлено на {ts} (через **{human}**).",
            ephemeral=True,
        )

    # /remind list
    @remind_group.command(name="list", description="Список ваших напоминаний")
    @app_commands.guild_only()
    async def remind_list(self, interaction: discord.Interaction):
        user_reminders = await reminders_db.get_user_reminders(interaction.user.id)
        if not user_reminders:
            await interaction.response.send_message(
                "📭 У вас нет активных напоминаний.", ephemeral=True
            )
            return

        lines = ["# 📋 Ваши напоминания", ""]
        for rid, r in user_reminders.items():
            fire_at = datetime.fromisoformat(r["fire_at"])
            ts = discord.utils.format_dt(fire_at, 'f')
            lines.append(f"`{rid}` — {ts}")
            lines.append(f"> {r['text'][:80]}")
            lines.append("")

        text = "\n".join(lines)
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        await interaction.response.send_message(view=view, ephemeral=True)

    # /remind cancel
    @remind_group.command(name="cancel", description="Отменить напоминание по ID")
    @app_commands.describe(reminder_id="ID напоминания (из /remind list)")
    @app_commands.guild_only()
    async def remind_cancel(self, interaction: discord.Interaction, reminder_id: str):
        user_reminders = await reminders_db.get_user_reminders(interaction.user.id)
        if reminder_id not in user_reminders:
            await interaction.response.send_message(
                "❌ Напоминание не найдено или не ваше.", ephemeral=True
            )
            return
        await reminders_db.remove_reminder(reminder_id)
        await interaction.response.send_message(
            f"✅ Напоминание `{reminder_id}` отменено.", ephemeral=True
        )

    # ========================================================
    # Фоновый обработчик напоминаний
    # ========================================================
    @tasks.loop(seconds=30)
    async def _reminder_loop(self):
        try:
            data = await reminders_db.load_reminders()
        except Exception as e:
            logger.exception(f"Ошибка чтения reminders.json: {e}")
            return

        now = datetime.now(timezone.utc)
        due: list[str] = []

        for rid, r in data.items():
            try:
                fire_at = datetime.fromisoformat(r["fire_at"])
            except (KeyError, ValueError):
                due.append(rid)
                continue
            if fire_at <= now:
                due.append(rid)

        for rid in due:
            r = data.get(rid)
            if r is None:
                continue
            await self._fire_reminder(rid, r)

    @_reminder_loop.before_loop
    async def _before_reminder_loop(self):
        await self.bot.wait_until_ready()

    async def _fire_reminder(self, reminder_id: str, r: dict):
        user_id = r.get("user_id")
        channel_id = r.get("channel_id")
        text = r.get("text", "")

        # Удаляем из хранилища сразу, чтобы не сработало дважды
        await reminders_db.remove_reminder(reminder_id)

        channel = self.bot.get_channel(channel_id)
        user_mention = f"<@{user_id}>"
        now_ts = discord.utils.format_dt(datetime.now(timezone.utc), 'T')

        body = (
            f"# Напоминание\n"
            f"> **Время:** {now_ts}\n"
            f"{user_mention}. {text}"
        )

        view = build_container(
            body,
            thumb_url="https://i.imgur.com/j1ubPNG.png",
            accent_color=0x9B59B6,
        )

        # Пытаемся отправить в исходный канал, при неудаче — в ЛС
        if channel is not None:
            try:
                await channel.send(view=view)
                return
            except Exception as e:
                logger.exception(f"Не удалось отправить напоминание в канал: {e}")

        # Fallback — в ЛС
        try:
            user = await self.bot.fetch_user(user_id)
            view_dm = build_container(
                body,
                thumb_url="https://i.imgur.com/j1ubPNG.png",
                accent_color=0x9B59B6,
            )
            await user.send(view=view_dm)
        except Exception as e:
            logger.exception(f"Не удалось отправить напоминание в ЛС {user_id}: {e}")

    # ========================================================
    # Обработчик ошибок слэш-команд
    # ========================================================
    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ У вас нет прав для этой команды."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏱️ Повторите через {error.retry_after:.1f} сек."
        else:
            logger.exception("Ошибка слэш-команды")
            msg = "⚠️ Произошла ошибка. Сообщите администрации."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommands(bot))