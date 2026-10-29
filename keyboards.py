from datetime import date

from aiogram.types import (InlineKeyboardButton, KeyboardButton,
                           ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SERVICES

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

BTN_BOOK = "📅 Записаться"
BTN_MY = "🗂 Мои записи"
BTN_SERVICES = "💈 Услуги и цены"
BTN_CONTACTS = "📍 Контакты"
BTN_CANCEL = "✖️ Отмена"


def format_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]} {d:%d.%m}"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_BOOK)],
            [KeyboardButton(text=BTN_MY), KeyboardButton(text=BTN_SERVICES)],
            [KeyboardButton(text=BTN_CONTACTS)],
        ],
        resize_keyboard=True,
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _nav_row(back: str | None) -> list[InlineKeyboardButton]:
    row = []
    if back:
        row.append(InlineKeyboardButton(text="← Назад", callback_data=back))
    row.append(InlineKeyboardButton(text=BTN_CANCEL, callback_data="flow_cancel"))
    return row


def services_kb():
    b = InlineKeyboardBuilder()
    for sid, s in SERVICES.items():
        b.button(text=f"{s['name']} — {s['price']} ₽", callback_data=f"svc:{sid}")
    b.adjust(1)
    b.row(*_nav_row(None))
    return b.as_markup()


def dates_kb(days: list[date]):
    b = InlineKeyboardBuilder()
    for d in days:
        b.button(text=format_date(d), callback_data=f"date:{d.isoformat()}")
    b.adjust(3)
    b.row(*_nav_row("back:service"))
    return b.as_markup()


def times_kb(slots: list[str]):
    b = InlineKeyboardBuilder()
    for t in slots:
        b.button(text=t, callback_data=f"time:{t}")
    b.adjust(4)
    b.row(*_nav_row("back:date"))
    return b.as_markup()


def confirm_kb():
    b = InlineKeyboardBuilder()
    b.button(text="✅ Подтвердить", callback_data="confirm")
    b.button(text=BTN_CANCEL, callback_data="flow_cancel")
    b.adjust(1)
    return b.as_markup()


def my_bookings_kb(bookings: list[dict]):
    b = InlineKeyboardBuilder()
    for bk in bookings:
        d = date.fromisoformat(bk["date"])
        b.button(text=f"❌ Отменить {format_date(d)} {bk['time']}",
                 callback_data=f"ucancel:{bk['id']}")
    b.adjust(1)
    return b.as_markup()


def admin_kb():
    b = InlineKeyboardBuilder()
    b.button(text="Сегодня", callback_data="adm:today")
    b.button(text="Завтра", callback_data="adm:tomorrow")
    b.button(text="7 дней", callback_data="adm:week")
    b.adjust(3)
    return b.as_markup()


def admin_booking_kb(booking_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отменить запись", callback_data=f"acancel:{booking_id}")
    return b.as_markup()
