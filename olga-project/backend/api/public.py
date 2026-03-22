"""
Публичные эндпоинты — вызываются из TMA (Telegram Mini App).
Авторизация не нужна: клиент просто открывает приложение.

Все пути начинаются с /api/v1/{slug}/
  slug — уникальное имя мастера, например "olga-manicure"
  TMA читает slug из ссылки: t.me/Bot/app?startapp=olga-manicure

Перед каждым запросом проверяем:
  1. Мастер с таким slug существует и активен
  2. Подписка мастера не истекла
"""

import uuid
from datetime import datetime, timezone, date as date_cls

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Master, Service, Booking

router = APIRouter(prefix="/api/v1")


async def _get_active_master(slug: str, db: AsyncSession) -> Master:
    """
    Вспомогательная функция: найти мастера по slug.
    Проверяет что мастер существует и подписка не истекла.
    Используется во всех публичных эндпоинтах.
    """
    result = await db.execute(
        select(Master).where(Master.slug == slug, Master.is_active == True)
    )
    master = result.scalar_one_or_none()

    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    # Проверяем подписку: если текущее время позже expires_at — подписка истекла
    now = datetime.now(timezone.utc)
    if master.subscription_expires_at < now:
        raise HTTPException(
            status_code=402,
            detail="Страница мастера временно недоступна. Свяжитесь с мастером напрямую."
        )

    return master


@router.get("/{slug}/profile")
async def get_profile(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает публичный профиль мастера.
    TMA показывает эти данные на главном экране.
    """
    master = await _get_active_master(slug, db)

    return {
        "name": master.name,
        "specialty": master.specialty,
        "city": master.city,
        "address": master.address,
        "phone": master.phone,
        "telegram_username": master.telegram_username,
        "avatar_url": master.avatar_url,
        "bio": master.bio,
        "trust_text": master.trust_text,
        "working_hours": master.working_hours,
        "cancellation_hours": master.cancellation_hours,
        "buffer_after_min": master.buffer_after_min,
        "slug": master.slug,
        "bot_username": master.bot_username,
    }


@router.get("/{slug}/services")
async def get_services(
    slug: str,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список услуг мастера.
    Только активные (is_active=true), отсортированные по sort_order.

    Опциональный фильтр: ?category=manicure
    Возможные категории: manicure, pedicure, design, extension
    """
    master = await _get_active_master(slug, db)

    query = (
        select(Service)
        .where(Service.master_id == master.id, Service.is_active == True)
        .order_by(Service.sort_order)
    )
    if category:
        query = query.where(Service.category == category)

    result = await db.execute(query)
    services = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "category": s.category,
            "name": s.name,
            "description_short": s.description_short,
            "price": s.price,
            "duration_min": s.duration_min,
            "icon": s.icon,
            "photo_url": s.photo_url,
            "gradient": s.gradient,
            "is_popular": s.is_popular,
        }
        for s in services
    ]


@router.get("/{slug}/slots")
async def get_slots(slug: str, date: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает занятые временные интервалы для выбранной даты.
    TMA использует это чтобы показать клиенту только свободное время.

    Параметр: ?date=YYYY-MM-DD
    Ответ: {"booked": [{"start": "10:00", "duration_min": 90}, ...]}
    """
    master = await _get_active_master(slug, db)

    result = await db.execute(
        select(Booking).where(
            Booking.master_id == master.id,
            Booking.booking_date == date,
            Booking.status != "cancelled",
        )
    )
    bookings = result.scalars().all()

    return {
        "booked": [
            {"start": b.booking_time, "duration_min": b.service_duration_min}
            for b in bookings
        ]
    }


# ── Создание записи (вызывается напрямую из TMA) ──────────────────────────────

class BookingCreate(BaseModel):
    service_name: str = Field(..., min_length=1)
    service_price: int = Field(..., ge=0)
    service_duration_min: int = Field(..., gt=0)
    booking_date: str          # YYYY-MM-DD
    booking_time: str          # HH:MM
    booking_label: str = ""
    client_telegram_id: int | None = None
    client_name: str | None = None
    client_username: str | None = None


async def _tg_send(token: str, chat_id: int, text: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
    except Exception:
        pass


@router.post("/{slug}/bookings")
async def create_booking(slug: str, body: BookingCreate, db: AsyncSession = Depends(get_db)):
    master = await _get_active_master(slug, db)

    # Проверка: дата не в прошлом
    try:
        booking_date_obj = date_cls.fromisoformat(body.booking_date)
        if booking_date_obj < date_cls.today():
            raise HTTPException(status_code=400, detail="Нельзя записаться на прошедшую дату")
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты")

    # Проверка: слот не занят
    conflict = await db.execute(
        select(Booking).where(
            Booking.master_id == master.id,
            Booking.booking_date == body.booking_date,
            Booking.booking_time == body.booking_time,
            Booking.status != "cancelled",
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Это время уже занято. Выберите другое.")

    # Сохраняем запись
    booking = Booking(
        id=uuid.uuid4(),
        master_id=master.id,
        client_telegram_id=body.client_telegram_id,
        client_name=body.client_name,
        client_username=body.client_username,
        service_name=body.service_name,
        service_price=body.service_price,
        service_duration_min=body.service_duration_min,
        booking_date=body.booking_date,
        booking_time=body.booking_time,
        status="pending",
    )
    db.add(booking)
    await db.commit()

    # Уведомляем мастера и клиента через Telegram
    if master.bot_token:
        client_mention = (
            f"@{body.client_username.replace('_', chr(92) + '_')}"
            if body.client_username
            else (body.client_name or "Клиент")
        )
        date_str = body.booking_label or f"{body.booking_date} в {body.booking_time}"

        if master.telegram_id:
            await _tg_send(
                master.bot_token,
                master.telegram_id,
                f"📩 *Новая заявка!*\n\n"
                f"👤 Клиент: {client_mention}\n"
                f"💅 Услуга: {body.service_name}\n"
                f"📅 Дата и время: {date_str}\n"
                f"💰 Стоимость: {body.service_price} ₽\n"
                f"⏱ Длительность: {body.service_duration_min} мин\n\n"
                f"Клиент ждёт подтверждения — напиши ему в Telegram.",
            )

        if body.client_telegram_id:
            await _tg_send(
                master.bot_token,
                body.client_telegram_id,
                f"✅ Заявка отправлена!\n\n"
                f"Вы записались на *{date_str}*.\n"
                f"*{master.name}* получила запрос и напишет в Telegram для подтверждения.",
            )

    return {"ok": True, "booking_id": str(booking.id)}
