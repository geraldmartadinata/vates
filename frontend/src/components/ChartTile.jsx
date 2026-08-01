import { useEffect, useRef } from 'react'

// Dynamic import — lightweight-charts ESM only
let chartLibPromise = null
function getChartLib() {
  if (!chartLibPromise) chartLibPromise = import('lightweight-charts')
  return chartLibPromise
}

export default function ChartTile({ data, title, subtitle }) {
  const containerRef = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    let chart = null
    let candleSeries = null
    let smaSeries = null
    let bbUpper = null
    let bbLower = null
    let resizeObserver = null
    let cancelled = false

    getChartLib()
      .then(({ createChart, ColorType, LineStyle }) => {
        if (cancelled || !containerRef.current) return

        chart = createChart(containerRef.current, {
          layout: {
            background: { type: ColorType.Solid, color: 'transparent' },
            textColor: '#71717a',
            fontSize: 10,
          },
          grid: {
            vertLines: { color: 'rgba(255,255,255,0.04)' },
            horzLines: { color: 'rgba(255,255,255,0.04)' },
          },
          rightPriceScale: { borderColor: 'rgba(255,255,255,0.08)' },
          timeScale: { borderColor: 'rgba(255,255,255,0.08)', timeVisible: false },
          crosshair: { mode: 0 },
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })

        candleSeries = chart.addCandlestickSeries({
          upColor: '#10b981', downColor: '#ef4444',
          borderUpColor: '#10b981', borderDownColor: '#ef4444',
          wickUpColor: '#10b981', wickDownColor: '#ef4444',
        })
        smaSeries = chart.addLineSeries({ color: '#3b82f6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
        bbUpper = chart.addLineSeries({ color: 'rgba(251,146,60,0.5)', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
        bbLower = chart.addLineSeries({ color: 'rgba(251,146,60,0.5)', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })

        const candles = []
        const sma = []
        const up = []
        const low = []
        for (const r of data) {
          const time = (r.date || '').slice(0, 10)
          if (!time) continue
          candles.push({ time, open: r.open, high: r.high, low: r.low, close: r.close })
          if (r.sma_20 != null) sma.push({ time, value: r.sma_20 })
          if (r.bb_upper != null) up.push({ time, value: r.bb_upper })
          if (r.bb_lower != null) low.push({ time, value: r.bb_lower })
        }
        candleSeries.setData(candles)
        if (sma.length) smaSeries.setData(sma)
        if (up.length) bbUpper.setData(up)
        if (low.length) bbLower.setData(low)
        chart.timeScale().fitContent()

        resizeObserver = new ResizeObserver(() => {
          if (chart && containerRef.current) {
            chart.applyOptions({
              width: containerRef.current.clientWidth,
              height: containerRef.current.clientHeight,
            })
          }
        })
        resizeObserver.observe(containerRef.current)
      })
      .catch((err) => console.error('Chart init failed:', err))

    return () => {
      cancelled = true
      if (resizeObserver) resizeObserver.disconnect()
      if (chart) chart.remove()
    }
  }, [data])

  return (
    <div className="flex flex-col bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">{title}</span>
          {subtitle && <span className="text-xs text-zinc-500">{subtitle}</span>}
        </div>
      </div>
      <div ref={containerRef} className="w-full h-[260px]" />
    </div>
  )
}
