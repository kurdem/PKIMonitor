import { useEffect, useState } from 'react'
import { api } from '../api'
import NotificationTest from './NotificationTest'
import StatCard from './StatCard'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.dashboard().then(setStats).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="rounded-lg bg-red-100 p-4 text-red-700">Fehler: {error}</div>
  if (!stats) return <div className="text-slate-500">Lade Dashboard…</div>

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        <StatCard label="Gesamt" value={stats.total} accent="blue" />
        <StatCard label="Abgelaufen" value={stats.expired} accent="red" />
        <StatCard label="Kritisch (<30T)" value={stats.critical} accent="red" />
        <StatCard label="Warnung (<60T)" value={stats.warning} accent="amber" />
        <StatCard label="OK" value={stats.ok} accent="emerald" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <StatCard label="Monitore gesamt" value={stats.monitors_total} accent="slate" />
        <StatCard label="Fehlerhafte Checks" value={stats.monitors_failing} accent="red" />
        <StatCard label="Ohne Ablaufdatum" value={stats.unknown} accent="slate" />
      </div>
      <NotificationTest />
    </div>
  )
}
