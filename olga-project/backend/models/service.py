"""
Модель таблицы 'services'.
Каждая услуга принадлежит конкретному мастеру (master_id).
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import TIMESTAMP
from database import Base


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    master_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("masters.id"), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description_short: Mapped[str | None] = mapped_column(Text)
    description_full: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(8))
    photo_url: Mapped[str | None] = mapped_column(Text)
    gradient: Mapped[str | None] = mapped_column(String(256))
    is_popular: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
