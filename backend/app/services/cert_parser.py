"""Parse certificates from PEM and PFX/PKCS12 byte blobs (import feature)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from ..utils import as_aware_utc, days_until

logger = logging.getLogger(__name__)


@dataclass
class ParsedCertificate:
    common_name: str | None
    issuer: str | None
    serial_number: str | None
    not_before: datetime | None
    not_after: datetime | None
    days_remaining: int | None


def _not_after(cert: x509.Certificate) -> datetime:
    return getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after


def _not_before(cert: x509.Certificate) -> datetime:
    return getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before


def _extract(cert: x509.Certificate) -> ParsedCertificate:
    cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    not_after = as_aware_utc(_not_after(cert))
    return ParsedCertificate(
        common_name=cn_attrs[0].value if cn_attrs else None,
        issuer=cert.issuer.rfc4514_string(),
        serial_number=format(cert.serial_number, "x"),
        not_before=as_aware_utc(_not_before(cert)),
        not_after=not_after,
        days_remaining=days_until(not_after),
    )


def parse_pem(data: bytes) -> ParsedCertificate:
    """Parse a single PEM-encoded X.509 certificate."""
    cert = x509.load_pem_x509_certificate(data)
    return _extract(cert)


def parse_pfx(data: bytes, password: str | None = None) -> ParsedCertificate:
    """Parse a PKCS12 (.pfx/.p12) container and extract the leaf certificate."""
    pwd = password.encode() if password else None
    _key, cert, _chain = pkcs12.load_key_and_certificates(data, pwd)
    if cert is None:
        raise ValueError("No certificate found in PFX/PKCS12 file")
    return _extract(cert)
