"""CRUD endpoints for manually-managed certificates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_api_key
from ..models import Certificate
from ..schemas import CertificateCreate, CertificateRead, CertificateUpdate

router = APIRouter(prefix="/api/certificates", tags=["certificates"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[CertificateRead])
def list_certificates(
    environment: str | None = Query(default=None, description="prod|test|dev|unknown"),
    cert_status: str | None = Query(
        default=None, alias="status", description="ok|warning|critical|expired|unknown"
    ),
    search: str | None = Query(default=None, description="Substring of name or CN"),
    db: Session = Depends(get_db),
):
    query = db.query(Certificate)
    if environment:
        query = query.filter(Certificate.environment == environment)
    if search:
        like = f"%{search}%"
        query = query.filter(
            Certificate.name.ilike(like) | Certificate.common_name.ilike(like)
        )

    certs = query.order_by(Certificate.expiration_date.asc()).all()
    result = [CertificateRead.model_validate(c) for c in certs]

    # status is a computed field, so filter after serialization.
    if cert_status:
        result = [c for c in result if c.status == cert_status]
    return result


@router.get("/{cert_id}", response_model=CertificateRead)
def get_certificate(cert_id: int, db: Session = Depends(get_db)):
    cert = db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    return cert


@router.post(
    "", response_model=CertificateRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_certificate(payload: CertificateCreate, db: Session = Depends(get_db)):
    cert = Certificate(**payload.model_dump(), source="manual")
    db.add(cert)
    db.commit()
    db.refresh(cert)
    logger.info("Created certificate %s (%s)", cert.id, cert.name)
    return cert


@router.put(
    "/{cert_id}", response_model=CertificateRead,
    dependencies=[Depends(require_api_key)],
)
def update_certificate(
    cert_id: int, payload: CertificateUpdate, db: Session = Depends(get_db)
):
    cert = db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cert, field, value)
    db.commit()
    db.refresh(cert)
    return cert


@router.delete(
    "/{cert_id}", status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_certificate(cert_id: int, db: Session = Depends(get_db)):
    cert = db.get(Certificate, cert_id)
    if cert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    db.delete(cert)
    db.commit()
    return None
