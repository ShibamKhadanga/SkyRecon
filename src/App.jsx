import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { lazy, Suspense } from 'react'
import AppLayout from './layouts/AppLayout'

const LandingPage = lazy(() => import('./pages/LandingPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const MappingPage = lazy(() => import('./pages/MappingPage'))
const DisasterPage = lazy(() => import('./pages/DisasterPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const MapPage = lazy(() => import('./pages/MapPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const LiveFeedPage = lazy(() => import('./pages/LiveFeedPage'))
const FindPage = lazy(() => import('./pages/FindPage'))
const RecordingsPage = lazy(() => import('./pages/RecordingsPage'))

export default function App() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
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
          <Route path="/live" element={<LiveFeedPage />} />
          <Route path="/find" element={<FindPage />} />
          <Route path="/recordings" element={<RecordingsPage />} />
        </Route>
      </Routes>
    </AnimatePresence>
    </Suspense>
  )
}
