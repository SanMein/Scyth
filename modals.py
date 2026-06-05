# modals.py - все модальные окна
import discord
from discord.ui import Modal, TextInput
from datetime import datetime

class BanModal(Modal, title="🔨 Блокировка пользователя"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    duration = TextInput(label="Длительность (пусто = навсегда)", placeholder="1d / 30m / 12h", required=False)
    reason = TextInput(label="Причина", placeholder="Причина блокировки", required=False, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Логика из команды ban переносится сюда
        # Использовать interaction.client вместо bot
        pass

class UnbanModal(Modal, title="🔓 Разблокировка пользователя"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    reason = TextInput(label="Причина", placeholder="Причина разблокировки", required=False, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class KickModal(Modal, title="👢 Кик пользователя"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    reason = TextInput(label="Причина", placeholder="Причина кика", required=False, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class TimeoutModal(Modal, title="⏱️ Таймаут пользователя"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    duration = TextInput(label="Длительность", placeholder="30m / 3h / 1d", required=True)
    reason = TextInput(label="Причина", placeholder="Причина таймаута", required=False, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class WarnModal(Modal, title="⚠️ Предупреждение"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    reason = TextInput(label="Причина", placeholder="Причина предупреждения", required=True, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class ClearModal(Modal, title="🧹 Очистка чата"):
    count = TextInput(label="Количество сообщений", placeholder="100", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class TerconModal(Modal, title="⚠️ Расторжение контракта"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    reason = TextInput(label="Причина", placeholder="Причина расторжения", required=True, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class ContractModal(Modal, title="✅ Заключение контракта"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    reason = TextInput(label="Причина", placeholder="Причина заключения", required=True, max_length=500, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class AdModal(Modal, title="📢 Реклама ЧВК"):
    confirm = TextInput(label="Напишите 'ОТПРАВИТЬ' для подтверждения", placeholder="ОТПРАВИТЬ", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class SinfoModal(Modal, title="📊 Информация о сервере"):
    confirm = TextInput(label="Напишите 'ОК' для получения информации", placeholder="ОК", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class LogsModal(Modal, title="📋 Логи пользователя"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class UnwarnModal(Modal, title="🔧 Снятие предупреждения"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)
    warn_number = TextInput(label="Номер предупреждения (пусто = последнее)", placeholder="3", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass

class ClwarnModal(Modal, title="🗑️ Очистка предупреждений"):
    user_id = TextInput(label="ID пользователя", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        pass