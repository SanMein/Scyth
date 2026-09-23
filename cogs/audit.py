# cogs/audit.py — аудит-логи событий сервера
from datetime import datetime

import discord
from discord.ext import commands

from config import AUDIT_LOG_CHANNEL_ID, FOOTER_ICON, FOOTER_TEXT


class Audit(commands.Cog, name="Аудит"):
    """Логирование событий сервера в отдельный канал."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_audit_log(self, guild: discord.Guild, action: str, target: str,
                              moderator=None, changes: str = None, extra_info: str = None):
        ch = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
        if not ch:
            return

        embed = discord.Embed(description=f"**{action}**", color=0x2b2d31, timestamp=datetime.now())
        if target:
            embed.add_field(name="Объект", value=f"`{target}`", inline=False)
        if moderator and moderator != target:
            mod_mention = getattr(moderator, 'mention', str(moderator))
            mod_id = getattr(moderator, 'id', '—')
            embed.add_field(name="Модератор", value=f"{mod_mention} (`{mod_id}`)", inline=True)
        if changes:
            embed.add_field(name="Изменения", value=changes, inline=False)
        if extra_info:
            embed.add_field(name="Дополнительно", value=extra_info, inline=False)
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass

    # ---------- Каналы ----------

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self._send_audit_log(
            channel.guild, "📁 Канал создан",
            f"{channel.mention} (`{channel.id}`)",
            channel.guild.me,
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._send_audit_log(
            channel.guild, "🗑️ Канал удалён",
            f"{channel.name} (`{channel.id}`)",
            channel.guild.me,
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel,
                                      after: discord.abc.GuildChannel):
        changes = []
        if before.name != after.name:
            changes.append(f"**Название:** {before.name} → {after.name}")
        if getattr(before, 'topic', None) != getattr(after, 'topic', None):
            changes.append(f"**Тема:** {before.topic or 'Нет'} → {after.topic or 'Нет'}")
        if changes:
            await self._send_audit_log(
                after.guild, "✏️ Канал изменён", after.mention,
                after.guild.me, "\n".join(changes),
            )

    # ---------- Сообщения ----------

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content = message.content[:500] if message.content else "[Без текста/Вложение]"
        await self._send_audit_log(
            message.guild, "🗑️ Сообщение удалено",
            f"#{message.channel.name}", message.author,
            f"Автор: {message.author.mention}\n**Текст:**\n{content}",
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        await self._send_audit_log(
            before.guild, "✏️ Сообщение изменено",
            f"#{before.channel.name}", before.author,
            f"**До:**\n{before.content[:300]}\n**После:**\n{after.content[:300]}",
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Audit(bot))