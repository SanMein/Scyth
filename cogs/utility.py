# cogs/utility.py — приветствие, join/leave-логи и трекинг инвайтов
from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot import bot, logger
from config import (
    GUILD_ID,
    JOIN_LOG_CHANNEL_ID,
    AUDIT_LOG_CHANNEL_ID,
    ON_JOIN_ROLE_IDS,
    WELCOME_THUMB_URL,
    WELCOME_ACCENT_COLOR,
    JOIN_LOG_THUMB_URL,
    JOIN_LOG_ACCENT_COLOR,
    MEMBER_JOIN_THUMB_URL,
    MEMBER_LEAVE_THUMB_URL,
    SUSPICIOUS_ACCOUNT_DAYS,
)


# ============================================================
# ПРИВЕТСТВЕННОЕ ЛС (Components V2)
# ============================================================

WELCOME_TEXT = (
    "# Частная Военная Компания «Military Special Forces – 043»\n\n"
    "Настоящим уведомляем: Вы идентифицированы системой Discord-сервера "
    "ЧВК «MSF-043» как **Незарегистрированный** участник. Доступ к основным "
    "каналам сервера для данной категории лиц ограничен.\n\n"
    "## Порядок регистрации в состав ЧВК «MSF-043»\n"
    "**1.** Ознакомьтесь с Регламентом ЧВК «MSF-043», являющимся основным "
    "сводом правил поведения и взаимодействия на сервере.\n"
    "> → <#1349365797515956229>\n\n"
    "**2.** Перейдите в канал тикет-системы и создайте тикет категории "
    "**«📝・Регистрация»**.\n"
    "> → <#1349365797658824716>\n\n"
    "**3.** Заполните регистрационную форму в строгом соответствии с "
    "инструкцией, размещённой в тикете. Отклонение от инструкции не "
    "допускается.\n\n"
    "**4.** Ожидайте решения уполномоченного лица. Повторная подача "
    "заявления без указания причин не предусмотрены.\n\n"
    "По завершении процедуры регистрации Вам будут присвоены роли, "
    "предоставляющие доступ к каналам сервера в объёме, соответствующем "
    "Вашему статусу.\n\n"
    "В случае возникновения технических или процедурных сложностей "
    "незамедлительно обратитесь к Операционным Директорам: "
    "<@1086319338371428372>, <@1496480145287151716>.\n\n"
    "*Нарушение установленного порядка регистрации либо игнорирование "
    "настоящих указаний влечёт блокировку доступа к серверу или отклонение "
    "регистрационной заявки.*"
)


def build_welcome_view() -> discord.ui.LayoutView:
    """Components V2 LayoutView для приветственного ЛС."""
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(
        accent_color=discord.Colour(WELCOME_ACCENT_COLOR),
    )
    section = discord.ui.Section(
        discord.ui.TextDisplay(WELCOME_TEXT),
        accessory=discord.ui.Thumbnail(WELCOME_THUMB_URL),
    )
    container.add_item(section)
    view.add_item(container)
    return view


# ============================================================
# ПРОСТОЙ JOIN/LEAVE-ЛОГ (Components V2)
# ============================================================

def build_member_simple_log_view(member: discord.Member, joined: bool) -> discord.ui.LayoutView:
    """
    Простой лог присоединения/ухода.
    joined=True  → «присоединился к серверу» + StYKfRf
    joined=False → «покинул сервер»         + wuRa2NQ
    """
    if joined:
        text = f"{member.display_name} | {member.mention} присоединился к серверу."
        thumb = MEMBER_JOIN_THUMB_URL
    else:
        text = f"{member.display_name} | {member.mention} покинул сервер."
        thumb = MEMBER_LEAVE_THUMB_URL

    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(
        accent_color=discord.Colour(JOIN_LOG_ACCENT_COLOR),
    )
    section = discord.ui.Section(
        discord.ui.TextDisplay(text),
        accessory=discord.ui.Thumbnail(thumb),
    )
    container.add_item(section)
    view.add_item(container)
    return view


# ============================================================
# ДЕТАЛЬНЫЙ JOIN-ЛОГ (с пригласившим)
# ============================================================

def _humanize_age(created_at: datetime) -> str:
    """Возвращает '5 дн.' / '7 мес.' / '2 г.' для указанного момента создания."""
    now = datetime.now(timezone.utc)
    days = (now - created_at).days
    if days < 30:
        return f"{days} дн."
    if days < 365:
        return f"{days // 30} мес."
    return f"{days // 365} г."


def build_join_log_view(
    inviter: discord.User | discord.Member | None,
    member: discord.Member,
    invite_code: str,
    num_invites: int,
) -> discord.ui.LayoutView:
    """Components V2 LayoutView с деталями присоединения."""

    if inviter is not None:
        inviter_full = inviter.display_name
        inviter_mention = inviter.mention
    else:
        inviter_full = "Неизвестно"
        inviter_mention = "—"

    member_full = member.display_name
    member_mention = member.mention
    created_str = discord.utils.format_dt(member.created_at, 'd')

    text = (
        f"> - {inviter_full} | {inviter_mention} пригласил на сервер "
        f"{member_full} | {member_mention} с помощью инвайта `{invite_code}`.\n\n"
        f"> - Аккаунт {member_full} | {member_mention} был создан {created_str}.\n\n"
        f"> - У {member_full} {num_invites} инвайтов."
    )

    age_days = (datetime.now(timezone.utc) - member.created_at).days
    if age_days < SUSPICIOUS_ACCOUNT_DAYS:
        text += (
            f"\n\n> - ⚠ Подозрительный аккаунт был создан "
            f"{_humanize_age(member.created_at)} назад"
        )

    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(
        accent_color=discord.Colour(JOIN_LOG_ACCENT_COLOR),
    )
    section = discord.ui.Section(
        discord.ui.TextDisplay(text),
        accessory=discord.ui.Thumbnail(JOIN_LOG_THUMB_URL),
    )
    container.add_item(section)
    view.add_item(container)
    return view


# ============================================================
# COG
# ============================================================

class Utility(commands.Cog, name="Утилиты"):
    """Приветствие, логи входов/выходов и трекинг инвайтов."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> {invite_code: discord.Invite}
        self._invite_cache: dict[int, dict[str, discord.Invite]] = {}

    # ---------- Инвайт-кеш ----------

    async def _refresh_invites(self, guild: discord.Guild):
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            logger.warning(f"Нет прав на просмотр инвайтов сервера {guild.id}")
            return
        except Exception as e:
            logger.exception(f"Ошибка получения инвайтов: {e}")
            return

        self._invite_cache[guild.id] = {inv.code: inv for inv in invites}

    async def _find_used_invite(self, member: discord.Member) -> discord.Invite | None:
        """Сравнивает текущие инвайты с кешем, возвращает использованный."""
        guild = member.guild
        old = self._invite_cache.get(guild.id, {})

        try:
            current_list = await guild.invites()
        except discord.Forbidden:
            return None

        used: discord.Invite | None = None
        for inv in current_list:
            old_inv = old.get(inv.code)
            if old_inv is None:
                if (inv.uses or 0) >= 1 and used is None:
                    used = inv
                continue
            if (inv.uses or 0) > (old_inv.uses or 0):
                used = inv
                break

        self._invite_cache[guild.id] = {inv.code: inv for inv in current_list}
        return used

    async def _count_user_invites(self, guild: discord.Guild, user_id: int) -> int:
        """Сумма использований всех инвайтов, созданных пользователем."""
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            return 0
        return sum(
            (inv.uses or 0) for inv in invites
            if inv.inviter and inv.inviter.id == user_id
        )

    # ---------- Слушатели инвайтов ----------

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._refresh_invites(guild)
        logger.info("Кеш инвайтов инициализирован.")

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        if invite.guild is None:
            return
        self._invite_cache.setdefault(invite.guild.id, {})[invite.code] = invite

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if invite.guild is None:
            return
        self._invite_cache.get(invite.guild.id, {}).pop(invite.code, None)

    # ---------- Общий помощник отправки простого лога в 2 канала ----------

    async def _send_simple_member_log(self, member: discord.Member, joined: bool):
        """Отправляет простое уведомление о входе/выходе в оба канала."""
        for ch_id in (JOIN_LOG_CHANNEL_ID, AUDIT_LOG_CHANNEL_ID):
            ch = bot.get_channel(ch_id)
            if not ch:
                logger.warning(f"Канал {ch_id} не найден — пропускаю member-лог.")
                continue
            try:
                view = build_member_simple_log_view(member, joined)
                await ch.send(view=view)
            except Exception as e:
                logger.exception(f"Ошибка отправки member-лога в {ch_id}: {e}")

    # ---------- Присоединение ----------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return

        # --- 1. Поиск пригласившего ДО выдачи ролей ---
        used_invite = await self._find_used_invite(member)
        inviter = used_invite.inviter if used_invite else None
        invite_code = used_invite.code if used_invite else "—"

        # --- 2. Выдача ролей ---
        roles_to_add = []
        for rid in ON_JOIN_ROLE_IDS:
            role = member.guild.get_role(rid)
            if role and role not in member.roles:
                roles_to_add.append(role)

        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Автовыдача при присоединении")
                logger.info(f"Роли выданы {member} ({member.id}): {[r.id for r in roles_to_add]}")
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(f"Не удалось выдать роли {member}: {e}")

        # --- 3. Смена никнейма ---
        try:
            await member.edit(nick="・", reason="Автосмена ника при присоединении")
        except (discord.Forbidden, discord.HTTPException) as e:
            logger.warning(f"Не удалось сменить ник {member}: {e}")

        # --- 4. Простой лог «присоединился» в JOIN_LOG и AUDIT_LOG ---
        await self._send_simple_member_log(member, joined=True)

        # --- 5. Детальный join-лог (с пригласившим) → только в JOIN_LOG ---
        num_invites = 0
        if inviter is not None:
            num_invites = await self._count_user_invites(member.guild, inviter.id)

        ch_join = bot.get_channel(JOIN_LOG_CHANNEL_ID)
        if ch_join:
            try:
                await ch_join.send(view=build_join_log_view(
                    inviter=inviter,
                    member=member,
                    invite_code=invite_code,
                    num_invites=num_invites,
                ))
            except Exception as e:
                logger.exception(f"Ошибка детального join-лога: {e}")

        # --- 6. Приветственное ЛС ---
        try:
            await member.send(view=build_welcome_view())
        except discord.Forbidden:
            logger.info(f"ЛС {member} закрыты — приветствие не отправлено.")
        except Exception as e:
            logger.exception(f"Ошибка приветствия для {member}: {e}")

    # ---------- Уход ----------

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return
        await self._send_simple_member_log(member, joined=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))