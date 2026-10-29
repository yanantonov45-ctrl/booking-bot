from datetime import date, timedelta

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from config import ADMIN_IDS, SERVICES, now
from texts import booking_card

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))


@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer("🔧 <b>Панель администратора</b>\nЗаписи за период:",
                         reply_markup=kb.admin_kb())


@router.callback_query(F.data.startswith("adm:"))
async def admin_list(call: CallbackQuery):
    period = call.data.split(":", 1)[1]
    today = now().date()
    start, end, title = {
        "today": (today, today, "Сегодня"),
        "tomorrow": (today + timedelta(days=1), today + timedelta(days=1), "Завтра"),
        "week": (today, today + timedelta(days=6), "Ближайшие 7 дней"),
    }.get(period, (today, today, "Сегодня"))

    rows = await db.get_bookings_between(start.isoformat(), end.isoformat())
    if not rows:
        text = f"<b>{title}</b>\n\nЗаписей нет."
    else:
        lines, current = [f"<b>{title}</b> — {len(rows)} шт."], None
        revenue = 0
        for r in rows:
            if r["date"] != current:
                current = r["date"]
                lines.append(f"\n📅 <b>{kb.format_date(date.fromisoformat(current))}</b>")
            s = SERVICES.get(r["service"], {"name": r["service"], "price": 0})
            revenue += s["price"]
            lines.append(f"{r['time']} — {s['name']}, {r['name']} ({r['phone']}) #{r['id']}")
        lines.append(f"\n💰 Ожидаемая выручка: <b>{revenue} ₽</b>")
        text = "\n".join(lines)

    try:
        await call.message.edit_text(text, reply_markup=kb.admin_kb())
    except TelegramBadRequest:  # текст не изменился
        pass
    await call.answer()


@router.callback_query(F.data.startswith("acancel:"))
async def admin_cancel(call: CallbackQuery, bot: Bot):
    booking_id = int(call.data.split(":", 1)[1])
    row = await db.cancel_booking(booking_id)
    if not row:
        return await call.answer("Запись уже отменена", show_alert=True)
    await call.message.edit_text(call.message.html_text + "\n\n❌ <b>Отменена администратором</b>")
    await call.answer("Отменено")
    try:
        await bot.send_message(
            row["user_id"],
            booking_card(row, "😔 Ваша запись отменена")
            + "\n\nИзвините за неудобства! Выберите другое время в меню «📅 Записаться».",
        )
    except Exception:
        pass
