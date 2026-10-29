from datetime import date
from html import escape

from config import SERVICES
from keyboards import format_date


def booking_card(b: dict, title: str = "") -> str:
    service = SERVICES.get(b["service"], {"name": b["service"], "price": "—"})
    d = date.fromisoformat(b["date"])
    lines = [f"<b>{title}</b>\n"] if title else []
    lines += [
        f"💈 {service['name']} — {service['price']} ₽",
        f"📅 {format_date(d)}, {b['time']}",
        f"👤 {escape(b['name'])}",
        f"📞 {b['phone']}",
    ]
    return "\n".join(lines)
