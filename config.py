import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DB_PATH = os.getenv("DB_PATH", "booking.db")
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Krasnoyarsk"))

SHOP_NAME = os.getenv("SHOP_NAME", "Barber Demo")

# Услуги: id -> название и цена
SERVICES = {
    "haircut": {"name": "Мужская стрижка", "price": 1200},
    "beard": {"name": "Оформление бороды", "price": 800},
    "combo": {"name": "Стрижка + борода", "price": 1800},
    "kids": {"name": "Детская стрижка", "price": 900},
}

# Расписание
OPEN_HOUR = 10          # первый слот 10:00
CLOSE_HOUR = 20         # последний слот 19:00
WORK_DAYS = {0, 1, 2, 3, 4, 5}  # Пн–Сб
DAYS_AHEAD = 7          # на сколько дней вперёд можно записаться

CONTACTS_TEXT = (
    f"<b>{SHOP_NAME}</b>\n\n"
    "📍 ул. Примерная, 1\n"
    "🕙 Пн–Сб, 10:00–20:00\n"
    "📞 +7 (900) 000-00-00"
)


def now() -> datetime:
    return datetime.now(TZ)
