export const UNIVERSE = [
  'BBCA', 'ASII', 'TLKM', 'BBRI', 'UNVR',
  'BBNI', 'BMRI', 'INDF', 'ICBP', 'GOTO',
  'ANTM', 'MDKA', 'KLBF', 'PTBA', 'ADRO',
]

export const HORIZONS = [
  { days: 1, label: '1D' },
  { days: 7, label: '7D' },
  { days: 30, label: '30D' },
]

export const fmtRp = (v) => {
  if (v == null || Number.isNaN(v)) return 'N/A'
  return 'Rp ' + Number(v).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

export const fmtPct = (v) => {
  if (v == null || Number.isNaN(v)) return 'N/A'
  return (v * 100).toFixed(1) + '%'
}

export const probColor = (p) => {
  if (p == null) return 'text-zinc-500'
  if (p >= 0.6) return 'text-emerald-400'
  if (p <= 0.4) return 'text-red-400'
  return 'text-amber-400'
}

export const recBadge = (rec) => {
  switch (rec) {
    case 'LONG': return { text: 'LONG', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' }
    case 'SHORT': return { text: 'SHORT', cls: 'bg-red-500/15 text-red-400 border-red-500/30' }
    default: return { text: 'NEUTRAL', cls: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/30' }
  }
}
