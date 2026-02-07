from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DeliveryStatus(str, Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    EXPIRED = "EXPIRED"


class CampaignStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PAUSED = "PAUSED"


class Template(Base):
    __tablename__ = "templates"
    __table_args__ = (
        UniqueConstraint(
            "template_code",
            "locale",
            "channel",
            name="uq_template_code_locale_channel",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    template_code: Mapped[str] = mapped_column(String(100))
    locale: Mapped[str] = mapped_column(String(10))
    channel: Mapped[str] = mapped_column(String(20))

    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_delivery"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_notification_delivery_job_id"),
    )

    # job_id is the PRIMARY KEY (idempotency key)
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        index=True,
    )

    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(20),
        default=DeliveryStatus.RETRYING.value,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    template_code: Mapped[str] = mapped_column(String(100))
    segment_id: Mapped[str] = mapped_column(String(255))
    schedule_cron: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        String(20),
        default=CampaignStatus.INACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    runs_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    max_runs: Mapped[int | None] = mapped_column(
        Integer,
    )
