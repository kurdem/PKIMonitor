export default function StatCard({ label, value, accent = 'slate' }) {
  const accents = {
    slate: 'border-slate-300 text-slate-800',
    red: 'border-red-400 text-red-600',
    amber: 'border-amber-400 text-amber-600',
    emerald: 'border-emerald-400 text-emerald-600',
    blue: 'border-blue-400 text-blue-600',
  }
  return (
    <div className={`rounded-xl border-l-4 bg-white p-4 shadow-sm ${accents[accent] || accents.slate}`}>
      <div className="text-sm font-medium text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-bold">{value}</div>
    </div>
  )
}
