// Runtime configuration for the PKIMonitor frontend.
//
// This file is loaded BEFORE the app bundle, so the SPA can be configured per
// deployment without rebuilding the image. In Docker it is regenerated at
// container start from environment variables (see docker-config-entrypoint.sh);
// during local `npm run dev` / `npm run preview` it is served as-is.
//
// apiBase: base URL for the REST API. Leave EMPTY to call the API same-origin
//          under /api — the correct setting behind a reverse proxy serving UI
//          and API on one domain. Set to e.g. "https://api.example.com" only if
//          the API lives on a different origin (then also add that origin to the
//          backend's CORS_ORIGINS).
// apiKey:  optional value sent as the X-API-Key header on write requests
//          (only needed if the backend has API_KEY configured).
window.__PKIMONITOR_CONFIG__ = {
  apiBase: '',
  apiKey: '',
}
