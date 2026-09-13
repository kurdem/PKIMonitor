// Thin fetch wrapper around the PKIMonitor REST API.
//
// Runtime config (window.__PKIMONITOR_CONFIG__, injected by /config.js) takes
// precedence over the build-time VITE_* vars, so the API base can be set per
// deployment without rebuilding. Empty = same-origin relative /api.
const runtimeConfig =
  (typeof window !== 'undefined' && window.__PKIMONITOR_CONFIG__) || {}
const API_BASE = runtimeConfig.apiBase || import.meta.env.VITE_API_BASE || ''
const API_KEY = runtimeConfig.apiKey || import.meta.env.VITE_API_KEY || ''

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (API_KEY) headers['X-API-Key'] = API_KEY

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Certificates
  listCertificates: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null),
    ).toString()
    return request(`/api/certificates${qs ? `?${qs}` : ''}`)
  },
  createCertificate: (data) => request('/api/certificates', { method: 'POST', body: JSON.stringify(data) }),
  updateCertificate: (id, data) => request(`/api/certificates/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCertificate: (id) => request(`/api/certificates/${id}`, { method: 'DELETE' }),

  // Monitors
  listMonitors: () => request('/api/monitors'),
  createMonitor: (data) => request('/api/monitors', { method: 'POST', body: JSON.stringify(data) }),
  deleteMonitor: (id) => request(`/api/monitors/${id}`, { method: 'DELETE' }),
  checkMonitor: (id) => request(`/api/monitors/${id}/check`, { method: 'POST' }),

  // Dashboard
  dashboard: () => request('/api/dashboard'),

  // Notifications
  testNotifications: (channel) =>
    request(`/api/notifications/test${channel ? `?channel=${channel}` : ''}`, { method: 'POST' }),

  // Import
  importPem: (formData) => request('/api/import/pem', { method: 'POST', body: formData }),
}
