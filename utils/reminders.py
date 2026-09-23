# utils/reminders.py — persistent-хранилище напоминаний
import json
import os
from datetime import datetime, timezone

import aiofiles

from config import REMINDERS_FILE

_lock = None  # инициализируется в cog


async def load_reminders() -> dict:
    if not os.path.exists(REMINDERS_FILE):
        return {}
    async with aiofiles.open(REMINDERS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.loads(await f.read())
        except json.JSONDecodeError:
            return {}


async def save_reminders(data: dict) -> None:
    async with aiofiles.open(REMINDERS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))


async def add_reminder(
    *,
    reminder_id: str,
    user_id: int,
    channel_id: int,
    guild_id: int,
    fire_at: datetime,
    text: str,
) -> None:
    data = await load_reminders()
    data[reminder_id] = {
        "user_id": user_id,
        "channel_id": channel_id,
        "guild_id": guild_id,
        "fire_at": fire_at.astimezone(timezone.utc).isoformat(),
        "text": text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await save_reminders(data)


async def remove_reminder(reminder_id: str) -> dict | None:
    data = await load_reminders()
    removed = data.pop(reminder_id, None)
    if removed is not None:
        await save_reminders(data)
    return removed


async def get_user_reminders(user_id: int) -> dict:
    data = await load_reminders()
    return {rid: r for rid, r in data.items() if r.get("user_id") == user_id}