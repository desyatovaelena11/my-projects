"""
Эндпоинты панели мастера.

Все маршруты защищены токеном: X-Admin-Token в заголовке.
Токен хранится в переменной окружения ADMIN_TOKEN.
Slug мастера берётся из ADMIN_SLUG.
"""

import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Master, Service, Booking

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Аутентификация ────────────────────────────────────────────────────────────

async def verify_token(x_admin_token: str = Header(...)):
    if x_admin_token != os.environ.get("ADMIN_TOKEN", ""):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _get_master(db: AsyncSession) -> Master:
    slug = os.environ.get("ADMIN_SLUG", "")
    result = await db.execute(select(Master).where(Master.slug == slug))
    master = result.scalar_one_or_none()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    return master


# ── Вход ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    token: str


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    if body.token != os.environ.get("ADMIN_TOKEN", ""):
        raise HTTPException(status_code=401, detail="Неверный токен")
    master = await _get_master(db)
    return {"slug": master.slug, "name": master.name}


# ── Профиль ───────────────────────────────────────────────────────────────────

@router.get("/profile")
async def get_profile(
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    return {
        "name": master.name,
        "specialty": master.specialty,
        "city": master.city,
        "address": master.address,
        "phone": master.phone,
        "bio": master.bio,
        "trust_text": master.trust_text,
        "working_hours": master.working_hours,
        "cancellation_hours": master.cancellation_hours,
    }


class ProfileUpdate(BaseModel):
    name: str | None = None
    specialty: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    bio: str | None = None
    trust_text: str | None = None
    working_hours: dict | None = None
    cancellation_hours: int | None = None


@router.put("/profile")
async def update_profile(
    body: ProfileUpdate,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)

    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="Имя не может быть пустым")
        master.name = body.name
    if body.specialty is not None:
        master.specialty = body.specialty
    if body.city is not None:
        master.city = body.city
    if body.address is not None:
        master.address = body.address
    if body.phone is not None:
        master.phone = body.phone
    if body.bio is not None:
        master.bio = body.bio
    if body.trust_text is not None:
        master.trust_text = body.trust_text
    if body.working_hours is not None:
        master.working_hours = body.working_hours
    if body.cancellation_hours is not None:
        master.cancellation_hours = body.cancellation_hours

    master.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True, "name": master.name}


# ── Услуги ────────────────────────────────────────────────────────────────────

@router.get("/services")
async def get_services(
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    result = await db.execute(
        select(Service)
        .where(Service.master_id == master.id)
        .order_by(Service.sort_order, Service.created_at)
    )
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
            "gradient": s.gradient,
            "is_popular": s.is_popular,
            "is_active": s.is_active,
            "sort_order": s.sort_order,
        }
        for s in services
    ]


class ServiceCreate(BaseModel):
    category: str = "manicure"
    name: str = Field(..., min_length=1, max_length=256)
    description_short: str | None = None
    price: int = Field(..., ge=0)
    duration_min: int = Field(..., gt=0)
    icon: str | None = "💅"
    gradient: str | None = "linear-gradient(135deg, #2a2a2a, #1a1a1a)"
    is_popular: bool = False
    is_active: bool = True
    sort_order: int = 0


@router.post("/services")
async def create_service(
    body: ServiceCreate,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    service = Service(
        id=uuid.uuid4(),
        master_id=master.id,
        category=body.category,
        name=body.name,
        description_short=body.description_short,
        price=body.price,
        duration_min=body.duration_min,
        icon=body.icon,
        gradient=body.gradient,
        is_popular=body.is_popular,
        is_active=body.is_active,
        sort_order=body.sort_order,
    )
    db.add(service)
    await db.commit()
    return {"ok": True, "id": str(service.id)}


class ServiceUpdate(BaseModel):
    category: str | None = None
    name: str | None = None
    description_short: str | None = None
    price: int | None = None
    duration_min: int | None = None
    icon: str | None = None
    gradient: str | None = None
    is_popular: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


@router.put("/services/{service_id}")
async def update_service(
    service_id: str,
    body: ServiceUpdate,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    result = await db.execute(
        select(Service).where(
            Service.id == uuid.UUID(service_id),
            Service.master_id == master.id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    if body.category is not None:
        service.category = body.category
    if body.name is not None:
        service.name = body.name
    if body.description_short is not None:
        service.description_short = body.description_short
    if body.price is not None:
        service.price = body.price
    if body.duration_min is not None:
        service.duration_min = body.duration_min
    if body.icon is not None:
        service.icon = body.icon
    if body.gradient is not None:
        service.gradient = body.gradient
    if body.is_popular is not None:
        service.is_popular = body.is_popular
    if body.is_active is not None:
        service.is_active = body.is_active
    if body.sort_order is not None:
        service.sort_order = body.sort_order

    await db.commit()
    return {"ok": True}


# ── Записи клиентов ───────────────────────────────────────────────────────────

@router.get("/bookings")
async def get_bookings(
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    result = await db.execute(
        select(Booking)
        .where(Booking.master_id == master.id)
        .order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
    )
    bookings = result.scalars().all()
    return [
        {
            "id": str(b.id),
            "client_name": b.client_name,
            "client_username": b.client_username,
            "service_name": b.service_name,
            "service_price": b.service_price,
            "service_duration_min": b.service_duration_min,
            "booking_date": b.booking_date,
            "booking_time": b.booking_time,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bookings
    ]


class StatusUpdate(BaseModel):
    status: str


@router.put("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    body: StatusUpdate,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in ("pending", "confirmed", "cancelled"):
        raise HTTPException(status_code=400, detail="Неверный статус")
    master = await _get_master(db)
    result = await db.execute(
        select(Booking).where(
            Booking.id == uuid.UUID(booking_id),
            Booking.master_id == master.id,
        )
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    booking.status = body.status
    await db.commit()

    # Уведомляем клиента если есть его Telegram ID
    if booking.client_telegram_id and master.bot_token:
        date_str = f"{booking.booking_date} в {booking.booking_time}" if booking.booking_date else ""
        if body.status == "confirmed":
            text = (
                f"✅ *{master.name}* подтвердила вашу запись!\n\n"
                f"💅 Услуга: {booking.service_name}\n"
                + (f"📅 Дата и время: {date_str}\n" if date_str else "") +
                f"\nЖдём вас!"
            )
        else:
            text = (
                f"❌ Запись отменена.\n\n"
                f"💅 Услуга: {booking.service_name}\n"
                + (f"📅 Дата и время: {date_str}\n" if date_str else "") +
                f"\nЕсли у вас есть вопросы — напишите мастеру напрямую."
            )
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{master.bot_token}/sendMessage",
                    json={"chat_id": booking.client_telegram_id, "text": text, "parse_mode": "Markdown"},
                    timeout=10,
                )
        except Exception:
            pass  # Не ломаем ответ если Telegram недоступен

    return {"ok": True}


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    _: None = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    master = await _get_master(db)
    result = await db.execute(
        select(Service).where(
            Service.id == uuid.UUID(service_id),
            Service.master_id == master.id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    await db.delete(service)
    await db.commit()
    return {"ok": True}
