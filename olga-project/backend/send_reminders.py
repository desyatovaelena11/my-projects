"""
Скрипт отправки напоминаний клиентам.

Запускается через cron в 15:00 UTC = 18:00 мск.
Находит все записи на завтра, отправляет напоминание в Telegram,
помечает reminder_sent = true чтобы не дублировать.

Запуск вручную для теста:
    cd /opt/ma-master
    venv/bin/python send_reminders.py
"""

import asyncio
import logging
import sys
from datetime import date, timedelta

import httpx
from sqlalchemy import select, update

sys.path.insert(0, '/opt/ma-master')
from database import SessionLocal
from models import Booking, Master

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger("reminders")


async def send_message(bot_token: str, chat_id: int, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }, timeout=10)
            result = r.json()
            if result.get("ok"):
                return True
            logger.error(f"Telegram error: {result}")
            return False
        except Exception as e:
            logger.error(f"HTTP error sending to {chat_id}: {e}")
            return False


async def run():
    tomorrow = (date.today() + timedelta(days=1)).isoformat()  # YYYY-MM-DD
    logger.info(f"Sending reminders for {tomorrow}")

    async with SessionLocal() as db:
        # Находим все записи на завтра, которые ещё не получили напоминание
        result = await db.execute(
            select(Booking, Master)
            .join(Master, Booking.master_id == Master.id)
            .where(
                Booking.booking_date == tomorrow,
                Booking.status.in_(["pending", "confirmed"]),
                Booking.reminder_sent == False,
                Booking.client_telegram_id.is_not(None),
            )
        )
        rows = result.all()

    logger.info(f"Found {len(rows)} bookings to remind")

    sent_ids = []

    for booking, master in rows:
        # Формируем текст напоминания
        date_obj = date.fromisoformat(booking.booking_date)
        months = [
            'января','февраля','марта','апреля','мая','июня',
            'июля','августа','сентября','октября','ноября','декабря'
        ]
        date_label = f"{date_obj.day} {months[date_obj.month - 1]}"
        time_label = booking.booking_time or ""

        address_line = f"📍 Адрес: {master.address}\n" if master.address else ""

        text = (
            f"🔔 *Напоминание о записи*\n\n"
            f"Привет! Напоминаем, что завтра у вас запись к мастеру *{master.name}*.\n\n"
            f"💅 Услуга: {booking.service_name}\n"
            f"📅 Дата: {date_label}\n"
            f"🕐 Время: {time_label}\n"
            f"{address_line}"
            f"\nЕсли планы изменились — напишите мастеру заранее. Ждём вас! 🙌"
        )

        ok = await send_message(master.bot_token, booking.client_telegram_id, text)

        if ok:
            sent_ids.append(booking.id)
            logger.info(f"Reminded client {booking.client_telegram_id} about booking {booking.id}")
        else:
            logger.warning(f"Failed to remind client {booking.client_telegram_id}")

    # Помечаем отправленные напоминания
    if sent_ids:
        async with SessionLocal() as db:
            await db.execute(
                update(Booking)
                .where(Booking.id.in_(sent_ids))
                .values(reminder_sent=True)
            )
            await db.commit()
        logger.info(f"Marked {len(sent_ids)} bookings as reminder_sent")

    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(run())
