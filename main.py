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
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='//', intents=intents)

# Конфигурация
GUILD_ID = 1349365796949856265
ADMIN_ROLE_IDS = [
    1447513054844555336,  # ἄλφα
    1349365796970954834,  # Генеральный Директор
    1349365796970954833  # Операционный директор
]
LOG_CHANNEL_ID = 1399890569165275348
JOIN_MESSAGE_CHANNEL_ID = 1349365797515956225
AUDIT_LOG_CHANNEL_ID = 1349365797515956227
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


# Команда //ban
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


# Команда //unban
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


# Команда //kick
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


# Команда //tout (таймаут)
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


# Команда //warn
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


# Команда //unwarn
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


# Команда //clwarn
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


# Команда //clear
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


# Команда //logs для просмотра логов
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
            description="❌ Укажите пользователя для просмотра логов.\nПример: `//logs @user`",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)

# Команда //ad для отправки текста рекламы (пиара)
@bot.command(name="ad")
async def ad(ctx):
    ad_content = "```\n# MILITARY SPECIAL FORCES – 043\n\nЧастная (игровая) военная компания, специализирующаяся на проведении высокоточных тактических операций в условиях интенсивности боевых действий *(первоначально на всех шутер-играх, но в данный момент - Roblox)*.\n\nМы ищем дисциплинированных, ответственных и мотивированных участников для комплектования: штурмовых, снайперских, технических и медицинских подразделений.\n\n### Наша система квалификации\n**Карбогрейд** – это официальная система квалификации личного состава ЧВК \"MSF-043\". Она отражает уровень боевой подготовки, опыт и профессионализм оператора.  \n> Система состоит из основного боевого грейда (от К1 до К6) и специализированных веток, которые можно совмещать (гибридная модель).\n\n### Специализированные направления службы (гибридные грейды):\n- **SM (Штурмовая служба)** – ближний бой, штурм зданий, прорыв обороны. Основное вооружение: автоматы, дробовики, пулемёты.\n- **SR (Снайперская служба)** – дальняя огневая поддержка, разведка и устранение приоритетных целей.\n- **MC (Медицинская служба)** – оказание первой помощи в бою, стабилизация раненых и организация эвакуации.\n- **TN (Техническая служба)** – ремонт и модификация снаряжения, работа с наземным и воздушным транспортом.\n\n### Что мы предлагаем:\n- Чёткую военную структуру и систему субординации;\n- Регулярные совместные операции в составе групп 4–5 человек;\n- Систему обучения и повышения квалификации (от К1 до К6);\n- Возможность роста до командных должностей (Старший Оператор, Командир взвода);\n- Организованную логистику и поддержку в ходе операций;\n\n### Требования к кандидатам:\n- Возраст 16 лет и старше;\n- Готовность соблюдать Регламент (базовые правила), Положения и Приказы командования;\n- Наличие базовых навыков взаимодействия в группе;\n- Желание развиваться и проходить обучение;\n\nЕсли вы ищете не просто игру, а службу в организованной военной структуре с системой роста, дисциплиной и общими целями – ЧВК \"MSF-043\" ждёт вас.\n\nСсылка: https://discord.gg/zsYN3CdGGu\n```"
    try:
        await ctx.send(ad_content)
    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота нет прав для отправки сообщений в этот канал.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка при отправке сообщения: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)


# Команда //sinfo - информация о сервере
@bot.command(name="sinfo")
async def server_info(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f"📊 Информация о сервере: {guild.name}",
        color=0x2b2d31,
        timestamp=datetime.now()
    )

    # Основные данные
    embed.add_field(
        name="📌 Основное",
        value=f"**Название:** {guild.name}\n"
              f"**ID:** `{guild.id}`\n"
              f"**Владелец:** {guild.owner.mention if guild.owner else 'Неизвестно'}\n"
              f"**Создан:** {guild.created_at.strftime('%d.%m.%Y %H:%M:%S')}",
        inline=False
    )

    # Статистика участников
    members = guild.members
    total = len(members)
    humans = len([m for m in members if not m.bot])
    bots = len([m for m in members if m.bot])
    online = len([m for m in members if m.status != discord.Status.offline])

    embed.add_field(
        name="👥 Участники",
        value=f"**Всего:** {total}\n"
              f"**Людей:** {humans}\n"
              f"**Ботов:** {bots}\n"
              f"**Онлайн:** {online}\n"
              f"**Лимит:** {guild.max_members}",
        inline=True
    )

    # Каналы
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)

    embed.add_field(
        name="💬 Каналы",
        value=f"**Текстовых:** {text_channels}\n"
              f"**Голосовых:** {voice_channels}\n"
              f"**Категорий:** {categories}",
        inline=True
    )

    # Бустеры
    embed.add_field(
        name="🚀 Бустеры",
        value=f"**Уровень:** {guild.premium_tier}\n"
              f"**Бустеров:** {guild.premium_subscription_count}",
        inline=True
    )

    # Роли и эмодзи
    embed.add_field(
        name="🎭 Контент",
        value=f"**Ролей:** {len(guild.roles)}\n"
              f"**Эмодзи:** {len(guild.emojis)}/{guild.emoji_limit}\n"
              f"**Стикеров:** {len(guild.stickers)}/{guild.sticker_limit}",
        inline=True
    )

    # Настройки
    embed.add_field(
        name="⚙️ Настройки",
        value=f"**Уровень верификации:** {guild.verification_level}\n"
              f"**Фильтр контента:** {guild.explicit_content_filter}\n"
              f"**2FA для модерации:** {'Да' if guild.mfa_level else 'Нет'}",
        inline=False
    )

    if guild.description:
        embed.add_field(
            name="📝 Описание",
            value=guild.description[:1024],
            inline=False
        )

    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

    try:
        await ctx.send(embed=embed)
    except Exception as e:
        print(f"[Scyth] ✗ Ошибка в sinfo: {e}")
        await ctx.send(f"❌ Ошибка при отправке информации: {e}")


# Команда //tercon - расторжение контракта
@bot.command(name="termination.contract")
async def tercon(ctx, member: discord.Member, *, reason="Без причины"):
    # Проверка на наличие нужных ролей
    allowed_role_ids = [
        1349365796970954834,  # Генеральный Директор
        1349365796970954833  # Операционный директор
    ]

    if not any(role.id in allowed_role_ids for role in ctx.author.roles):
        embed = discord.Embed(
            description="❌ У вас нет прав для использования этой команды.\nТребуется роль: <@&1349365796970954834> или <@&1349365796970954833>",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    TERCON_ROLE_ID = 1502050970941657310
    tercon_role = ctx.guild.get_role(TERCON_ROLE_ID)

    if not tercon_role:
        embed = discord.Embed(
            description="❌ Роль теркона не найдена на сервере.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    # Получаем список ролей для удаления (все, кроме @everyone)
    roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role]

    if not roles_to_remove:
        embed = discord.Embed(
            description=f"❌ У пользователя {member.mention} нет ролей для снятия.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        return

    # Запоминаем названия ролей для логов
    removed_roles_names = [role.name for role in roles_to_remove]

    try:
        # Снимаем все роли
        await member.remove_roles(*roles_to_remove, reason=f"Расторжение: {reason}")
        print(f"[Scyth] ✓ Сняты все роли с {member.name}")

        # Выдача роли расторжения
        await member.add_roles(tercon_role, reason=f"Расторжение: {reason}")
        print(f"[Scyth] ✓ Выдана роль {tercon_role.name} пользователю {member.name}")

        # Отправляем сообщение в канал
        embed = discord.Embed(
            description=f"✅ Пользователь {member.mention} был расторжен.\n"
                        f"**Сняты роли:** {len(removed_roles_names)}\n"
                        f"**Выдана роль:** {tercon_role.mention}\n"
                        f"**Причина:** {reason}\n"
                        f"**Модератор:** {ctx.author.mention}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)

        # Отправляем пустой эмбед в личные сообщения
        try:
            dm_embed = discord.Embed(
                description=f"",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            dm_embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            await member.send(embed=dm_embed)
            print(f"[Scyth] ✓ Отправлен пустой эмбед в ЛС пользователю {member.name}")
        except discord.Forbidden:
            print(f"[Scyth] ✗ Не удалось отправить ЛС пользователю {member.name}")
        except Exception as e:
            print(f"[Scyth] ✗ Ошибка при отправке ЛС: {e}")

        # Логирование
        await add_moderation_log(
            "Расторжение",
            ctx.author,
            member,
            f"Причина: {reason}. Снято ролей: {', '.join(removed_roles_names)}. Выдана роль: {tercon_role.name}"
        )

    except discord.Forbidden:
        embed = discord.Embed(
            description="❌ У бота недостаточно прав для управления ролями этого пользователя.\n"
                        "Убедитесь, что роль бота находится выше выдаваемых/снимаемых ролей.",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        print(f"[Scyth] ✗ Недостаточно прав для управления ролями {member.name}")

    except discord.HTTPException as e:
        embed = discord.Embed(
            description=f"❌ Ошибка Discord API: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        print(f"[Scyth] ✗ HTTP ошибка: {e}")

    except Exception as e:
        embed = discord.Embed(
            description=f"❌ Неожиданная ошибка: {type(e).__name__}: {e}",
            color=0xff0000,
            timestamp=datetime.now()
        )
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await ctx.send(embed=embed)
        print(f"[Scyth] ✗ Неожиданная ошибка в termination.contact: {e}")

# Функция для отправки логов аудита
async def send_audit_log(guild, action, target, moderator=None, changes=None, extra_info=None):
    """Отправляет сообщение о событии в канал аудита"""
    log_channel = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not log_channel:
        return

    embed = discord.Embed(
        description=f"**{action}**",
        color=0x2b2d31,
        timestamp=datetime.now()
    )

    if target:
        embed.add_field(name="Объект", value=f"`{target}`", inline=False)

    if moderator and moderator != target:
        embed.add_field(name="Модератор", value=f"{moderator.mention} (`{moderator.id}`)", inline=True)

    if changes:
        embed.add_field(name="Изменения", value=changes, inline=False)

    if extra_info:
        embed.add_field(name="Дополнительно", value=extra_info, inline=False)

    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

    try:
        await log_channel.send(embed=embed)
    except:
        pass


# ========== КАНАЛЫ ==========

@bot.event
async def on_guild_channel_create(channel):
    """Канал создан"""
    await send_audit_log(channel.guild, "📁 Канал создан", f"{channel.mention} (`{channel.id}`)\nТип: {channel.type}",
                         channel.guild.me)


@bot.event
async def on_guild_channel_delete(channel):
    """Канал удалён"""
    await send_audit_log(channel.guild, "🗑️ Канал удалён", f"{channel.name} (`{channel.id}`)\nТип: {channel.type}",
                         channel.guild.me)


@bot.event
async def on_guild_channel_update(before, after):
    """Канал изменён"""
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")
    if before.topic != after.topic:
        changes.append(f"**Тема:** {before.topic or 'Нет'} → {after.topic or 'Нет'}")
    if before.category != after.category:
        changes.append(
            f"**Категория:** {before.category.name if before.category else 'Нет'} → {after.category.name if after.category else 'Нет'}")
    if before.position != after.position:
        changes.append(f"**Позиция:** {before.position} → {after.position}")

    # Проверка прав (NSFW, медленный режим)
    if before.is_nsfw() != after.is_nsfw():
        changes.append(f"**NSFW:** {'Включён' if after.is_nsfw() else 'Выключен'}")
    if before.slowmode_delay != after.slowmode_delay:
        changes.append(f"**Медленный режим:** {before.slowmode_delay}с → {after.slowmode_delay}с")

    if changes:
        await send_audit_log(after.guild, "✏️ Канал изменён", after.mention, after.guild.me, "\n".join(changes))


# ========== ЭМОДЗИ ==========

@bot.event
async def on_guild_emojis_update(guild, before, after):
    """Эмодзи добавлен/удалён/изменён"""
    # Добавленные эмодзи
    added = [e for e in after if e not in before]
    for emoji in added:
        await send_audit_log(guild, "😀 Эмодзи добавлен", f"{emoji} (`{emoji.id}`)\nНазвание: {emoji.name}", guild.me)

    # Удалённые эмодзи
    removed = [e for e in before if e not in after]
    for emoji in removed:
        await send_audit_log(guild, "🗑️ Эмодзи удалён", f"{emoji} (`{emoji.id}`)\nНазвание: {emoji.name}", guild.me)

    # Изменённые эмодзи
    for emoji_before in before:
        emoji_after = discord.utils.get(after, id=emoji_before.id)
        if emoji_after and emoji_before.name != emoji_after.name:
            await send_audit_log(guild, "✏️ Эмодзи изменён",
                                 f"{emoji_after} (`{emoji_after.id}`)\nНазвание: {emoji_before.name} → {emoji_after.name}",
                                 guild.me)


# ========== СЕРВЕР ==========

@bot.event
async def on_guild_update(before, after):
    """Сервер изменён"""
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")
    if before.icon != after.icon:
        changes.append(f"**Иконка:** Изменена")
    if before.banner != after.banner:
        changes.append(f"**Баннер:** Изменён")
    if before.description != after.description:
        changes.append(f"**Описание:** {before.description or 'Нет'} → {after.description or 'Нет'}")
    if before.afk_channel != after.afk_channel:
        changes.append(
            f"**AFK канал:** {before.afk_channel.mention if before.afk_channel else 'Нет'} → {after.afk_channel.mention if after.afk_channel else 'Нет'}")
    if before.system_channel != after.system_channel:
        changes.append(
            f"**Системный канал:** {before.system_channel.mention if before.system_channel else 'Нет'} → {after.system_channel.mention if after.system_channel else 'Нет'}")

    if changes:
        await send_audit_log(after, "🏠 Сервер изменён", after.name, after.me, "\n".join(changes))


# ========== ПРИГЛАШЕНИЯ ==========

@bot.event
async def on_invite_create(invite):
    """Приглашение создано"""
    info = f"Код: {invite.code}\nКанал: {invite.channel.mention}\nМакс. использований: {invite.max_uses or '∞'}\nСрок: {invite.max_age} сек"
    await send_audit_log(invite.guild, "🔗 Приглашение создано", invite.code, invite.inviter or invite.guild.me, info)


@bot.event
async def on_invite_delete(invite):
    """Приглашение удалено"""
    await send_audit_log(invite.guild, "🗑️ Приглашение удалено", invite.code, invite.guild.me)


# ========== СООБЩЕНИЯ ==========

@bot.event
async def on_message_delete(message):
    """Сообщение удалено"""
    if message.author.bot:
        return

    content = message.content[:500] if message.content else "[Без текста/Вложение]"
    info = f"Автор: {message.author.mention}\nКанал: {message.channel.mention}\n**Текст:**\n{content}"

    if message.attachments:
        info += f"\n**Вложения:** {len(message.attachments)} шт."

    await send_audit_log(message.guild, "🗑️ Сообщение удалено", f"#{message.channel.name}", message.author, info)


@bot.event
async def on_message_edit(before, after):
    """Сообщение изменено"""
    if before.author.bot:
        return
    if before.content == after.content:
        return

    info = f"Автор: {before.author.mention}\nКанал: {before.channel.mention}\n**До:**\n{before.content[:300]}\n**После:**\n{after.content[:300]}"
    await send_audit_log(before.guild, "✏️ Сообщение изменено", f"#{before.channel.name}", before.author, info)


# ========== РОЛИ ==========

@bot.event
async def on_guild_role_create(role):
    """Роль создана"""
    await send_audit_log(role.guild, "🎭 Роль создана", role.mention, role.guild.me,
                         f"Название: {role.name}\nЦвет: {role.color}\nОтображать отдельно: {role.hoist}\nУпоминаемая: {role.mentionable}")


@bot.event
async def on_guild_role_delete(role):
    """Роль удалена"""
    await send_audit_log(role.guild, "🗑️ Роль удалена", role.name, role.guild.me)


@bot.event
async def on_guild_role_update(before, after):
    """Роль изменена"""
    changes = []

    if before.name != after.name:
        changes.append(f"**Название:** {before.name} → {after.name}")
    if before.color != after.color:
        changes.append(f"**Цвет:** {before.color} → {after.color}")
    if before.permissions != after.permissions:
        changes.append(f"**Права:** Изменены")
    if before.hoist != after.hoist:
        changes.append(f"**Отдельное отображение:** {before.hoist} → {after.hoist}")
    if before.mentionable != after.mentionable:
        changes.append(f"**Упоминаемая:** {before.mentionable} → {after.mentionable}")

    if changes:
        await send_audit_log(after.guild, "✏️ Роль изменена", after.mention, after.guild.me, "\n".join(changes))


@bot.event
async def on_member_update(before, after):
    """Роль добавлена/убрана у участника"""
    # Добавленные роли
    added_roles = [r for r in after.roles if r not in before.roles and r != after.guild.default_role]
    for role in added_roles:
        await send_audit_log(after.guild, "➕ Роль добавлена", after.mention, role,
                             f"Роль: {role.mention}\nУчастник: {after.mention}")

    # Удалённые роли
    removed_roles = [r for r in before.roles if r not in after.roles and r != before.guild.default_role]
    for role in removed_roles:
        await send_audit_log(after.guild, "➖ Роль убрана", after.mention, role,
                             f"Роль: {role.mention}\nУчастник: {after.mention}")

    # Никнейм изменён
    if before.nick != after.nick:
        await send_audit_log(after.guild, "✏️ Никнейм изменён", after.mention, after,
                             f"Было: {before.nick or after.name}\nСтало: {after.nick or after.name}")


# ========== СТИКЕРЫ ==========

@bot.event
async def on_guild_stickers_update(guild, before, after):
    """Стикер создан/удалён/изменён"""
    # Добавленные стикеры
    added = [s for s in after if s not in before]
    for sticker in added:
        await send_audit_log(guild, "🏷️ Стикер добавлен", sticker.name, guild.me,
                             f"ID: {sticker.id}\nОписание: {sticker.description or 'Нет'}")

    # Удалённые стикеры
    removed = [s for s in before if s not in after]
    for sticker in removed:
        await send_audit_log(guild, "🗑️ Стикер удалён", sticker.name, guild.me)

    # Изменённые стикеры
    for sticker_before in before:
        sticker_after = discord.utils.get(after, id=sticker_before.id)
        if sticker_after:
            changes = []
            if sticker_before.name != sticker_after.name:
                changes.append(f"Название: {sticker_before.name} → {sticker_after.name}")
            if sticker_before.description != sticker_after.description:
                changes.append(
                    f"Описание: {sticker_before.description or 'Нет'} → {sticker_after.description or 'Нет'}")
            if changes:
                await send_audit_log(guild, "✏️ Стикер изменён", sticker_after.name, guild.me, "\n".join(changes))


# ========== ВЕТКИ (THREADS) ==========
@bot.event
async def on_thread_create(thread):
    """Ветка создана"""
    await send_audit_log(thread.guild, "🧵 Ветка создана", thread.mention, thread.owner or thread.guild.me,
                         f"Канал: {thread.parent.mention}\nНазвание: {thread.name}")


@bot.event
async def on_thread_delete(thread):
    """Ветка удалена"""
    await send_audit_log(thread.guild, "🗑️ Ветка удалена", thread.name, thread.guild.me)


@bot.event
async def on_thread_update(before, after):
    """Ветка изменена"""
    changes = []

    if before.name != after.name:
        changes.append(f"Название: {before.name} → {after.name}")
    if before.archived != after.archived:
        changes.append(f"Архивирована: {after.archived}")
    if before.locked != after.locked:
        changes.append(f"Заблокирована: {after.locked}")
    if before.slowmode_delay != after.slowmode_delay:
        changes.append(f"Медленный режим: {before.slowmode_delay}с → {after.slowmode_delay}с")

    if changes:
        await send_audit_log(after.guild, "✏️ Ветка изменена", after.mention, after.guild.me, "\n".join(changes))


# ========== ПОЛЬЗОВАТЕЛЬ ==========

@bot.event
async def on_user_update(before, after):
    """Пользователь изменён (глобально)"""
    changes = []

    if before.name != after.name:
        changes.append(f"Имя: {before.name} → {after.name}")
    if before.avatar != after.avatar:
        changes.append("Аватар: Изменён")
    if before.discriminator != after.discriminator and after.discriminator != "0":
        changes.append(f"Дискриминатор: {before.discriminator} → {after.discriminator}")

    if changes:
        # Ищем сервер, где есть этот пользователь
        for guild in bot.guilds:
            member = guild.get_member(after.id)
            if member:
                await send_audit_log(guild, "👤 Пользователь изменён", after.mention, after, "\n".join(changes))
                break


# ========== ГОЛОСОВЫЕ СОБЫТИЯ ==========
@bot.event
async def on_voice_state_update(member, before, after):
    """Голосовые события: подключение, отключение, перемещение, мьюты"""

    # Подключение к голосовому каналу
    if before.channel is None and after.channel is not None:
        await send_audit_log(member.guild, "🎤 Голосовое подключение", member.mention, member,
                             f"Канал: {after.channel.mention}")

    # Отключение от голосового канала
    elif before.channel is not None and after.channel is None:
        await send_audit_log(member.guild, "🔇 Голосовое отключение", member.mention, member,
                             f"Был в: {before.channel.mention}")

    # Перемещение между каналами
    elif before.channel != after.channel and before.channel is not None and after.channel is not None:
        await send_audit_log(member.guild, "🔄 Голосовое перемещение", member.mention, member,
                             f"Был: {before.channel.mention}\nСтал: {after.channel.mention}")

    # Серверный мьют (включение/отключение)
    if before.mute != after.mute:
        if after.mute:
            await send_audit_log(member.guild, "🔇 Мьют (серверный)", member.mention, after,
                                 "Участник заглушен модератором")
        else:
            await send_audit_log(member.guild, "🔊 Снятие мьюта (серверный)", member.mention, after,
                                 "Участник разглушён модератором")

    # Мьют микрофона (самостоятельный)
    if before.self_mute != after.self_mute:
        if after.self_mute:
            await send_audit_log(member.guild, "🎙️ Микрофон выключен", member.mention, member,
                                 "Участник сам выключил микрофон")
        else:
            await send_audit_log(member.guild, "🎙️ Микрофон включён", member.mention, member,
                                 "Участник сам включил микрофон")

    # Глушение по голосу (voice deafen от модератора)
    if before.deaf != after.deaf:
        if after.deaf:
            await send_audit_log(member.guild, "🔇 Глушение (серверное)", member.mention, after,
                                 "Участник оглушён модератором")
        else:
            await send_audit_log(member.guild, "🔊 Снятие глушения (серверное)", member.mention, after,
                                 "Участник разглушён модератором")

    # Самостоятельное глушение
    if before.self_deaf != after.self_deaf:
        if after.self_deaf:
            await send_audit_log(member.guild, "🎧 Глушение (самостоятельное)", member.mention, member,
                                 "Участник сам оглушился")
        else:
            await send_audit_log(member.guild, "🎧 Снятие глушения (самостоятельное)", member.mention, member,
                                 "Участник снял оглушение")

# Выдача Авто-ролей при присоединении участника
@bot.event
async def on_member_join(member):
    # Проверяем, что это нужный сервер
    if member.guild.id != GUILD_ID:
        return

    # Список ID ролей для автоматической выдачи
    AUTO_ROLES = [
        1447513458676334602,  # έψιλον
        1353491969111887904,  # ・Оперативный состав・・・>
        1349365796949856273,  # Рекрут
        1399638957955747912,  # ・Карбогрейд・・・>
        1448670667347071089,  # Ку
        1438622419073105981,  # ・Состав・・・>
        1438622602703667290  # Military Special Forces
    ]

    added_roles = []
    failed_roles = []

    for role_id in AUTO_ROLES:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role, reason="Автоматическая выдача роли при входе")
                added_roles.append(role.name)
                print(f"[Scyth] ✓ {member.name} получил роль {role.name}")
            except discord.Forbidden:
                failed_roles.append(role.name)
                print(f"[Scyth] ✗ Нет прав на выдачу роли {role.name}")
            except discord.HTTPException as e:
                failed_roles.append(role.name)
                print(f"[Scyth] ✗ Ошибка при выдаче {role.name}: {e}")
        else:
            failed_roles.append(str(role_id))
            print(f"[Scyth] ✗ Роль с ID {role_id} не найдена")

    # Лог выдачи ролей (опционально)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel and added_roles:
        embed = discord.Embed(
            description=f"📥 **{member.mention}** присоединился к серверу\n\n✅ Выданы роли: {', '.join(added_roles)}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        if failed_roles:
            embed.description += f"\n\n❌ Не удалось выдать: {', '.join(failed_roles)}"
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await log_channel.send(embed=embed)

    # Отправка приветственного сообщения в личные сообщения
    try:
        welcome_embed = discord.Embed(
            description=f"# Добро пожаловать в [ЧВК «Military Special Forces - 043»](https://discord.gg/zsYN3CdGGu)\n\n### Обязательные действия в первые 15 минут:\n> 1. Ознакомьтесь с правилами (Регламентом) сервера\n→ <#1349365797515956229>\n> 2. Пройдите регистрацию в базу данных ЧВК, открыв соответствующий тикет\n→ <#1349365797658824716>\n> 3. Пообщайтесь и ознакомьтесь с оперативниками на остальном сервере\n→ <#1349365797658824718>\n\nЕсли возникнут осложнения или проблемы – сообщите Генеральному Директору <@1086319338371428372> или команде модерации.\n\n\nПриятного дальнейшего времени.",
            color=0x9B59B6,
            timestamp=datetime.now()
        )
        welcome_embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)

        await member.send(embed=welcome_embed)
        print(f"[Scyth] ✓ Приветственное сообщение отправлено {member.name}")
    except discord.Forbidden:
        print(f"[Scyth] ✗ Не удалось отправить ЛС пользователю {member.name} (закрытые ЛС)")
    except discord.HTTPException as e:
        print(f"[Scyth] ✗ Ошибка при отправке ЛС: {e}")

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
        print("❌ ОШИБКА: Неверный токен. Необходима проверка .env и сброс токена в Developer Portal (http://discord.com/developers/applications/).")
    except Exception as e:
        print(f"❌ ОШИБКА: Произошла ошибка{e}")
    finally:
        print("🛑 Завершение работы...")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
