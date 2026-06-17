import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { formatDate, statusInfo } from '../lib/status'
import CertificateForm from './CertificateForm'

const STATUS_OPTIONS = [
  { value: '', label: 'Alle Status' },
  { value: 'expired', label: 'Abgelaufen' },
  { value: 'critical', label: 'Kritisch (<30T)' },
  { value: 'warning', label: 'Warnung (<60T)' },
  { value: 'ok', label: 'OK' },
]

export default function CertificateTable() {
  const [certs, setCerts] = useState([])
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ environment: '', status: '', search: '' })
  const [sort, setSort] = useState({ key: 'expiration_date', dir: 'asc' })
  const [showForm, setShowForm] = useState(false)

  async function load() {
    try {
      setCerts(await api.listCertificates(filters))
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { load() }, [filters]) // eslint-disable-line react-hooks/exhaustive-deps

  const sorted = useMemo(() => {
    const copy = [...certs]
    copy.sort((a, b) => {
      const av = a[sort.key] ?? ''
      const bv = b[sort.key] ?? ''
      if (av < bv) return sort.dir === 'asc' ? -1 : 1
      if (av > bv) return sort.dir === 'asc' ? 1 : -1
      return 0
    })
    return copy
  }, [certs, sort])

  function toggleSort(key) {
    setSort((s) => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }))
  }

  async function remove(id) {
    if (!confirm('Zertifikat wirklich löschen?')) return
    try {
      await api.deleteCertificate(id)
      load()
    } catch (e) {
      alert(e.message)
    }
  }

  const header = (key, label) => (
    <th onClick={() => toggleSort(key)} className="cursor-pointer select-none px-3 py-2 text-left font-semibold hover:text-blue-600">
      {label}{sort.key === key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
    </th>
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input
          placeholder="Suche (Name / CN)…"
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <select value={filters.environment} onChange={(e) => setFilters({ ...filters, environment: e.target.value })}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm">
          <option value="">Alle Umgebungen</option>
          <option value="prod">Prod</option>
          <option value="test">Test</option>
          <option value="dev">Dev</option>
          <option value="unknown">Unbekannt</option>
        </select>
        <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          className="rounded-md border border-slate-300 px-3 py-2 text-sm">
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <button onClick={() => setShowForm(true)}
          className="ml-auto rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Zertifikat
        </button>
      </div>

      {error && <div className="rounded bg-red-100 p-3 text-sm text-red-700">{error}</div>}

      <div className="overflow-x-auto rounded-xl bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="border-b bg-slate-50 text-slate-600">
            <tr>
              {header('name', 'Name')}
              {header('common_name', 'CN')}
              {header('issuer', 'Aussteller')}
              {header('environment', 'Umgebung')}
              {header('expiration_date', 'Ablauf')}
              {header('days_remaining', 'Tage')}
              <th className="px-3 py-2 text-left font-semibold">Status</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c) => {
              const s = statusInfo(c.status, c.days_remaining)
              return (
                <tr key={c.id} className={`border-b last:border-0 ${s.row}`}>
                  <td className="px-3 py-2 font-medium">{c.name}</td>
                  <td className="px-3 py-2 text-slate-600">{c.common_name || '—'}</td>
                  <td className="px-3 py-2 text-slate-600">{c.issuer || '—'}</td>
                  <td className="px-3 py-2 uppercase text-slate-500">{c.environment}</td>
                  <td className="px-3 py-2">{formatDate(c.expiration_date)}</td>
                  <td className="px-3 py-2">{c.days_remaining ?? '—'}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${s.badge}`}>{s.label}</span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => remove(c.id)} className="text-xs text-red-600 hover:underline">Löschen</button>
                  </td>
                </tr>
              )
            })}
            {sorted.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-400">Keine Zertifikate gefunden.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && <CertificateForm onClose={() => setShowForm(false)} onSaved={load} />}
    </div>
  )
}
