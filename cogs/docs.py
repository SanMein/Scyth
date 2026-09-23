# cogs/docs.py — управление базой знаний документов
import uuid

import discord
from discord import app_commands
from discord.ext import commands

from bot import logger
from config import (
    GUILD_ID,
    FOOTER_ICON,
    ADMIN_ROLE_IDS,
    DIRECTOR_ROLE_IDS,
)
from utils.containers import build_container
from utils import rag


# Проверка прав: админ или директор
def _is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id in (ADMIN_ROLE_IDS + DIRECTOR_ROLE_IDS) for r in member.roles)


class Docs(commands.Cog, name="Документы"):
    """Управление базой знаний документов."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- /doc-add ----------

    @app_commands.command(name="doc-add", description="Добавить документ в базу знаний")
    @app_commands.describe(
        doc_id="Короткий ID документа (латиница, цифры, дефис). Пример: ustav",
        title="Отображаемое название",
        file="Файл .txt / .md / .json",
        content="Или текст напрямую (если файла нет)",
    )
    @app_commands.guild_only()
    async def doc_add(
        self,
        interaction: discord.Interaction,
        doc_id: str,
        title: str,
        file: discord.Attachment | None = None,
        content: str | None = None,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        # Санитайз ID
        doc_id = doc_id.strip().lower()
        if not doc_id.replace("-", "").replace("_", "").isalnum():
            await interaction.response.send_message(
                "❌ ID должен содержать только латиницу, цифры, `-` и `_`.",
                ephemeral=True,
            )
            return

        existing = rag.list_documents()
        if doc_id in existing:
            await interaction.response.send_message(
                f"❌ Документ `{doc_id}` уже существует. Используй `/doc-update`.",
                ephemeral=True,
            )
            return

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

        chunks = await rag.add_document(
            doc_id=doc_id,
            title=title,
            content=text,
            source=f"uploaded by {interaction.user}",
        )

        await interaction.followup.send(
            f"✅ Документ добавлен.\n"
            f"> **ID:** `{doc_id}`\n"
            f"> **Название:** {title}\n"
            f"> **Чанков:** {chunks}\n"
            f"> **Размер:** {len(text):,} символов",
            ephemeral=True,
        )

    # ---------- /doc-update ----------

    @app_commands.command(name="doc-update", description="Обновить содержимое документа")
    @app_commands.describe(
        doc_id="ID документа (см. /doc-list)",
        file="Новый файл .txt / .md",
        content="Или новый текст напрямую",
    )
    @app_commands.guild_only()
    async def doc_update(
        self,
        interaction: discord.Interaction,
        doc_id: str,
        file: discord.Attachment | None = None,
        content: str | None = None,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        existing = rag.list_documents()
        if doc_id not in existing:
            await interaction.response.send_message(
                f"❌ Документ `{doc_id}` не найден.", ephemeral=True
            )
            return

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
            await interaction.followup.send("❌ Новый текст пустой.", ephemeral=True)
            return

        # Удаляем старую версию и добавляем новую под тем же ID
        old_chunks = rag.delete_document(doc_id)
        title = existing[doc_id]["title"]

        new_chunks = await rag.add_document(
            doc_id=doc_id,
            title=title,
            content=text,
            source=f"updated by {interaction.user}",
        )

        await interaction.followup.send(
            f"✅ Документ `{doc_id}` обновлён.\n"
            f"> Было чанков: {old_chunks}\n"
            f"> Стало чанков: {new_chunks}",
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

        lines = [f"# 📚 Документы в базе ({len(docs)})", ""]
        for did, info in sorted(docs.items()):
            lines.append(f"• `{did}` — **{info['title']}** · {info['chunks']} чанков")

        view = build_container(
            "\n".join(lines),
            thumb_url=FOOTER_ICON,
            accent_color=0x3498DB,
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    # ---------- /doc-view ----------

    @app_commands.command(name="doc-view", description="Показать содержимое документа")
    @app_commands.describe(doc_id="ID документа")
    @app_commands.guild_only()
    async def doc_view(self, interaction: discord.Interaction, doc_id: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        data = rag._load()
        if doc_id not in data:
            await interaction.response.send_message("❌ Документ не найден.", ephemeral=True)
            return

        doc = data[doc_id]
        chunks = doc.get("chunks", [])
        preview = "\n\n---\n\n".join(chunks[:3])
        if len(preview) > 1800:
            preview = preview[:1800] + "…"

        text = (
            f"# 📄 {doc.get('title', doc_id)}\n"
            f"> **ID:** `{doc_id}`\n"
            f"> **Чанков:** {len(chunks)}\n"
            f"> **Источник:** {doc.get('source', '—')}\n\n"
            f"**Первые 3 чанка:**\n```\n{preview}\n```"
        )
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        await interaction.response.send_message(view=view, ephemeral=True)

    # ---------- /doc-remove ----------

    @app_commands.command(name="doc-remove", description="Удалить документ по ID")
    @app_commands.describe(doc_id="ID документа", confirm="Подтверждение (напиши 'ДА')")
    @app_commands.guild_only()
    async def doc_remove(
        self,
        interaction: discord.Interaction,
        doc_id: str,
        confirm: str,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        if confirm.strip().upper() != "ДА":
            await interaction.response.send_message(
                "❌ Для удаления напиши `ДА` в поле confirm.", ephemeral=True
            )
            return

        removed = rag.delete_document(doc_id)
        if removed == 0:
            await interaction.response.send_message("❌ Документ не найден.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ Удалён документ `{doc_id}` ({removed} чанков).", ephemeral=True
        )

    # ---------- /doc-search ----------

    @app_commands.command(name="doc-search", description="Поиск по базе знаний")
    @app_commands.describe(query="Поисковый запрос", top_k="Сколько результатов (1–10)")
    @app_commands.guild_only()
    async def doc_search(
        self,
        interaction: discord.Interaction,
        query: str,
        top_k: app_commands.Range[int, 1, 10] = 5,
    ):
        await interaction.response.defer(ephemeral=True)

        hits = await rag.search(query, top_k=top_k)
        if not hits:
            await interaction.followup.send("🔍 Ничего не найдено.", ephemeral=True)
            return

        lines = [f"# 🔍 Результаты поиска ({len(hits)})", f"-# Запрос: {query}", ""]
        for i, h in enumerate(hits, 1):
            excerpt = h["text"][:250].replace("\n", " ")
            lines.append(f"**[{i}] {h['title']}** (скор: {h['score']})")
            lines.append(f"> {excerpt}…")
            lines.append("")

        text = "\n".join(lines)
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x3498DB)
        await interaction.followup.send(view=view, ephemeral=True)

    # ---------- /doc-import ----------

    @app_commands.command(name="doc-import", description="Импортировать канал как документы")
    @app_commands.describe(
        channel="Канал для импорта",
        prefix="Префикс ID (латиница)",
        limit="Сколько последних сообщений взять (1–500)",
    )
    @app_commands.guild_only()
    async def doc_import(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        prefix: str,
        limit: app_commands.Range[int, 1, 500] = 100,
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        added = 0
        async for msg in channel.history(limit=limit):
            if not msg.content or len(msg.content) < 20:
                continue
            doc_id = f"{prefix}-{msg.id}"
            title = f"{prefix} #{msg.id} ({msg.author.display_name})"
            await rag.add_document(
                doc_id=doc_id,
                title=title,
                content=msg.content,
                source=f"#{channel.name}",
            )
            added += 1

        await interaction.followup.send(
            f"✅ Импортировано {added} сообщений из {channel.mention}.", ephemeral=True
        )

    # ---------- /doc-stats ----------

    @app_commands.command(name="doc-stats", description="Статистика базы знаний")
    @app_commands.guild_only()
    async def doc_stats(self, interaction: discord.Interaction):
        docs = rag.list_documents()
        if not docs:
            await interaction.response.send_message("📭 База знаний пуста.", ephemeral=True)
            return

        total_docs = len(docs)
        total_chunks = sum(d["chunks"] for d in docs.values())
        biggest = max(docs.items(), key=lambda x: x[1]["chunks"])
        smallest = min(docs.items(), key=lambda x: x[1]["chunks"])

        text = (
            f"# 📊 Статистика базы знаний\n\n"
            f"## 📚 Общее\n"
            f"> **Документов:** {total_docs}\n"
            f"> **Всего чанков:** {total_chunks}\n"
            f"> **Среднее чанков/док:** {total_chunks / total_docs:.1f}\n\n"
            f"## 📈 Экстремумы\n"
            f"> **Самый большой:** `{biggest[0]}` — {biggest[1]['chunks']} чанков\n"
            f"> **Самый маленький:** `{smallest[0]}` — {smallest[1]['chunks']} чанков"
        )
        view = build_container(text, thumb_url=FOOTER_ICON, accent_color=0x2ECC71)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Docs(bot))