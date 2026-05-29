import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Scan, FileText, AlertTriangle, Map, Eye, Upload,
  Activity, Layers, Cpu, BarChart3, RefreshCw, ArrowRight,
  TrendingUp, Zap
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts'
import StatCard from '../components/ui/StatCard'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

// ── Fallback data (shown only when backend is offline) ────────────────────────
const FALLBACK_STATS = { total_analyses: 0, total_detections: 0, total_reports: 0, active_alerts: 0 }

const FALLBACK_AREA = [
  { name: 'Mon', analyses: 0, detections: 0 },
  { name: 'Tue', analyses: 0, detections: 0 },
  { name: 'Wed', analyses: 0, detections: 0 },
  { name: 'Thu', analyses: 0, detections: 0 },
  { name: 'Fri', analyses: 0, detections: 0 },
  { name: 'Sat', analyses: 0, detections: 0 },
  { name: 'Sun', analyses: 0, detections: 0 },
]

const CATEGORY_COLORS = {
  Vehicles: '#f97316', People: '#06b6d4', Plants: '#22c55e',
  Trees: '#4ade80', Buildings: '#a855f7', Houses: '#c084fc',
  Roads: '#64748b', 'Road Potholes': '#dc2626', 'Water Bodies': '#0ea5e9',
  'Fire & Smoke': '#ef4444', 'Flood Water': '#3b82f6',
  'Electric Poles': '#eab308', 'Traffic Lights': '#a855f7',
  Animals: '#d97706', 'Solar Panels': '#fbbf24', default: '#94a3b8',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-panel p-3 border border-green-500/10">
      <p className="text-xs font-semibold mb-1 text-white">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-xs text-[var(--text-secondary)]">
          <span style={{ color: entry.color }}>●</span> {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(FALLBACK_STATS)
  const [analyses, setAnalyses] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [areaData, setAreaData] = useState(FALLBACK_AREA)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [apiOnline, setApiOnline] = useState(null) // null=checking, true, false

  const fetchAll = async () => {
    setLoading(true)
    try {
      // ── 1. Health check ──
      const health = await fetch('/api/health').catch(() => null)
      setApiOnline(health?.ok ?? false)

      // ── 2. Stats ──
      const statsRes = await fetch('/api/v1/dashboard/stats')
      if (statsRes.ok) {
        const data = await statsRes.json()
        setStats(data)
      }

      // ── 3. Recent analyses ──
      const analysesRes = await fetch('/api/v1/dashboard/recent-analyses')
      if (analysesRes.ok) {
        const data = await analysesRes.json()
        if (Array.isArray(data)) {
          setAnalyses(data.map(item => ({
            id: item.id,
            displayId: `AN-${String(item.id).padStart(3, '0')}`,
            name: item.project_name,
            status: item.status,
            objects: item.total_objects,
            mode: item.detection_mode,
            date: item.created_at
              ? new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
              : 'Just now',
          })))
        }
      }

      // ── 4. All analyses for chart + category breakdown ──
      const allRes = await fetch('/api/v1/analysis/?limit=50')
      if (allRes.ok) {
        const allData = await allRes.json()

        // Build 7-day area chart from real analysis created_at dates
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        const dayMap = {}
        days.forEach(d => { dayMap[d] = { name: d, analyses: 0, detections: 0 } })
        allData.forEach(a => {
          if (!a.created_at) return
          const day = days[new Date(a.created_at).getDay()]
          dayMap[day].analyses += 1
          dayMap[day].detections += a.total_objects || 0
        })
        // Rotate so today is last
        const todayIdx = new Date().getDay()
        const ordered = [...days.slice(todayIdx + 1), ...days.slice(0, todayIdx + 1)]
        setAreaData(ordered.map(d => dayMap[d]))
      }

      // ── 5. Category breakdown from detections ──
      const catRes = await fetch('/api/v1/categories/')
      if (catRes.ok) {
        const cats = await catRes.json()
        // Fetch detection counts per category via summary endpoint
        const detRes = await fetch('/api/v1/analysis/?limit=100')
        if (detRes.ok) {
          const allAnalyses = await detRes.json()
          // Aggregate category_breakdown from all completed analyses
          const catCounts = {}
          for (const a of allAnalyses) {
            if (a.status !== 'completed') continue
            try {
              const sumRes = await fetch(`/api/v1/analysis/${a.id}/summary`)
              if (!sumRes.ok) continue
              const sum = await sumRes.json()
              const breakdown = sum.category_breakdown || {}
              Object.entries(breakdown).forEach(([cat, count]) => {
                catCounts[cat] = (catCounts[cat] || 0) + count
              })
            } catch { /* skip */ }
          }
          if (Object.keys(catCounts).length > 0) {
            const sorted = Object.entries(catCounts)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([name, value]) => ({
                name,
                value,
                color: CATEGORY_COLORS[name] || CATEGORY_COLORS.default,
              }))
            setCategoryData(sorted)
          } else {
            // Fallback: show categories with 0 if no detections yet
            setCategoryData(
              cats.slice(0, 6).map(c => ({
                name: c.name,
                value: 0,
                color: c.color || CATEGORY_COLORS.default,
              }))
            )
          }
        }
      }

      setLastRefresh(new Date())
    } catch (e) {
      console.warn('Dashboard fetch error:', e)
      setApiOnline(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold mb-1">Command Center</h1>
          <div className="flex items-center gap-2">
            <p className="text-sm text-[var(--text-muted)]">AI Drone Intelligence Dashboard</p>
            {/* Live / Offline indicator */}
            <span className={`flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full border ${
              apiOnline === null ? 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5' :
              apiOnline ? 'text-green-400 border-green-500/20 bg-green-500/5' :
              'text-red-400 border-red-500/20 bg-red-500/5'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${
                apiOnline === null ? 'bg-yellow-400 animate-pulse' :
                apiOnline ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              }`} />
              {apiOnline === null ? 'CONNECTING' : apiOnline ? 'LIVE' : 'OFFLINE — SHOWING DB DATA'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Refresh button */}
          <button
            onClick={fetchAll}
            disabled={loading}
            title={`Last refreshed: ${lastRefresh.toLocaleTimeString()}`}
            className="p-2 rounded-xl border border-white/10 hover:border-green-500/30 text-[var(--text-muted)] hover:text-green-400 transition-all cursor-pointer disabled:opacity-40"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
          <NeonButton variant="secondary" icon={Map} onClick={() => navigate('/map')}>
            Open Map
          </NeonButton>
          <NeonButton variant="primary" icon={Upload} onClick={() => navigate('/mapping')}>
            Upload Video
          </NeonButton>
        </div>
      </div>

      {/* Stats Row — each card navigates somewhere */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div onClick={() => navigate('/mapping')} className="cursor-pointer">
          <StatCard icon={Scan} label="Total Analyses" value={stats.total_analyses} color="green" delay={0} />
        </div>
        <div onClick={() => navigate('/mapping')} className="cursor-pointer">
          <StatCard icon={Eye} label="Objects Detected" value={stats.total_detections} color="cyan" delay={0.05} />
        </div>
        <div onClick={() => navigate('/reports')} className="cursor-pointer">
          <StatCard icon={FileText} label="Reports Generated" value={stats.total_reports} color="purple" delay={0.1} />
        </div>
        <div onClick={() => navigate('/disaster')} className="cursor-pointer">
          <StatCard icon={AlertTriangle} label="Active Alerts" value={stats.active_alerts} color="orange" delay={0.15} />
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Area Chart */}
        <GlassCard className="lg:col-span-2" delay={0.2} hover={false}>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold">Analysis Trend</h3>
              <p className="text-xs text-[var(--text-muted)]">Detections & analyses by day of week</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-green-500/5 border border-green-500/10">
                <Activity size={12} className="text-green-400" />
                <span className="text-xs text-green-400 font-mono">
                  {loading ? 'LOADING...' : 'LIVE DATA'}
                </span>
              </div>
              <button
                onClick={() => navigate('/mapping')}
                className="text-[10px] font-mono text-[var(--text-muted)] hover:text-green-400 flex items-center gap-1 transition-colors cursor-pointer"
              >
                New Analysis <ArrowRight size={10} />
              </button>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={areaData}>
              <defs>
                <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="detections" name="Detections" stroke="#22c55e" fillOpacity={1} fill="url(#greenGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="analyses" name="Analyses" stroke="#06b6d4" fillOpacity={1} fill="url(#cyanGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        {/* Pie Chart */}
        <GlassCard delay={0.25} hover={false}>
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-semibold">Detection Categories</h3>
            <button
              onClick={() => navigate('/mapping')}
              className="text-[10px] font-mono text-[var(--text-muted)] hover:text-green-400 flex items-center gap-1 transition-colors cursor-pointer"
            >
              Analyse <ArrowRight size={10} />
            </button>
          </div>
          <p className="text-xs text-[var(--text-muted)] mb-3">
            {categoryData.length === 0 ? 'No detections yet — run an analysis' : 'Distribution from real detections'}
          </p>
          {categoryData.length === 0 ? (
            <div className="h-[180px] flex flex-col items-center justify-center gap-3">
              <BarChart3 size={32} className="text-[var(--text-muted)]" />
              <p className="text-xs text-[var(--text-muted)] text-center font-mono">
                Upload a video and run<br />an analysis to see data here
              </p>
              <button
                onClick={() => navigate('/mapping')}
                className="text-xs text-green-400 hover:text-green-300 font-mono flex items-center gap-1 cursor-pointer"
              >
                Start now <ArrowRight size={11} />
              </button>
            </div>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={75}
                    paddingAngle={3} dataKey="value" strokeWidth={0}
                  >
                    {categoryData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1.5 mt-2">
                {categoryData.map(cat => (
                  <div key={cat.name} className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                    <span className="truncate">{cat.name}</span>
                    <span className="text-[var(--text-muted)] ml-auto">{cat.value}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </GlassCard>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Analyses — each row is clickable */}
        <GlassCard delay={0.3} hover={false}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Recent Analyses</h3>
            <button
              onClick={() => navigate('/mapping')}
              className="text-xs text-green-400 hover:text-green-300 font-mono flex items-center gap-1 transition-colors cursor-pointer"
            >
              New Analysis <ArrowRight size={11} />
            </button>
          </div>

          {analyses.length === 0 ? (
            <div className="py-10 flex flex-col items-center gap-3 text-center">
              <Layers size={28} className="text-[var(--text-muted)]" />
              <p className="text-xs text-[var(--text-muted)] font-mono">No analyses yet</p>
              <button
                onClick={() => navigate('/mapping')}
                className="text-xs text-green-400 hover:text-green-300 font-mono flex items-center gap-1 cursor-pointer"
              >
                Upload your first video <ArrowRight size={11} />
              </button>
            </div>
          ) : (
            <div className="space-y-1">
              {analyses.map(analysis => (
                <motion.div
                  key={analysis.id}
                  whileHover={{ x: 4, backgroundColor: 'rgba(255,255,255,0.02)' }}
                  onClick={() => navigate('/mapping')}
                  className="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors group"
                >
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    analysis.status === 'processing'
                      ? 'bg-cyan-500/10 text-cyan-400'
                      : analysis.status === 'failed'
                      ? 'bg-red-500/10 text-red-400'
                      : 'bg-green-500/10 text-green-400'
                  }`}>
                    {analysis.status === 'processing'
                      ? <Cpu size={16} className="animate-spin" />
                      : <Layers size={16} />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate group-hover:text-white transition-colors">{analysis.name}</p>
                    <p className="text-xs text-[var(--text-muted)]">{analysis.displayId} · {analysis.mode}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className={`text-xs font-semibold ${
                      analysis.status === 'processing' ? 'text-cyan-400' :
                      analysis.status === 'failed' ? 'text-red-400' : 'text-green-400'
                    }`}>
                      {analysis.status === 'processing' ? 'Processing...' :
                       analysis.status === 'failed' ? 'Failed' :
                       `${analysis.objects} objects`}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">{analysis.date}</p>
                  </div>
                  <ArrowRight size={12} className="text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>

        {/* Quick Actions — replaces the static detection list */}
        <GlassCard delay={0.35} hover={false}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold">Quick Actions</h3>
            <span className="text-[10px] font-mono text-[var(--text-muted)]">NAVIGATE</span>
          </div>
          <div className="space-y-2">
            {[
              {
                icon: Upload, label: 'Upload & Analyse Video',
                desc: 'Start a new mapping or survey analysis',
                path: '/mapping', color: 'green',
                bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-400',
              },
              {
                icon: AlertTriangle, label: 'Disaster Assessment',
                desc: 'Scan footage for floods, fire, structural damage',
                path: '/disaster', color: 'red',
                bg: 'bg-red-500/10', border: 'border-red-500/20', text: 'text-red-400',
              },
              {
                icon: Map, label: 'Open GIS Map',
                desc: 'View detections on interactive Leaflet map',
                path: '/map', color: 'cyan',
                bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-400',
              },
              {
                icon: FileText, label: 'View All Reports',
                desc: 'Download PDF / DOCX analysis reports',
                path: '/reports', color: 'purple',
                bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400',
              },
              {
                icon: Zap, label: 'Admin Panel',
                desc: 'Manage categories, AI settings, users',
                path: '/admin', color: 'yellow',
                bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', text: 'text-yellow-400',
              },
            ].map(action => (
              <motion.button
                key={action.path}
                whileHover={{ x: 4 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate(action.path)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border ${action.border} ${action.bg} hover:brightness-125 transition-all cursor-pointer text-left group`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${action.bg} ${action.text}`}>
                  <action.icon size={15} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold ${action.text}`}>{action.label}</p>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5">{action.desc}</p>
                </div>
                <ArrowRight size={12} className="text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
              </motion.button>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* AI Status Bar — clicking checks health */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        onClick={fetchAll}
        title="Click to refresh"
        className="glass-panel p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:border-green-500/20 transition-colors"
      >
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <motion.div
              className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-green-400' : 'bg-red-400'}`}
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className={`text-xs font-mono ${apiOnline ? 'text-green-400' : 'text-red-400'}`}>
              {apiOnline ? 'AI ENGINE ONLINE' : 'AI ENGINE OFFLINE'}
            </span>
          </div>
          <span className="text-xs text-[var(--text-muted)] hidden sm:inline">|</span>
          <span className="text-xs text-[var(--text-muted)] font-mono hidden sm:inline">YOLOv8 Ready</span>
          <span className="text-xs text-[var(--text-muted)] hidden sm:inline">|</span>
          <span className="text-xs text-[var(--text-muted)] font-mono hidden sm:inline">OpenCV Active</span>
          <span className="text-xs text-[var(--text-muted)] hidden sm:inline">|</span>
          <span className="text-xs text-[var(--text-muted)] font-mono hidden sm:inline">PostgreSQL Connected</span>
        </div>
        <div className="flex items-center gap-2">
          <Cpu size={12} className="text-[var(--text-muted)]" />
          <span className="text-xs text-[var(--text-muted)] font-mono">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </span>
        </div>
      </motion.div>
    </div>
  )
}
