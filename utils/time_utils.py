# utils/time_utils.py — работа со временем
from datetime import datetime, timezone, timedelta


def parse_duration(duration_str: str) -> timedelta:
    """
    Разбирает строку вида '30s', '5m', '2h', '1d', '1w', '1y' в timedelta.
    Бросает ValueError при неверном формате.
    """
    if not duration_str:
        raise ValueError("Пустая строка длительности")

    s = duration_str.strip().lower()
    if len(s) < 2 or not s[-1].isalpha() or not s[:-1].isdigit():
        raise ValueError(f"Неверный формат: {duration_str}")

    value = int(s[:-1])
    unit = s[-1]
    units = {
        's': timedelta(seconds=value),
        'm': timedelta(minutes=value),
        'h': timedelta(hours=value),
        'd': timedelta(days=value),
        'w': timedelta(weeks=value),
        'y': timedelta(days=value * 365),
    }
    if unit not in units:
        raise ValueError(f"Неизвестная единица: {unit}")
    return units[unit]


def humanize_age(created_at: datetime) -> str:
    """Возвращает '5 дн.' / '7 мес.' / '2 г.' для указанного момента создания."""
    now = datetime.now(timezone.utc)
    days = (now - created_at).days
    if days < 30:
        return f"{days} дн."
    if days < 365:
        return f"{days // 30} мес."
    return f"{days // 365} г."


def format_delta(delta: timedelta) -> str:
    """Форматирует timedelta в человекочитаемую строку."""
    total = int(delta.total_seconds())
    if total < 0:
        return "0 сек."
    if total < 60:
        return f"{total} сек."
    if total < 3600:
        return f"{total // 60} мин."
    if total < 86400:
        return f"{total // 3600} ч. {total % 3600 // 60} мин."
    return f"{total // 86400} дн. {total % 86400 // 3600} ч."


def parse_remind_time(value: str) -> tuple[timedelta | None, str | None]:
    """
    Разбирает строку времени для напоминания.
    Возвращает (timedelta, None) или (None, error_message).

    Поддерживает:
    - '30s', '5m', '2h', '1d', '1w', '1y' — относительное время
    - Unix timestamp (10+ цифр) — абсолютное время
    """
    s = value.strip().lower()

    # Unix timestamp
    if s.isdigit() and len(s) >= 10:
        try:
            ts = int(s)
            target = datetime.fromtimestamp(ts, tz=timezone.utc)
            delta = target - datetime.now(timezone.utc)
            if delta.total_seconds() <= 0:
                return None, "❌ Указанное время уже прошло."
            return delta, None
        except (ValueError, OSError):
            return None, "❌ Неверный timestamp."

    # Относительный формат
    if len(s) >= 2 and s[-1].isalpha() and s[:-1].isdigit():
        try:
            return parse_duration(s), None
        except ValueError:
            pass

    return None, "❌ Неверный формат. Пример: `30s`, `5m`, `2h`, `1d`, `1w` или unix timestamp."