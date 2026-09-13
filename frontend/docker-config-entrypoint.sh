#!/bin/sh
# Regenerate the frontend runtime config from environment variables.
#
# The official nginx image runs every executable script in
# /docker-entrypoint.d/ before starting nginx, so this writes /config.js from
# PUBLIC_API_BASE / PUBLIC_API_KEY on each container start — no rebuild needed.
set -eu

CONFIG_FILE="/usr/share/nginx/html/config.js"

cat > "$CONFIG_FILE" <<EOF
window.__PKIMONITOR_CONFIG__ = {
  apiBase: "${PUBLIC_API_BASE:-}",
  apiKey: "${PUBLIC_API_KEY:-}",
};
EOF

echo "[pkimonitor] runtime config written: apiBase='${PUBLIC_API_BASE:-}' (empty = same-origin /api)"
