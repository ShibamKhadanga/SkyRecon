import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { 
  AlertTriangle, Download, Volume2, MapPin, Clock, Users, 
  Truck, Activity, Shield, Flame, Droplets, Building, Phone
} from 'lucide-react'
import GlassCard from '../components/ui/GlassCard'
import NeonButton from '../components/ui/NeonButton'
import SeverityBadge from '../components/ui/SeverityBadge'
import ConfidenceBar from '../components/ui/ConfidenceBar'
import AnimatedCounter from '../components/ui/AnimatedCounter'

const mockDisasterEvents = [
  { id: 'D-001', type: 'Flood Area', severity: 5, confidence: 94, time: '00:12', gps: '28.63°N, 77.22°E', area: '2.4 km²', icon: Droplets, color: '#3b82f6' },
  { id: 'D-002', type: 'Damaged Building', severity: 4, confidence: 89, time: '00:28', gps: '28.62°N, 77.21°E', area: '450 m²', icon: Building, color: '#f97316' },
  { id: 'D-003', type: 'Fire Active', severity: 5, confidence: 97, time: '00:35', gps: '28.64°N, 77.23°E', area: '800 m²', icon: Flame, color: '#ef4444' },
  { id: 'D-004', type: 'Road Collapse', severity: 3, confidence: 82, time: '00:48', gps: '28.61°N, 77.20°E', area: '120 m²', icon: AlertTriangle, color: '#eab308' },
  { id: 'D-005', type: 'Trapped People', severity: 5, confidence: 76, time: '01:05', gps: '28.63°N, 77.21°E', area: 'Point', icon: Users, color: '#ef4444' },
]

const resourceEstimation = [
  { label: 'Rescue Teams', value: 12, icon: Shield, color: '#22c55e' },
  { label: 'Ambulances', value: 8, icon: Truck, color: '#ef4444' },
  { label: 'Fire Engines', value: 4, icon: Flame, color: '#f97316' },
  { label: 'Boats', value: 6, icon: Droplets, color: '#3b82f6' },
  { label: 'Support Staff', value: 45, icon: Users, color: '#06b6d4' },
]

export default function DisasterResultsPage() {
  const { id } = useParams()
  const [voiceAlertPlayed, setVoiceAlertPlayed] = useState(false)

  const playVoiceAlert = () => {
    const msg = new SpeechSynthesisUtterance(
      'Critical alert. Severe flood zone detected in sector 4. Immediate evacuation required. Fire detected in adjacent area. Deploy rescue teams immediately.'
    )
    msg.rate = 0.9
    msg.pitch = 0.8
    window.speechSynthesis.speak(msg)
    setVoiceAlertPlayed(true)
  }

  return (
    <div className="space-y-6">
      {/* Alert Header */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="glass-card p-5 border-red-500/20"
        style={{ animation: 'alert-pulse 3s ease-in-out infinite' }}
      >
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20"
            >
              <AlertTriangle size={22} className="text-red-400" />
            </motion.div>
            <div>
              <h1 className="text-xl font-bold">Disaster Assessment Report</h1>
              <p className="text-sm text-[var(--text-muted)] font-mono">Incident: {id} • {mockDisasterEvents.length} events detected</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <NeonButton variant="danger" icon={Volume2} onClick={playVoiceAlert}>
              Voice Alert
            </NeonButton>
            <NeonButton variant="secondary" icon={Download}>
              Export Report
            </NeonButton>
          </div>
        </div>
      </motion.div>

      {/* Overall Severity + Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard className="md:col-span-1 text-center border-red-500/20" delay={0.1} hover={false}>
          <p className="text-xs text-[var(--text-muted)] mb-2 uppercase tracking-wider">Overall Severity</p>
          <div className="text-5xl font-black text-red-400 mb-2" style={{ fontFamily: 'var(--font-display)' }}>
            <AnimatedCounter value={5} />
          </div>
          <SeverityBadge level={5} size="lg" />
          <p className="text-xs text-red-300/60 mt-2 font-mono">CRITICAL EMERGENCY</p>
        </GlassCard>

        <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: 'Events Detected', value: 5, color: '#ef4444' },
            { label: 'Affected Area', value: 3.8, suffix: ' km²', color: '#f97316' },
            { label: 'Est. People at Risk', value: 1240, color: '#3b82f6' },
            { label: 'Structures Damaged', value: 23, color: '#a855f7' },
            { label: 'Active Fires', value: 2, color: '#ef4444' },
            { label: 'Rescue Priority', value: 1, suffix: ' (Max)', color: '#22c55e' },
          ].map((stat, i) => (
            <GlassCard key={stat.label} className="p-4" delay={0.15 + i * 0.05} hover={false}>
              <p className="text-2xl font-bold mb-1" style={{ color: stat.color }}>
                <AnimatedCounter value={stat.value} suffix={stat.suffix || ''} />
              </p>
              <p className="text-[0.65rem] text-[var(--text-muted)] uppercase tracking-wider">{stat.label}</p>
            </GlassCard>
          ))}
        </div>
      </div>

      {/* Disaster Events + Resource Estimation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Events List */}
        <div className="lg:col-span-2">
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Activity size={14} className="text-red-400" />
              Detected Disaster Events
            </h3>
            <div className="space-y-3">
              {mockDisasterEvents.map((event, i) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.08 }}
                  className="glass-panel p-4"
                >
                  <div className="flex items-start gap-3">
                    <div 
                      className="p-2 rounded-lg flex-shrink-0"
                      style={{ background: `${event.color}15`, border: `1px solid ${event.color}20` }}
                    >
                      <event.icon size={18} style={{ color: event.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-2">
                        <div>
                          <h4 className="text-sm font-semibold">{event.type}</h4>
                          <p className="text-[0.65rem] text-[var(--text-muted)] font-mono">{event.id}</p>
                        </div>
                        <SeverityBadge level={event.severity} size="sm" />
                      </div>
                      <div className="flex items-center gap-4 text-xs text-[var(--text-muted)] mb-2">
                        <span className="flex items-center gap-1"><Clock size={10} />{event.time}</span>
                        <span className="flex items-center gap-1"><MapPin size={10} />{event.gps}</span>
                        <span>Area: {event.area}</span>
                      </div>
                      <ConfidenceBar value={event.confidence} label="AI Confidence" />
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </div>

        {/* Resource Estimation */}
        <div className="space-y-4">
          <GlassCard hover={false}>
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
              <Shield size={14} className="text-green-400" />
              Resource Estimation
            </h3>
            <div className="space-y-3">
              {resourceEstimation.map((res, i) => (
                <motion.div
                  key={res.label}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + i * 0.08 }}
                  className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02]"
                >
                  <div 
                    className="p-2 rounded-lg"
                    style={{ background: `${res.color}10` }}
                  >
                    <res.icon size={16} style={{ color: res.color }} />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-[var(--text-muted)]">{res.label}</p>
                  </div>
                  <p className="text-lg font-bold font-mono" style={{ color: res.color }}>
                    <AnimatedCounter value={res.value} />
                  </p>
                </motion.div>
              ))}
            </div>
          </GlassCard>

          {/* Emergency Contacts */}
          <GlassCard hover={false} className="border-red-500/10">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Phone size={14} className="text-red-400" />
              Emergency Actions
            </h3>
            <div className="space-y-2">
              <NeonButton variant="danger" size="sm" className="w-full justify-start">
                🚨 Request Immediate Evacuation
              </NeonButton>
              <NeonButton variant="secondary" size="sm" className="w-full justify-start">
                📡 Send Alert to Control Room
              </NeonButton>
              <NeonButton variant="secondary" size="sm" className="w-full justify-start">
                🗺️ Deploy Rescue Teams to GPS
              </NeonButton>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
