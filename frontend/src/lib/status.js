// Maps remaining days / backend status to colours and labels.
// Highlighting rule: < 30 days = red, < 60 days = yellow.

export function statusInfo(status, daysRemaining) {
  switch (status) {
    case 'expired':
      return { label: 'Abgelaufen', badge: 'bg-red-600 text-white', row: 'bg-red-50', dot: 'bg-red-600' }
    case 'critical':
      return { label: 'Kritisch (<30T)', badge: 'bg-red-100 text-red-700 border border-red-300', row: 'bg-red-50', dot: 'bg-red-500' }
    case 'warning':
      return { label: 'Warnung (<60T)', badge: 'bg-amber-100 text-amber-800 border border-amber-300', row: 'bg-amber-50', dot: 'bg-amber-400' }
    case 'ok':
      return { label: 'OK', badge: 'bg-emerald-100 text-emerald-700 border border-emerald-300', row: '', dot: 'bg-emerald-500' }
    default:
      return { label: 'Unbekannt', badge: 'bg-slate-100 text-slate-600 border border-slate-300', row: '', dot: 'bg-slate-400' }
  }
}

export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('de-DE', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('de-DE')
}
