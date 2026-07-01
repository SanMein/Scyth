import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
import asyncio
import os
import json
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
import aiofiles
from collections import defaultdict

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
GUILD_ID = 1349365796949856265
ADMIN_ROLE_IDS = [-, -, -]
LOG_CHANNEL_ID = -
AUDIT_LOG_CHANNEL_ID = -
WARNINGS_FILE = 'warnings.json'
MODERATION_LOGS_FILE = 'moderation_logs.json'
FOOTER_TEXT = "Scyth // Σκύθ"
FOOTER_ICON = "https://i.imgur.com/IlA74Ij.png"

FLOOD_LIMIT = 5
FLOOD_WINDOW = 2
FLOOD_MUTE = 300
MENTION_LIMIT = 3
MENTION_WINDOW = 5
MENTION_MUTE = 900
IMMUNE_ROLES = [-, -]

CONTRACT_ROLES = [-, -, -, -, -, -, -]
TERCON_ROLE_ID = -

AD_CONTENT = "```\n# MILITARY SPECIAL FORCES – 043\n\nЧастная (игровая) военная компания, специализирующаяся на проведении высокоточных тактических операций...\n\nСсылка: https://discord.gg/zsYN3CdGGu\n```"

# ============================================================
# НАСТРОЙКА БОТА
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='//', intents=intents)

# Анти-спам кэш
flood_cache = defaultdict(list)
mention_cache = defaultdict(list)
violation_counter = defaultdict(list)
DISCORD_INVITE_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li|com/invite)|discordapp\.com/invite)/[a-zA-Z0-9\-_]+', re.IGNORECASE)

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
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
        units = {'m': timedelta(minutes=value), 'h': timedelta(hours=value), 'd': timedelta(days=value), 'w': timedelta(weeks=value), 'y': timedelta(days=value*365)}
        return units.get(unit, timedelta(minutes=5))
    except:
        return timedelta(minutes=5)

def create_embed(description, color=0xff0000):
    embed = discord.Embed(description=description, color=color, timestamp=datetime.now())
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed

async def add_moderation_log(action, moderator, target, reason, duration=None):
    logs = await load_moderation_logs()
    log_entry = {"action": action, "moderator": str(moderator), "moderator_name": moderator.name if hasattr(moderator,'name') else str(moderator), "target": str(target), "target_name": target.name if hasattr(target,'name') else str(target), "reason": reason, "duration": duration, "date": datetime.now().isoformat()}
    if str(target) not in logs: logs[str(target)] = []
    logs[str(target)].append(log_entry)
    await save_moderation_logs(logs)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(embed=create_embed(f"**{action}**\nМодератор: {moderator.mention if hasattr(moderator,'mention') else moderator}\nЦель: {target.mention if hasattr(target,'mention') else target}\nПричина: {reason}\nВремя: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", 0xff0000 if action in ["Бан","Кик","Таймаут"] else 0xffaa00))

def has_admin_role(member):
    return any(role.id in ADMIN_ROLE_IDS for role in member.roles)

def has_director_role(member):
    return any(role.id in [1349365796970954834, 1349365796970954833] for role in member.roles)

# ============================================================
# АНТИ-СПАМ ФУНКЦИИ
# ============================================================
async def check_flood(message):
    now = datetime.now()
    uid = message.author.id
    flood_cache[uid].append(now)
    flood_cache[uid] = [t for t in flood_cache[uid] if (now - t).total_seconds() <= FLOOD_WINDOW]
    if len(flood_cache[uid]) > FLOOD_LIMIT:
        await delete_spam_messages(message)
        await apply_antispam(message.author, FLOOD_MUTE, "5.1: Запрещён спам, флуд, капс, повторение сообщений/эмодзи, массовые реакции и любое действие, перегружающее каналы.", "Флуд")
        flood_cache[uid].clear()
        await log_violation(message, "Флуд", f"{len(flood_cache[uid])} сообщений за {FLOOD_WINDOW}с")
    elif len(flood_cache[uid]) == 1 and (now - flood_cache[uid][0]).total_seconds() > 10:
        flood_cache[uid].clear()

async def check_mentions(message):
    if message.mention_everyone:
        await message.delete()
        await apply_antispam(message.author, MENTION_MUTE, "5.8: Запрещены массовые упоминания.", "@everyone/@here")
        await message.channel.send(f"{message.author.mention} использование @everyone/@here запрещено. Таймаут 15 минут.", delete_after=10)
        return
    total = len(message.mentions) + len(message.role_mentions)
    if total > 0:
        now = datetime.now()
        uid = message.author.id
        mention_cache[uid].append({"time": now, "count": total, "message_id": message.id})
        mention_cache[uid] = [m for m in mention_cache[uid] if (now - m["time"]).total_seconds() <= MENTION_WINDOW]
        total_count = sum(m["count"] for m in mention_cache[uid])
        if total_count >= MENTION_LIMIT:
            for m_data in mention_cache[uid]:
                try: await (await message.channel.fetch_message(m_data["message_id"])).delete()
                except: pass
            await apply_antispam(message.author, MENTION_MUTE, "5.8: Запрещены массовые упоминания.", "Массовые упоминания")
            mention_cache[uid].clear()
            await log_violation(message, "Массовые упоминания", f"{total_count} упоминаний за {MENTION_WINDOW}с")

async def check_links(message):
    invites = DISCORD_INVITE_PATTERN.findall(message.content)
    if invites:
        await message.delete()
        await apply_antispam(message.author, None, "5.1: Запрещено распространение ссылок на сторонние Discord-сервера.", "Запрещённая ссылка")
        await message.channel.send(f"{message.author.mention} публикация ссылок на Discord-сервера запрещена.", delete_after=10)
        await log_violation(message, "Запрещённая ссылка", f"Найдены: {', '.join(invites)}")

async def delete_spam_messages(message):
    try:
        async for msg in message.channel.history(limit=FLOOD_LIMIT + 1):
            if msg.author.id == message.author.id: await msg.delete()
    except: pass

async def apply_antispam(member, duration, reason, vtype):
    uid = member.id
    violation_counter[uid].append({"time": datetime.now().isoformat(), "type": vtype, "reason": reason})
    warnings = await load_warnings()
    if str(uid) not in warnings: warnings[str(uid)] = []
    warnings[str(uid)].append({"reason": reason, "duration": "permanent", "moderator": "Анти-спам система", "date": datetime.now().isoformat()})
    await save_warnings(warnings)
    if duration:
        try: await member.timeout(timedelta(seconds=duration), reason=reason)
        except: pass
    wc = len(warnings[str(uid)])
    try: await member.send(embed=create_embed(f"## ⚠️ Нарушение: {vtype}\n\n**Причина:** {reason}\n\n{'⏳ **Таймаут:** ' + str(duration//60) + ' минут' if duration else ''}\n⚠️ **Предупреждение:** #{wc}\n\nЗа 3 предупреждения - таймаут 30 мин,\nза 6 - таймаут 3 часа, за 10 - перманентный бан.\n\n-# Ошибка? → <@1086319338371428372>", 0xFFA500))
    except: pass

async def log_violation(message, vtype, details):
    ch = bot.get_channel(LOG_CHANNEL_ID)
    if ch: await ch.send(embed=create_embed(f"**🛡️ Анти-спам: {vtype}**\n**Нарушитель:** {message.author.mention}\n**Канал:** {message.channel.mention}\n**Детали:** {details}\n**Время:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", 0xFFA500))

# ============================================================
# ОБРАБОТЧИК СООБЩЕНИЙ (АНТИ-СПАМ)
# ============================================================
@bot.event
async def on_message(message):
    if message.author.bot: await bot.process_commands(message); return
    if not message.guild: await bot.process_commands(message); return
    if message.author.id == message.guild.owner_id: await bot.process_commands(message); return
    if any(role.id in IMMUNE_ROLES for role in message.author.roles): await bot.process_commands(message); return
    await check_flood(message)
    await check_mentions(message)
    await check_links(message)
    await bot.process_commands(message)

# ============================================================
# МОДАЛЬНЫЕ ОКНА
# ============================================================
class BanModal(Modal, title="🔨 Блокировка пользователя"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    dur = TextInput(label="Длительность (пусто = навсегда)", placeholder="1d / 30m / 12h", required=False)
    reason = TextInput(label="Причина", placeholder="Причина блокировки", required=False, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        if not self.uid.value.isdigit(): await interaction.response.send_message(embed=create_embed("❌ Неверный ID."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        try: user = await bot.fetch_user(int(self.uid.value))
        except: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        reason = self.reason.value or "Без причины"
        try:
            if self.dur.value:
                delta = parse_duration(self.dur.value)
                await guild.ban(user, reason=reason, delete_message_days=0)
                try: await user.send(embed=create_embed(f"🔨 Вы заблокированы на сервере **MSF-043** по причине **{reason}** на **{self.dur.value}**.", 0xff0000))
                except: pass
                await interaction.response.send_message(embed=create_embed(f"✅ **{user.name}** забанен на **{self.dur.value}**. Причина: {reason}", 0x00ff00))
                await add_moderation_log("Временный бан", interaction.user, user, reason, self.dur.value)
                await asyncio.sleep(delta.total_seconds())
                await guild.unban(user, reason="Истек временный бан")
                ch = bot.get_channel(LOG_CHANNEL_ID)
                if ch: await ch.send(embed=create_embed(f"🔓 **{user.name}** разбанен автоматически.", 0x00ff00))
            else:
                await guild.ban(user, reason=reason, delete_message_days=0)
                try: await user.send(embed=create_embed(f"🔨 Вы перманентно заблокированы на сервере **MSF-043** по причине **{reason}**.", 0xff0000))
                except: pass
                await interaction.response.send_message(embed=create_embed(f"✅ **{user.name}** перманентно забанен. Причина: {reason}", 0x00ff00))
                await add_moderation_log("Перманентный бан", interaction.user, user, reason)
        except discord.Forbidden: await interaction.response.send_message(embed=create_embed("❌ Нет прав для бана."), ephemeral=True)
        except Exception as e: await interaction.response.send_message(embed=create_embed(f"❌ Ошибка: {e}"), ephemeral=True)

class UnbanModal(Modal, title="🔓 Разблокировка"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    reason = TextInput(label="Причина", required=False, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        if not self.uid.value.isdigit(): await interaction.response.send_message(embed=create_embed("❌ Неверный ID."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        try: user = await bot.fetch_user(int(self.uid.value))
        except: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        reason = self.reason.value or "Без причины"
        try:
            bans = await guild.bans()
            if any(ban.user.id == int(self.uid.value) for ban in bans):
                await guild.unban(user, reason=reason)
                try: await user.send(embed=create_embed(f"🔓 Вы разблокированы на сервере **MSF-043**. Причина: **{reason}**\nСсылка: https://discord.gg/zsYN3CdGGu", 0x00ff00))
                except: pass
                await interaction.response.send_message(embed=create_embed(f"✅ **{user.name}** разбанен.", 0x00ff00))
                await add_moderation_log("Разбан", interaction.user, user, reason)
            else: await interaction.response.send_message(embed=create_embed(f"❌ **{user.name}** не забанен."), ephemeral=True)
        except discord.Forbidden: await interaction.response.send_message(embed=create_embed("❌ Нет прав для разбана."), ephemeral=True)
        except Exception as e: await interaction.response.send_message(embed=create_embed(f"❌ Ошибка: {e}"), ephemeral=True)

class KickModal(Modal, title="👢 Кик"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    reason = TextInput(label="Причина", required=False, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(int(self.uid.value)) if self.uid.value.isdigit() else None
        if not member: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден на сервере."), ephemeral=True); return
        reason = self.reason.value or "Без причины"
        try:
            await member.kick(reason=reason)
            try: await member.send(embed=create_embed(f"👢 Вы кикнуты с сервера **MSF-043** по причине **{reason}**.\nСсылка: https://discord.gg/zsYN3CdGGu", 0xffaa00))
            except: pass
            await interaction.response.send_message(embed=create_embed(f"✅ {member.mention} кикнут.", 0x00ff00))
            await add_moderation_log("Кик", interaction.user, member, reason)
        except discord.Forbidden: await interaction.response.send_message(embed=create_embed("❌ Нет прав для кика."), ephemeral=True)
        except Exception as e: await interaction.response.send_message(embed=create_embed(f"❌ Ошибка: {e}"), ephemeral=True)

class TimeoutModal(Modal, title="⏱️ Таймаут"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    dur = TextInput(label="Длительность", placeholder="30m / 3h / 1d")
    reason = TextInput(label="Причина", required=False, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(int(self.uid.value)) if self.uid.value.isdigit() else None
        if not member: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        delta = parse_duration(self.dur.value)
        reason = self.reason.value or "Без причины"
        try:
            await member.timeout(delta, reason=reason)
            try: await member.send(embed=create_embed(f"🔇 Таймаут на сервере **MSF-043** по причине **{reason}** на **{self.dur.value}**.", 0xffaa00))
            except: pass
            await interaction.response.send_message(embed=create_embed(f"✅ {member.mention} получил таймаут на **{self.dur.value}**.", 0x00ff00))
            await add_moderation_log("Таймаут", interaction.user, member, reason, self.dur.value)
        except discord.Forbidden: await interaction.response.send_message(embed=create_embed("❌ Нет прав для таймаута."), ephemeral=True)
        except Exception as e: await interaction.response.send_message(embed=create_embed(f"❌ Ошибка: {e}"), ephemeral=True)

class WarnModal(Modal, title="⚠️ Предупреждение"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    reason = TextInput(label="Причина", required=True, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(int(self.uid.value)) if self.uid.value.isdigit() else None
        if not member: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        warnings = await load_warnings()
        uid = str(member.id)
        if uid not in warnings: warnings[uid] = []
        warnings[uid].append({"reason": self.reason.value, "duration": "permanent", "moderator": str(interaction.user), "date": datetime.now().isoformat()})
        await save_warnings(warnings)
        wc = len(warnings[uid])
        try: await member.send(embed=create_embed(f"⚠️ Предупреждение **(#{wc})** на сервере **MSF-043** по причине **{self.reason.value}**.\n\n3 предупреждения = таймаут 30 мин, 6 = 3 часа, 10 = бан.\n-# Ошибка? → <@1086319338371428372>", 0xffaa00))
        except: pass
        await interaction.response.send_message(embed=create_embed(f"⚠️ {member.mention} получил предупреждение #{wc}.", 0xffaa00))
        await add_moderation_log("Предупреждение", interaction.user, member, self.reason.value, "permanent")
        if wc == 3: await member.timeout(timedelta(minutes=30), reason="3 предупреждения"); await interaction.channel.send(embed=create_embed(f"🔇 {member.mention} таймаут 30 мин (3 предупреждения).", 0xffaa00))
        elif wc == 6: await member.timeout(timedelta(hours=3), reason="6 предупреждений"); await interaction.channel.send(embed=create_embed(f"🔇 {member.mention} таймаут 3 часа (6 предупреждений).", 0xffaa00))
        elif wc >= 10: await member.ban(reason="10 предупреждений"); await interaction.channel.send(embed=create_embed(f"🔨 {member.mention} забанен (10 предупреждений).", 0xff0000))

class ClearModal(Modal, title="🧹 Очистка чата"):
    count = TextInput(label="Количество сообщений (1-1000)", placeholder="100")
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        try: c = int(self.count.value)
        except: await interaction.response.send_message(embed=create_embed("❌ Введите число."), ephemeral=True); return
        if c <= 0 or c > 1000: await interaction.response.send_message(embed=create_embed("❌ От 1 до 1000."), ephemeral=True); return
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=c)
        msg = await interaction.channel.send(embed=create_embed(f"✅ Удалено **{len(deleted)}** сообщений.", 0x00ff00))
        await add_moderation_log("Очистка чата", interaction.user, interaction.channel, f"Удалено {len(deleted)} сообщений")
        await asyncio.sleep(3); await msg.delete()

class LogsModal(Modal, title="📋 Логи"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    async def on_submit(self, interaction: discord.Interaction):
        if not has_admin_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Нет прав."), ephemeral=True); return
        logs = await load_moderation_logs()
        if self.uid.value in logs and logs[self.uid.value]:
            user_logs = logs[self.uid.value][-15:]
            embed = discord.Embed(title=f"📋 Логи модерации", color=0x00aaff, timestamp=datetime.now())
            embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
            for log in user_logs:
                date = datetime.fromisoformat(log['date']).strftime('%d.%m.%Y %H:%M')
                embed.add_field(name=f"{log['action']} ({date})", value=f"Модератор: {log['moderator_name']}\nПричина: {log['reason']}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else: await interaction.response.send_message(embed=create_embed("❌ Логов не найдено."), ephemeral=True)

class TerconModal(Modal, title="⚠️ Расторжение контракта"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    reason = TextInput(label="Причина", required=True, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_director_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Требуется роль Генерального или Операционного директора."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(int(self.uid.value)) if self.uid.value.isdigit() else None
        if not member: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        tr = guild.get_role(TERCON_ROLE_ID)
        if not tr: await interaction.response.send_message(embed=create_embed("❌ Роль теркона не найдена."), ephemeral=True); return
        roles_to_remove = [r for r in member.roles if r != guild.default_role]
        if not roles_to_remove: await interaction.response.send_message(embed=create_embed("❌ Нет ролей для снятия."), ephemeral=True); return
        removed = [r.name for r in roles_to_remove]
        try:
            await member.remove_roles(*roles_to_remove, reason=f"Расторжение: {self.reason.value}")
            await member.add_roles(tr, reason=f"Расторжение: {self.reason.value}")
            await interaction.response.send_message(embed=create_embed(f"✅ Контракт с {member.mention} расторгнут.\n**Причина:** {self.reason.value}\n**Снято ролей:** {len(removed)}\n**Выдана роль:** {tr.mention}", 0x00ff00))
            try: await member.send(embed=create_embed(f"## ⚠️ Контракт расторгнут\nВы расторжены с **[ЧВК \"MSF-043\"](https://discord.gg/zsYN3CdGGu)** по причине: **«{self.reason.value}»**\n\nПрава отсутствуют до повторного заключения.\n### Повторная регистрация:\nТикет в <#1349365797658824716>\n-# Проблемы? → <@1086319338371428372>", 0xE91E63))
            except: pass
            await add_moderation_log("Расторжение", interaction.user, member, f"Причина: {self.reason.value}. Снято: {', '.join(removed)}. Выдана: {tr.name}")
        except Exception as e: await interaction.response.send_message(embed=create_embed(f"❌ Ошибка: {e}"), ephemeral=True)

class ContractModal(Modal, title="✅ Заключение контракта"):
    uid = TextInput(label="ID пользователя", placeholder="123456789012345678")
    reason = TextInput(label="Причина", required=True, max_length=500, style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        if not has_director_role(interaction.user): await interaction.response.send_message(embed=create_embed("❌ Требуется роль Директора."), ephemeral=True); return
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(int(self.uid.value)) if self.uid.value.isdigit() else None
        if not member: await interaction.response.send_message(embed=create_embed("❌ Пользователь не найден."), ephemeral=True); return
        added, failed = [], []
        for rid in CONTRACT_ROLES:
            role = guild.get_role(rid)
            if role:
                try: await member.add_roles(role, reason=f"Контракт: {self.reason.value}"); added.append(role.mention)
                except: failed.append(role.name)
            else: failed.append(str(rid))
        if added:
            await interaction.response.send_message(embed=create_embed(f"✅ Контракт с {member.mention} заключён.\n**Причина:** {self.reason.value}\n**Выданы роли:** {', '.join(added)}" + (f"\n❌ Не выданы: {', '.join(failed)}" if failed else ""), 0x2ECC71))
            try: await member.send(embed=create_embed(f"## ✅ Контракт заключён\nВы приняты в **[ЧВК \"MSF-043\"](https://discord.gg/zsYN3CdGGu)** по причине: **«{self.reason.value}»**\n\nПрава восстановлены.\n-# Проблемы? → <@1086319338371428372>", 0x2ECC71))
            except: pass
            await add_moderation_log("Заключение контракта", interaction.user, member, f"Причина: {self.reason.value}. Выданы: {', '.join(added)}")
        else: await interaction.response.send_message(embed=create_embed("❌ Не удалось выдать ни одной роли."), ephemeral=True)

class AdModal(Modal, title="📢 Реклама ЧВК"):
    confirm = TextInput(label="Напишите 'ОТПРАВИТЬ' для подтверждения", placeholder="ОТПРАВИТЬ")
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "ОТПРАВИТЬ": await interaction.response.send_message(embed=create_embed("❌ Подтверждение не пройдено."), ephemeral=True); return
        await interaction.response.send_message(AD_CONTENT)

class SinfoModal(Modal, title="📊 Информация о сервере"):
    confirm = TextInput(label="Напишите 'ОК' для получения информации", placeholder="ОК")
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "ОК": await interaction.response.send_message(embed=create_embed("❌ Неверно."), ephemeral=True); return
        guild = interaction.guild
        m = guild.members
        embed = discord.Embed(title=f"📊 {guild.name}", color=0x2b2d31, timestamp=datetime.now())
        embed.add_field(name="📌 Основное", value=f"**Название:** {guild.name}\n**ID:** `{guild.id}`\n**Владелец:** {guild.owner.mention}\n**Создан:** {guild.created_at.strftime('%d.%m.%Y %H:%M:%S')}", inline=False)
        embed.add_field(name="👥 Участники", value=f"**Всего:** {len(m)}\n**Людей:** {len([x for x in m if not x.bot])}\n**Ботов:** {len([x for x in m if x.bot])}\n**Онлайн:** {len([x for x in m if x.status != discord.Status.offline])}", inline=True)
        embed.add_field(name="💬 Каналы", value=f"**Текстовых:** {len(guild.text_channels)}\n**Голосовых:** {len(guild.voice_channels)}\n**Категорий:** {len(guild.categories)}", inline=True)
        embed.add_field(name="🚀 Бустеры", value=f"**Уровень:** {guild.premium_tier}\n**Бустеров:** {guild.premium_subscription_count}", inline=True)
        embed.add_field(name="🎭 Контент", value=f"**Ролей:** {len(guild.roles)}\n**Эмодзи:** {len(guild.emojis)}/{guild.emoji_limit}\n**Стикеров:** {len(guild.stickers)}/{guild.sticker_limit}", inline=True)
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await interaction.response.send_message(embed=embed)

# ============================================================
# КОМАНДЫ-ТРИГГЕРЫ ДЛЯ МОДАЛЬНЫХ ОКОН
# ============================================================
@bot.command(name="ban")
async def ban_cmd(ctx): await ctx.send(view=ModalView(BanModal()))

@bot.command(name="unban")
async def unban_cmd(ctx): await ctx.send(view=ModalView(UnbanModal()))

@bot.command(name="kick")
async def kick_cmd(ctx): await ctx.send(view=ModalView(KickModal()))

@bot.command(name="tout")
async def tout_cmd(ctx): await ctx.send(view=ModalView(TimeoutModal()))

@bot.command(name="warn")
async def warn_cmd(ctx): await ctx.send(view=ModalView(WarnModal()))

@bot.command(name="clear")
async def clear_cmd(ctx): await ctx.send(view=ModalView(ClearModal()))

@bot.command(name="logs")
async def logs_cmd(ctx): await ctx.send(view=ModalView(LogsModal()))

@bot.command(name="termination.contract")
async def tercon_cmd(ctx): await ctx.send(view=ModalView(TerconModal()))

@bot.command(name="conclusion.contract")
async def contract_cmd(ctx): await ctx.send(view=ModalView(ContractModal()))

@bot.command(name="ad")
async def ad_cmd(ctx): await ctx.send(view=ModalView(AdModal()))

@bot.command(name="sinfo")
async def sinfo_cmd(ctx): await ctx.send(view=ModalView(SinfoModal()))

# ============================================================
# VIEW ДЛЯ МОДАЛЬНЫХ ОКОН
# ============================================================
class ModalView(View):
    def __init__(self, modal):
        super().__init__(timeout=300)
        self.modal = modal
    @discord.ui.button(label="Открыть форму", style=discord.ButtonStyle.primary, emoji="📝")
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(self.modal)

# ============================================================
# СОБЫТИЯ СЕРВЕРА (АУДИТ)
# ============================================================
async def send_audit_log(guild, action, target, moderator=None, changes=None, extra_info=None):
    ch = guild.get_channel(AUDIT_LOG_CHANNEL_ID)
    if not ch: return
    embed = discord.Embed(description=f"**{action}**", color=0x2b2d31, timestamp=datetime.now())
    if target: embed.add_field(name="Объект", value=f"`{target}`", inline=False)
    if moderator and moderator != target: embed.add_field(name="Модератор", value=f"{moderator.mention} (`{moderator.id}`)", inline=True)
    if changes: embed.add_field(name="Изменения", value=changes, inline=False)
    if extra_info: embed.add_field(name="Дополнительно", value=extra_info, inline=False)
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    try: await ch.send(embed=embed)
    except: pass

@bot.event
async def on_guild_channel_create(channel): await send_audit_log(channel.guild, "📁 Канал создан", f"{channel.mention} (`{channel.id}`)", channel.guild.me)
@bot.event
async def on_guild_channel_delete(channel): await send_audit_log(channel.guild, "🗑️ Канал удалён", f"{channel.name} (`{channel.id}`)", channel.guild.me)
@bot.event
async def on_guild_channel_update(before, after):
    changes = []
    if before.name != after.name: changes.append(f"**Название:** {before.name} → {after.name}")
    if before.topic != after.topic: changes.append(f"**Тема:** {before.topic or 'Нет'} → {after.topic or 'Нет'}")
    if changes: await send_audit_log(after.guild, "✏️ Канал изменён", after.mention, after.guild.me, "\n".join(changes))

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    content = message.content[:500] if message.content else "[Без текста/Вложение]"
    await send_audit_log(message.guild, "🗑️ Сообщение удалено", f"#{message.channel.name}", message.author, f"Автор: {message.author.mention}\n**Текст:**\n{content}")

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content: return
    await send_audit_log(before.guild, "✏️ Сообщение изменено", f"#{before.channel.name}", before.author, f"**До:**\n{before.content[:300]}\n**После:**\n{after.content[:300]}")

@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID: return
    ch = bot.get_channel(LOG_CHANNEL_ID)
    if ch: await ch.send(embed=create_embed(f"📥 **{member.mention}** присоединился к серверу.", 0x00ff00))
    try:
        welcome_embed = create_embed(f"# Добро пожаловать в [ЧВК «Military Special Forces - 043»](https://discord.gg/zsYN3CdGGu)\n\n### Обязательные действия:\n> 1. Ознакомьтесь с регламентом\n→ <#1349365797515956229>\n> 2. Пройдите регистрацию\n→ <#1349365797658824716>\n> 3. Общий чат\n→ <#1349365797658824718>\n\n-# Проблемы? → <@1086319338371428372>", 0x9B59B6)
        await member.send(embed=welcome_embed)
    except: pass

# ============================================================
# КАСТОМНЫЙ HELP
# ============================================================
class CustomHelp(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="📚 Команды Скифа", description="`//help <команда>` для деталей", color=0x2b2d31, timestamp=datetime.now())
        cats = {"🛡️ Модерация": ["ban","unban","kick","tout","warn","clear","logs"], "📋 Контракты": ["termination.contract","conclusion.contract"], "📢 Прочее": ["ad","sinfo"]}
        for cat, cmds in cats.items():
            names = []
            for c in cmds:
                cmd = self.context.bot.get_command(c)
                if cmd: names.append(f"`//{c}` - {cmd.short_doc or 'Нет описания'}")
            if names: embed.add_field(name=cat, value="\n".join(names), inline=False)
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await self.context.send(embed=embed)
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"📖 //{command.name}", description=command.help or "Нет описания", color=0x2b2d31, timestamp=datetime.now())
        if command.signature: embed.add_field(name="📝 Использование", value=f"`//{command.name} {command.signature}`", inline=False)
        embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
        await self.context.send(embed=embed)

bot.help_command = CustomHelp()

# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    load_dotenv()
    token = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN')
    if token == 'YOUR_BOT_TOKEN': print("❌ Укажите токен в .env"); return
    print("🚀 Запуск бота...")
    try: await bot.start(token)
    except KeyboardInterrupt: print("\n👋 Остановка..."); await bot.close()
    except discord.errors.LoginFailure: print("❌ Неверный токен.")
    except Exception as e: print(f"❌ Ошибка: {e}")
    finally: print("🛑 Завершение."); await bot.close()

if __name__ == "__main__": asyncio.run(main())
