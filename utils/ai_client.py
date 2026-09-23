# utils/ai_client.py — клиент DeepSeek через AITunnel
import os

from openai import AsyncOpenAI

from bot import logger
from config import (
    AITUNNEL_BASE_URL,
    AITUNNEL_MODEL,
    AI_SYSTEM_PROMPT,
    AI_MAX_TOKENS,
)


_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI | None:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("AITUNNEL_API_KEY")
    if not api_key:
        logger.error("❌ Переменная AITUNNEL_API_KEY не задана в .env")
        return None

    _client = AsyncOpenAI(
        api_key=api_key,
        base_url=AITUNNEL_BASE_URL,
    )
    return _client


async def ask(
    question: str,
    history: list[dict] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Отправляет вопрос в DeepSeek. Возвращает строку — никогда не None.
    """
    client = get_client()
    if client is None:
        return "⚠️ AI-сервис недоступен: не настроен API-ключ."

    messages: list[dict] = [
        {"role": "system", "content": system_prompt or AI_SYSTEM_PROMPT},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    try:
        response = await client.chat.completions.create(
            model=AITUNNEL_MODEL,
            messages=messages,
            max_tokens=AI_MAX_TOKENS,
        )
    except Exception as e:
        logger.exception(f"Ошибка запроса к DeepSeek: {e}")
        return "⚠️ Не удалось получить ответ от AI. Попробуйте позже."

    if not response.choices:
        logger.warning("DeepSeek вернул пустой choices")
        return "⚠️ AI не вернул ответа."

    choice = response.choices[0]
    finish = getattr(choice, "finish_reason", None)
    message = choice.message

    # --- Основной путь: content ---
    content = getattr(message, "content", None)
    if content:
        return content.strip()

    # --- Fallback: reasoning_content (DeepSeek-R1 / v4-flash) ---
    reasoning = getattr(message, "reasoning_content", None)
    if reasoning:
        logger.info("DeepSeek вернул reasoning_content вместо content — используем его.")
        return reasoning.strip()

    # --- Логируем для отладки и отдаём понятную ошибку ---
    logger.warning(
        f"DeepSeek вернул пустой content. finish_reason={finish}, "
        f"message={message!r}"
    )

    if finish == "length":
        return "⚠️ Ответ оказался слишком длинным и был обрезан. Попробуйте переформулировать вопрос короче."

    return "⚠️ AI не смог дать ответ. Попробуйте ещё раз или переформулируйте вопрос."