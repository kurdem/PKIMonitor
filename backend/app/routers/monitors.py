"""CRUD + on-demand checks for URL/TLS monitors."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_api_key
from ..models import Monitor
from ..schemas import (
    CheckResultRead,
    MonitorCreate,
    MonitorDetail,
    MonitorImportItem,
    MonitorImportRequest,
    MonitorImportResponse,
    MonitorImportResultItem,
    MonitorRead,
    MonitorUpdate,
)
from ..services.monitoring import run_monitor_check
from ..services.ssl_checker import parse_target
from ..utils import days_until

router = APIRouter(prefix="/api/monitors", tags=["monitors"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[MonitorRead])
def list_monitors(db: Session = Depends(get_db)):
    return db.query(Monitor).order_by(Monitor.created_at.desc()).all()


@router.get("/{monitor_id}", response_model=MonitorDetail)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    return monitor


def _create_monitor(
    db: Session, url: str, name: str | None, port: int, enabled: bool = True
) -> Monitor:
    hostname, port = parse_target(url, port)
    monitor = Monitor(url=url, name=name, hostname=hostname, port=port, enabled=enabled)
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    logger.info("Created monitor %s for %s:%s", monitor.id, hostname, port)
    return monitor


def _check_and_tag(db: Session, monitor: Monitor, environment: str | None) -> None:
    """Best-effort immediate TLS check; never raises (errors are persisted)."""
    try:
        run_monitor_check(monitor, db)
        if environment and monitor.certificate is not None:
            monitor.certificate.environment = environment
            db.commit()
        db.refresh(monitor)
    except Exception:
        logger.exception("Immediate check failed for monitor %s", monitor.id)
        db.rollback()


@router.post(
    "", response_model=MonitorRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_monitor(
    payload: MonitorCreate,
    check: bool = Query(default=True, description="Run a TLS check immediately"),
    db: Session = Depends(get_db),
):
    """Create a monitor.

    By default the certificate is checked right away, so its expiration date is
    discovered and shown in the calendar without waiting for the scheduler.
    Pass ``?check=false`` to skip the immediate check.
    """
    try:
        monitor = _create_monitor(db, payload.url, payload.name, payload.port, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    if check:
        _check_and_tag(db, monitor, payload.environment)
    return monitor


@router.post(
    "/import", response_model=MonitorImportResponse,
    dependencies=[Depends(require_api_key)],
)
def import_monitors(payload: MonitorImportRequest, db: Session = Depends(get_db)):
    """Bulk-import URL monitors (idempotent on hostname:port).

    Accepts either detailed ``monitors`` items or a plain ``urls`` list. When
    ``check`` is true (default) each target is TLS-checked immediately, so the
    discovered certificates and expiry dates appear right away.
    """
    items: list[MonitorImportItem] = list(payload.monitors)
    items += [MonitorImportItem(url=u) for u in payload.urls]

    results: list[MonitorImportResultItem] = []
    created = reused = check_failed = 0

    for item in items:
        res = MonitorImportResultItem(url=item.url)
        try:
            hostname, port = parse_target(item.url, item.port)
        except ValueError as exc:
            res.error = str(exc)
            results.append(res)
            check_failed += 1
            continue

        # Idempotency: reuse an existing monitor for the same host:port.
        monitor = (
            db.query(Monitor)
            .filter(Monitor.hostname == hostname, Monitor.port == port)
            .first()
        )
        if monitor is None:
            monitor = _create_monitor(db, item.url, item.name, port)
            res.created = True
            created += 1
        else:
            reused += 1

        res.monitor_id = monitor.id
        environment = item.environment or payload.default_environment

        if payload.check:
            _check_and_tag(db, monitor, environment)
            res.checked = True
            res.success = monitor.last_success
            if monitor.last_success:
                cert = monitor.certificate
                if cert is not None:
                    res.common_name = cert.common_name
                    res.expiration_date = cert.expiration_date
                    res.days_remaining = days_until(cert.expiration_date)
            else:
                res.error = monitor.last_error
                check_failed += 1
        elif environment:
            # No check requested but still want to remember the environment
            # once a certificate exists.
            if monitor.certificate is not None:
                monitor.certificate.environment = environment
                db.commit()

        results.append(res)

    logger.info("Bulk import: %d created, %d reused, %d check-failed",
                created, reused, check_failed)
    return MonitorImportResponse(
        total=len(items), created=created, reused=reused,
        check_failed=check_failed, items=results,
    )


@router.put(
    "/{monitor_id}", response_model=MonitorRead,
    dependencies=[Depends(require_api_key)],
)
def update_monitor(
    monitor_id: int, payload: MonitorUpdate, db: Session = Depends(get_db)
):
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")

    data = payload.model_dump(exclude_unset=True)
    if "url" in data or "port" in data:
        url = data.get("url", monitor.url)
        port = data.get("port", monitor.port)
        try:
            monitor.hostname, monitor.port = parse_target(url, port)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    for field, value in data.items():
        setattr(monitor, field, value)
    db.commit()
    db.refresh(monitor)
    return monitor


@router.delete(
    "/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    db.delete(monitor)
    db.commit()
    return None


@router.post(
    "/{monitor_id}/check", response_model=CheckResultRead,
    dependencies=[Depends(require_api_key)],
)
def check_monitor_now(monitor_id: int, db: Session = Depends(get_db)):
    """Trigger an immediate TLS check for a single monitor."""
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    return run_monitor_check(monitor, db)
