import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import LandingPage from './pages/LandingPage'
import AppLayout from './layouts/AppLayout'
import DashboardPage from './pages/DashboardPage'
import MappingPage from './pages/MappingPage'
import DisasterPage from './pages/DisasterPage'
import ReportsPage from './pages/ReportsPage'
import MapPage from './pages/MapPage'
import AdminPage from './pages/AdminPage'

export default function App() {
  return (
    <AnimatePresence mode="wait">
      <Routes>
        {/* Landing / Module Selection */}
        <Route path="/" element={<LandingPage />} />
        
        {/* App routes with sidebar layout */}
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/mapping" element={<MappingPage />} />
          <Route path="/disaster" element={<DisasterPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </AnimatePresence>
  )
}
