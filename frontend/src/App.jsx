import { useState } from 'react'
import CalendarView from './components/CalendarView'
import CertificateTable from './components/CertificateTable'
import Dashboard from './components/Dashboard'
import MonitorList from './components/MonitorList'

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'certificates', label: 'Zertifikate' },
  { id: 'calendar', label: 'Kalender' },
  { id: 'monitors', label: 'URL-Monitoring' },
]

export default function App() {
  const [tab, setTab] = useState('dashboard')

  return (
    <div className="min-h-screen">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-4">
          <span className="text-xl font-bold">🔐 PKIMonitor</span>
          <span className="text-sm text-slate-400">Zertifikatsverwaltung &amp; TLS-Überwachung</span>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 px-4">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`rounded-t-md px-4 py-2 text-sm font-medium transition ${
                tab === t.id ? 'bg-slate-100 text-slate-900' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'certificates' && <CertificateTable />}
        {tab === 'calendar' && <CalendarView />}
        {tab === 'monitors' && <MonitorList />}
      </main>
    </div>
  )
}
