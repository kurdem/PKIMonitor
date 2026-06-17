"""Aggregated dashboard statistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Certificate, Monitor
from ..schemas import CertificateRead, DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db)):
    certs = [CertificateRead.model_validate(c) for c in db.query(Certificate).all()]
    monitors = db.query(Monitor).all()

    def count(status_value: str) -> int:
        return sum(1 for c in certs if c.status == status_value)

    return DashboardStats(
        total=len(certs),
        expired=count("expired"),
        critical=count("critical"),
        warning=count("warning"),
        ok=count("ok"),
        unknown=count("unknown"),
        monitors_total=len(monitors),
        monitors_failing=sum(1 for m in monitors if m.last_success is False),
    )
