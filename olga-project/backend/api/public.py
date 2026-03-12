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

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Master, Service

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
