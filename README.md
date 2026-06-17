# 🔐 PKIMonitor

Ein modulares Tool zur **Verwaltung und Überwachung von TLS/SSL-Zertifikaten**.

- Manuelle Erfassung von Zertifikaten (UI / JSON / API)
- Übersicht als Tabelle (Filter & Sortierung), Kalender und Dashboard
- Automatisches zyklisches Monitoring von URLs (TLS-Handshake → Ablaufdatum)
- Benachrichtigungen per E-Mail (SMTP) und Webhook (Slack / Teams / generisch)
- Import aus PEM / PFX
- Saubere Trennung Backend (FastAPI) / Frontend (React + Tailwind), Scheduler als Background-Worker

---

## Inhaltsverzeichnis

1. [Architektur](#1-architektur)
2. [Datenmodell](#2-datenmodell)
3. [Beispiel-Code](#3-beispiel-code)
4. [UI-Struktur](#4-ui-struktur)
5. [Docker-Compose-Setup](#5-docker-compose-setup)
6. [Lokales Setup (Entwicklung)](#6-lokales-setup-entwicklung)
7. [API-Referenz](#7-api-referenz)
8. [Konfiguration](#8-konfiguration)
9. [Best Practices](#9-best-practices-im-projekt)

---

## 1. Architektur

### 1.1 Komponenten (textuelle Beschreibung)

```
                          ┌──────────────────────────────────────────────┐
                          │                  Browser                      │
                          │   React SPA (Vite + Tailwind)                  │
                          │   Dashboard · Tabelle · Kalender · Monitoring  │
                          └───────────────────────┬──────────────────────┘
                                                   │  HTTPS / REST (JSON)
                                                   │  /api/*
                          ┌────────────────────────▼──────────────────────┐
                          │  nginx (Prod)  -  Static SPA + Reverse Proxy    │
                          └────────────────────────┬──────────────────────┘
                                                   │  proxy_pass → backend:8000
        ┌──────────────────────────────────────────▼─────────────────────────────────────┐
        │                              Backend (FastAPI)                                    │
        │                                                                                   │
        │   Routers ──────────────►  Services ───────────────►  Persistenz                  │
        │   /api/certificates        ssl_checker  (TLS-Read)     SQLAlchemy ORM             │
        │   /api/monitors            cert_parser  (PEM/PFX)      └── SQLite / PostgreSQL     │
        │   /api/dashboard           notifications(SMTP/Webhook)                            │
        │   /api/import              monitoring   (Jobs)                                    │
        │                                                                                   │
        │   ┌─────────────────────────────────────────────────────────────────────────┐   │
        │   │  APScheduler (BackgroundScheduler, In-Process)                            │   │
        │   │   • check_all_monitors   alle MONITOR_INTERVAL_HOURS (Default 6h)         │   │
        │   │   • evaluate_alerts      alle ALERT_INTERVAL_HOURS   (Default 24h)        │   │
        │   └───────────────┬─────────────────────────────────┬───────────────────────┘   │
        └───────────────────┼─────────────────────────────────┼───────────────────────────┘
                            │ TLS-Handshake                    │ Alerts
                            ▼                                  ▼
              ┌──────────────────────────┐        ┌──────────────────────────────┐
              │  Externe Hosts / URLs     │        │  SMTP-Server / Slack / Teams  │
              │  (Port 443, …)            │        │                               │
              └──────────────────────────┘        └──────────────────────────────┘
```

### 1.2 Request- und Job-Flows

**URL-Monitoring (zyklisch oder „Jetzt prüfen")**
1. Scheduler ruft `check_all_monitors()` auf.
2. Für jeden aktiven Monitor öffnet `ssl_checker.check_certificate()` einen TLS-Socket
   (ohne Trust-Verification, damit auch abgelaufene/self-signed Zertifikate gelesen werden).
3. Ergebnis wird als `CheckResult` gespeichert; das verknüpfte `Certificate` wird
   aktualisiert oder neu angelegt.

**Alerting**
1. Scheduler ruft `evaluate_alerts()` auf.
2. Pro Zertifikat werden die Resttage gegen die Schwellwerte (z. B. 60/30/7) geprüft.
3. Für den jeweils dringendsten überschrittenen Schwellwert wird – sofern noch nicht
   für dieses Ablaufdatum versendet – eine Benachrichtigung verschickt und in `AlertLog`
   protokolliert (De-Duplizierung; Re-Arm bei Zertifikatserneuerung).

### 1.3 Technologie-Stack

| Schicht       | Technologie                                  |
|---------------|----------------------------------------------|
| Frontend      | React 18, Vite, Tailwind CSS                 |
| Backend / API | Python 3.12, FastAPI, Pydantic v2            |
| ORM / DB      | SQLAlchemy 2.0, SQLite (Default) / PostgreSQL|
| Scheduler     | APScheduler (BackgroundScheduler)            |
| TLS / Krypto  | `cryptography`, stdlib `ssl`/`socket`        |
| Notifications | `smtplib`, `httpx` (Webhooks)                |
| Deployment    | Docker, docker-compose, nginx                |

---

## 2. Datenmodell

### 2.1 Entitäten

- **Certificate** — logischer Zertifikatseintrag (manuell, importiert oder via URL entdeckt)
- **Monitor** — eine zu prüfende URL/Host:Port-Zielangabe, optional 1:1 mit einem `Certificate` verknüpft
- **CheckResult** — Historie einzelner Monitor-Prüfungen
- **AlertLog** — versendete Benachrichtigungen (zur De-Duplizierung)

```
Certificate 1 ───── 0..1 Monitor 1 ───── 0..* CheckResult
     │
     └────── 0..* AlertLog
```

| Feld (Certificate) | Typ        | Beschreibung                                  |
|--------------------|------------|-----------------------------------------------|
| id                 | int        | Primärschlüssel                               |
| name               | str        | Anzeigename / Beschreibung                    |
| description        | str?       | Freitext                                      |
| common_name        | str?       | CN des Zertifikats                            |
| issuer             | str?       | Aussteller                                    |
| serial_number      | str?       | Seriennummer (hex)                            |
| expiration_date    | datetime?  | Ablaufdatum (UTC)                             |
| valid_from         | datetime?  | Gültig ab                                     |
| environment        | enum       | `prod` / `test` / `dev` / `unknown`           |
| location           | str?       | Standort                                      |
| contact            | str?       | Ansprechpartner                               |
| source             | enum       | `manual` / `url` / `import`                   |
| created_at         | datetime   | Anlage                                        |
| updated_at         | datetime   | Letzte Änderung                               |

Berechnete Felder im API-Response: `days_remaining` (Resttage) und
`status` (`ok` / `warning` < 60T / `critical` < 30T / `expired` / `unknown`).

### 2.2 Beispiel-JSON

**Zertifikat (Response `GET /api/certificates/1`):**

```json
{
  "id": 1,
  "name": "Intranet Portal",
  "description": "Wildcard für *.corp.local",
  "common_name": "intranet.corp.local",
  "issuer": "CN=Corp Issuing CA,O=Corp",
  "serial_number": "0a1b2c3d4e5f",
  "expiration_date": "2026-06-29T23:59:59Z",
  "valid_from": "2025-06-29T00:00:00Z",
  "environment": "prod",
  "location": "RZ-Nord",
  "contact": "it-pki@corp.local",
  "source": "manual",
  "created_at": "2026-01-10T08:00:00Z",
  "updated_at": "2026-01-10T08:00:00Z",
  "days_remaining": 12,
  "status": "critical"
}
```

**Anlage eines Monitors (`POST /api/monitors`):**

```json
{ "url": "https://intranet.corp.local", "name": "Intranet", "port": 443, "enabled": true }
```

**Check-Ergebnis (`CheckResult`):**

```json
{
  "id": 42,
  "checked_at": "2026-06-17T06:00:00Z",
  "success": true,
  "error_message": null,
  "common_name": "intranet.corp.local",
  "issuer": "CN=Corp Issuing CA,O=Corp",
  "expiration_date": "2026-06-29T23:59:59Z",
  "days_remaining": 12
}
```

---

## 3. Beispiel-Code

> Alle Snippets stammen 1:1 aus dem Repo – die Pfade sind als Referenz angegeben.

### 3.1 Zertifikat per URL auslesen (`backend/app/services/ssl_checker.py`)

```python
def check_certificate(hostname: str, port: int = 443, timeout: int | None = None) -> SSLCheckResult:
    timeout = timeout or settings.ssl_timeout_seconds

    context = ssl.create_default_context()
    context.check_hostname = False          # auch ungültige/abgelaufene Zertifikate lesen
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls:
                der = tls.getpeercert(binary_form=True)
        cert = x509.load_der_x509_certificate(der)
        not_after = as_aware_utc(_not_after(cert))
        return SSLCheckResult(
            success=True, hostname=hostname, port=port,
            common_name=_common_name(cert.subject),
            issuer=cert.issuer.rfc4514_string(),
            serial_number=format(cert.serial_number, "x"),
            not_after=not_after,
            days_remaining=days_until(not_after),
        )
    except (socket.timeout, ConnectionError, OSError, ssl.SSLError) as exc:
        return SSLCheckResult(success=False, hostname=hostname, port=port, error=str(exc))
```

### 3.2 Scheduler-Job (`backend/app/scheduler.py` + `services/monitoring.py`)

```python
scheduler = BackgroundScheduler(timezone="UTC")

def start_scheduler() -> None:
    scheduler.add_job(check_all_monitors, "interval",
                      hours=settings.monitor_interval_hours, id="monitor_check")
    scheduler.add_job(evaluate_alerts, "interval",
                      hours=settings.alert_interval_hours, id="alert_eval")
    scheduler.start()


def check_all_monitors() -> None:
    db = SessionLocal()
    try:
        for monitor in db.query(Monitor).filter(Monitor.enabled.is_(True)).all():
            run_monitor_check(monitor, db)   # speichert CheckResult + aktualisiert Certificate
    finally:
        db.close()
```

### 3.3 API-Endpoint (`backend/app/routers/certificates.py`)

```python
@router.get("", response_model=list[CertificateRead])
def list_certificates(environment: str | None = None,
                      cert_status: str | None = Query(None, alias="status"),
                      search: str | None = None,
                      db: Session = Depends(get_db)):
    query = db.query(Certificate)
    if environment:
        query = query.filter(Certificate.environment == environment)
    if search:
        like = f"%{search}%"
        query = query.filter(Certificate.name.ilike(like) | Certificate.common_name.ilike(like))
    result = [CertificateRead.model_validate(c)
              for c in query.order_by(Certificate.expiration_date.asc()).all()]
    if cert_status:
        result = [c for c in result if c.status == cert_status]
    return result


@router.post("", response_model=CertificateRead, status_code=201,
             dependencies=[Depends(require_api_key)])
def create_certificate(payload: CertificateCreate, db: Session = Depends(get_db)):
    cert = Certificate(**payload.model_dump(), source="manual")
    db.add(cert); db.commit(); db.refresh(cert)
    return cert
```

---

## 4. UI-Struktur

```
src/
├── App.jsx                     # Tab-Navigation (Dashboard / Zertifikate / Kalender / Monitoring)
├── api.js                      # zentraler fetch-Client (inkl. optionalem X-API-Key)
├── lib/status.js               # Status→Farbe-Mapping (<30=rot, <60=gelb) + Datumsformat
└── components/
    ├── Dashboard.jsx           # Kennzahlen-Kacheln (gesamt / abgelaufen / kritisch / warnung / ok)
    ├── StatCard.jsx            # wiederverwendbare Kennzahlen-Kachel
    ├── CertificateTable.jsx    # Tabelle mit Filter (Umgebung/Status/Suche), Sortierung, Zeilen-Highlight
    ├── CertificateForm.jsx     # Modal zum Anlegen eines Zertifikats
    ├── CalendarView.jsx        # Monatskalender mit Ablaufdaten + Farb-Legende
    └── MonitorList.jsx         # URL-Monitore: anlegen, „Jetzt prüfen", löschen, Status
```

**Farb-Hervorhebung (zentral in `lib/status.js`):**
`expired` → rot gefüllt · `critical` (<30 T) → rot · `warning` (<60 T) → gelb · `ok` → grün.

---

## 5. Docker-Compose-Setup

```bash
cp .env.example .env        # bei Bedarf SMTP/Webhook/API_KEY konfigurieren
docker compose up -d --build
```

- Frontend (nginx):  http://localhost:8080
- Backend (API):     http://localhost:8000  ·  Swagger-UI: http://localhost:8000/docs
- SQLite liegt im benannten Volume `pkimonitor-data` (`/app/data/pkimonitor.db`).

`docker-compose.yml` (gekürzt):

```yaml
services:
  backend:
    build: ./backend
    env_file: .env
    volumes: [ "pkimonitor-data:/app/data" ]
    ports: [ "8000:8000" ]
  frontend:
    build: ./frontend
    depends_on: [ backend ]
    ports: [ "8080:80" ]      # nginx proxyt /api → backend:8000
volumes:
  pkimonitor-data:
```

---

## 6. Lokales Setup (Entwicklung)

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m scripts.seed                 # optional: Beispieldaten
uvicorn app.main:app --reload --port 8000
pytest                                  # Tests
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                             # Vite-Dev-Server auf :5173, /api → :8000 (Proxy)
```

Oder bequem über den `Makefile`: `make backend-install`, `make seed`,
`make backend-run`, `make frontend-install`, `make frontend-run`.

---

## 7. API-Referenz

| Methode | Pfad                          | Beschreibung                                  | Auth* |
|---------|-------------------------------|-----------------------------------------------|:-----:|
| GET     | `/api/health`                 | Healthcheck                                   |   –   |
| GET     | `/api/certificates`           | Liste (Query: `environment`, `status`, `search`) | – |
| GET     | `/api/certificates/{id}`      | Einzelnes Zertifikat                          |   –   |
| POST    | `/api/certificates`           | Anlegen                                       |   ✓   |
| PUT     | `/api/certificates/{id}`      | Aktualisieren (partiell)                      |   ✓   |
| DELETE  | `/api/certificates/{id}`      | Löschen                                       |   ✓   |
| GET     | `/api/monitors`               | Monitor-Liste                                 |   –   |
| GET     | `/api/monitors/{id}`          | Monitor inkl. Check-Historie                  |   –   |
| POST    | `/api/monitors`               | Monitor anlegen                               |   ✓   |
| PUT     | `/api/monitors/{id}`          | Monitor aktualisieren                         |   ✓   |
| DELETE  | `/api/monitors/{id}`          | Monitor löschen                               |   ✓   |
| POST    | `/api/monitors/{id}/check`    | Sofortprüfung auslösen                        |   ✓   |
| GET     | `/api/dashboard`              | Aggregierte Kennzahlen                        |   –   |
| POST    | `/api/import/pem`             | Import PEM (multipart `file`)                 |   ✓   |
| POST    | `/api/import/pfx`             | Import PFX (multipart `file`, `password`)     |   ✓   |

\* Auth nur aktiv, wenn `API_KEY` gesetzt ist; dann Header `X-API-Key: <key>`.

Beispiele:
```bash
# Zertifikat anlegen
curl -X POST localhost:8000/api/certificates -H 'Content-Type: application/json' -d '{
  "name":"Intranet","common_name":"intranet.corp.local",
  "expiration_date":"2026-06-29T23:59:59Z","environment":"prod"}'

# URL überwachen und sofort prüfen
curl -X POST localhost:8000/api/monitors -H 'Content-Type: application/json' \
     -d '{"url":"https://example.com"}'
curl -X POST localhost:8000/api/monitors/1/check

# PEM importieren
curl -X POST localhost:8000/api/import/pem -F 'file=@cert.pem' -F 'environment=prod'
```

---

## 8. Konfiguration

Alle Optionen über Umgebungsvariablen oder `.env` (siehe `.env.example`).
Wichtigste Werte:

| Variable                 | Default                          | Bedeutung                              |
|--------------------------|----------------------------------|----------------------------------------|
| `DATABASE_URL`           | `sqlite:///./data/pkimonitor.db` | DB-Verbindung                          |
| `API_KEY`                | (leer)                           | aktiviert Schreibschutz via Header     |
| `MONITOR_INTERVAL_HOURS` | `6`                              | Prüf-Intervall der URL-Monitore        |
| `ALERT_INTERVAL_HOURS`   | `24`                             | Intervall der Alert-Auswertung         |
| `ALERT_THRESHOLDS`       | `60,30,7`                        | Schwellwerte in Tagen                  |
| `SMTP_ENABLED` / `SMTP_*`| `false`                          | E-Mail-Versand                         |
| `WEBHOOK_ENABLED` / `WEBHOOK_URL` / `WEBHOOK_TYPE` | `false` / – / `slack` | Slack/Teams/generischer Webhook |

---

## 9. Best Practices im Projekt

- **Logging**: zentral konfiguriert (`logging_config.py`), strukturierte Zeilen, ruhiggestellte Drittbibliotheken.
- **Error Handling**: SSL-/Netzwerkfehler werden abgefangen und als Fehlerergebnis persistiert statt den Job abzubrechen; pro Monitor isoliert (ein Fehler stoppt nicht den ganzen Lauf).
- **Config**: `pydantic-settings`, 12-Factor-konform über Env/`.env`, keine Secrets im Code.
- **Trennung der Schichten**: Router (HTTP) → Services (Domänenlogik) → Models (Persistenz).
- **Zeitzonen**: alle Zeitpunkte als UTC; naive DB-Werte werden konsistent als UTC interpretiert (`utils.py`).
- **De-Duplizierung von Alerts** mit Re-Arm bei Zertifikatserneuerung (`AlertLog`).
- **Tests**: `pytest` für SSL-Parsing, Statuslogik und API-CRUD.
- **Erweiterbar**: neue Notification-Kanäle in `notifications.py`, weitere Importformate in `cert_parser.py`, zusätzliche Endpunkte als eigener Router.

### Hinweise für den Produktivbetrieb
- Genau **ein** Backend-Worker, da der Scheduler in-process läuft (mehrere Worker ⇒ mehrfache Jobs). Für horizontale Skalierung Scheduler in eigenen Prozess auslagern oder externen Job-Runner verwenden.
- Für Schemamigrationen statt `create_all` **Alembic** einsetzen (hier bewusst schlank gehalten).
- API hinter TLS/Reverse-Proxy betreiben und `API_KEY` setzen.
