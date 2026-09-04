import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Analyze from './pages/Analyze'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Served by FastAPI at /dashboard — support both root and /dashboard */}
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/dashboard/analyze" element={<Analyze />} />
      </Routes>
    </BrowserRouter>
  )
}
