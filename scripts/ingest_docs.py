# scripts/ingest_docs.py — пакетная загрузка документов из папки docs/
import asyncio
import sys
from pathlib import Path

# корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import rag


DOCS_DIR = Path("docs")
SUPPORTED_EXTS = {".txt", ".md"}


async def main():
    if not DOCS_DIR.exists():
        print(f"❌ Папка {DOCS_DIR} не найдена. Создай её и положи .txt/.md файлы.")
        return

    files = [f for f in DOCS_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXTS]
    if not files:
        print("❌ Нет .txt или .md файлов в docs/")
        return

    total_chunks = 0
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ {f.name}: {e}")
            continue

        doc_id = f.stem  # имя файла без расширения
        chunks = await rag.add_document(
            doc_id=doc_id,
            title=f.stem,
            content=content,
            source=f"file:{f.name}",
        )
        total_chunks += chunks
        print(f"✅ {f.name} → {chunks} чанков")

    print(f"\n📚 Итог: {len(files)} файлов, {total_chunks} чанков.")
    print("\nДокументы в базе:")
    for did, info in rag.list_documents().items():
        print(f"  • {did} — {info['title']} ({info['chunks']} чанков)")


if __name__ == "__main__":
    asyncio.run(main())