import { useEffect, useState } from 'react'
import { api } from '../api'
import { formatDateTime } from '../lib/status'

export default function MonitorList() {
  const [monitors, setMonitors] = useState([])
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(null)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    try {
      setMonitors(await api.listMonitors())
      setError(null)
    } catch (e) { setError(e.message) }
  }

  useEffect(() => { load() }, [])

  async function add(e) {
    e.preventDefault()
    if (!url) return
    setAdding(true)
    setError(null)
    try {
      // Backend checks the certificate immediately, so the expiry date is
      // discovered right away and appears in the calendar.
      await api.createMonitor({ url })
      setUrl('')
      load()
    } catch (e) { setError(e.message) } finally { setAdding(false) }
  }

  async function checkNow(id) {
    setBusy(id)
    try {
      await api.checkMonitor(id)
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(null) }
  }

  async function remove(id) {
    if (!confirm('Monitor löschen?')) return
    try { await api.deleteMonitor(id); load() } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={add} className="flex flex-wrap items-center gap-2">
        <input
          placeholder="https://host.example.com:443"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button disabled={adding}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {adding ? 'Prüfe Zertifikat…' : 'URL überwachen'}
        </button>
      </form>

      {error && <div className="rounded bg-red-100 p-3 text-sm text-red-700">{error}</div>}

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="border-b bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left font-semibold">URL</th>
              <th className="px-3 py-2 text-left font-semibold">Host:Port</th>
              <th className="px-3 py-2 text-left font-semibold">Letzter Check</th>
              <th className="px-3 py-2 text-left font-semibold">Ergebnis</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {monitors.map((m) => (
              <tr key={m.id} className="border-b last:border-0">
                <td className="px-3 py-2 font-medium">{m.url}</td>
                <td className="px-3 py-2 text-slate-600">{m.hostname}:{m.port}</td>
                <td className="px-3 py-2 text-slate-600">{formatDateTime(m.last_checked)}</td>
                <td className="px-3 py-2">
                  {m.last_success == null ? (
                    <span className="text-slate-400">—</span>
                  ) : m.last_success ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">OK</span>
                  ) : (
                    <span title={m.last_error} className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">Fehler</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => checkNow(m.id)} disabled={busy === m.id}
                    className="mr-3 text-xs text-blue-600 hover:underline disabled:opacity-50">
                    {busy === m.id ? 'Prüfe…' : 'Jetzt prüfen'}
                  </button>
                  <button onClick={() => remove(m.id)} className="text-xs text-red-600 hover:underline">Löschen</button>
                </td>
              </tr>
            ))}
            {monitors.length === 0 && (
              <tr><td colSpan={5} className="px-3 py-8 text-center text-slate-400">Noch keine URLs hinterlegt.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
