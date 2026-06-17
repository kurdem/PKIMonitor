"""CRUD + on-demand checks for URL/TLS monitors."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_api_key
from ..models import Monitor
from ..schemas import (
    CheckResultRead,
    MonitorCreate,
    MonitorDetail,
    MonitorRead,
    MonitorUpdate,
)
from ..services.monitoring import run_monitor_check
from ..services.ssl_checker import parse_target

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


@router.post(
    "", response_model=MonitorRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
    try:
        hostname, port = parse_target(payload.url, payload.port)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    monitor = Monitor(
        url=payload.url,
        name=payload.name,
        hostname=hostname,
        port=port,
        enabled=payload.enabled,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    logger.info("Created monitor %s for %s:%s", monitor.id, hostname, port)
    return monitor


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
