"""SQLAlchemy ORM models.

Domain model
------------
Certificate   A logical certificate entry (manually added, imported or
              auto-discovered via a URL monitor).
Monitor       A URL/host:port target that is periodically TLS-checked.
              Optionally linked 1:1 to a Certificate it keeps up to date.
CheckResult   Historical record of a single monitor check.
AlertLog      Record of notifications already sent (used to de-duplicate
              alerts per threshold and expiration date).
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base
from .utils import utcnow


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    common_name = Column(String(255), nullable=True, index=True)
    issuer = Column(String(512), nullable=True)
    serial_number = Column(String(128), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True, index=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    environment = Column(String(20), default="unknown", nullable=False)  # prod|test|dev|unknown
    location = Column(String(255), nullable=True)
    contact = Column(String(255), nullable=True)
    source = Column(String(20), default="manual", nullable=False)  # manual|url|import

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    monitor = relationship(
        "Monitor", back_populates="certificate", uselist=False
    )
    alerts = relationship(
        "AlertLog", back_populates="certificate", cascade="all, delete-orphan"
    )


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    url = Column(String(512), nullable=False)
    hostname = Column(String(255), nullable=False)
    port = Column(Integer, default=443, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)

    certificate_id = Column(
        Integer, ForeignKey("certificates.id", ondelete="SET NULL"), nullable=True
    )
    last_checked = Column(DateTime(timezone=True), nullable=True)
    last_success = Column(Boolean, nullable=True)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    certificate = relationship("Certificate", back_populates="monitor")
    results = relationship(
        "CheckResult",
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="desc(CheckResult.checked_at)",
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True)
    monitor_id = Column(
        Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    success = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)

    common_name = Column(String(255), nullable=True)
    issuer = Column(String(512), nullable=True)
    serial_number = Column(String(128), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    days_remaining = Column(Integer, nullable=True)

    monitor = relationship("Monitor", back_populates="results")


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True)
    certificate_id = Column(
        Integer, ForeignKey("certificates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    threshold_days = Column(Integer, nullable=False)
    channel = Column(String(50), nullable=False)  # email|webhook
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    certificate = relationship("Certificate", back_populates="alerts")
