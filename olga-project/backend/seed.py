"""
Одноразовый скрипт: вставляет данные Ольги в базу.

Запускать один раз после деплоя:
  cd backend
  python seed.py

Если Ольга уже есть в базе — скрипт ничего не делает.

ВАЖНО: замени telegram_id на реальный Telegram ID Ольги.
Как узнать Telegram ID: написать боту @userinfobot в Telegram.
"""

import asyncio
from sqlalchemy import select
from database import SessionLocal
from models import Master


async def seed():
    async with SessionLocal() as db:
        # Проверяем: мастер уже существует?
        result = await db.execute(select(Master).where(Master.slug == "olga-manicure"))
        if result.scalar_one_or_none():
            print("⚠️  Мастер с slug 'olga-manicure' уже существует. Пропускаю.")
            return

        master = Master(
            telegram_id=123456789,        # ← ЗАМЕНИТЬ на реальный Telegram ID Ольги
            slug="olga-manicure",         # ← URL: /api/v1/olga-manicure/...
            name="Ольга · мастер маникюра",
            specialty="Мастер ногтевого сервиса",
            city="Ростов-на-Дону",
            address="ул. Мечникова, 135",
            phone="+79001234567",
            telegram_username="Pogorelova77",
            working_hours={
                "mon": "9:00-21:00",
                "tue": "9:00-21:00",
                "wed": "9:00-21:00",
                "thu": "9:00-21:00",
                "fri": "9:00-21:00",
                "sat": "10:00-18:00",
                "sun": None,
            },
        )

        db.add(master)
        await db.commit()
        print("✅ Данные Ольги добавлены!")
        print(f"   slug:       olga-manicure")
        print(f"   Проверить:  GET /api/v1/olga-manicure/profile")


if __name__ == "__main__":
    asyncio.run(seed())
