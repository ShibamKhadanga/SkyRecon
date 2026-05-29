import { Shield, AlertTriangle, AlertOctagon, Info, Zap } from 'lucide-react'

const severityConfig = {
  1: { label: 'Minor', color: 'severity-1', icon: Info },
  2: { label: 'Low', color: 'severity-2', icon: Shield },
  3: { label: 'Moderate', color: 'severity-3', icon: AlertTriangle },
  4: { label: 'High', color: 'severity-4', icon: Zap },
  5: { label: 'Critical', color: 'severity-5', icon: AlertOctagon },
}

export default function SeverityBadge({ level = 1, showLabel = true, size = 'md' }) {
  const config = severityConfig[level] || severityConfig[1]
  const Icon = config.icon
  const sizeClass = size === 'sm' ? 'text-[0.65rem] px-2 py-0.5' : size === 'lg' ? 'text-sm px-4 py-1.5' : ''

  return (
    <span className={`severity-badge ${config.color} ${sizeClass}`}>
      <Icon size={size === 'sm' ? 10 : size === 'lg' ? 16 : 12} />
      {showLabel && <span>Level {level} – {config.label}</span>}
    </span>
  )
}
