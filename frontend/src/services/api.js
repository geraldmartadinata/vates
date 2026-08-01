// API client — Vates Core backend (FastAPI).
// Dev: Vite proxy → localhost:8000. Prod: same-origin (served by FastAPI).

const BASE = '/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const getStock = (ticker, period = '6mo') =>
  request(`/stocks/${encodeURIComponent(ticker)}?period=${period}`)

export const getIndicators = (ticker, period = '6mo') =>
  request(`/indicators/${encodeURIComponent(ticker)}?period=${period}`)

export const getRankings = (horizon = 30, topN = 5) =>
  request(`/rankings/${horizon}?top_n=${topN}`)

export const getPrediction = (ticker) =>
  request(`/predict/${encodeURIComponent(ticker)}`)

export const analyze = (ticker) =>
  request(`/analyze/${encodeURIComponent(ticker)}`, { method: 'POST' })

export const HEALTH = '/health'
