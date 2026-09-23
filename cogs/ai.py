# cogs/ai.py — AI-ответы (DeepSeek) на упоминание бота и слэш-команду /ask
import uuid

import discord
from discord import app_commands
from discord.ext import commands

from bot import logger
from config import (
    GUILD_ID,
    AI_CONTEXT_MESSAGES,
    AI_IGNORED_CHANNELS,
    FOOTER_ICON,
)
from utils.containers import build_container
from utils.ai_client import ask
from utils import rag


class AI(commands.Cog, name="AI-ассистент"):
    """AI-ответы от DeepSeek с поиском по документам."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- Сбор контекста канала ----------

    async def _collect_history(
        self,
        channel: discord.abc.Messageable,
        limit: int = AI_CONTEXT_MESSAGES,
    ) -> list[dict]:
        history: list[dict] = []
        try:
            async for msg in channel.history(limit=limit):
                if not msg.content:
                    continue
                if msg.author.id == self.bot.user.id:
                    continue
                role = "assistant" if msg.author.bot else "user"
                author_name = msg.author.display_name
                content = f"{author_name}: {msg.content}" if role == "user" else msg.content
                history.append({"role": role, "content": content})
        except discord.Forbidden:
            logger.warning(f"Нет прав читать историю канала {channel.id}")

        history.reverse()
        return history

    # ---------- RAG-контекст ----------

    async def _build_rag_context(self, question: str, top_k: int = 3) -> str:
        hits = await rag.search(question, top_k=top_k)
        if not hits:
            return ""

        lines = ["Релевантные выдержки из документов ЧВК «MSF-043»:"]
        for i, h in enumerate(hits, 1):
            lines.append(f"\n[{i}] Из документа «{h['title']}»:")
            lines.append(h["text"])

        return "\n".join(lines)

    # ---------- Общая логика ответа ----------

    async def _answer(self, question: str, channel) -> str:
        history = await self._collect_history(channel)
        rag_context = await self._build_rag_context(question)

        if rag_context:
            full_question = (
                f"{rag_context}\n\n"
                f"---\n\n"
                f"На основании приведённых выдержек и общих знаний ответь на вопрос.\n"
                f"Если в выдержках нет ответа — скажи, что информации в документах нет.\n\n"
                f"Вопрос: {question}"
            )
        else:
            full_question = question

        return await ask(full_question, history)

    # ---------- Реакция на упоминание ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.guild.id != GUILD_ID:
            return
        if self.bot.user not in message.mentions:
            return
        if message.channel.id in AI_IGNORED_CHANNELS:
            return

        if (
            message.reference
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author.id == self.bot.user.id
        ):
            return

        question = message.content
        for m in message.mentions:
            if m.id == self.bot.user.id:
                question = question.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        question = question.strip() or "О чём запрос?"

        async with message.channel.typing():
            answer = await self._answer(question, message.channel)

        text = (
            f"# Ответ\n"
            f"-# Запрос от {message.author.mention}\n\n"
            f"{answer}"
        )
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        try:
            await message.reply(view=view, mention_author=False)
        except discord.Forbidden:
            logger.warning(f"Нет прав ответить в {message.channel.id}")
        except Exception as e:
            logger.exception(f"Ошибка отправки AI-ответа: {e}")

    # ---------- /ask ----------

    @app_commands.command(name="ask", description="Задать вопрос AI-ассистенту")
    @app_commands.describe(question="Текст вопроса")
    @app_commands.guild_only()
    async def ask_cmd(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer(thinking=True)

        answer = await self._answer(question, interaction.channel)

        text = (
            f"# Ответ\n"
            f"-# Запрос от {interaction.user.mention}\n\n"
            f"**Вопрос:** {question}\n\n"
            f"**Ответ:** {answer}"
        )
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        await interaction.followup.send(view=view)

    # ---------- /ai-reset ----------

    @app_commands.command(name="ai-reset", description="Сбросить контекст диалога в этом канале")
    @app_commands.guild_only()
    async def ai_reset(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"✅ Контекст будет собран заново из последних {AI_CONTEXT_MESSAGES} сообщений канала.",
            ephemeral=True,
        )

    # ---------- /doc-add ----------

    @app_commands.command(name="doc-add", description="Добавить документ в базу знаний")
    @app_commands.describe(
        title="Название документа",
        content="Текст (если короткий) или оставьте пустым и прикрепите файл",
        file="Файл .txt / .md (опционально)",
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def doc_add(
        self,
        interaction: discord.Interaction,
        title: str,
        content: str | None = None,
        file: discord.Attachment | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        text = content or ""
        if file is not None:
            try:
                raw = await file.read()
                text = raw.decode("utf-8", errors="ignore")
            except Exception as e:
                await interaction.followup.send(f"❌ Не удалось прочитать файл: {e}", ephemeral=True)
                return

        if not text.strip():
            await interaction.followup.send("❌ Документ пустой.", ephemeral=True)
            return

        doc_id = uuid.uuid4().hex[:12]
        chunks = await rag.add_document(
            doc_id=doc_id,
            title=title,
            content=text,
            source=f"uploaded by {interaction.user}",
        )

        await interaction.followup.send(
            f"✅ Документ **{title}** добавлен.\n"
            f"> ID: `{doc_id}`\n"
            f"> Чанков: {chunks}",
            ephemeral=True,
        )

    # ---------- /doc-list ----------

    @app_commands.command(name="doc-list", description="Список документов в базе знаний")
    @app_commands.guild_only()
    async def doc_list(self, interaction: discord.Interaction):
        docs = rag.list_documents()
        if not docs:
            await interaction.response.send_message("📭 База знаний пуста.", ephemeral=True)
            return

        lines = [f"• `{did}` — **{info['title']}** ({info['chunks']} чанков)" for did, info in docs.items()]
        text = f"# 📚 Документы в базе ({len(docs)})\n" + "\n".join(lines)
        view = build_container(text, accent_color=0x3498DB)
        await interaction.response.send_message(view=view, ephemeral=True)

    # ---------- /doc-remove ----------

    @app_commands.command(name="doc-remove", description="Удалить документ из базы знаний")
    @app_commands.describe(doc_id="ID документа (см. /doc-list)")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def doc_remove(self, interaction: discord.Interaction, doc_id: str):
        removed = rag.delete_document(doc_id)
        if removed == 0:
            await interaction.response.send_message("❌ Документ не найден.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ Удалено {removed} чанков документа `{doc_id}`.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AI(bot))