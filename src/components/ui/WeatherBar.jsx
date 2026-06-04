import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Wind, Thermometer, Cloud, Droplets, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import useWeather from '../../hooks/useWeather'

// Weather code → short label
function weatherLabel(code) {
  if (code === 0)           return 'Clear'
  if (code <= 3)            return 'Cloudy'
  if (code <= 49)           return 'Foggy'
  if (code <= 67)           return 'Rain'
  if (code <= 77)           return 'Snow'
  if (code <= 82)           return 'Showers'
  if (code <= 99)           return 'Thunderstorm'
  return 'Unknown'
}

export default function WeatherBar() {
  const { weather, issues, loading, error, safe } = useWeather()
  const audioCtx = useRef(null)
  const hasWarnedRef = useRef(false)

  // Play a beep-beep warning tone when unsafe
  useEffect(() => {
    if (!safe && !loading && issues.length > 0 && !hasWarnedRef.current) {
      hasWarnedRef.current = true
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)()
        audioCtx.current = ctx
        const beep = (startTime) => {
          const osc  = ctx.createOscillator()
          const gain = ctx.createGain()
          osc.connect(gain)
          gain.connect(ctx.destination)
          osc.frequency.value = 880
          osc.type = 'sine'
          gain.gain.setValueAtTime(0.3, startTime)
          gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.3)
          osc.start(startTime)
          osc.stop(startTime + 0.3)
        }
        beep(ctx.currentTime)
        beep(ctx.currentTime + 0.4)
        beep(ctx.currentTime + 0.8)
      } catch (_) {}
    }
    if (safe) hasWarnedRef.current = false
  }, [safe, loading, issues])

  if (loading) return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.02] border border-white/5 text-[10px] font-mono text-[var(--text-muted)]">
      <Loader2 size={11} className="animate-spin" /> Fetching weather...
    </div>
  )

  if (error) return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.02] border border-white/5 text-[10px] font-mono text-[var(--text-muted)]">
      <Cloud size={11} /> Weather unavailable
    </div>
  )

  const w = weather

  return (
    <div className="space-y-2">
      {/* Weather stats strip */}
      <div className="flex items-center gap-2 flex-wrap px-3 py-2 rounded-xl bg-white/[0.02] border border-white/5">
        {/* Safety badge */}
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
          safe
            ? 'bg-green-500/10 border border-green-500/20 text-green-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {safe
            ? <><CheckCircle size={9} /> Safe to fly</>
            : <><AlertTriangle size={9} /> Do NOT fly</>
          }
        </div>

        <span className="text-white/10">|</span>

        {/* Weather label */}
        <span className="text-[10px] font-mono text-[var(--text-secondary)]">
          {weatherLabel(w.weather_code)}
        </span>

        {[
          { icon: Thermometer, value: `${w.temperature}°C`,    color: 'text-orange-400' },
          { icon: Wind,        value: `${w.wind_speed} m/s`,   color: w.wind_speed > 10 ? 'text-red-400' : 'text-cyan-400' },
          { icon: Droplets,    value: `${w.precipitation} mm`, color: w.precipitation > 0.5 ? 'text-red-400' : 'text-blue-400' },
          { icon: Cloud,       value: `${w.cloud_cover}%`,     color: w.cloud_cover > 90 ? 'text-red-400' : 'text-[var(--text-muted)]' },
        ].map(({ icon: Icon, value, color }) => (
          <div key={value} className="flex items-center gap-1">
            <Icon size={10} className={color} />
            <span className={`text-[10px] font-mono ${color}`}>{value}</span>
          </div>
        ))}
      </div>

      {/* Warning banner */}
      <AnimatePresence>
        {!safe && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="flex items-start gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/30"
          >
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            >
              <AlertTriangle size={13} className="text-red-400 flex-shrink-0 mt-0.5" />
            </motion.div>
            <div>
              <p className="text-[11px] font-semibold text-red-400 mb-0.5">⚠ Unsafe flying conditions detected</p>
              <p className="text-[10px] text-red-300/80 leading-relaxed">{issues.join(' · ')}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
