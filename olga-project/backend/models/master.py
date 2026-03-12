"""
Модель таблицы 'masters'.

Модель — это Python-класс, который описывает таблицу в базе данных.
Каждое поле класса = один столбец в таблице.
SQLAlchemy использует эти классы чтобы читать и писать данные.
"""

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, String, Text, Integer, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import TIMESTAMP
from database import Base


class Master(Base):
    __tablename__ = "masters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(32))
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)
    trust_text: Mapped[str | None] = mapped_column(String(256))
    working_hours: Mapped[dict | None] = mapped_column(JSONB)
    timezone: Mapped[str] = mapped_column(
        String(64), server_default="Europe/Moscow"
    )
    slot_duration_min: Mapped[int] = mapped_column(
        Integer, server_default="30"
    )
    buffer_after_min: Mapped[int] = mapped_column(
        Integer, server_default="15"
    )
    cancellation_hours: Mapped[int] = mapped_column(
        Integer, server_default="2"
    )
    subscription_status: Mapped[str] = mapped_column(
        String(16), server_default="trial"
    )
    subscription_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now() + INTERVAL '14 days'"),
    )
    bot_token: Mapped[str | None] = mapped_column(String(128), unique=True)
    bot_username: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
