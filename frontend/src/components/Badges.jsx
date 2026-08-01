import { recBadge, fmtRp, fmtPct, probColor } from '../utils/format'

export function RecBadge({ rec }) {
  const b = recBadge(rec)
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${b.cls}`}>
      {b.text}
    </span>
  )
}

export function ProbBadge({ prob }) {
  if (prob == null) return <span className="text-xs text-zinc-600">—</span>
  return (
    <span className={`text-sm font-semibold ${probColor(prob)}`}>
      {fmtPct(prob)}
    </span>
  )
}

export function RankRow({ item, rank, kind }) {
  const isTop = kind === 'top'
  return (
    <div className="flex items-center justify-between px-4 py-2.5 hover:bg-white/[3%] transition-colors">
      <div className="flex items-center gap-3">
        <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold ${
          isTop ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'
        }`}>
          {rank}
        </span>
        <span className="text-sm font-medium text-white">{item.ticker}</span>
        <span className="text-xs text-zinc-500">{item.horizon_days}D</span>
      </div>
      <ProbBadge prob={item.predicted_prob} />
    </div>
  )
}
