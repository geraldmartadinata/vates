import { useState } from 'react'
import ChartTile from '../components/ChartTile'
import { RecBadge, ProbBadge } from '../components/Badges'
import { getStock, getIndicators, getPrediction, analyze } from '../services/api'
import { UNIVERSE, fmtRp } from '../utils/format'

export default function Analyze() {
  const [ticker, setTicker] = useState('BBCA')
  const [stock, setStock] = useState(null)
  const [ind, setInd] = useState(null)
  const [pred, setPred] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [requested, setRequested] = useState(false)

  const merged = () => {
    const s = stock?.recent || []
    const i = ind?.recent || []
    const map = new Map()
    for (const row of s) map.set(row.date, { ...row })
    for (const row of i) map.set(row.date, { ...map.get(row.date), ...row })
    return [...map.values()].sort((a, b) => (a.date < b.date ? -1 : 1))
  }

  async function runAnalysis() {
    if (!ticker.trim()) return
    setLoading(true)
    setError(null)
    setRequested(true)
    try {
      const [s, i, p] = await Promise.all([
        getStock(ticker, '6mo'),
        getIndicators(ticker, '6mo'),
        getPrediction(ticker),
      ])
      setStock(s)
      setInd(i)
      setPred(p)
      setAnalysis(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function requestAnalyze() {
    setLoading(true)
    setError(null)
    try {
      const a = await analyze(ticker)
      setAnalysis(a)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/[7%] bg-zinc-950/80 backdrop-blur-2xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white rounded-xl flex items-center justify-center">
              <span className="text-zinc-900 font-bold text-sm">V</span>
            </div>
            <div>
              <h1 className="text-white font-semibold leading-tight">Vates Core</h1>
              <p className="text-[11px] text-zinc-500 leading-tight">Analisis Saham</p>
            </div>
          </div>
          <a href="/" className="px-4 py-2 rounded-xl text-xs font-medium bg-zinc-800/60 border border-white/10 text-zinc-200 hover:bg-zinc-700/60">
            ← Dashboard
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Ticker input */}
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-[11px] text-zinc-500 mb-1.5">Kode Saham</label>
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && runAnalysis()}
              placeholder="BBCA"
              className="px-3.5 py-2 rounded-xl bg-zinc-900/60 border border-white/[8%] text-white text-sm w-40 focus:outline-none focus:border-white/25"
            />
          </div>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-5 py-2 rounded-xl text-sm font-medium bg-white text-zinc-900 hover:bg-zinc-200 disabled:opacity-50"
          >
            {loading ? 'Memuat…' : 'Analisis'}
          </button>
          <button
            onClick={requestAnalyze}
            disabled={loading || !stock}
            className="px-5 py-2 rounded-xl text-sm font-medium bg-zinc-800/60 border border-white/10 text-zinc-200 hover:bg-zinc-700/60 disabled:opacity-50"
          >
            ⟳ Request Ulang (Refit Model)
          </button>
          <div className="flex flex-wrap gap-1.5 ml-2">
            {UNIVERSE.slice(0, 8).map((t) => (
              <button
                key={t}
                onClick={() => setTicker(t)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-colors ${
                  ticker === t ? 'bg-white text-zinc-900 border-white' : 'bg-zinc-900/60 text-zinc-500 border-white/[8%] hover:text-white'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-sm text-red-400">
            {error}
          </div>
        )}

        {requested && !loading && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Chart */}
            <div className="lg:col-span-2">
              <ChartTile data={merged()} title={ticker} subtitle={stock?.ticker || ''} />
            </div>

            {/* Panel */}
            <div className="space-y-4">
              {/* Rekomendasi */}
              <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl p-4">
                <h3 className="text-xs text-zinc-500 mb-3">Rekomendasi</h3>
                <div className="flex items-center justify-between">
                  <RecBadge rec={analysis?.recommendation || pred?.recommendation || 'NEUTRAL'} />
                  <span className="text-xs text-zinc-500">{analysis ? 'model segar' : 'prediksi harian'}</span>
                </div>
                {analysis && (
                  <div className="mt-3 pt-3 border-t border-white/[6%] space-y-1.5 text-sm">
                    <div className="flex justify-between"><span className="text-zinc-500">Close</span><span className="text-white font-medium">{fmtRp(analysis.close)}</span></div>
                    <div className="flex justify-between"><span className="text-zinc-500">MACD Hist</span><span className={analysis.macd_hist > 0 ? 'text-emerald-400' : 'text-red-400'}>{analysis.macd_hist?.toFixed(2)}</span></div>
                  </div>
                )}
              </div>

              {/* Prediksi per horizon */}
              <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl p-4">
                <h3 className="text-xs text-zinc-500 mb-3">Probabilitas Naik</h3>
                <div className="space-y-2.5">
                  {(analysis?.preds || pred?.preds || []).map((p) => (
                    <div key={p.horizon_days} className="flex items-center justify-between">
                      <span className="text-sm text-zinc-300">{p.horizon_days} hari</span>
                      <ProbBadge prob={p.predicted_prob} />
                    </div>
                  ))}
                  {(!analysis?.preds?.length && !pred?.preds?.length) && (
                    <p className="text-xs text-zinc-600">Belum ada prediksi untuk saham ini.</p>
                  )}
                </div>
              </div>

              {/* Indikator */}
              {ind?.indicators && (
                <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl p-4">
                  <h3 className="text-xs text-zinc-500 mb-3">Indikator Terkini</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div><span className="text-zinc-500">SMA 20</span><p className="text-white font-medium">{fmtRp(ind.indicators.sma_20)}</p></div>
                    <div><span className="text-zinc-500">RSI 14</span><p className="text-white font-medium">{ind.indicators.rsi_14?.toFixed(1)}</p></div>
                    <div><span className="text-zinc-500">MACD</span><p className="text-white font-medium">{ind.indicators.macd?.toFixed(2)}</p></div>
                    <div><span className="text-zinc-500">BB Upper</span><p className="text-white font-medium">{fmtRp(ind.indicators.bb_upper)}</p></div>
                    <div><span className="text-zinc-500">BB Mid</span><p className="text-white font-medium">{fmtRp(ind.indicators.bb_middle)}</p></div>
                    <div><span className="text-zinc-500">BB Lower</span><p className="text-white font-medium">{fmtRp(ind.indicators.bb_lower)}</p></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
