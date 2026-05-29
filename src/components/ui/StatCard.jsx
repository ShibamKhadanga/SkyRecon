import { motion } from 'framer-motion'
import AnimatedCounter from './AnimatedCounter'

export default function StatCard({ 
  icon: Icon, 
  label, 
  value, 
  suffix = '', 
  prefix = '',
  trend,
  trendLabel = '',
  color = 'green',
  delay = 0,
  className = '' 
}) {
  const colorMap = {
    green: { bg: 'rgba(34,197,94,0.1)', border: 'rgba(34,197,94,0.2)', text: '#4ade80', icon: '#22c55e' },
    cyan: { bg: 'rgba(6,182,212,0.1)', border: 'rgba(6,182,212,0.2)', text: '#22d3ee', icon: '#06b6d4' },
    orange: { bg: 'rgba(249,115,22,0.1)', border: 'rgba(249,115,22,0.2)', text: '#fb923c', icon: '#f97316' },
    red: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.2)', text: '#f87171', icon: '#ef4444' },
    purple: { bg: 'rgba(168,85,247,0.1)', border: 'rgba(168,85,247,0.2)', text: '#c084fc', icon: '#a855f7' },
  }

  const c = colorMap[color] || colorMap.green

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -4, borderColor: c.border }}
      className={`glass-card p-5 cursor-default ${className}`}
      style={{ borderColor: c.border }}
    >
      <div className="flex items-start justify-between mb-3">
        <div 
          className="p-2.5 rounded-xl"
          style={{ background: c.bg }}
        >
          {Icon && <Icon size={20} style={{ color: c.icon }} />}
        </div>
        {trend !== undefined && (
          <span 
            className="text-xs font-semibold px-2 py-0.5 rounded-full"
            style={{ 
              color: trend >= 0 ? '#4ade80' : '#f87171',
              background: trend >= 0 ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
            }}
          >
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% {trendLabel}
          </span>
        )}
      </div>
      <div className="text-2xl font-bold mb-1" style={{ color: c.text }}>
        <AnimatedCounter value={value} prefix={prefix} suffix={suffix} />
      </div>
      <div className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wider">
        {label}
      </div>
    </motion.div>
  )
}
