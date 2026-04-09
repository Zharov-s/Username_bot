from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class ConsentStatus(str, Enum):
    OPT_IN = "opt_in"
    NO_CONSENT = "no_consent"
    REVOKED = "revoked"


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    contacts: Mapped[list["ContactRecord"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    imports: Mapped[list["ImportBatch"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class ContactRecord(Base):
    __tablename__ = "contact_records"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "source_name", "phone_e164", name="uq_contact_owner_source_phone"),
        Index("ix_contact_owner_source_phone", "owner_user_id", "source_name", "phone_e164"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    phone_e164: Mapped[str] = mapped_column(String(32), index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_status: Mapped[ConsentStatus] = mapped_column(
        SQLEnum(ConsentStatus, name="consent_status", native_enum=False, length=32),
        default=ConsentStatus.OPT_IN,
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="contacts")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_name: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="imports")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_owner_action_created", "owner_user_id", "action", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(default=True)
    target_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="audit_logs")
