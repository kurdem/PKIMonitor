"""Read the TLS/SSL certificate presented by a remote host.

The checker intentionally disables trust verification so that it can still
report on self-signed, mis-configured or already-expired certificates — those
are exactly the cases we want to surface, not hide behind a handshake error.
"""

from __future__ import annotations

import logging
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from cryptography import x509
from cryptography.x509.oid import NameOID

from ..config import settings
from ..utils import as_aware_utc, days_until

logger = logging.getLogger(__name__)


@dataclass
class SSLCheckResult:
    success: bool
    hostname: str
    port: int
    common_name: str | None = None
    issuer: str | None = None
    serial_number: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    days_remaining: int | None = None
    error: str | None = None


def parse_target(url_or_host: str, default_port: int = 443) -> tuple[str, int]:
    """Extract (hostname, port) from a URL or bare ``host[:port]`` string."""
    raw = (url_or_host or "").strip()
    if not raw:
        raise ValueError("Empty target")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.hostname
    port = parsed.port or default_port
    if not host:
        raise ValueError(f"Could not parse hostname from '{url_or_host}'")
    return host, port


def _name_to_str(name: x509.Name) -> str:
    try:
        return name.rfc4514_string()
    except Exception:  # pragma: no cover - defensive
        return str(name)


def _common_name(name: x509.Name) -> str | None:
    try:
        attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        if attrs:
            return attrs[0].value
    except Exception:  # pragma: no cover - defensive
        pass
    return None


def _not_after(cert: x509.Certificate) -> datetime:
    # cryptography >= 42 exposes tz-aware *_utc accessors; fall back for older.
    return getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after


def _not_before(cert: x509.Certificate) -> datetime:
    return getattr(cert, "not_valid_before_utc", None) or cert.not_valid_before


def check_certificate(
    hostname: str, port: int = 443, timeout: int | None = None
) -> SSLCheckResult:
    """Connect to ``hostname:port`` and return parsed certificate info."""
    timeout = timeout or settings.ssl_timeout_seconds

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls:
                der = tls.getpeercert(binary_form=True)

        if not der:
            return SSLCheckResult(
                success=False, hostname=hostname, port=port,
                error="No certificate returned by server",
            )

        cert = x509.load_der_x509_certificate(der)
        not_after = as_aware_utc(_not_after(cert))
        not_before = as_aware_utc(_not_before(cert))

        return SSLCheckResult(
            success=True,
            hostname=hostname,
            port=port,
            common_name=_common_name(cert.subject),
            issuer=_name_to_str(cert.issuer),
            serial_number=format(cert.serial_number, "x"),
            not_before=not_before,
            not_after=not_after,
            days_remaining=days_until(not_after),
        )
    except (socket.timeout, ConnectionError, OSError, ssl.SSLError) as exc:
        logger.warning("SSL check failed for %s:%s -> %s", hostname, port, exc)
        return SSLCheckResult(success=False, hostname=hostname, port=port, error=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error during SSL check for %s:%s", hostname, port)
        return SSLCheckResult(success=False, hostname=hostname, port=port, error=str(exc))
