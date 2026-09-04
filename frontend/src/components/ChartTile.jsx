import { useEffect, useRef, useState } from 'react'

// Dynamic import — lightweight-charts ESM only
let chartLibPromise = null
function getChartLib() {
  if (!chartLibPromise) chartLibPromise = import('lightweight-charts')
  return chartLibPromise
}

export default function ChartTile({ data, title, subtitle }) {
  const containerRef = useRef(null)
  const [chartError, setChartError] = useState(null)

  useEffect(() => {
    if (!data || data.length === 0) return
    let cancelled = false

    getChartLib()
      .then(({ createChart, ColorType, LineStyle, CandlestickSeries, LineSeries }) => {
        if (cancelled || !containerRef.current) return

        try {
          const chart = createChart(containerRef.current, {
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
            width: containerRef.current.clientWidth || 400,
            height: containerRef.current.clientHeight || 260,
          })

          const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#10b981', downColor: '#ef4444',
            borderUpColor: '#10b981', borderDownColor: '#ef4444',
            wickUpColor: '#10b981', wickDownColor: '#ef4444',
          })
          const smaSeries = chart.addSeries(LineSeries, {
            color: '#3b82f6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false,
          })
          const bbUpper = chart.addSeries(LineSeries, {
            color: 'rgba(251,146,60,0.5)', lineWidth: 1,
            lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false,
          })
          const bbLower = chart.addSeries(LineSeries, {
            color: 'rgba(251,146,60,0.5)', lineWidth: 1,
            lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false,
          })

          const candles = [], sma = [], up = [], low = []
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

          const observer = new ResizeObserver(() => {
            if (chart && containerRef.current) {
              chart.applyOptions({
                width: containerRef.current.clientWidth,
                height: containerRef.current.clientHeight,
              })
            }
          })
          if (containerRef.current) observer.observe(containerRef.current)

          // Cleanup stored refs for next effect run
          chart._cleanup = () => {
            observer.disconnect()
            chart.remove()
          }
        } catch (err) {
          console.error('Chart init failed:', err)
          if (!cancelled) setChartError(err.message)
        }
      })
      .catch((err) => {
        console.error('lightweight-charts load failed:', err)
        if (!cancelled) setChartError('Chart library failed to load')
      })

    return () => {
      cancelled = true
      // Cleanup chart on unmount or data change
      if (containerRef.current && containerRef.current._chart) {
        try { containerRef.current._chart.remove() } catch {}
      }
    }
  }, [data])

  if (chartError) {
    return (
      <div className="flex flex-col bg-zinc-900/60 backdrop-blur-xl border border-white/[7%] rounded-2xl overflow-hidden h-[260px] items-center justify-center">
        <div className="text-xs text-red-400 px-4 text-center">{chartError}</div>
      </div>
    )
  }

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
