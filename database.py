import sqlite3

import aiosqlite

from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                phone      TEXT    NOT NULL,
                service    TEXT    NOT NULL,
                date       TEXT    NOT NULL,
                time       TEXT    NOT NULL,
                status     TEXT    NOT NULL DEFAULT 'active',
                created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Один активный клиент на слот — защита от двойной записи
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_slot "
            "ON bookings(date, time) WHERE status = 'active'"
        )
        await db.commit()


async def _fetch(query: str, params: tuple = ()) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        return [dict(r) for r in await cur.fetchall()]


async def get_busy_times(day: str) -> set[str]:
    rows = await _fetch(
        "SELECT time FROM bookings WHERE date = ? AND status = 'active'", (day,)
    )
    return {r["time"] for r in rows}


async def add_booking(user_id: int, name: str, phone: str,
                      service: str, day: str, time: str) -> int | None:
    """Возвращает id записи или None, если слот уже занят."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "INSERT INTO bookings (user_id, name, phone, service, date, time) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, phone, service, day, time),
            )
            await db.commit()
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


async def get_booking(booking_id: int) -> dict | None:
    rows = await _fetch("SELECT * FROM bookings WHERE id = ?", (booking_id,))
    return rows[0] if rows else None


async def get_user_bookings(user_id: int, from_day: str) -> list[dict]:
    return await _fetch(
        "SELECT * FROM bookings WHERE user_id = ? AND status = 'active' "
        "AND date >= ? ORDER BY date, time",
        (user_id, from_day),
    )


async def get_bookings_between(start: str, end: str) -> list[dict]:
    return await _fetch(
        "SELECT * FROM bookings WHERE status = 'active' "
        "AND date BETWEEN ? AND ? ORDER BY date, time",
        (start, end),
    )


async def cancel_booking(booking_id: int, user_id: int | None = None) -> dict | None:
    """Отменяет запись. Если передан user_id — только свою."""
    row = await get_booking(booking_id)
    if not row or row["status"] != "active":
        return None
    if user_id is not None and row["user_id"] != user_id:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await db.commit()
    return row
