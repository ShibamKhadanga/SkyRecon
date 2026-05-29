import { useState } from 'react'
import { NavLink, useLocation, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Scan, FileText, Map, Settings,
  AlertTriangle, ChevronLeft, ChevronRight, Crosshair
} from 'lucide-react'

const navSections = [
  {
    title: 'Mapping & Survey',
    items: [
      { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { path: '/mapping', icon: Scan, label: 'Mapping Workspace' },
    ],
  },
  {
    title: 'Disaster Response',
    items: [
      { path: '/disaster', icon: AlertTriangle, label: 'Disaster Workspace' },
    ],
  },
  {
    title: 'Analytics & Tools',
    items: [
      { path: '/map', icon: Map, label: 'GIS Map View' },
      { path: '/reports', icon: FileText, label: 'All Reports' },
    ],
  },
]

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }) {
  const location = useLocation()

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className={`glass-sidebar fixed left-0 top-0 h-screen z-40 flex flex-col overflow-hidden
        transition-transform duration-300
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}
    >
      {/* Logo / Header Link to Landing Page */}
      <Link 
        to="/" 
        className="flex items-center gap-3 px-4 h-16 border-b border-white/5 flex-shrink-0 cursor-pointer hover:bg-white/[0.01] transition-colors"
      >
        <motion.div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, rgba(34,197,94,0.2), rgba(57,255,20,0.1))',
            border: '1px solid rgba(57,255,20,0.2)',
          }}
          whileHover={{ scale: 1.1, rotate: 5 }}
        >
          <Crosshair size={18} className="text-green-400" />
        </motion.div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <h1 
                className="text-base font-bold tracking-widest"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                <span className="text-gradient-green">SKY</span>
                <span className="text-white">RECON</span>
              </h1>
            </motion.div>
          )}
        </AnimatePresence>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-8 px-2 space-y-10">
        {navSections.map((section) => (
          <div key={section.title}>
            <AnimatePresence>
              {!collapsed && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--text-muted)] px-3 mb-3"
                >
                  {section.title}
                </motion.p>
              )}
            </AnimatePresence>

            <div className="space-y-2.5">
              {section.items.map((item) => {
                const isActive = location.pathname === item.path || 
                  (item.path !== '/dashboard' && location.pathname.startsWith(item.path))

                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className="block"
                  >
                    <motion.div
                      whileHover={{ x: 2 }}
                      className={`
                        relative flex items-center gap-3 px-3 py-3 rounded-xl
                        transition-all duration-200 group
                        ${isActive 
                          ? 'bg-green-500/10 text-green-400' 
                          : 'text-[var(--text-secondary)] hover:bg-white/[0.03] hover:text-[var(--text-primary)]'
                        }
                      `}
                    >
                      {/* Active indicator */}
                      {isActive && (
                        <motion.div
                          layoutId="sidebar-active"
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-green-400"
                          style={{ boxShadow: '0 0 8px rgba(57,255,20,0.5)' }}
                          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                        />
                      )}

                      <item.icon size={18} className="flex-shrink-0" />
                      
                      <AnimatePresence>
                        {!collapsed && (
                          <motion.span
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            className="text-sm font-medium whitespace-nowrap"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  </NavLink>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System / Admin Panel Option at Bottom */}
      <div className="px-2 pb-2 pt-4 border-t border-white/5 space-y-1.5 flex-shrink-0">
        <AnimatePresence>
          {!collapsed && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-[0.65rem] font-semibold uppercase tracking-widest text-[var(--text-muted)] px-3 mb-2"
            >
              System
            </motion.p>
          )}
        </AnimatePresence>
        <NavLink
          to="/admin"
          className="block"
        >
          <motion.div
            whileHover={{ x: 2 }}
            className={`
              relative flex items-center gap-3 px-3 py-3 rounded-xl
              transition-all duration-200 group
              ${location.pathname === '/admin' 
                ? 'bg-green-500/10 text-green-400' 
                : 'text-[var(--text-secondary)] hover:bg-white/[0.03] hover:text-[var(--text-primary)]'
              }
            `}
          >
            {location.pathname === '/admin' && (
              <motion.div
                layoutId="sidebar-active"
                className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-green-400"
                style={{ boxShadow: '0 0 8px rgba(57,255,20,0.5)' }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}
            <Settings size={18} className="flex-shrink-0" />
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="text-sm font-medium whitespace-nowrap"
                >
                  Admin Panel
                </motion.span>
              )}
            </AnimatePresence>
          </motion.div>
        </NavLink>
      </div>

      {/* Collapse button */}
      <div className="p-3 border-t border-white/5 flex-shrink-0">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-xl
                     text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/[0.03]
                     transition-colors"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-xs"
              >
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  )
}
