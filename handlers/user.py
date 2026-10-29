import logging
import re
from datetime import date
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from config import ADMIN_IDS, CONTACTS_TEXT, SERVICES, SHOP_NAME, now
from slots import available_dates, free_slots
from texts import booking_card

router = Router()
log = logging.getLogger(__name__)


class Booking(StatesGroup):
    service = State()
    date = State()
    time = State()
    name = State()
    phone = State()
    confirm = State()


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    if not 11 <= len(digits) <= 12:
        return None
    return "+" + digits


async def notify_admins(bot: Bot, text: str, reply_markup=None) -> None:
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception as e:  # админ мог не запустить бота
            log.warning("Не удалось уведомить админа %s: %s", admin_id, e)


# ---------- Общие команды (работают в любом состоянии) ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {escape(message.from_user.first_name)}! 👋\n\n"
        f"Я бот-администратор <b>{SHOP_NAME}</b>.\n"
        "Запишу вас к мастеру за минуту — без звонков и ожидания.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("cancel"))
@router.message(F.text == kb.BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_SERVICES)
async def show_services(message: Message, state: FSMContext):
    await state.clear()
    lines = [f"• {s['name']} — <b>{s['price']} ₽</b>" for s in SERVICES.values()]
    await message.answer("<b>Услуги и цены</b>\n\n" + "\n".join(lines))


@router.message(F.text == kb.BTN_CONTACTS)
async def show_contacts(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(CONTACTS_TEXT)


# ---------- Запись ----------

@router.message(Command("book"))
@router.message(F.text == kb.BTN_BOOK)
async def book_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Booking.service)
    await message.answer("Выберите услугу:", reply_markup=kb.services_kb())


async def show_dates(call: CallbackQuery, state: FSMContext) -> None:
    days = await available_dates()
    if not days:
        await state.clear()
        await call.message.edit_text(
            "😔 На ближайшую неделю свободных окон нет. Загляните позже!"
        )
        return
    await state.set_state(Booking.date)
    s = SERVICES[(await state.get_data())["service"]]
    await call.message.edit_text(
        f"<b>{s['name']}</b> — {s['price']} ₽\n\nВыберите день:",
        reply_markup=kb.dates_kb(days),
    )


@router.callback_query(Booking.service, F.data.startswith("svc:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    sid = call.data.split(":", 1)[1]
    if sid not in SERVICES:
        return await call.answer()
    await state.update_data(service=sid)
    await show_dates(call, state)
    await call.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    day = date.fromisoformat(call.data.split(":", 1)[1])
    slots = await free_slots(day)
    if not slots:
        return await call.answer("На этот день всё занято", show_alert=True)
    await state.update_data(date=day.isoformat())
    await state.set_state(Booking.time)
    await call.message.edit_text(
        f"📅 {kb.format_date(day)} — выберите время:",
        reply_markup=kb.times_kb(slots),
    )
    await call.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    slot = call.data.split(":", 1)[1]
    data = await state.get_data()
    if slot not in await free_slots(date.fromisoformat(data["date"])):
        return await call.answer("Это время только что заняли, выберите другое",
                                 show_alert=True)
    await state.update_data(time=slot)
    await state.set_state(Booking.name)
    day = date.fromisoformat(data["date"])
    await call.message.edit_text(f"📅 {kb.format_date(day)}, {slot} ✅")
    await call.message.answer("Как к вам обращаться?")
    await call.answer()


@router.callback_query(F.data == "back:service")
async def back_to_service(call: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.service)
    await call.message.edit_text("Выберите услугу:", reply_markup=kb.services_kb())
    await call.answer()


@router.callback_query(F.data == "back:date")
async def back_to_date(call: CallbackQuery, state: FSMContext):
    if "service" not in await state.get_data():
        return await call.answer("Начните запись заново", show_alert=True)
    await show_dates(call, state)
    await call.answer()


@router.callback_query(F.data == "flow_cancel")
async def flow_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Запись отменена. Возвращайтесь, когда будет удобно 🙂")
    await call.answer()


@router.message(Booking.name, F.text)
async def get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not 2 <= len(name) <= 40:
        return await message.answer("Введите имя от 2 до 40 символов.")
    await state.update_data(name=name)
    await state.set_state(Booking.phone)
    await message.answer(
        "Отправьте номер телефона кнопкой ниже или введите вручную:",
        reply_markup=kb.phone_kb(),
    )


async def _save_phone(message: Message, state: FSMContext, raw: str) -> None:
    phone = normalize_phone(raw)
    if not phone:
        await message.answer("Похоже, номер некорректный. Пример: +7 913 123-45-67")
        return
    await state.update_data(phone=phone)
    await state.set_state(Booking.confirm)
    data = await state.get_data()
    await message.answer("Почти готово 👇", reply_markup=kb.main_menu())
    await message.answer(booking_card(data, "Проверьте запись:"),
                         reply_markup=kb.confirm_kb())


@router.message(Booking.phone, F.contact)
async def get_contact(message: Message, state: FSMContext):
    await _save_phone(message, state, message.contact.phone_number)


@router.message(Booking.phone, F.text)
async def get_phone_text(message: Message, state: FSMContext):
    await _save_phone(message, state, message.text)


@router.callback_query(Booking.confirm, F.data == "confirm")
async def confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    booking_id = await db.add_booking(
        call.from_user.id, data["name"], data["phone"],
        data["service"], data["date"], data["time"],
    )
    if booking_id is None:
        await call.answer("Увы, это время уже заняли 😔 Выберите другое.",
                          show_alert=True)
        await show_dates(call, state)
        return

    await state.clear()
    await call.message.edit_text(
        booking_card(data, "✅ Вы записаны!")
        + "\n\nПередумали? Отменить можно в разделе «Мои записи»."
    )
    await call.answer()

    user = call.from_user
    client_link = f'<a href="tg://user?id={user.id}">{escape(user.full_name)}</a>'
    await notify_admins(
        bot,
        booking_card(data, f"🆕 Новая запись #{booking_id}") + f"\n💬 {client_link}",
        reply_markup=kb.admin_booking_kb(booking_id),
    )


# ---------- Мои записи ----------

def _my_bookings_text(rows: list[dict]) -> str:
    if not rows:
        return "У вас нет активных записей. Нажмите «📅 Записаться» 🙂"
    parts = [booking_card(r) for r in rows]
    return "<b>Ваши записи:</b>\n\n" + "\n\n".join(parts)


@router.message(F.text == kb.BTN_MY)
async def my_bookings(message: Message, state: FSMContext):
    await state.clear()
    rows = await db.get_user_bookings(message.from_user.id, now().date().isoformat())
    await message.answer(_my_bookings_text(rows),
                         reply_markup=kb.my_bookings_kb(rows) if rows else None)


@router.callback_query(F.data.startswith("ucancel:"))
async def user_cancel(call: CallbackQuery, bot: Bot):
    booking_id = int(call.data.split(":", 1)[1])
    row = await db.cancel_booking(booking_id, user_id=call.from_user.id)
    if not row:
        return await call.answer("Запись не найдена или уже отменена", show_alert=True)
    await call.answer("Запись отменена")

    rows = await db.get_user_bookings(call.from_user.id, now().date().isoformat())
    await call.message.edit_text(_my_bookings_text(rows),
                                 reply_markup=kb.my_bookings_kb(rows) if rows else None)
    await notify_admins(bot, booking_card(row, f"❌ Клиент отменил запись #{booking_id}"))


# ---------- Всё остальное ----------

@router.message()
async def fallback(message: Message):
    await message.answer("Не совсем понял 🙂 Воспользуйтесь меню ниже.",
                         reply_markup=kb.main_menu())
