import { useEffect, useState } from 'react'
import ChartTile from '../components/ChartTile'
import { RankRow } from '../components/Badges'
import { getStock, getIndicators, getRankings } from '../services/api'
import { UNIVERSE, HORIZONS } from '../utils/format'

export default function Dashboard() {
  const [tickers, setTickers] = useState(UNIVERSE.slice(0, 8))
  const [stockData, setStockData] = useState({})
  const [indData, setIndData] = useState({})
  const [rankings, setRankings] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [horizon, setHorizon] = useState(30)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const results = await Promise.allSettled([
          ...tickers.map((t) => getStock(t, '6mo')),
          ...tickers.map((t) => getIndicators(t, '6mo')),
          getRankings(horizon, 5),
        ])
        const stock = {}
        const ind = {}
        tickers.forEach((t, i) => {
          if (results[i].status === 'fulfilled') stock[t] = results[i].value
        })
        tickers.forEach((t, i) => {
          const r = results[tickers.length + i]
          if (r.status === 'fulfilled') ind[t] = r.value
        })
        const rankRes = results[tickers.length * 2]
        if (rankRes.status === 'fulfilled') setRankings(rankRes.value)
        if (!cancelled) {
          setStockData(stock)
          setIndData(ind)
        }
      } catch (e) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [tickers, horizon, refreshKey])

  const mergedData = (t) => {
    // Gabungkan recent stocks + recent indicators by date
    const s = stockData[t]?.recent || []
    const i = indData[t]?.recent || []
    const map = new Map()
    for (const row of s) map.set(row.date, { ...row })
    for (const row of i) map.set(row.date, { ...map.get(row.date), ...row })
    return [...map.values()].sort((a, b) => (a.date < b.date ? -1 : 1))
  }

  const lastPrice = (t) => {
    const s = stockData[t]
    if (!s?.last_price) return null
    return s.last_price
  }

  const lastInd = (t) => {
    const i = indData[t]
    if (!i?.indicators) return null
    return i.indicators
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-white/[7%] bg-zinc-950/80 backdrop-blur-2xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white rounded-xl flex items-center justify-center">
              <span className="text-zinc-900 font-bold text-sm">V</span>
            </div>
            <div>
              <h1 className="text-white font-semibold leading-tight">Vates Core</h1>
              <p className="text-[11px] text-zinc-500 leading-tight">Analitik Kuantitatif IHSG</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex rounded-xl border border-white/[8%] bg-zinc-900/60 p-0.5">
              {HORIZONS.map((h) => (
                <button
                  key={h.days}
                  onClick={() => setHorizon(h.days)}
                  className={`px-3 py-1.5 rounded-[10px] text-xs font-medium transition-colors ${
                    horizon === h.days ? 'bg-white text-zinc-900' : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  {h.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => setRefreshKey((k) => k + 1)}
              className="px-4 py-2 rounded-xl text-xs font-medium bg-zinc-800/60 border border-white/10 text-zinc-200 hover:bg-zinc-700/60 transition-colors"
            >
              ⟳ Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Ticker selector */}
        <div className="flex flex-wrap gap-2">
          {UNIVERSE.map((t) => {
            const active = tickers.includes(t)
            return (
              <button
                key={t}
                onClick={() =>
                  setTickers((prev) =>
                    active ? prev.filter((x) => x !== t) : prev.length < 8 ? [...prev, t] : prev
                  )
                }
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                  active
                    ? 'bg-white text-zinc-900 border-white'
                    : 'bg-zinc-900/60 text-zinc-400 border-white/[8%] hover:text-white'
                }`}
              >
                {t}
              </button>
            )
          })}
          {tickers.length >= 8 && (
            <span className="text-[11px] text-zinc-600 self-center">Maks 8 chart — hapus dulu untuk ganti</span>
          )}
        </div>

        {/* Grid 2x4 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tickers.map((t) => {
            const last = lastPrice(t)
            const ind = lastInd(t)
            const changePct = last && last.close != null && last.open != null
              ? ((last.close - last.open) / last.open) * 100
              : null
            return (
              <div key={t} className="space-y-1">
                <ChartTile data={mergedData(t)} title={t} />
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-3">
                    {last && (
                      <>
                        <span className="text-sm font-semibold text-white">{fmtRp(last.close)}</span>
                        <span className={`text-xs ${changePct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {changePct >= 0 ? '+' : ''}{changePct?.toFixed(2)}%
                        </span>
                      </>
                    )}
                  </div>
                  {ind && (
                    <div className="flex items-center gap-3 text-[11px] text-zinc-500">
                      {ind.rsi_14 != null && <span>RSI {ind.rsi_14.toFixed(0)}</span>}
                      {ind.macd_histogram != null && (
                        <span className={ind.macd_histogram > 0 ? 'text-emerald-400' : 'text-red-400'}>
                          MACD {ind.macd_histogram > 0 ? '+' : ''}{ind.macd_histogram.toFixed(2)}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Rankings */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
          <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[6%] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Top — {horizon}D</h2>
              <span className="text-[11px] text-zinc-500">probabilitas naik tertinggi</span>
            </div>
            <div className="divide-y divide-white/[4%]">
              {rankings.top?.map((item, i) => (
                <RankRow key={item.ticker} item={item} rank={i + 1} kind="top" />
              ))}
              {(!rankings.top || rankings.top.length === 0) && (
                <p className="px-4 py-6 text-center text-xs text-zinc-600">
                  Belum ada prediksi. Jalankan scheduler dulu.
                </p>
              )}
            </div>
          </div>

          <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[6%] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Bottom — {horizon}D</h2>
              <span className="text-[11px] text-zinc-500">probabilitas naik terendah</span>
            </div>
            <div className="divide-y divide-white/[4%]">
              {rankings.bottom?.map((item, i) => (
                <RankRow key={item.ticker} item={item} rank={i + 1} kind="bottom" />
              ))}
              {(!rankings.bottom || rankings.bottom.length === 0) && (
                <p className="px-4 py-6 text-center text-xs text-zinc-600">
                  Belum ada prediksi. Jalankan scheduler dulu.
                </p>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
