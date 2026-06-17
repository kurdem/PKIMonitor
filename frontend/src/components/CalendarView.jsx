import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { statusInfo } from '../lib/status'

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

export default function CalendarView() {
  const [certs, setCerts] = useState([])
  const [cursor, setCursor] = useState(() => {
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() }
  })

  useEffect(() => { api.listCertificates().then(setCerts).catch(() => {}) }, [])

  // Group certificates by YYYY-MM-DD of their expiration date.
  const byDay = useMemo(() => {
    const map = {}
    for (const c of certs) {
      if (!c.expiration_date) continue
      const d = new Date(c.expiration_date)
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      ;(map[key] ||= []).push(c)
    }
    return map
  }, [certs])

  const { year, month } = cursor
  // Build a Monday-first grid for the visible month.
  const firstDay = new Date(year, month, 1)
  const startOffset = (firstDay.getDay() + 6) % 7 // 0 = Monday
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const today = new Date()
  const move = (delta) => setCursor(({ year, month }) => {
    const m = month + delta
    return { year: year + Math.floor(m / 12), month: ((m % 12) + 12) % 12 }
  })

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <button onClick={() => move(-1)} className="rounded-md px-3 py-1 text-sm hover:bg-slate-100">‹ Zurück</button>
        <h2 className="text-lg font-semibold">{MONTHS[month]} {year}</h2>
        <button onClick={() => move(1)} className="rounded-md px-3 py-1 text-sm hover:bg-slate-100">Weiter ›</button>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-slate-500">
        {WEEKDAYS.map((d) => <div key={d} className="py-1">{d}</div>)}
      </div>

      <div className="mt-1 grid grid-cols-7 gap-1">
        {cells.map((day, idx) => {
          if (day === null) return <div key={`e${idx}`} className="min-h-[84px] rounded-md bg-slate-50" />
          const key = `${year}-${month}-${day}`
          const items = byDay[key] || []
          const isToday = today.getFullYear() === year && today.getMonth() === month && today.getDate() === day
          return (
            <div key={key} className={`min-h-[84px] rounded-md border p-1 text-left ${isToday ? 'border-blue-400 ring-1 ring-blue-300' : 'border-slate-200'}`}>
              <div className="text-xs font-medium text-slate-400">{day}</div>
              <div className="mt-0.5 space-y-0.5">
                {items.map((c) => {
                  const s = statusInfo(c.status, c.days_remaining)
                  return (
                    <div key={c.id} title={`${c.name} — läuft ab`} className={`truncate rounded px-1 py-0.5 text-[11px] ${s.badge}`}>
                      {c.name}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
        <Legend className="bg-red-600" label="Abgelaufen / Kritisch (<30T)" />
        <Legend className="bg-amber-400" label="Warnung (<60T)" />
        <Legend className="bg-emerald-500" label="OK (>60T)" />
      </div>
    </div>
  )
}

function Legend({ className, label }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`inline-block h-3 w-3 rounded ${className}`} />{label}
    </span>
  )
}
