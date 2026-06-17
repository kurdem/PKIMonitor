"""Background jobs: run URL monitor checks and evaluate expiry alerts."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models import AlertLog, Certificate, CheckResult, Monitor
from ..utils import as_aware_utc, cert_status, days_until, utcnow
from . import notifications
from .ssl_checker import check_certificate

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Monitor checks
# --------------------------------------------------------------------------
def run_monitor_check(monitor: Monitor, db: Session) -> CheckResult:
    """Check a single monitor, persist the result and sync its certificate."""
    result = check_certificate(monitor.hostname, monitor.port)

    check = CheckResult(
        monitor_id=monitor.id,
        success=result.success,
        error_message=result.error,
        common_name=result.common_name,
        issuer=result.issuer,
        serial_number=result.serial_number,
        expiration_date=result.not_after,
        days_remaining=result.days_remaining,
    )
    db.add(check)

    monitor.last_checked = utcnow()
    monitor.last_success = result.success
    monitor.last_error = result.error

    if result.success:
        cert = monitor.certificate
        if cert is None:
            cert = Certificate(
                name=monitor.name or monitor.hostname,
                common_name=result.common_name,
                source="url",
            )
            db.add(cert)
            db.flush()  # assign cert.id
            monitor.certificate_id = cert.id
        cert.common_name = result.common_name or cert.common_name
        cert.issuer = result.issuer
        cert.serial_number = result.serial_number
        cert.expiration_date = result.not_after
        cert.valid_from = result.not_before
        cert.source = "url"

    db.commit()
    db.refresh(check)
    return check


def check_all_monitors() -> None:
    """Scheduler entry point: check every enabled monitor."""
    db = SessionLocal()
    try:
        monitors = db.query(Monitor).filter(Monitor.enabled.is_(True)).all()
        logger.info("Running scheduled certificate check for %d monitor(s)", len(monitors))
        for monitor in monitors:
            try:
                run_monitor_check(monitor, db)
            except Exception:
                logger.exception("Error checking monitor %s (%s)", monitor.id, monitor.url)
                db.rollback()
    finally:
        db.close()


# --------------------------------------------------------------------------
# Alert evaluation
# --------------------------------------------------------------------------
def evaluate_alerts() -> None:
    """Scheduler entry point: emit notifications for soon-to-expire certs."""
    db = SessionLocal()
    try:
        thresholds = settings.alert_threshold_list
        certs = (
            db.query(Certificate)
            .filter(Certificate.expiration_date.isnot(None))
            .all()
        )
        logger.info(
            "Evaluating alerts for %d certificate(s), thresholds=%s",
            len(certs), thresholds,
        )
        for cert in certs:
            days = days_until(cert.expiration_date)
            if days is None:
                continue
            # Smallest (most urgent) threshold the certificate falls within.
            matched = next((t for t in sorted(thresholds) if days <= t), None)
            if matched is None:
                continue
            if _already_alerted(db, cert, matched):
                continue
            _send_alert(db, cert, days, matched)
    finally:
        db.close()


def _already_alerted(db: Session, cert: Certificate, threshold: int) -> bool:
    """True if we already alerted for this threshold and current expiry date.

    Storing the expiration date on the AlertLog means a renewed certificate
    (new expiry) re-arms the alerting instead of staying silent forever.
    """
    last = (
        db.query(AlertLog)
        .filter(
            AlertLog.certificate_id == cert.id,
            AlertLog.threshold_days == threshold,
        )
        .order_by(AlertLog.sent_at.desc())
        .first()
    )
    if last is None:
        return False
    return as_aware_utc(last.expiration_date) == as_aware_utc(cert.expiration_date)


def _send_alert(db: Session, cert: Certificate, days: int, threshold: int) -> None:
    status = cert_status(days)
    if days < 0:
        subject = f"[PKIMonitor] ABGELAUFEN: {cert.name} ({cert.common_name})"
        lead = f"Das Zertifikat '{cert.name}' (CN: {cert.common_name}) ist seit {abs(days)} Tag(en) abgelaufen."
    else:
        subject = f"[PKIMonitor] Läuft in {days} Tagen ab: {cert.name}"
        lead = f"Das Zertifikat '{cert.name}' (CN: {cert.common_name}) läuft in {days} Tag(en) ab."

    body = (
        f"{lead}\n\n"
        f"Ablaufdatum:     {cert.expiration_date}\n"
        f"Aussteller:      {cert.issuer}\n"
        f"Umgebung:        {cert.environment}\n"
        f"Standort:        {cert.location or '-'}\n"
        f"Ansprechpartner: {cert.contact or '-'}\n"
        f"Schwellwert:     {threshold} Tage\n"
        f"Status:          {status}\n"
    )

    channels = notifications.notify(subject, body)
    for channel in channels:
        db.add(
            AlertLog(
                certificate_id=cert.id,
                threshold_days=threshold,
                channel=channel,
                expiration_date=cert.expiration_date,
            )
        )
    if channels:
        db.commit()
        logger.info("Alert sent for certificate %s via %s", cert.id, channels)
