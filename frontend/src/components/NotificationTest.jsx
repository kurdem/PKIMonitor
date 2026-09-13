import { useState } from 'react'
import { api } from '../api'

// Test button for notifications (issue #5): triggers a test e-mail / webhook
// and shows per-channel results returned by POST /api/notifications/test.
export default function NotificationTest() {
  const [results, setResults] = useState(null)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)

  async function run(channel) {
    setBusy(channel || 'all')
    setError(null)
    setResults(null)
    try {
      setResults(await api.testNotifications(channel))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(null)
    }
  }

  const btn =
    'rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium ' +
    'hover:bg-slate-50 disabled:opacity-50'

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-1 text-sm font-semibold text-slate-700">Benachrichtigungen testen</div>
      <p className="mb-3 text-xs text-slate-500">
        Sendet eine Testnachricht über die konfigurierten Kanäle (E-Mail / Webhook).
      </p>

      <div className="flex flex-wrap gap-2">
        <button onClick={() => run()} disabled={busy} className={btn}>
          {busy === 'all' ? 'Sende…' : 'Alle testen'}
        </button>
        <button onClick={() => run('email')} disabled={busy} className={btn}>
          {busy === 'email' ? 'Sende…' : 'E-Mail testen'}
        </button>
        <button onClick={() => run('webhook')} disabled={busy} className={btn}>
          {busy === 'webhook' ? 'Sende…' : 'Webhook testen'}
        </button>
      </div>

      {error && <div className="mt-3 rounded bg-red-100 p-2 text-sm text-red-700">{error}</div>}

      {results && (
        <ul className="mt-3 space-y-2">
          {results.map((r) => (
            <li key={r.channel} className="flex items-start gap-2 text-sm">
              <span
                className={`mt-0.5 inline-block h-2.5 w-2.5 shrink-0 rounded-full ${
                  r.success ? 'bg-emerald-500' : r.enabled ? 'bg-red-500' : 'bg-slate-300'
                }`}
                title={r.success ? 'OK' : r.enabled ? 'Fehler' : 'Deaktiviert'}
              />
              <span>
                <span className="font-medium capitalize">{r.channel}</span>
                <span className="text-slate-500"> — {r.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
