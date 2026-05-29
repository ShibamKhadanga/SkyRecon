import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Map, AlertTriangle, Crosshair, Satellite, Shield, Cpu, 
  Radio, Eye, Radar, ChevronRight, Zap, Globe, Activity
} from 'lucide-react'
import RadarPulse from '../components/ui/RadarPulse'
import AnimatedCounter from '../components/ui/AnimatedCounter'

// Typing effect hook
function useTypingEffect(texts, typingSpeed = 60, deleteSpeed = 40, pauseTime = 2000) {
  const [displayText, setDisplayText] = useState('')
  const [textIndex, setTextIndex] = useState(0)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    const currentFullText = texts[textIndex]
    
    const timeout = setTimeout(() => {
      if (!isDeleting) {
        setDisplayText(currentFullText.slice(0, displayText.length + 1))
        if (displayText.length === currentFullText.length) {
          setTimeout(() => setIsDeleting(true), pauseTime)
        }
      } else {
        setDisplayText(currentFullText.slice(0, displayText.length - 1))
        if (displayText.length === 0) {
          setIsDeleting(false)
          setTextIndex((prev) => (prev + 1) % texts.length)
        }
      }
    }, isDeleting ? deleteSpeed : typingSpeed)

    return () => clearTimeout(timeout)
  }, [displayText, isDeleting, textIndex, texts])

  return displayText
}

// Drone SVG component
function DroneIcon({ className = '' }) {
  return (
    <svg viewBox="0 0 120 60" fill="none" className={className}>
      {/* Arms */}
      <line x1="35" y1="25" x2="50" y2="30" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      <line x1="85" y1="25" x2="70" y2="30" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      <line x1="35" y1="40" x2="50" y2="35" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      <line x1="85" y1="40" x2="70" y2="35" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
      {/* Body */}
      <rect x="45" y="26" width="30" height="12" rx="6" fill="currentColor" opacity="0.9"/>
      {/* Propellers */}
      <ellipse cx="35" cy="25" rx="14" ry="3" fill="currentColor" opacity="0.3"/>
      <ellipse cx="85" cy="25" rx="14" ry="3" fill="currentColor" opacity="0.3"/>
      <ellipse cx="35" cy="40" rx="14" ry="3" fill="currentColor" opacity="0.3"/>
      <ellipse cx="85" cy="40" rx="14" ry="3" fill="currentColor" opacity="0.3"/>
      {/* Motor dots */}
      <circle cx="35" cy="25" r="3" fill="currentColor" opacity="0.6"/>
      <circle cx="85" cy="25" r="3" fill="currentColor" opacity="0.6"/>
      <circle cx="35" cy="40" r="3" fill="currentColor" opacity="0.6"/>
      <circle cx="85" cy="40" r="3" fill="currentColor" opacity="0.6"/>
      {/* Camera */}
      <circle cx="60" cy="38" r="3" fill="currentColor" opacity="0.7"/>
      <circle cx="60" cy="38" r="1.5" fill="currentColor"/>
    </svg>
  )
}

// Animated stat for hero
function HeroStat({ icon: Icon, value, label, suffix = '', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.6 }}
      className="text-center"
    >
      <div className="flex items-center justify-center gap-1.5 mb-1">
        <Icon size={14} className="text-green-500" />
        <span className="text-xl font-bold text-gradient-green font-mono">
          <AnimatedCounter value={value} suffix={suffix} />
        </span>
      </div>
      <p className="text-[0.65rem] text-[var(--text-muted)] uppercase tracking-widest">{label}</p>
    </motion.div>
  )
}

export default function LandingPage() {
  const navigate = useNavigate()
  const [showContent, setShowContent] = useState(false)
  const [hoveredModule, setHoveredModule] = useState(null)

  const typedText = useTypingEffect([
    'AI Powered Aerial Intelligence',
    'Smart City Surveillance',
    'Disaster Detection & Response',
    'Real-Time Drone Analytics',
    'Infrastructure Monitoring',
  ])

  useEffect(() => {
    const timer = setTimeout(() => setShowContent(true), 600)
    return () => clearTimeout(timer)
  }, [])

  const modules = [
    {
      id: 'mapping',
      title: 'Mapping & Survey',
      subtitle: 'Smart Mapping • Land Analysis • Infrastructure',
      description: 'AI-powered aerial mapping, land surveying, traffic analysis, plantation monitoring, and smart city analytics.',
      icon: Map,
      features: ['Object Detection', 'Traffic Analysis', 'Vegetation Mapping', 'Infrastructure Scan'],
      gradient: 'from-green-500/20 via-emerald-500/10 to-cyan-500/5',
      borderColor: 'rgba(34,197,94,0.3)',
      glowColor: 'rgba(34,197,94,0.15)',
      path: '/mapping',
    },
    {
      id: 'disaster',
      title: 'Disaster Analysis',
      subtitle: 'Emergency Detection • Response • Monitoring',
      description: 'Real-time disaster detection, severity assessment, emergency resource estimation, and rescue coordination.',
      icon: AlertTriangle,
      features: ['Flood Detection', 'Fire & Smoke', 'Structural Damage', 'Rescue Planning'],
      gradient: 'from-orange-500/20 via-red-500/10 to-yellow-500/5',
      borderColor: 'rgba(249,115,22,0.3)',
      glowColor: 'rgba(249,115,22,0.12)',
      path: '/disaster',
    },
  ]

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* ─── Background Effects ─── */}
      {/* Grid */}
      <div className="absolute inset-0 bg-grid" />

      {/* Gradient orbs */}
      <div className="gradient-orb gradient-orb-green absolute w-[600px] h-[600px] -top-40 -left-40 opacity-60" />
      <div className="gradient-orb gradient-orb-cyan absolute w-[500px] h-[500px] bottom-0 right-0 opacity-40" />
      <div className="gradient-orb gradient-orb-green absolute w-[400px] h-[400px] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-20" />

      {/* Scan line */}
      <motion.div
        className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-green-400/20 to-transparent"
        animate={{ y: ['-100vh', '100vh'] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
      />

      {/* Flying drone */}
      <motion.div
        className="absolute text-green-400/30 w-32"
        animate={{ 
          x: ['-150px', 'calc(100vw + 150px)'],
          y: [80, 40, 100, 60, 80],
        }}
        transition={{ 
          x: { duration: 15, repeat: Infinity, ease: 'linear' },
          y: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
        }}
      >
        <DroneIcon />
      </motion.div>

      {/* Second drone, opposite direction */}
      <motion.div
        className="absolute text-cyan-400/15 w-20 top-1/3"
        animate={{ 
          x: ['calc(100vw + 100px)', '-100px'],
          y: [200, 160, 220, 180, 200],
        }}
        transition={{ 
          x: { duration: 20, repeat: Infinity, ease: 'linear', delay: 5 },
          y: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
        }}
      >
        <DroneIcon />
      </motion.div>

      {/* ─── Content ─── */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4 py-8">
        
        <AnimatePresence>
          {showContent && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full max-w-5xl mx-auto"
            >
              {/* Top: Radar + Branding */}
              <div className="flex flex-col items-center mb-12">
                {/* Radar */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  className="mb-6"
                >
                  <RadarPulse size={160} />
                </motion.div>

                {/* Logo */}
                <motion.h1
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.6 }}
                  className="text-5xl md:text-7xl font-black tracking-[0.2em] mb-3"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  <span className="text-gradient-green">SKY</span>
                  <span className="text-white">RECON</span>
                </motion.h1>

                {/* Typing tagline */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.6 }}
                  className="h-7 flex items-center"
                >
                  <span className="text-sm md:text-base text-[var(--text-secondary)] font-mono tracking-wider">
                    {typedText}
                  </span>
                  <motion.span
                    className="inline-block w-0.5 h-5 bg-green-400 ml-1"
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  />
                </motion.div>

                {/* Status bar */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 }}
                  className="flex items-center gap-2 mt-4 px-4 py-1.5 rounded-full bg-green-500/5 border border-green-500/10"
                >
                  <motion.div
                    className="w-1.5 h-1.5 rounded-full bg-green-400"
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                  <span className="text-xs text-green-400 font-mono">SYSTEMS ONLINE</span>
                  <span className="text-xs text-[var(--text-muted)]">•</span>
                  <span className="text-xs text-[var(--text-muted)] font-mono">AI ENGINE READY</span>
                </motion.div>
              </div>

              {/* Stats Row */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="flex flex-wrap items-center justify-center gap-6 md:gap-16 mb-12"
              >
                <HeroStat icon={Eye} value={25} label="AI Categories" delay={1.1} />
                <div className="hidden sm:block w-px h-8 bg-white/10" />
                <HeroStat icon={Radar} value={5} label="Detection Layers" delay={1.2} />
                <div className="hidden sm:block w-px h-8 bg-white/10" />
                <HeroStat icon={Globe} value={99} suffix="%" label="Accuracy" delay={1.3} />
                <div className="hidden md:block w-px h-8 bg-white/10" />
                <HeroStat icon={Zap} value={30} suffix="fps" label="Processing" delay={1.4} />
              </motion.div>

              {/* Module Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 max-w-5xl mx-auto px-6 md:px-8">
                {modules.map((mod, i) => (
                  <motion.div
                    key={mod.id}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.2 + i * 0.15, duration: 0.6, ease: [0.175, 0.885, 0.32, 1.275] }}
                    onMouseEnter={() => setHoveredModule(mod.id)}
                    onMouseLeave={() => setHoveredModule(null)}
                    onClick={() => navigate(mod.path)}
                    className="group relative cursor-pointer"
                  >
                    <div
                      className={`
                        relative overflow-hidden rounded-2xl p-6 md:p-8
                        bg-gradient-to-br ${mod.gradient}
                        border transition-all duration-500
                        ${hoveredModule === mod.id 
                          ? 'border-opacity-100 scale-[1.02]' 
                          : 'border-opacity-50 scale-100'
                        }
                      `}
                      style={{ 
                        borderColor: mod.borderColor,
                        boxShadow: hoveredModule === mod.id 
                          ? `0 20px 60px ${mod.glowColor}, 0 0 100px ${mod.glowColor}`
                          : `0 8px 32px rgba(0,0,0,0.3)`,
                        backdropFilter: 'blur(20px)',
                      }}
                    >
                      {/* Background icon */}
                      <div className="absolute -right-6 -bottom-6 opacity-[0.04] group-hover:opacity-[0.08] transition-opacity duration-500">
                        <mod.icon size={180} strokeWidth={0.5} />
                      </div>

                      {/* Scanning line on hover */}
                      {hoveredModule === mod.id && (
                        <motion.div
                          className="absolute left-0 right-0 h-px"
                          style={{
                            background: `linear-gradient(90deg, transparent, ${mod.borderColor}, transparent)`,
                          }}
                          initial={{ top: 0, opacity: 0 }}
                          animate={{ top: '100%', opacity: [0, 1, 1, 0] }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        />
                      )}

                      {/* Content */}
                      <div className="relative z-10 flex flex-col items-center text-center">
                        <div className="flex flex-col items-center justify-center mb-4">
                          <div
                            className="p-3 rounded-xl mb-2 flex items-center justify-center"
                            style={{ 
                              background: `${mod.borderColor.replace('0.3', '0.1')}`,
                              border: `1px solid ${mod.borderColor.replace('0.3', '0.15')}`,
                            }}
                          >
                            <mod.icon size={24} style={{ color: mod.borderColor.replace('0.3', '1') }} />
                          </div>
                          <span className={`text-[0.65rem] font-mono px-2 py-0.5 rounded border ${
                            mod.id === 'mapping'
                              ? 'bg-green-500/5 text-green-400 border-green-500/20'
                              : 'bg-orange-500/5 text-orange-400 border-orange-500/20'
                          }`}>
                            READY
                          </span>
                        </div>

                        <h2 className="text-xl md:text-2xl font-bold mb-1">{mod.title}</h2>
                        <p className="text-xs text-[var(--text-muted)] font-mono mb-3">{mod.subtitle}</p>
                        <p className="text-sm text-[var(--text-secondary)] mb-5 leading-relaxed max-w-sm">{mod.description}</p>

                        {/* Feature chips */}
                        <div className="flex flex-wrap items-center justify-center gap-2 mb-6">
                          {mod.features.map((feat) => (
                            <span
                              key={feat}
                              className="px-2.5 py-1 rounded-lg text-[0.7rem] font-medium
                                         bg-white/5 text-[var(--text-secondary)] border border-white/5
                                         group-hover:border-white/10 transition-colors"
                            >
                              {feat}
                            </span>
                          ))}
                        </div>

                        {/* Launch Action Button */}
                        <div className="w-full pt-4 border-t border-white/5 flex flex-col items-center justify-center">
                          <span 
                            className={`
                              w-full inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-bold font-mono transition-all duration-300
                              ${mod.id === 'mapping' 
                                ? 'bg-green-500/10 text-green-400 group-hover:bg-green-500 group-hover:text-black border border-green-500/20 shadow-[0_0_15px_rgba(34,197,94,0.05)]' 
                                : 'bg-orange-500/10 text-orange-400 group-hover:bg-orange-500 group-hover:text-black border border-orange-500/20 shadow-[0_0_15px_rgba(249,115,22,0.05)]'
                              }
                            `}
                          >
                            Launch System
                            <ChevronRight size={16} />
                          </span>
                          <span className="text-[10px] font-mono text-[var(--text-muted)] mt-2">
                            Click to initialize module
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Bottom info */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.8 }}
                className="flex items-center justify-center gap-6 mt-10 text-[0.65rem] text-[var(--text-muted)]"
              >
                <span className="flex items-center gap-1.5">
                  <Cpu size={10} /> YOLOv8 + YOLO-World
                </span>
                <span className="flex items-center gap-1.5">
                  <Satellite size={10} /> GIS Enabled
                </span>
                <span className="flex items-center gap-1.5">
                  <Shield size={10} /> Enterprise Grade
                </span>
                <span className="flex items-center gap-1.5">
                  <Activity size={10} /> Real-Time
                </span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
