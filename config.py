# config.py - все константы
import os

GUILD_ID = 1349365796949856265

AUDIT_LOG_CHANNEL_ID = 1349365797515956227
JOIN_LOG_CHANNEL_ID = 1457964655711355027
CLEANUP_LOG_CHANNEL_ID = 1457964655711355027

ADMIN_ROLE_IDS = [
    1447513054844555336,
    1349365796970954834,
    1349365796970954833,
]

DIRECTOR_ROLE_IDS = [
    1349365796970954834,
    1349365796970954833,
]

# Куда пересылать медиа из голосовых чатов
VOICE_MEDIA_FORWARD_CHANNEL_ID = 1349365797658824720

# Голосовые каналы, которые НЕ нужно очищать в 6:00 МСК
VOICE_CLEANUP_EXCLUDED_IDS: list[int] = []

# Голосовые каналы, медиа из которых НЕ пересылать
VOICE_MEDIA_EXCLUDED_IDS: list[int] = []

FOOTER_TEXT = "Scyth ⊷ Σκύθ"
FOOTER_ICON = "https://i.imgur.com/f5TVI4f.png"

ON_JOIN_ROLE_IDS = [
    1502050970941657310,
    1508562311428833480,
]

WELCOME_THUMB_URL = "https://i.imgur.com/f5TVI4f.png"
WELCOME_ACCENT_COLOR = 0x9B59B6

JOIN_LOG_THUMB_URL = "https://i.imgur.com/LGICBgf.png"
JOIN_LOG_ACCENT_COLOR = 0x9B59B6

MEMBER_JOIN_THUMB_URL = "https://i.imgur.com/StYKfRf.png"
MEMBER_LEAVE_THUMB_URL = "https://i.imgur.com/wuRa2NQ.png"

SUSPICIOUS_ACCOUNT_DAYS = 90

# Московское время
MSK_OFFSET_HOURS = 3

# Хранилище напоминаний
REMINDERS_FILE = "reminders.json"

# === AI (DeepSeek через AITunnel) ===
AITUNNEL_BASE_URL = "https://api.aitunnel.ru/v1"
AITUNNEL_MODEL = "deepseek-v4-flash-0731"

# Системный промпт — ЭТО и есть «как я захочу»
AI_SYSTEM_PROMPT = """Ты — Скиф (Σκύθ), AI-ассистент игровой ЧВК «Military Special Forces — 043».
Отвечай кратко, по делу, в сухом юридически-формальном стиле.
Обращайся к пользователю на «вы».
Не выдумывай приказы, факты и события. Если не знаешь — скажи об этом прямо.
Отвечай только на русском языке.
Максимум 1-2 предложения в ответе, если не просят подробнее.
Ответ должен быть живым, а не «Ы, я робот. Сообщение получено, протокол соблюдён».
Не пиши reasoning_content. Отвечай сразу текстом в поле content.
Если ты в контексте найдёшь нарушения - сообщай сразу же.
"""

# Сколько последних сообщений канала давать модели как контекст
AI_CONTEXT_MESSAGES = 20

# Максимум токенов на ответ
AI_MAX_TOKENS = 4096

# Каналы, где бот НЕ отвечает на упоминания
AI_IGNORED_CHANNELS: list[int] = [1349365797658824720,
                                  1544180365566935090,
                                  1349365797658824722,
                                  1527750540799381647,
                                  1349365797515956232,
                                  1349365797968941105,
                                  1349365797515956228
                                  ]