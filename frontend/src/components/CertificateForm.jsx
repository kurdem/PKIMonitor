import { useState } from 'react'
import { api } from '../api'

const EMPTY = {
  name: '', common_name: '', issuer: '', expiration_date: '',
  environment: 'unknown', location: '', contact: '', description: '',
}

export default function CertificateForm({ onClose, onSaved }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload = { ...form }
      // Convert <input type=date> value to ISO datetime, or drop if empty.
      if (payload.expiration_date) {
        payload.expiration_date = new Date(payload.expiration_date).toISOString()
      } else {
        delete payload.expiration_date
      }
      Object.keys(payload).forEach((k) => { if (payload[k] === '') delete payload[k] })
      await api.createCertificate(payload)
      onSaved()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const field = 'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/40 p-4">
      <form onSubmit={submit} className="w-full max-w-lg space-y-4 rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Zertifikat hinzufügen</h2>
        {error && <div className="rounded bg-red-100 p-2 text-sm text-red-700">{error}</div>}

        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2 text-sm font-medium">Name *
            <input required value={form.name} onChange={update('name')} className={field} />
          </label>
          <label className="text-sm font-medium">Common Name (CN)
            <input value={form.common_name} onChange={update('common_name')} className={field} />
          </label>
          <label className="text-sm font-medium">Aussteller
            <input value={form.issuer} onChange={update('issuer')} className={field} />
          </label>
          <label className="text-sm font-medium">Ablaufdatum
            <input type="date" value={form.expiration_date} onChange={update('expiration_date')} className={field} />
          </label>
          <label className="text-sm font-medium">Umgebung
            <select value={form.environment} onChange={update('environment')} className={field}>
              <option value="unknown">Unbekannt</option>
              <option value="prod">Prod</option>
              <option value="test">Test</option>
              <option value="dev">Dev</option>
            </select>
          </label>
          <label className="text-sm font-medium">Standort
            <input value={form.location} onChange={update('location')} className={field} />
          </label>
          <label className="text-sm font-medium">Ansprechpartner
            <input value={form.contact} onChange={update('contact')} className={field} />
          </label>
          <label className="col-span-2 text-sm font-medium">Beschreibung
            <textarea value={form.description} onChange={update('description')} className={field} rows={2} />
          </label>
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md px-4 py-2 text-sm text-slate-600 hover:bg-slate-100">Abbrechen</button>
          <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Speichern…' : 'Speichern'}
          </button>
        </div>
      </form>
    </div>
  )
}
