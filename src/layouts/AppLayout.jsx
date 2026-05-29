import { useState, useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, Search, User, Menu } from 'lucide-react'
import Sidebar from '../components/Sidebar'

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const location = useLocation()

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileSidebarOpen(false)
  }, [location.pathname])

  // Detect if mobile
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])

  const sidebarWidth = isMobile ? 0 : (sidebarCollapsed ? 72 : 260)

  // Breadcrumb from path
  const pathParts = location.pathname.split('/').filter(Boolean)
  const breadcrumbs = pathParts.map((part, i) => ({
    label: part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, ' '),
    path: '/' + pathParts.slice(0, i + 1).join('/'),
  }))

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Sidebar */}
      <Sidebar 
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Mobile overlay backdrop */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Main content area */}
      <motion.div
        animate={{ marginLeft: sidebarWidth }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="min-h-screen"
      >
        {/* Top Navbar */}
        <header className="glass-navbar sticky top-0 z-30 h-16 flex items-center justify-between px-4 md:px-6">
          {/* Left: Hamburger (mobile) + Breadcrumb */}
          <div className="flex items-center gap-3 text-sm">
            <button
              className="md:hidden p-2 rounded-xl hover:bg-white/[0.05] text-[var(--text-secondary)] transition-colors"
              onClick={() => setMobileSidebarOpen(true)}
            >
              <Menu size={20} />
            </button>
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path} className="flex items-center gap-2">
                {i > 0 && <span className="text-[var(--text-muted)]">/</span>}
                <span className={i === breadcrumbs.length - 1 
                  ? 'text-[var(--text-primary)] font-medium' 
                  : 'text-[var(--text-muted)]'
                }>
                  {crumb.label}
                </span>
              </span>
            ))}
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2 md:gap-3">
            {/* Search */}
            <div className="relative hidden md:block">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Search analyses..."
                className="glass-input pr-4 py-2 text-sm w-56"
                style={{ paddingLeft: '2.25rem' }}
              />
            </div>

            {/* Notifications */}
            <div className="relative">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setShowNotifications(!showNotifications)
                  setShowProfile(false)
                }}
                className="relative p-2.5 rounded-xl hover:bg-white/[0.03] text-[var(--text-secondary)] transition-colors z-50"
              >
                <Bell size={18} />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              </motion.button>

              {/* Click outside backdrop for notifications */}
              {showNotifications && (
                <div 
                  className="fixed inset-0 z-40 bg-transparent cursor-default" 
                  onClick={() => setShowNotifications(false)} 
                />
              )}

              <AnimatePresence>
                {showNotifications && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-80 bg-[#0b0f19] border border-green-500/30 shadow-2xl rounded-xl p-4 z-50 text-left backdrop-blur-xl"
                  >
                    <div className="flex items-center justify-between pb-2 border-b border-white/5 mb-2">
                      <span className="text-xs font-bold text-green-400 font-mono">SYSTEM ALERTS</span>
                      <span 
                        className="text-[10px] text-[var(--text-muted)] cursor-pointer hover:text-green-400 font-mono"
                        onClick={() => setShowNotifications(false)}
                      >
                        Clear all
                      </span>
                    </div>
                    <div className="space-y-3">
                      <div className="text-xs hover:bg-white/[0.02] p-1.5 rounded transition-colors cursor-pointer">
                        <p className="font-semibold text-white">Traffic Jam Detected</p>
                        <p className="text-[var(--text-secondary)] mt-0.5">Heavy congestion on highway NH-48 sector 4.</p>
                        <span className="text-[10px] text-green-400/70 font-mono mt-1 block">2 mins ago</span>
                      </div>
                      <div className="text-xs hover:bg-white/[0.02] p-1.5 rounded transition-colors cursor-pointer">
                        <p className="font-semibold text-white">Structural Damage Alert</p>
                        <p className="text-[var(--text-secondary)] mt-0.5">Building facade crack detected at Sector 12.</p>
                        <span className="text-[10px] text-orange-400/70 font-mono mt-1 block">15 mins ago</span>
                      </div>
                      <div className="text-xs hover:bg-white/[0.02] p-1.5 rounded transition-colors cursor-pointer">
                        <p className="font-semibold text-white">Analysis Complete</p>
                        <p className="text-[var(--text-secondary)] mt-0.5">Dataset "Forest Fire Scan 1" processing finished.</p>
                        <span className="text-[10px] text-[var(--text-muted)] font-mono mt-1 block">1 hour ago</span>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* User avatar */}
            <div className="relative">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setShowProfile(!showProfile)
                  setShowNotifications(false)
                }}
                className="w-9 h-9 rounded-xl flex items-center justify-center
                           bg-gradient-to-br from-green-500/20 to-cyan-500/10
                           border border-green-500/20 text-green-400 z-50"
              >
                <User size={16} />
              </motion.button>

              {/* Click outside backdrop for profile */}
              {showProfile && (
                <div 
                  className="fixed inset-0 z-40 bg-transparent cursor-default" 
                  onClick={() => setShowProfile(false)} 
                />
              )}

              <AnimatePresence>
                {showProfile && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute right-0 mt-2 w-56 bg-[#0b0f19] border border-green-500/30 shadow-2xl rounded-xl p-3 z-50 text-left backdrop-blur-xl"
                  >
                    <div className="pb-2 border-b border-white/5 mb-2 px-1">
                      <p className="text-xs font-bold text-white">Drone Intern</p>
                      <p className="text-[10px] text-[var(--text-muted)]">intern@nitr.edu</p>
                    </div>
                    <div className="space-y-1">
                      <button className="w-full text-left text-xs text-[var(--text-secondary)] hover:text-green-400 hover:bg-white/[0.02] py-2 px-1.5 rounded transition-colors font-mono">
                        PROFILE SETTINGS
                      </button>
                      <button className="w-full text-left text-xs text-[var(--text-secondary)] hover:text-green-400 hover:bg-white/[0.02] py-2 px-1.5 rounded transition-colors font-mono">
                        SYSTEM CONFIG
                      </button>
                      <button className="w-full text-left text-xs text-red-400 hover:text-red-300 hover:bg-white/[0.02] py-2 px-1.5 rounded transition-colors font-mono border-t border-white/5 mt-1.5">
                        DISCONNECT API
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 md:p-6">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Outlet />
          </motion.div>
        </main>
      </motion.div>
    </div>
  )
}
