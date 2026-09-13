"""Pydantic v2 request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from .utils import cert_status, days_until


# --------------------------------------------------------------------------
# Certificates
# --------------------------------------------------------------------------
class CertificateBase(BaseModel):
    name: str
    description: str | None = None
    common_name: str | None = None
    issuer: str | None = None
    expiration_date: datetime | None = None
    valid_from: datetime | None = None
    environment: str = "unknown"
    location: str | None = None
    contact: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    common_name: str | None = None
    issuer: str | None = None
    expiration_date: datetime | None = None
    environment: str | None = None
    location: str | None = None
    contact: str | None = None


class CertificateRead(CertificateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_number: str | None = None
    source: str
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def days_remaining(self) -> int | None:
        return days_until(self.expiration_date)

    @computed_field  # type: ignore[misc]
    @property
    def status(self) -> str:
        return cert_status(self.days_remaining)


# --------------------------------------------------------------------------
# Monitors
# --------------------------------------------------------------------------
class MonitorBase(BaseModel):
    url: str
    name: str | None = None
    port: int = 443
    enabled: bool = True


class MonitorCreate(MonitorBase):
    # Optional environment applied to the auto-discovered certificate.
    environment: str | None = None


class MonitorUpdate(BaseModel):
    url: str | None = None
    name: str | None = None
    port: int | None = None
    enabled: bool | None = None


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checked_at: datetime
    success: bool
    error_message: str | None = None
    common_name: str | None = None
    issuer: str | None = None
    expiration_date: datetime | None = None
    days_remaining: int | None = None


class MonitorRead(MonitorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    certificate_id: int | None = None
    last_checked: datetime | None = None
    last_success: bool | None = None
    last_error: str | None = None
    created_at: datetime


class MonitorDetail(MonitorRead):
    results: list[CheckResultRead] = []


# --------------------------------------------------------------------------
# Bulk import of URL monitors
# --------------------------------------------------------------------------
class MonitorImportItem(BaseModel):
    url: str
    name: str | None = None
    port: int = 443
    environment: str | None = None


class MonitorImportRequest(BaseModel):
    # Either pass detailed items via `monitors`, or a plain list of URLs.
    monitors: list[MonitorImportItem] = []
    urls: list[str] = []
    # Run a TLS check immediately so the expiry date is available at once.
    check: bool = True
    # Default environment for discovered certificates (per-item value wins).
    default_environment: str | None = None


class MonitorImportResultItem(BaseModel):
    url: str
    monitor_id: int | None = None
    created: bool = False        # False if an existing monitor was reused
    checked: bool = False
    success: bool | None = None  # result of the immediate TLS check
    common_name: str | None = None
    expiration_date: datetime | None = None
    days_remaining: int | None = None
    error: str | None = None


class MonitorImportResponse(BaseModel):
    total: int
    created: int
    reused: int
    check_failed: int
    items: list[MonitorImportResultItem]


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
class NotificationTestResult(BaseModel):
    channel: str
    enabled: bool
    success: bool
    detail: str


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total: int
    expired: int
    critical: int  # < 30 days
    warning: int   # < 60 days
    ok: int
    unknown: int
    monitors_total: int
    monitors_failing: int
