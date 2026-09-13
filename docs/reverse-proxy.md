# Betrieb hinter einem Reverse Proxy

PKIMonitor ist so gebaut, dass die Web-UI (SPA) und die API **denselben Origin**
teilen: die SPA ruft die API **relativ** unter `/api` auf. Der Frontend-Container
(nginx) liefert das UI und leitet `/api` intern an das Backend weiter. Damit
brauchst du hinter einem Reverse Proxy auf **einer Domain** weder `IP:port` noch
CORS.

## Empfohlene Topologie (eine Domain)

```
Browser ──HTTPS──▶ Reverse Proxy ──▶ frontend (nginx :80)
                                        ├─ /        → SPA (index.html)
                                        └─ /api/    → backend :8000
```

Der Reverse Proxy zeigt auf den **Frontend-Container** und reicht **alle** Pfade
(inkl. `/api`) durch. Das Backend muss **nicht** öffentlich erreichbar sein.

Beispiel (nginx als äußerer Proxy):

```nginx
server {
    listen 443 ssl;
    server_name pkimonitor.example.com;
    # ... ssl ...

    location / {
        proxy_pass http://frontend:80;      # bzw. host:FRONTEND_PORT
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;             # deckt den Sofort-Check beim Anlegen ab
    }
}
```

Traefik/Caddy analog: eine Route für die Domain → Service `frontend`.

Bei dieser Variante bleibt `PUBLIC_API_BASE` **leer** (Default) — die SPA nutzt
`/api` same-origin.

## Laufzeit-Konfiguration der API-Basis

Die API-Basis-URL der SPA ist **zur Laufzeit** setzbar — ohne das Image neu zu
bauen. Beim Containerstart schreibt ein Init-Skript aus den Environment-Variablen
die Datei `/config.js`, die die SPA vor dem App-Bundle lädt.

| Variable          | Default | Bedeutung                                                        |
|-------------------|---------|------------------------------------------------------------------|
| `PUBLIC_API_BASE` | (leer)  | Basis-URL der API. Leer = same-origin `/api`.                    |
| `PUBLIC_API_KEY`  | (leer)  | optionaler `X-API-Key` für Schreibrequests (nur falls `API_KEY`) |

```bash
# Same-origin (Standard, hinter Reverse Proxy auf einer Domain): nichts setzen
docker compose up -d

# API auf eigenem Origin:
PUBLIC_API_BASE=https://api.pkimonitor.example.com docker compose up -d
```

Precedence in der SPA: `window.__PKIMONITOR_CONFIG__.apiBase` (Laufzeit) →
`VITE_API_BASE` (Build-Zeit) → leer (`/api`).

## Getrennte Origins (UI und API auf verschiedenen Hosts)

Nur falls du UI und API bewusst trennst:

1. **`PUBLIC_API_BASE`** auf die API-URL setzen, z. B. `https://api.example.com`.
2. Diese muss **HTTPS** sein, wenn das UI über HTTPS läuft — sonst blockiert der
   Browser den Request als *Mixed Content*.
3. Im Backend den **UI-Origin** freigeben (kein Rebuild):
   ```env
   CORS_ORIGINS=https://pkimonitor.example.com
   ```
   ⚠️ Nicht `*` verwenden — das Backend läuft mit `allow_credentials=true`.

## Troubleshooting

| Symptom | Ursache | Lösung |
|---|---|---|
| UI lädt, aber Anlegen scheitert nur im Browser (curl auf `/api` geht) | SPA ruft eine andere/absolute API-URL auf (altes `VITE_API_BASE` im Bundle) | `PUBLIC_API_BASE` leeren bzw. korrekt setzen; ggf. Frontend neu bauen |
| `GET /api/health` liefert HTML/404 | `/api` wird nicht ans Backend geproxyt | nginx-`/api`-Block prüfen / am Proxy `/api` aufs Backend routen |
| `502/504` auf `/api` | Backend nicht erreichbar oder Timeout | Docker-Netz/Servicename `backend`; `proxy_read_timeout` erhöhen |
| Mixed-Content-Fehler in der Konsole | `PUBLIC_API_BASE` ist `http://…` bei HTTPS-UI | API über HTTPS bereitstellen |

**Schneller Check:** `curl -i https://deine-domain/api/health` → `{"status":"ok"}`
erwartet. Im Browser (DevTools → Netzwerk) muss der „URL überwachen"-Request an
`https://deine-domain/api/monitors` gehen.
