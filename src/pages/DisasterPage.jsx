import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertTriangle, Upload, ArrowRight, Play, Cpu, 
  FileDown, ShieldAlert, Clock, Image, Flame, CheckCircle,
  Volume2, VolumeX, Radio, Wifi, WifiOff, Shield, HeartHandshake, HelpCircle,
  BarChart2
} from 'lucide-react'
import FileDropzone from '../components/ui/FileDropzone'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'

// Severity level style helper
const getSeverityStyle = (level) => {
  const styles = {
    1: { label: 'Level 1: Low Risk (Minor)', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
    2: { label: 'Level 2: Light Damage', color: 'text-lime-400', bg: 'bg-lime-500/10 border-lime-500/20' },
    3: { label: 'Level 3: Moderate Threat', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' },
    4: { label: 'Level 4: High Severity', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/20' },
    5: { label: 'Level 5: Critical (Life Threat)', color: 'text-red-500', bg: 'bg-red-500/10 border-red-500/20' }
  }
  return styles[level] || styles[3]
}

// Mock detected disaster items from complete Master Prompt
const mockDetections = [
  { 
    id: 'DST-001',
    time: '00:14',
    type: 'Fallen Tree & Power Line Blockage',
    level: 3, 
    description: 'Banyan tree fell across roadway Sector 4, snapping overhead electricity cables. Obstruction restricts light vehicles.',
    colorDeg: 'from-yellow-600/30 to-yellow-950/20',
    typeClass: 'blockage'
  },
  { 
    id: 'DST-002',
    time: '00:42',
    type: 'Flooded Residential Area',
    level: 5, 
    description: 'Severe water logging (~4.5ft depth) trapping residents in ground floors. High priority evacuation and rescue active.',
    colorDeg: 'from-red-600/30 to-red-950/20',
    typeClass: 'flood'
  },
  { 
    id: 'DST-003',
    time: '01:05',
    type: 'Fallen Utility Electric Pole',
    level: 2, 
    description: 'Electric wooden utility pole listing at 45 degrees over secondary alleyway. Normal emergency queue, no immediate threat.',
    colorDeg: 'from-lime-600/30 to-lime-950/20',
    typeClass: 'infrastructure'
  },
  { 
    id: 'DST-004',
    time: '01:38',
    type: 'Partially Broken Roof / Structure',
    level: 4, 
    description: 'Industrial warehouse tin roof collapse. Massive debris blockage. Potential structural threat to surrounding workers.',
    colorDeg: 'from-orange-600/30 to-orange-950/20',
    typeClass: 'structure'
  }
]

export default function DisasterPage() {
  const [file, setFile] = useState(null)
  const [videoUrl, setVideoUrl] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [showReport, setShowReport] = useState(false)
  const [analysisId, setAnalysisId] = useState(null)
  const [realEvents, setRealEvents] = useState([])
  const [apiError, setApiError] = useState(null)
  const pollRef = useRef(null)

  const [offlineMode, setOfflineMode] = useState(false)
  const [voiceAlertsEnabled, setVoiceAlertsEnabled] = useState(true)

  const triggerVoiceSpeech = (events) => {
    if (!window.speechSynthesis || !voiceAlertsEnabled) return
    // Only speak for genuinely critical fire or flood events at severity >= 4
    const critical = events.filter(e => (e.disaster_type === 'fire' || e.disaster_type === 'flood') && e.severity >= 4)
    if (critical.length === 0) return
    let text = 'Attention. SkyRecon disaster assessment complete. '
    const fires = critical.filter(e => e.disaster_type === 'fire')
    const floods = critical.filter(e => e.disaster_type === 'flood')
    if (fires.length > 0) text += 'Critical fire detected. Deploy fire suppression units immediately. '
    if (floods.length > 0) text += 'Critical flood zone detected. Emergency evacuation required immediately. '
    const u = new SpeechSynthesisUtterance(text)
    u.rate = 0.92
    window.speechSynthesis.speak(u)
  }

  useEffect(() => {
    if (!file) { setVideoUrl(null); return }
    const url = URL.createObjectURL(file)
    setVideoUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleStartScan = async () => {
    if (!file) return
    setScanning(true)
    setShowReport(false)
    setRealEvents([])
    setApiError(null)
    setScanProgress(5)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('project_name', `Disaster Scan – ${file.name}`)
      formData.append('analysis_type', 'disaster')
      formData.append('detection_mode', 'standard')

      const res = await fetch('/api/v1/analysis/upload', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
      const data = await res.json()
      setAnalysisId(data.id)
      setScanProgress(15)

      // Poll for completion
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(async () => {
        try {
          const sr = await fetch(`/api/v1/analysis/${data.id}/status`)
          const sd = await sr.json()
          // Use real progress from backend
          if (typeof sd.progress === 'number' && sd.progress > 0) {
            setScanProgress(sd.progress)
          } else if (sd.status === 'processing') {
            setScanProgress(prev => Math.min(prev + 2, 90))
          }
          if (sd.status === 'completed') {
            clearInterval(pollRef.current)
            setScanProgress(100)
            const er = await fetch(`/api/v1/analysis/${data.id}/disasters`)
            const events = await er.json()
            setRealEvents(events)
            setScanning(false)
            setShowReport(true)
            setTimeout(() => triggerVoiceSpeech(events), 300)
          } else if (sd.status === 'failed') {
            clearInterval(pollRef.current)
            setApiError('Disaster analysis failed on server.')
            setScanning(false)
          }
        } catch (e) {
          console.warn('Poll error:', e)
        }
      }, 3000)
    } catch (e) {
      setApiError(e.message)
      setScanning(false)
    }
  }

  // Resource totals from real events
  const resources = realEvents.reduce((acc, e) => {
    const r = e.resource_estimation || {}
    acc.rescueTeams += r.rescue_teams || 0
    acc.ambulances += r.ambulances || 0
    acc.rescueBoats += r.rescue_boats || 0
    acc.emergencyVehicles += r.emergency_vehicles || 0
    acc.supportStaff += r.support_staff || 0
    return acc
  }, { rescueTeams: 0, ambulances: 0, rescueBoats: 0, emergencyVehicles: 0, supportStaff: 0 })

  const handleExport = async (format) => {
    if (!analysisId) return
    try {
      const res = await fetch(
        `/api/v1/analysis/${analysisId}/report?report_type=disaster&fmt=${format}`,
        { method: 'POST' }
      )
      const data = await res.json()
      const rid = data.report_id
      const poll = setInterval(async () => {
        const sr = await fetch(`/api/v1/analysis/report/${rid}/status`)
        const sd = await sr.json()
        if (sd.status === 'ready') {
          clearInterval(poll)
          window.open(`/api/v1/analysis/report/${rid}/download`, '_blank')
        }
      }, 2000)
    } catch (e) {
      alert(`Report generation failed: ${e.message}`)
    }
  }

  return (
    <div className="w-full max-w-none space-y-6 px-1">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 flex-shrink-0 mt-1">
            <AlertTriangle size={20} className="text-red-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-1">Disaster Assessment & Rescue Workspace</h1>
            <p className="text-sm text-[var(--text-muted)]">
              Full-viewport emergency command dashboard to isolate floods, structural failures, blockages, and deploy rescue assets
            </p>
          </div>
        </div>

        {/* Global Disaster Flags (Offline & Voice alerts) */}
        <div className="flex items-center gap-3">
          {/* Section 29 Offline mode */}
          <button
            type="button"
            onClick={() => setOfflineMode(!offlineMode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold font-mono transition-all cursor-pointer ${
              offlineMode 
                ? 'bg-orange-500/10 text-orange-400 border-orange-500/30' 
                : 'bg-white/5 text-[var(--text-secondary)] border-white/5 hover:border-white/10'
            }`}
            title="Toggle offline processing model for isolated search & rescue"
          >
            {offlineMode ? <WifiOff size={14} /> : <Wifi size={14} />}
            {offlineMode ? '📡 OFFLINE OPERATIONS' : '📡 ONLINE COMMAND'}
          </button>

          {/* Section 30 Voice alerts */}
          <button
            type="button"
            onClick={() => setVoiceAlertsEnabled(!voiceAlertsEnabled)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold font-mono transition-all cursor-pointer ${
              voiceAlertsEnabled 
                ? 'bg-red-500/10 text-red-400 border-red-500/30' 
                : 'bg-white/5 text-[var(--text-secondary)] border-white/5 hover:border-white/10'
            }`}
          >
            {voiceAlertsEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
            {voiceAlertsEnabled ? '🔊 VOICE ALARM ACTIVE' : '🔇 VOICE ALARM MUTED'}
          </button>
        </div>
      </div>

      {/* Main Grid: De-congested 3-Column Wide Viewport Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Dropzone - Spans 8 cols */}
        <div className="xl:col-span-8 space-y-4">
          <FileDropzone onFileSelect={setFile} />

          {file && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <GlassCard hover={false}>
                <div className="rounded-xl overflow-hidden bg-black/40 aspect-video flex items-center justify-center relative">
                  <video src={videoUrl} controls className="w-full h-full object-contain" />
                  {scanning && (
                    <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center p-4">
                      <Cpu size={40} className="text-red-400 animate-spin mb-4" />
                      <p className="text-sm font-semibold font-mono text-white mb-2">RUNNING DISASTER INFERENCE SWEEP...</p>
                      <div className="w-64 bg-white/5 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-red-500 h-full transition-all duration-150" style={{ width: `${scanProgress}%` }} />
                      </div>
                      <span className="text-[10px] font-mono text-[var(--text-muted)] mt-2">Buffer frame scans at {scanProgress}%</span>
                    </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          )}
        </div>

        {/* Scan button panel */}
        <div className="xl:col-span-4">
          <GlassCard hover={false} className="h-full flex flex-col justify-between border-red-500/10 bg-red-500/[0.01] p-5">
            <div className="space-y-4">
              <h3 className="text-sm font-semibold flex items-center gap-2 text-red-400 border-b border-white/5 pb-2">
                <ShieldAlert size={16} />
                Assessment Controls
              </h3>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                Initialize the high-priority AI disaster scan once the drone footage completes processing. 
                Our neural models will frame all hazards, rank structural distress, tag GPS coordinates, and speak audio announcements directly to local emergency response teams.
              </p>

              {offlineMode && (
                <div className="p-3 rounded-lg bg-orange-500/5 border border-orange-500/10 text-[10px] text-orange-400 font-mono flex items-start gap-2">
                  <Radio size={14} className="flex-shrink-0 animate-pulse mt-0.5" />
                  <div>
                    <span className="font-bold">LOW BANDWIDTH DETECTED:</span> Local edge inference models loaded. YOLO-World is working in standalone edge mode. Report exports are saved locally in SQLite cache.
                  </div>
                </div>
              )}
            </div>
            
            <div className="pt-6 border-t border-white/5 mt-8">
              <NeonButton 
                variant="danger" 
                className="w-full justify-center"
                icon={Play}
                onClick={handleStartScan}
                disabled={!file || scanning}
              >
                {scanning ? 'Scanning...' : 'Start Disaster Scan'}
              </NeonButton>
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Detections grid output (Spans full viewport width) */}
      <AnimatePresence>
        {showReport && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            
            {/* Sub-Header Actions */}
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle size={16} className="text-green-400 animate-bounce" />
                <h2 className="text-base font-bold text-white">Disaster Scan Results ({realEvents.length} Incidents Classified)</h2>
              </div>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => handleExport('docx')}
                  className="px-3 py-1.5 rounded-xl border border-white/5 hover:border-red-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer bg-white/[0.01]"
                >
                  <FileDown size={14} />
                  DOCX
                </button>
                <button 
                  onClick={() => handleExport('pdf')}
                  className="px-3 py-1.5 rounded-xl border border-white/5 hover:border-red-500/30 text-xs font-mono text-[var(--text-secondary)] hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer bg-white/[0.01]"
                >
                  <FileDown size={14} />
                  PDF
                </button>
              </div>
            </div>

            {/* Severity summary strip — shown when events exist */}
            {realEvents.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {[1,2,3,4,5].map(lvl => {
                  const count = realEvents.filter(e => e.severity === lvl).length
                  if (count === 0) return null
                  const colors = ['','text-green-400 bg-green-500/10 border-green-500/20','text-lime-400 bg-lime-500/10 border-lime-500/20','text-yellow-400 bg-yellow-500/10 border-yellow-500/20','text-orange-400 bg-orange-500/10 border-orange-500/20','text-red-400 bg-red-500/10 border-red-500/20']
                  return (
                    <span key={lvl} className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold border ${colors[lvl]}`}>
                      L{lvl}: {count} event{count > 1 ? 's' : ''}
                    </span>
                  )
                })}
                <span className="px-2.5 py-1 rounded-lg text-[10px] font-mono border border-white/10 text-[var(--text-muted)]">
                  Max severity: {Math.max(...realEvents.map(e => e.severity))}
                </span>
              </div>
            )}

            {/* Simulated Detections Cards & Dynamic Resource Estimator Grid */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              
            {/* Real Incident Cards */}
            <div className="xl:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-4">
              {realEvents.length === 0 && (
                <div className="col-span-2 text-center py-12 text-[var(--text-muted)] text-sm font-mono">
                  No confirmed disaster events detected in this footage.
                </div>
              )}
              {realEvents.map((event) => {
                const sStyle = getSeverityStyle(event.severity)
                return (
                  <GlassCard key={event.id} hover={false} className="overflow-hidden border-white/5">
                    <div className={`aspect-video w-full rounded-xl bg-gradient-to-br from-red-900/20 to-red-950/40 border border-white/5 relative flex items-center justify-center overflow-hidden`}>
                      <div className="absolute inset-0 bg-grid opacity-20" />
                      {event.screenshot_path ? (
                        <img src={event.screenshot_path} alt={event.disaster_type} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-24 h-16 border-2 border-red-500/40 rounded flex items-center justify-center relative">
                          <div className="absolute -top-1 -left-1 w-2.5 h-2.5 border-t-2 border-l-2 border-red-400" />
                          <div className="absolute -top-1 -right-1 w-2.5 h-2.5 border-t-2 border-r-2 border-red-400" />
                          <div className="absolute -bottom-1 -left-1 w-2.5 h-2.5 border-b-2 border-l-2 border-red-400" />
                          <div className="absolute -bottom-1 -right-1 w-2.5 h-2.5 border-b-2 border-r-2 border-red-400" />
                          <span className="text-[8px] font-mono text-red-400 tracking-wider text-center">TARGET LOCKED</span>
                        </div>
                      )}
                      <div className="absolute bottom-2 left-2 flex items-center gap-1.5 bg-black/70 px-2 py-0.5 rounded text-[8px] font-mono text-[var(--text-secondary)]">
                        <Clock size={10} />
                        TIME: {event.timestamp ? `${event.timestamp.toFixed(1)}s` : '—'}
                      </div>
                      <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-0.5 rounded text-[8px] font-mono text-[var(--text-secondary)]">
                        CONF: {event.confidence ? `${(event.confidence * 100).toFixed(0)}%` : '—'}
                      </div>
                    </div>
                    <div className="p-4 space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold text-white truncate capitalize">{event.disaster_type.replace('_', ' ')}</h4>
                        <span className={`px-2.5 py-0.5 rounded text-[9px] font-mono border whitespace-nowrap ${sStyle.color} ${sStyle.bg}`}>
                          {sStyle.label}
                        </span>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{event.recommendations}</p>
                    </div>
                  </GlassCard>
                )
              })}
            </div>

              {/* Dynamic Resource Estimation Table (Section 28) (Spans 5 columns) */}
              <div className="xl:col-span-5 space-y-4">
                <GlassCard hover={false} className="border-red-500/20 bg-red-500/[0.01] p-5">
                  <div className="flex items-center gap-3 mb-4 pb-2 border-b border-white/5">
                    <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
                      <HeartHandshake size={18} />
                    </div>
                    <div>
                      <span className="text-[9px] font-mono text-red-400 uppercase tracking-widest block">AI Operations Dispatch</span>
                      <h3 className="text-sm font-semibold text-white">Emergency Resource Estimation Table</h3>
                    </div>
                  </div>

                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-4">
                    Based on incident severity, structural collapse spread, and flood water levels, the platform calculates active resource requirements:
                  </p>

                  <div className="space-y-3 font-mono text-xs">
                    {[
                      { label: 'Rescue Teams Required', value: `${resources.rescueTeams} squads`, desc: 'First responders for search, hazard clearance' },
                      { label: 'Ambulances Allocated', value: `${resources.ambulances} units`, desc: 'Medical emergency support on standby' },
                      { label: 'Rescue Boats Needed', value: `${resources.rescueBoats} boats`, desc: 'For deep flooded sectors eviction' },
                      { label: 'Emergency Vehicles', value: `${resources.emergencyVehicles} assets`, desc: 'Heavy debris clearance & dispatch trucks' },
                      { label: 'On-Ground Support Staff', value: `${resources.supportStaff} personnel`, desc: 'Command directors, coordinators, camp workers' }
                    ].map((row, i) => (
                      <div key={i} className="flex justify-between items-start p-2.5 rounded-lg bg-white/[0.01] border border-white/5 hover:bg-white/[0.02] transition-colors">
                        <div>
                          <p className="font-semibold text-white text-xs">{row.label}</p>
                          <p className="text-[9px] text-[var(--text-muted)] mt-0.5">{row.desc}</p>
                        </div>
                        <span className="text-xs font-bold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/10 whitespace-nowrap">
                          {row.value}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 p-3 rounded-lg bg-red-500/5 border border-red-500/10 flex items-start gap-2">
                    <Shield size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
                      {realEvents.length > 0
                        ? `${realEvents.length} incident(s) confirmed. Highest severity: Level ${Math.max(...realEvents.map(e => e.severity))}. Dispatch resources as estimated above.`
                        : 'No confirmed disaster events detected in this footage. Area appears safe.'}
                    </p>
                  </div>
                </GlassCard>
              </div>

            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
