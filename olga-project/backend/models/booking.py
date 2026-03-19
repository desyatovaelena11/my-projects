"""
Модель таблицы 'bookings'.
Хранит все записи клиентов к мастеру.
"""

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, ForeignKey, text
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
        UUID(as_uuid=True), ForeignKey("masters.id"), nullable=False
    )
    # Данные клиента
    client_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    client_name: Mapped[str | None] = mapped_column(String(256))
    client_username: Mapped[str | None] = mapped_column(String(64))

    # Данные услуги (дублируем на момент записи — услуга может измениться)
    service_name: Mapped[str] = mapped_column(String(256), nullable=False)
    service_price: Mapped[int] = mapped_column(Integer, nullable=False)
    service_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)

    # Дата и время записи
    booking_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    booking_time: Mapped[str] = mapped_column(String(5), nullable=False)   # HH:MM

    # Статус: pending → confirmed / cancelled
    status: Mapped[str] = mapped_column(
        String(16), server_default=text("'pending'"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
