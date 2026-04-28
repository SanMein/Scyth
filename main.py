import discord
from discord.ext import commands
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import aiofiles
from collections import defaultdict

# Настройка бота
intents = discord.Intents.default()
intents.members = True
intents.bans = True
intents.message_content = True
intents.invites = True
bot = commands.Bot(command_prefix='//', intents=intents)

# Конфигурация
GUILD_ID = 1349365796949856273
ADMIN_ROLE_IDS = [
    1447513054844555336,  # ἄλφα
    1349365796970954834,  # Генеральный Директор
    1349365796970954833  # Операционный директор
]
LOG_CHANNEL_ID = 1399890569165275348
JOIN_MESSAGE_CHANNEL_ID = 1349365797515956225
WARNINGS_FILE = 'warnings.json'
MODERATION_LOGS_FILE = 'moderation_logs.json'
INVITES_FILE = 'invites.json'
FOOTER_TEXT = "Scyth // Σκύθ"
FOOTER_ICON = "https://i.imgur.com/IlA74Ij.png"

# Асинхронная загрузка/сохранение данных
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


async def load_invites():
    if os.path.exists(INVITES_FILE):
        async with aiofiles.open(INVITES_FILE, 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    return {}


async def save_invites(data):
    async with aiofiles.open(INVITES_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))


async def add_moderation_log(action, moderator, target, reason, duration=None):
    logs = await load_moderation_logs()
    log_entry = {
        "action": action,
        "moderator": str(moderator),
        "moderator_name": moderator.name if hasattr(moderator, 'name') else str(moderator),
        "target": str(target),
        "target_name": target.name if hasattr(target, 'name') else str(target),
        "reason": reason,
        "duration": duration,
        "date": datetime.now().isoformat()
    }

    if str(target) not in logs:
        logs[str(target)] = []
    logs[str(target)].append(log_entry)
    await save_moderation_logs(logs)

    # Отправка в канал логов
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            description=f"**{action}**\nМодератор: {moderator.mention if hasattr(moderator, 'mention') else moderator}\nЦель: {target.mention if hasattr(target, 'mention') else target}\nПричина: {reason}\nВремя: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            color=0xff0000 if action in ["Бан", "Кик", "Таймаут"] else 0xffaa00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await log_channel.send(embed=embed)


# Проверка прав
def has_admin_role(ctx):
    return any(role.id in ADMIN_ROLE_IDS for role in ctx.author.roles)


# Парсинг времени
def parse_duration(duration_str: str) -> timedelta:
    if not duration_str or not duration_str[-1].isalpha():
        return timedelta(minutes=5)

    try:
        value = int(duration_str[:-1])
        unit = duration_str[-1].lower()

        units = {
            'm': timedelta(minutes=value),
            'h': timedelta(hours=value),
            'd': timedelta(days=value),
            'w': timedelta(weeks=value),
            't': timedelta(minutes=value),
            'y': timedelta(days=value * 365)
        }
        return units.get(unit, timedelta(minutes=5))
    except ValueError:
        return timedelta(minutes=5)


# Команда !ban
@bot.command(name="ban")
async def ban(ctx, user_id: str, duration: str = None, *, reason="Без причины"):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    if not user_id.isdigit():
        embed = discord.Embed(
            description="❌ Укажите валидный ID пользователя.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    guild = bot.get_guild(GUILD_ID)
    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(
            description="❌ Пользователь не найден.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    try:
        if duration:
            delta = parse_duration(duration)
            await guild.ban(user, reason=reason, delete_message_days=0)
            embed = discord.Embed(
                description=f"🔨 Вы были заблокированы на сервере **MSF-043** по причине **{reason}** на **{duration}**.\n\n---\n\nЖелаем вам приятных игровых сессий и проведения времени.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            try:
                await user.send(embed=embed)
            except:
                pass

            embed = discord.Embed(
                description=f"✅ Пользователь **{user.name}** забанен на **{duration}**. Причина: {reason}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await ctx.send(embed=embed)

            await add_moderation_log("Временный бан", ctx.author, user, reason, duration)

            await asyncio.sleep(delta.total_seconds())
            await guild.unban(user, reason=f"Истек временный бан")

            embed = discord.Embed(
                description=f"🔓 Пользователь **{user.name}** разбанен автоматически (истек срок бана).",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await log_channel.send(embed=embed)
        else:
            await guild.ban(user, reason=reason, delete_message_days=0)
            embed = discord.Embed(
                description=f"🔨 Вы были перманентно заблокированы на сервере **MSF-043** по причине **{reason}**.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            try:
                await user.send(embed=embed)
            except:
                pass

            embed = discord.Embed(
                description=f"✅ Пользователь **{user.name}** перманентно забанен. Причина: {reason}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await ctx.send(embed=embed)

            await add_moderation_log("Перманентный бан", ctx.author, user, reason)
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для бана этого пользователя.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при бане: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !unban
@bot.command(name="unban")
async def unban(ctx, user_id: str, *, reason="Без причины"):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    if not user_id.isdigit():
        embed = discord.Embed(
            description="❌ Укажите валидный ID пользователя.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    guild = bot.get_guild(GUILD_ID)
    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(
            description="❌ Пользователь не найден.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    try:
        banned_users = await guild.bans()
        if any(ban.user.id == int(user_id) for ban in banned_users):
            await guild.unban(user, reason=reason)
            embed = discord.Embed(
                description=f"🔓 Вы были разблокированы на сервере **MSF-043**. Ранее вы были забанены по причине **{reason}**\n\n---\n\nЖелаем вам приятных игровых сессий и проведения времени. Ссылка на сервер - **[Нажмите](https://discord.gg/zsYN3CdGGu)**.",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            try:
                await user.send(embed=embed)
            except:
                pass

            embed = discord.Embed(
                description=f"✅ Пользователь **{user.name}** разбанен. Причина: {reason}",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await ctx.send(embed=embed)

            await add_moderation_log("Разбан", ctx.author, user, reason)
        else:
            embed = discord.Embed(
                description=f"❌ Пользователь **{user.name}** не забанен.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для разбана.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при разбане: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !kick
@bot.command(name="kick")
async def kick(ctx, member: discord.Member, *, reason="Без причины"):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            description=f"👢 Вы были выгнаны с сервера **MSF-043** по причине **{reason}**.\n\n---\n\nЖелаем вам приятных игровых сессий и проведения времени.\n\n---\n\nЕсли ваш кик был ошибкой или намеренным без чёткого указания причины, просим обратиться к **<@1086319338371428372>** или повторно зайти на сервер - **[Нажмите](https://discord.gg/zsYN3CdGGu)**.",
            color=0xffaa00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        try:
            await member.send(embed=embed)
        except:
            pass

        embed = discord.Embed(
            description=f"✅ Пользователь {member.mention} кикнут. Причина: {reason}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)

        await add_moderation_log("Кик", ctx.author, member, reason)
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для кика.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при кике: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !tout (таймаут)
@bot.command(name="tout")
async def timeout_command(ctx, member: discord.Member, duration: str, *, reason="Без причины"):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    delta = parse_duration(duration)
    if delta.total_seconds() > 2419200:
        embed = discord.Embed(
            description="❌ Максимальная длительность таймаута - 28 дней.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    try:
        await member.timeout(delta, reason=reason)

        embed = discord.Embed(
            description=f"🔇 Вы получили таймаут на сервере **MSF-043** по причине **{reason}** на **{duration}**.\n\n---\n\nЖелаем вам приятных игровых сессий и проведения времени.",
            color=0xffaa00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        try:
            await member.send(embed=embed)
        except:
            pass

        embed = discord.Embed(
            description=f"✅ Пользователь {member.mention} получил таймаут на **{duration}**. Причина: {reason}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)

        await add_moderation_log("Таймаут", ctx.author, member, reason, duration)
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для таймаута.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при таймауте: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !warn
@bot.command(name="warn")
async def warn(ctx, member: discord.Member, duration: str, *, reason="Без причины"):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    warnings = await load_warnings()
    user_id = str(member.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warning_data = {
        "reason": reason,
        "duration": duration,
        "moderator": str(ctx.author),
        "date": datetime.now().isoformat()
    }
    warnings[user_id].append(warning_data)
    await save_warnings(warnings)

    warning_count = len(warnings[user_id])

    embed = discord.Embed(
        description=f"⚠️ Вы получили предупреждение **(#{warning_count})** на сервере **MSF-043** по причине **{reason}** на **{duration}**.\n\nНапоминаем, что за 3 предупреждения вы получите таймаут на 30 минут, за 6 - таймаут на 3 часа, а за 10 - перманентный бан.\n\n---\n\nЖелаем вам приятных игровых сессий и проведения времени.\n\nЕсли ваш пред был ошибкой, просим обратиться к **<@1086319338371428372>**.",
        color=0xffaa00,
        timestamp=datetime.now()
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    try:
        await member.send(embed=embed)
    except:
        pass

    embed = discord.Embed(
        description=f"⚠️ Пользователь {member.mention} получил предупреждение #{warning_count}. Причина: {reason}",
        color=0xffaa00,
        timestamp=datetime.now()
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    await ctx.send(embed=embed)

    await add_moderation_log("Предупреждение", ctx.author, member, reason, duration)

    # Автоматические действия
    if warning_count == 3:
        delta = parse_duration("30m")
        await member.timeout(delta, reason="Накоплено 3 предупреждения")
        embed = discord.Embed(
            description=f"🔇 Пользователь {member.mention} автоматически получил таймаут на 30 минут (3 предупреждения).",
            color=0xffaa00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    elif warning_count == 6:
        delta = parse_duration("3h")
        await member.timeout(delta, reason="Накоплено 6 предупреждений")
        embed = discord.Embed(
            description=f"🔇 Пользователь {member.mention} автоматически получил таймаут на 3 часа (6 предупреждений).",
            color=0xffaa00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    elif warning_count == 10:
        await member.ban(reason="Накоплено 10 предупреждений")
        embed = discord.Embed(
            description=f"🔨 Пользователь {member.mention} автоматически забанен (10 предупреждений).",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !unwarn
@bot.command(name="unwarn")
async def unwarn(ctx, member: discord.Member, warning_number: int = None):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    warnings = await load_warnings()
    user_id = str(member.id)

    if user_id not in warnings or not warnings[user_id]:
        embed = discord.Embed(
            description=f"❌ У пользователя {member.mention} нет предупреждений.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    if warning_number is None:
        removed = warnings[user_id].pop()
        embed = discord.Embed(
            description=f"✅ У пользователя {member.mention} удалено последнее предупреждение. Осталось: {len(warnings[user_id])}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    elif 1 <= warning_number <= len(warnings[user_id]):
        removed = warnings[user_id].pop(warning_number - 1)
        embed = discord.Embed(
            description=f"✅ У пользователя {member.mention} удалено предупреждение #{warning_number}. Осталось: {len(warnings[user_id])}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description=f"❌ Неверный номер предупреждения. Всего предупреждений: {len(warnings[user_id])}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    await save_warnings(warnings)
    await add_moderation_log("Снятие предупреждения", ctx.author, member,
                             f"Удалено предупреждение #{warning_number if warning_number else 'последнее'}")


# Команда !clwarn
@bot.command(name="clwarn")
async def clear_warnings(ctx, member: discord.Member):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    warnings = await load_warnings()
    user_id = str(member.id)

    if user_id in warnings and warnings[user_id]:
        count = len(warnings[user_id])
        warnings[user_id] = []
        await save_warnings(warnings)

        embed = discord.Embed(
            description=f"✅ У пользователя {member.mention} очищены все предупреждения ({count} шт.).",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)

        await add_moderation_log("Очистка предупреждений", ctx.author, member, f"Удалено {count} предупреждений")
    else:
        embed = discord.Embed(
            description=f"❌ У пользователя {member.mention} нет предупреждений.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !clear
@bot.command(name="clear")
async def clear_messages(ctx, count: int):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    if count <= 0:
        embed = discord.Embed(
            description="❌ Укажите положительное число сообщений для удаления.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    if count > 1000:
        embed = discord.Embed(
            description="❌ Можно удалить не более 1000 сообщений за раз.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    try:
        deleted = await ctx.channel.purge(limit=count)

        embed = discord.Embed(
            description=f"✅ Удалено **{len(deleted)}** сообщений в канале {ctx.channel.mention}.",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(3)
        await msg.delete()

        await add_moderation_log("Очистка чата", ctx.author, ctx.channel, f"Удалено {len(deleted)} сообщений")
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для удаления сообщений.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при удалении: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда !logs для просмотра логов
@bot.command(name="logs")
async def view_logs(ctx, member: discord.Member = None):
    if not has_admin_role(ctx):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    logs = await load_moderation_logs()

    if member:
        user_id = str(member.id)
        if user_id in logs and logs[user_id]:
            user_logs = logs[user_id][-15:]
            embed = discord.Embed(
                title=f"📋 Логи модерации для {member.name}",
                color=0x00aaff,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

            for log in user_logs:
                date = datetime.fromisoformat(log['date']).strftime('%d.%m.%Y %H:%M')
                embed.add_field(
                    name=f"{log['action']} ({date})",
                    value=f"Модератор: {log['moderator_name']}\nПричина: {log['reason']}",
                    inline=False
                )

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"❌ У пользователя {member.mention} нет логов модерации.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description="❌ Укажите пользователя для просмотра логов.\nПример: `!logs @user`",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Система приглашений
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} (MSF-043 GuardTool) готов к работе!')

    guild = bot.get_guild(GUILD_ID)
    if guild:
        invites = await guild.invites()
        invites_dict = {}
        for invite in invites:
            invites_dict[invite.code] = {
                "code": invite.code,
                "uses": invite.uses or 0,
                "inviter": str(invite.inviter.id) if invite.inviter else None,
                "inviter_name": invite.inviter.name if invite.inviter else "Unknown",
                "max_uses": invite.max_uses,
                "created_at": invite.created_at.isoformat() if invite.created_at else None
            }
        await save_invites(invites_dict)
        print(f"📊 Загружено {len(invites_dict)} инвайтов")


@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID:
        return

    await asyncio.sleep(2)

    guild = member.guild
    new_invites = await guild.invites()
    old_invites = await load_invites()

    used_invite = None
    inviter = None

    for invite in new_invites:
        old_data = old_invites.get(invite.code)
        if old_data:
            old_uses = old_data.get("uses", 0)
            if invite.uses and invite.uses > old_uses:
                used_invite = invite
                if invite.inviter:
                    inviter = invite.inviter
                break

    if not used_invite:
        for invite in new_invites:
            if invite.code not in old_invites:
                used_invite = invite
                if invite.inviter:
                    inviter = invite.inviter
                break

    invites_dict = {}
    for invite in new_invites:
        invites_dict[invite.code] = {
            "code": invite.code,
            "uses": invite.uses or 0,
            "inviter": str(invite.inviter.id) if invite.inviter else None,
            "inviter_name": invite.inviter.name if invite.inviter else "Unknown",
            "max_uses": invite.max_uses,
            "created_at": invite.created_at.isoformat() if invite.created_at else None
        }
    await save_invites(invites_dict)

    join_channel = bot.get_channel(JOIN_MESSAGE_CHANNEL_ID)
    if not join_channel:
        return

    inviter_stats = await load_warnings()
    num_invites = 0

    if inviter:
        for code, data in invites_dict.items():
            if data.get("inviter") == str(inviter.id):
                num_invites += 1

    member_created = member.created_at
    current_time = datetime.now()
    account_age_days = (current_time - member_created).days
    account_age_years = account_age_days // 365
    account_age_months = (account_age_days % 365) // 30
    account_age_days_remainder = (account_age_days % 365) % 30

    if account_age_years > 0:
        age_string = f"{account_age_years}г {account_age_months}м {account_age_days_remainder}д"
    elif account_age_months > 0:
        age_string = f"{account_age_months}м {account_age_days_remainder}д"
    else:
        age_string = f"{account_age_days_remainder}д"

    if inviter:
        description = f"{inviter.global_name or inviter.name} | {inviter.mention} пригласил на сервер {member.global_name or member.name} {member.mention} с помощью {used_invite.code if used_invite else 'неизвестной'} инвайта.\nАккаунт {member.mention} | {member.global_name or member.name} был создан {age_string} назад.\nУ {inviter.global_name or inviter.name} {num_invites} инвайтов."
    else:
        description = f"Неизвестный пользователь пригласил на сервер {member.global_name or member.name} {member.mention} через неизвестный инвайт.\nАккаунт {member.mention} | {member.global_name or member.name} был создан {age_string} назад."

    embed = discord.Embed(
        description=description,
        color=16711680,
        timestamp=datetime.now()
    )
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

    await join_channel.send(embed=embed)


@bot.event
async def on_invite_create(invite):
    if invite.guild.id != GUILD_ID:
        return

    invites = await load_invites()
    invites[invite.code] = {
        "code": invite.code,
        "uses": invite.uses or 0,
        "inviter": str(invite.inviter.id) if invite.inviter else None,
        "inviter_name": invite.inviter.name if invite.inviter else "Unknown",
        "max_uses": invite.max_uses,
        "created_at": invite.created_at.isoformat() if invite.created_at else None
    }
    await save_invites(invites)


@bot.event
async def on_invite_delete(invite):
    if invite.guild.id != GUILD_ID:
        return

    invites = await load_invites()
    if invite.code in invites:
        del invites[invite.code]
        await save_invites(invites)


# Запуск бота
async def main():
    load_dotenv()
    token = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')

    if token == 'YOUR_BOT_TOKEN':
        print("❌ ОШИБКА: Укажите токен в файле .env")
        print("Создайте файл .env с содержимым: BOT_TOKEN=ваш_токен")
        return

    print(f"🚀 Запуск бота...")

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\n👋 Остановка бота по запросу пользователя...")
        await bot.close()
    except discord.errors.LoginFailure:
        print("❌ ОШИБКА: Неверный токен. Проверьте .env и сбросьте токен в Developer Portal.")
    except Exception as e:
        print(f"❌ ОШИБКА: Произошла ошибка: {e}")
    finally:
        print("🛑 Завершение работы...")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())