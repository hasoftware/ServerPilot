"""Database models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base model class."""
    pass


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    totp_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class Cronjob(Base):
    """Cronjob model."""
    __tablename__ = "cronjobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="CURL")  # CURL or WGET
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_log: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    logs: Mapped[list["CronjobLog"]] = relationship("CronjobLog", back_populates="cronjob", cascade="all, delete-orphan")


class CronjobLog(Base):
    """Cronjob execution log."""
    __tablename__ = "cronjob_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cronjob_id: Mapped[int] = mapped_column(Integer, ForeignKey("cronjobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, failed, error
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    cronjob: Mapped["Cronjob"] = relationship("Cronjob", back_populates="logs")
