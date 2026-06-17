"""Import certificates from uploaded PEM / PFX files."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_api_key
from ..models import Certificate
from ..schemas import CertificateRead
from ..services.cert_parser import parse_pem, parse_pfx

router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)


def _persist(db: Session, parsed, name: str, environment: str) -> Certificate:
    cert = Certificate(
        name=name,
        common_name=parsed.common_name,
        issuer=parsed.issuer,
        serial_number=parsed.serial_number,
        expiration_date=parsed.not_after,
        valid_from=parsed.not_before,
        environment=environment,
        source="import",
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    logger.info("Imported certificate %s (%s)", cert.id, cert.name)
    return cert


@router.post("/pem", response_model=CertificateRead, dependencies=[Depends(require_api_key)])
async def import_pem(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    environment: str = Form(default="unknown"),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        parsed = parse_pem(data)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid PEM file: {exc}")
    return _persist(db, parsed, name or parsed.common_name or file.filename, environment)


@router.post("/pfx", response_model=CertificateRead, dependencies=[Depends(require_api_key)])
async def import_pfx(
    file: UploadFile = File(...),
    password: str | None = Form(default=None),
    name: str | None = Form(default=None),
    environment: str = Form(default="unknown"),
    db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        parsed = parse_pfx(data, password)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid PFX file: {exc}")
    return _persist(db, parsed, name or parsed.common_name or file.filename, environment)
