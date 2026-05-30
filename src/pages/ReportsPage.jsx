import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  FileText, Download, Eye, Calendar, BarChart3,
  Filter, Search, FileIcon, Trash2, X, RefreshCw
} from 'lucide-react'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'
import SeverityBadge from '../components/ui/SeverityBadge'

export default function ReportsPage() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedReport, setSelectedReport] = useState(null)
  const [activeFilter, setActiveFilter] = useState('all')
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [downloading, setDownloading] = useState(null)

  const fetchReports = async () => {
    setLoading(true)
    try {
      // Fetch reports list from backend (includes all completed analyses)
      const reportsRes = await fetch('/api/v1/analysis/reports/')
      if (reportsRes.ok) {
        const data = await reportsRes.json()
        setReports(data)
      } else {
        // Fallback: fetch completed analyses directly
        const res = await fetch('/api/v1/analysis/?limit=50')
        const analyses = await res.json()
        const built = analyses
          .filter(a => a.status === 'completed')
          .map(a => ({
            id: null,
            analysis_id: a.id,
            title: a.project_name || `Analysis #${a.id}`,
            report_type: 'mapping',
            format: 'pdf',
            status: 'ready',
            total_objects: a.total_objects || 0,
            created_at: a.completed_at || a.created_at,
            processing_time: a.processing_time,
          }))
        setReports(built)
      }
    } catch (e) {
      console.error('Failed to fetch reports:', e)
      setReports([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReports() }, [])

  const handleDownload = async (report, fmt) => {
    const aid = report.analysis_id || report.id
    if (!aid) return
    setDownloading(`${aid}-${fmt}`)
    try {
      // Request report generation
      const res = await fetch(
        `/api/v1/analysis/${aid}/report?report_type=${report.report_type || 'mapping'}&fmt=${fmt}`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error('Failed to start report generation')
      const data = await res.json()
      const rid = data.report_id

      // Poll until ready
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        if (attempts > 30) { clearInterval(poll); setDownloading(null); return }
        try {
          const sr = await fetch(`/api/v1/analysis/report/${rid}/status`)
          const sd = await sr.json()
          if (sd.status === 'ready') {
            clearInterval(poll)
            setDownloading(null)
            window.open(`/api/v1/analysis/report/${rid}/download`, '_blank')
          } else if (sd.status === 'failed') {
            clearInterval(poll)
            setDownloading(null)
            alert('Report generation failed.')
          }
        } catch (_) {}
      }, 2000)
    } catch (e) {
      setDownloading(null)
      alert(`Download failed: ${e.message}`)
    }
  }

  const handleDelete = async (report) => {
    const aid = report.analysis_id || report.id
    if (!aid) return
    if (!confirm(`Delete analysis #${aid} and all its data?`)) return
    try {
      await fetch(`/api/v1/analysis/${aid}`, { method: 'DELETE' })
      setReports(prev => prev.filter(r => (r.analysis_id || r.id) !== aid))
    } catch (e) {
      alert(`Delete failed: ${e.message}`)
    }
  }

  const filtered = reports.filter(r => {
    const title = r.title || r.project_name || ''
    const matchSearch = title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchFilter =
      activeFilter === 'all' ||
      r.report_type === activeFilter ||
      r.status === activeFilter
    return matchSearch && matchFilter
  })

  const formatDate = (dt) => {
    if (!dt) return '—'
    return new Date(dt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Reports</h1>
          <p className="text-sm text-[var(--text-muted)]">All completed analysis reports</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchReports}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-xs text-[var(--text-secondary)] hover:text-white hover:border-white/20 transition-all cursor-pointer"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none z-10" />
            <input
              type="text"
              placeholder="Search reports..."
              className="glass-input text-sm w-48"
              style={{ paddingLeft: '2.25rem', paddingRight: '1rem', paddingTop: '0.5rem', paddingBottom: '0.5rem' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(prev => !prev)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-medium transition-all cursor-pointer ${
                activeFilter !== 'all'
                  ? 'bg-green-500/10 text-green-400 border-green-500/30'
                  : 'bg-white/[0.03] text-[var(--text-secondary)] border-white/10 hover:border-white/20 hover:text-white'
              }`}
            >
              <Filter size={13} />
              {activeFilter === 'all' ? 'Filter' : activeFilter.charAt(0).toUpperCase() + activeFilter.slice(1)}
            </button>
            <AnimatePresence>
              {showFilterMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowFilterMenu(false)} />
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 6 }}
                    className="absolute right-0 mt-2 w-44 bg-[#0b0f19] border border-green-500/20 rounded-xl shadow-2xl z-50 overflow-hidden"
                  >
                    {[
                      { value: 'all',      label: 'All Reports' },
                      { value: 'mapping',  label: 'Mapping Only' },
                      { value: 'disaster', label: 'Disaster Only' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => { setActiveFilter(opt.value); setShowFilterMenu(false) }}
                        className={`w-full text-left px-4 py-2.5 text-xs transition-colors cursor-pointer ${
                          activeFilter === opt.value
                            ? 'bg-green-500/10 text-green-400 font-semibold'
                            : 'text-[var(--text-secondary)] hover:bg-white/[0.04] hover:text-white'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Reports', value: reports.length, icon: FileText, color: '#22c55e' },
          { label: 'Mapping', value: reports.filter(r => r.report_type !== 'disaster').length, icon: BarChart3, color: '#06b6d4' },
          { label: 'Disaster', value: reports.filter(r => r.report_type === 'disaster').length, icon: FileIcon, color: '#ef4444' },
          { label: 'Total Objects', value: reports.reduce((s, r) => s + (r.total_objects || 0), 0), icon: Calendar, color: '#a855f7' },
        ].map((stat, i) => (
          <GlassCard key={stat.label} className="p-4" delay={i * 0.05} hover={false}>
            <div className="flex items-center gap-2 mb-2">
              <stat.icon size={14} style={{ color: stat.color }} />
              <span className="text-xs text-[var(--text-muted)]">{stat.label}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: stat.color }}>{stat.value}</p>
          </GlassCard>
        ))}
      </div>

      {/* Reports List */}
      <GlassCard hover={false}>
        {loading ? (
          <div className="text-center py-12 text-[var(--text-muted)] font-mono text-sm">
            Loading reports...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-[var(--text-muted)] font-mono text-sm">
            {reports.length === 0
              ? 'No completed analyses yet. Upload a video and run an analysis first.'
              : 'No reports match your search.'}
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((report, i) => {
              const aid = report.analysis_id || report.id
              const isDownloading = downloading?.startsWith(`${aid}-`)
              return (
                <motion.div
                  key={aid}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-center gap-4 p-4 rounded-xl hover:bg-white/[0.02] transition-all border border-transparent hover:border-white/5"
                >
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    report.report_type === 'disaster' ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
                  }`}>
                    <FileText size={18} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate">{report.title || report.project_name || `Analysis #${aid}`}</p>
                    <div className="flex items-center gap-3 text-xs text-[var(--text-muted)] mt-0.5">
                      <span className="font-mono">#{aid}</span>
                      <span>{formatDate(report.created_at)}</span>
                      <span>{report.total_objects || 0} objects</span>
                      {report.processing_time && <span>{report.processing_time.toFixed(1)}s</span>}
                    </div>
                  </div>

                  <span className={`px-2.5 py-1 rounded-lg text-xs font-medium ${
                    report.report_type === 'disaster' ? 'bg-red-500/10 text-red-400' : 'bg-green-500/10 text-green-400'
                  }`}>
                    {report.report_type === 'disaster' ? 'Disaster' : 'Mapping'}
                  </span>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleDownload(report, 'pdf')}
                      disabled={isDownloading}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/5 hover:border-green-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white transition-colors cursor-pointer disabled:opacity-40"
                    >
                      {isDownloading && downloading === `${aid}-pdf`
                        ? <><RefreshCw size={12} className="animate-spin" /> Generating...</>
                        : <><Download size={12} /> PDF</>}
                    </button>
                    <button
                      onClick={() => handleDownload(report, 'docx')}
                      disabled={isDownloading}
                      className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-white/5 hover:border-blue-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white transition-colors cursor-pointer disabled:opacity-40"
                    >
                      {isDownloading && downloading === `${aid}-docx`
                        ? <><RefreshCw size={12} className="animate-spin" /> Generating...</>
                        : <><Download size={12} /> DOCX</>}
                    </button>
                    <button
                      onClick={() => handleDelete(report)}
                      className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400/50 hover:text-red-400 transition-colors cursor-pointer"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
