import { motion } from 'framer-motion'

export default function ConfidenceBar({ value = 0, label = '', className = '' }) {
  const level = value >= 80 ? 'high' : value >= 50 ? 'medium' : 'low'

  return (
    <div className={`space-y-1 ${className}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span className="font-mono font-semibold text-[var(--text-primary)]">{value}%</span>
      </div>
      <div className="confidence-bar">
        <motion.div
          className={`confidence-fill confidence-${level}`}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1.2, ease: [0.4, 0, 0.2, 1], delay: 0.3 }}
        />
      </div>
    </div>
  )
}
