from datetime import date, timedelta

import database as db
from config import CLOSE_HOUR, DAYS_AHEAD, OPEN_HOUR, WORK_DAYS, now


async def free_slots(day: date) -> list[str]:
    """Свободные часы на день (прошедшее время сегодня не показываем)."""
    if day.weekday() not in WORK_DAYS:
        return []
    busy = await db.get_busy_times(day.isoformat())
    current = now()
    result = []
    for hour in range(OPEN_HOUR, CLOSE_HOUR):
        slot = f"{hour:02d}:00"
        if slot in busy:
            continue
        if day == current.date() and hour <= current.hour:
            continue
        result.append(slot)
    return result


async def available_dates() -> list[date]:
    today = now().date()
    result = []
    for i in range(DAYS_AHEAD):
        day = today + timedelta(days=i)
        if await free_slots(day):
            result.append(day)
    return result
