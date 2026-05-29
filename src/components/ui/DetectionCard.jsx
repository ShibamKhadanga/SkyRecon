import { motion } from 'framer-motion'
import ConfidenceBar from './ConfidenceBar'
import { MapPin, Clock, Tag } from 'lucide-react'

export default function DetectionCard({ 
  label = 'Object',
  category = 'General',
  confidence = 0,
  timestamp = '',
  location = '',
  thumbnailColor,
  count = 1,
  delay = 0,
  className = '' 
}) {
  const randomColor = thumbnailColor || `hsl(${Math.random() * 60 + 120}, 70%, 50%)`

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ x: 4, borderColor: 'rgba(57,255,20,0.3)' }}
      className={`glass-panel p-4 cursor-pointer transition-colors ${className}`}
    >
      <div className="flex items-start gap-3">
        {/* Thumbnail / Icon */}
        <div 
          className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 text-sm font-bold"
          style={{ 
            background: `${randomColor}15`,
            color: randomColor,
            border: `1px solid ${randomColor}30`,
          }}
        >
          {count > 1 ? `×${count}` : label.charAt(0)}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="font-semibold text-sm truncate">{label}</h4>
          </div>
          
          <div className="flex items-center gap-3 text-[0.7rem] text-[var(--text-muted)] mb-2">
            <span className="flex items-center gap-1">
              <Tag size={10} />
              {category}
            </span>
            {timestamp && (
              <span className="flex items-center gap-1">
                <Clock size={10} />
                {timestamp}
              </span>
            )}
            {location && (
              <span className="flex items-center gap-1">
                <MapPin size={10} />
                {location}
              </span>
            )}
          </div>

          <ConfidenceBar value={confidence} label="Confidence" />
        </div>
      </div>
    </motion.div>
  )
}
