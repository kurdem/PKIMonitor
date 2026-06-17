"""Seed the database with sample certificates and monitors.

Usage (from the backend/ directory):
    python -m scripts.seed
"""

from __future__ import annotations

from datetime import timedelta

from app.database import Base, SessionLocal, engine
from app.models import Certificate, Monitor
from app.services.ssl_checker import parse_target
from app.utils import utcnow


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Certificate).count() or db.query(Monitor).count():
            print("Database already contains data; skipping seed.")
            return

        now = utcnow()
        samples = [
            Certificate(name="Intranet Portal", common_name="intranet.corp.local",
                        issuer="Corp Issuing CA", environment="prod", location="RZ-Nord",
                        contact="it-pki@corp.local",
                        expiration_date=now + timedelta(days=12), source="manual"),
            Certificate(name="Test API Gateway", common_name="api.test.corp.local",
                        issuer="Corp Issuing CA", environment="test",
                        expiration_date=now + timedelta(days=45), source="manual"),
            Certificate(name="VPN Concentrator", common_name="vpn.corp.local",
                        issuer="DigiCert", environment="prod", location="RZ-Sued",
                        expiration_date=now + timedelta(days=200), source="manual"),
            Certificate(name="Altsystem (abgelaufen)", common_name="legacy.corp.local",
                        issuer="Old CA", environment="dev",
                        expiration_date=now - timedelta(days=5), source="manual"),
        ]
        db.add_all(samples)

        for url in ["https://example.com", "https://github.com"]:
            host, port = parse_target(url)
            db.add(Monitor(name=host, url=url, hostname=host, port=port))

        db.commit()
        print(f"Seeded {len(samples)} certificates and 2 monitors.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
