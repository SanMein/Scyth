# main.py — точка входа
import asyncio
import os

import discord
from dotenv import load_dotenv

from bot import bot, logger
from config import GUILD_ID

INITIAL_COGS = [
    'cogs.audit',
    'cogs.utility',
    'cogs.voice_tools',
    'cogs.slash_commands',
    'cogs.mention_react',
    'cogs.ai',
]


@bot.event
async def setup_hook():
    # 1. Guild-only для всех команд дерева (глобально)
    bot.tree.guild_only = True

    # 2. Загружаем когги
    for cog in INITIAL_COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f'✅ Загружен когг: {cog}')
        except Exception as e:
            logger.exception(f'❌ Ошибка загрузки {cog}: {e}')

    # 3. Синхронизация слэш-команд
    try:
        guild = discord.Object(id=GUILD_ID)

        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f'✅ Синхронизировано {len(synced)} слэш-команд с гильдией {GUILD_ID}')

        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        logger.info('✅ Глобальный реестр команд очищен')
    except Exception as e:
        logger.exception(f'❌ Ошибка синхронизации слэш-команд: {e}')


@bot.event
async def on_ready():
    logger.info(f'Бот запущен: {bot.user} (ID: {bot.user.id})')
    try:
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Частная Военная Компания «Military Special Forces — 043»",
            ),
        )
    except Exception as e:
        logger.warning(f"Не удалось установить статус: {e}")


async def main():
    load_dotenv()
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("❌ Переменная BOT_TOKEN не задана в .env")
        return

    logger.info("🚀 Запуск бота...")
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("👋 Остановка по Ctrl+C...")
    except Exception as e:
        logger.exception(f"❌ Критическая ошибка: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()
        logger.info("🛑 Завершение работы.")


if __name__ == "__main__":
    asyncio.run(main())