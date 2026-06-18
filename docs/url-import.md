# URLs automatisiert per API importieren

Diese Anleitung zeigt, wie du **URL-Monitore automatisiert anlegst** und dabei
das TLS-Zertifikat **sofort prüfen** lässt. Das ermittelte Ablaufdatum landet
direkt am Zertifikat und damit in **Tabelle, Dashboard und Kalender** – ohne auf
den nächsten Scheduler-Lauf zu warten.

> Basis-URL in allen Beispielen: `http://localhost:8000` (Backend).
> Hinter dem nginx-Frontend stattdessen `http://localhost:8080`.

---

## Inhalt
1. [Sofort-Check beim Anlegen](#1-sofort-check-beim-anlegen)
2. [Einzelne URL anlegen](#2-einzelne-url-anlegen-post-apimonitors)
3. [Mehrere URLs auf einmal (Bulk-Import)](#3-mehrere-urls-auf-einmal-bulk-import)
4. [Import aus einer Datei (Bash)](#4-import-aus-einer-datei-bash)
5. [Import per Python-Skript](#5-import-per-python-skript)
6. [Authentifizierung](#6-authentifizierung)
7. [Verhalten & Felder im Detail](#7-verhalten--felder-im-detail)

---

## 1. Sofort-Check beim Anlegen

Beim Anlegen eines Monitors wird das Zertifikat **standardmäßig sofort geprüft**.
Dadurch wird automatisch ein `Certificate`-Eintrag erzeugt (oder aktualisiert)
mit `common_name`, `issuer`, `serial_number` und – entscheidend – dem
`expiration_date`. Dieser Eintrag erscheint unmittelbar im Kalender.

- Steuerung über den Query-Parameter `check` (Default `true`).
- `?check=false` überspringt die Sofortprüfung; der zyklische Scheduler
  (Default alle 6 h) holt das Ablaufdatum dann beim nächsten Lauf nach.

---

## 2. Einzelne URL anlegen (`POST /api/monitors`)

```bash
curl -X POST http://localhost:8000/api/monitors \
  -H 'Content-Type: application/json' \
  -d '{
        "url": "https://home.intern.waeldchen.net",
        "name": "Heim-Portal",
        "environment": "prod"
      }'
```

Antwort (gekürzt) – der Monitor ist geprüft und mit einem Zertifikat verknüpft:

```json
{
  "id": 1,
  "url": "https://home.intern.waeldchen.net",
  "hostname": "home.intern.waeldchen.net",
  "port": 443,
  "enabled": true,
  "certificate_id": 1,
  "last_checked": "2026-06-18T06:00:00Z",
  "last_success": true,
  "last_error": null
}
```

Das zugehörige Zertifikat (inkl. Ablaufdatum) liegt danach unter
`GET /api/certificates` bzw. `GET /api/certificates/1`.

Felder im Request-Body:

| Feld          | Pflicht | Default | Bedeutung                                        |
|---------------|:------:|---------|--------------------------------------------------|
| `url`         |   ✓    | –       | URL oder `host[:port]` (Schema optional)         |
| `name`        |   –    | `null`  | Anzeigename                                      |
| `port`        |   –    | `443`   | Port, falls nicht in der URL enthalten           |
| `enabled`     |   –    | `true`  | zyklische Überwachung aktiv                      |
| `environment` |   –    | `null`  | wird auf das erkannte Zertifikat gesetzt (`prod`/`test`/`dev`) |

---

## 3. Mehrere URLs auf einmal (Bulk-Import)

Endpoint: `POST /api/monitors/import`. **Idempotent** – existiert bereits ein
Monitor für dieselbe `host:port`-Kombination, wird er wiederverwendet statt
doppelt angelegt. Damit kann der Import gefahrlos wiederholt werden (z. B. als
Cronjob).

### Variante A – einfache URL-Liste

```bash
curl -X POST http://localhost:8000/api/monitors/import \
  -H 'Content-Type: application/json' \
  -d '{
        "urls": [
          "https://home.intern.waeldchen.net",
          "https://nas.intern.waeldchen.net:5001",
          "mail.intern.waeldchen.net:993"
        ],
        "check": true,
        "default_environment": "prod"
      }'
```

### Variante B – detaillierte Einträge (Name/Port/Umgebung je URL)

```bash
curl -X POST http://localhost:8000/api/monitors/import \
  -H 'Content-Type: application/json' \
  -d '{
        "check": true,
        "default_environment": "prod",
        "monitors": [
          { "url": "https://home.intern.waeldchen.net", "name": "Portal" },
          { "url": "nas.intern.waeldchen.net:5001",     "name": "NAS",   "environment": "test" },
          { "url": "https://vpn.waeldchen.net",          "name": "VPN",   "port": 443 }
        ]
      }'
```

`urls` und `monitors` dürfen auch gemischt im selben Request stehen.

### Antwort (Beispiel)

```json
{
  "total": 3,
  "created": 2,
  "reused": 1,
  "check_failed": 0,
  "items": [
    {
      "url": "https://home.intern.waeldchen.net",
      "monitor_id": 1,
      "created": true,
      "checked": true,
      "success": true,
      "common_name": "home.intern.waeldchen.net",
      "expiration_date": "2026-09-12T10:00:00Z",
      "days_remaining": 86,
      "error": null
    }
  ]
}
```

| Request-Feld          | Default | Bedeutung                                                |
|-----------------------|---------|----------------------------------------------------------|
| `urls`                | `[]`    | einfache Liste von URLs / `host[:port]`                  |
| `monitors`            | `[]`    | detaillierte Einträge `{url, name?, port?, environment?}`|
| `check`               | `true`  | jedes Ziel sofort per TLS prüfen                         |
| `default_environment` | `null`  | Umgebung für erkannte Zertifikate (pro-Eintrag schlägt sie) |

| Response-Feld   | Bedeutung                                              |
|-----------------|--------------------------------------------------------|
| `total`         | Anzahl verarbeiteter Einträge                          |
| `created`       | neu angelegte Monitore                                 |
| `reused`        | wiederverwendete (bereits vorhandene) Monitore         |
| `check_failed`  | Einträge mit Parser- oder TLS-Fehler                   |
| `items[]`       | Detailergebnis je URL (inkl. Ablaufdatum/Resttage)     |

---

## 4. Import aus einer Datei (Bash)

`urls.txt` (eine URL pro Zeile, `#`-Kommentare erlaubt):

```text
# Interne Dienste
https://home.intern.waeldchen.net
https://nas.intern.waeldchen.net:5001
mail.intern.waeldchen.net:993
```

Import-Skript `import-urls.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

API="${API:-http://localhost:8000}"
FILE="${1:-urls.txt}"
API_KEY="${API_KEY:-}"               # nur nötig, wenn Auth aktiv ist

# Zeilen einlesen (Kommentare/Leerzeilen überspringen) und als JSON-Array bauen
mapfile -t urls < <(grep -vE '^\s*(#|$)' "$FILE")
json=$(printf '%s\n' "${urls[@]}" | jq -R . | jq -s \
  '{urls: ., check: true, default_environment: "prod"}')

curl -fsS -X POST "$API/api/monitors/import" \
  -H 'Content-Type: application/json' \
  ${API_KEY:+-H "X-API-Key: $API_KEY"} \
  -d "$json" | jq '{created, reused, check_failed}'
```

Aufruf:

```bash
chmod +x import-urls.sh
./import-urls.sh urls.txt
# oder mit Auth / anderem Host:
API=http://localhost:8080 API_KEY=geheim ./import-urls.sh urls.txt
```

---

## 5. Import per Python-Skript

```python
#!/usr/bin/env python3
"""Importiert URLs aus einer Textdatei in PKIMonitor."""
import os
import sys
import httpx

API = os.environ.get("API", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY")  # optional

def load_urls(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh
                if ln.strip() and not ln.lstrip().startswith("#")]

def main(path: str) -> None:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    payload = {
        "urls": load_urls(path),
        "check": True,
        "default_environment": "prod",
    }
    resp = httpx.post(f"{API}/api/monitors/import", json=payload,
                      headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    print(f"created={data['created']} reused={data['reused']} "
          f"check_failed={data['check_failed']}")
    for item in data["items"]:
        status = "OK" if item["success"] else f"FEHLER ({item['error']})"
        exp = item.get("expiration_date") or "-"
        print(f"  {item['url']:45} {status:18} läuft ab: {exp}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "urls.txt")
```

Aufruf: `python import-urls.py urls.txt` (benötigt `pip install httpx`).

---

## 6. Authentifizierung

Ist im Backend `API_KEY` gesetzt, brauchen **Schreibanfragen** (also auch der
Import) den Header `X-API-Key`:

```bash
curl -X POST http://localhost:8000/api/monitors/import \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <dein-key>' \
  -d '{ "urls": ["https://home.intern.waeldchen.net"] }'
```

Ist `API_KEY` leer/nicht gesetzt, ist die Auth deaktiviert und der Header
entfällt.

---

## 7. Verhalten & Felder im Detail

- **Sofort-Check**: `check=true` (Default) öffnet je Ziel einen TLS-Handshake
  (Timeout `SSL_TIMEOUT_SECONDS`, Default 10 s). Auch abgelaufene/selbstsignierte
  Zertifikate werden gelesen – genau die wollen wir ja sehen.
- **Kalender/Tabelle**: gespeist aus `GET /api/certificates`. Nach dem Import
  enthalten die Einträge `expiration_date`, `days_remaining` und einen `status`
  (`ok` / `warning` < 60 T / `critical` < 30 T / `expired`).
- **Idempotenz**: Schlüssel ist `hostname:port`. Wiederholter Import prüft
  bestehende Monitore erneut, statt Duplikate zu erzeugen.
- **Fehler je Eintrag** stoppen den Import nicht: nicht erreichbare Hosts werden
  als `success=false` mit `error` zurückgegeben und beim nächsten Scheduler-Lauf
  erneut versucht.
- **Umgebung**: `environment` (pro Eintrag) bzw. `default_environment` wird auf
  das erkannte Zertifikat geschrieben – nützlich zum Filtern nach Prod/Test/Dev.
- **Regelmäßiger Re-Import**: Skript einfach per Cron aufrufen, z. B. täglich:

  ```cron
  30 6 * * *  API=http://localhost:8000 /opt/pkimonitor/import-urls.sh /opt/pkimonitor/urls.txt
  ```
