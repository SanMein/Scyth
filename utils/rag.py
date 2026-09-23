# utils/rag.py — простое хранилище документов с keyword-поиском
import json
import os
import re
from collections import Counter

from bot import logger


DOCS_FILE = "knowledge_base.json"


def _load() -> dict:
    if not os.path.exists(DOCS_FILE):
        return {}
    with open(DOCS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save(data: dict) -> None:
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _tokenize(text: str) -> list[str]:
    """Простая токенизация: слова из букв/цифр длиной >= 2."""
    return [w for w in re.findall(r"[а-яёa-z0-9]{2,}", text.lower())]


def _chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """
    Разбивает текст на чанки по абзацам, а слишком длинные абзацы — по size.
    """
    chunks = []
    # Сначала режем по двойным переносам
    paragraphs = re.split(r"\n\s*\n", text)

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(p) <= size:
            chunks.append(p)
        else:
            # Режем длинный абзац с перекрытием
            start = 0
            while start < len(p):
                end = start + size
                chunks.append(p[start:end].strip())
                start = end - overlap

    return [c for c in chunks if c]


async def add_document(
    *,
    doc_id: str,
    title: str,
    content: str,
    source: str = "",
    tags: list[str] | None = None,
) -> int:
    """Добавляет документ, возвращает кол-во чанков."""
    data = _load()
    chunks = _chunk(content)

    data[doc_id] = {
        "title": title,
        "source": source,
        "tags": tags or [],
        "chunks": chunks,
    }
    _save(data)
    logger.info(f"📚 Добавлен документ '{title}' ({len(chunks)} чанков)")
    return len(chunks)


async def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Ищет релевантные чанки по ключевым словам.
    Скор = сумма пересечений токенов запроса и чанка, с весом для точных совпадений.
    """
    data = _load()
    if not data:
        return []

    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return []

    scored: list[dict] = []

    for doc_id, doc in data.items():
        for i, chunk in enumerate(doc["chunks"]):
            c_tokens = _tokenize(chunk)
            if not c_tokens:
                continue

            c_counter = Counter(c_tokens)

            # Базовый скор: сколько токенов запроса встречается
            hits = sum(1 for t in q_tokens if t in c_counter)

            # Бонус: чем чаще токен в чанке (но не линейно), тем лучше
            weight = sum(min(c_counter[t], 3) for t in q_tokens if t in c_counter)

            score = hits * 2 + weight

            # Бонус за совпадение фразы целиком (2+ слова)
            query_lower = query.lower()
            if len(query_lower) > 8 and query_lower in chunk.lower():
                score += 10

            if score > 0:
                scored.append({
                    "text": chunk,
                    "title": doc["title"],
                    "source": doc.get("source", ""),
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "score": score,
                })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def delete_document(doc_id: str) -> int:
    data = _load()
    if doc_id not in data:
        return 0
    n = len(data[doc_id]["chunks"])
    del data[doc_id]
    _save(data)
    logger.info(f"🗑️ Удалён документ {doc_id} ({n} чанков)")
    return n


def list_documents() -> dict[str, dict]:
    """Список документов: {doc_id: {'title': ..., 'chunks': N}}"""
    data = _load()
    return {
        doc_id: {
            "title": doc.get("title", doc_id),
            "chunks": len(doc.get("chunks", [])),
        }
        for doc_id, doc in data.items()
    }