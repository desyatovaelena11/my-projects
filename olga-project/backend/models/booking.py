"""
Модель таблицы 'bookings'.
Хранит все записи клиентов к мастеру.
"""

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import TIMESTAMP
from database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    master_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    # Данные клиента
    client_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    client_name: Mapped[str | None] = mapped_column(String(256))
    client_username: Mapped[str | None] = mapped_column(String(64))

    # Данные услуги (дублируем на момент записи — услуга может измениться)
    service_name: Mapped[str | None] = mapped_column(String(256))
    service_price: Mapped[int | None] = mapped_column(Integer)
    service_duration_min: Mapped[int | None] = mapped_column(Integer)

    # Дата и время записи
    booking_date: Mapped[str | None] = mapped_column(String(10))  # YYYY-MM-DD
    booking_time: Mapped[str | None] = mapped_column(String(5))   # HH:MM

    # Статус: pending → confirmed / cancelled
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'pending'"), nullable=False
    )

    # Доп. поля из оригинальной схемы БД
    note: Mapped[str | None] = mapped_column(String)
    reminder_sent: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cancellation_by: Mapped[str | None] = mapped_column(String(16))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
