import { motion } from 'framer-motion'

export default function RadarPulse({ size = 200, className = '' }) {
  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      {/* Radar rings */}
      {[0, 1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border"
          style={{
            width: `${(i + 1) * 25}%`,
            height: `${(i + 1) * 25}%`,
            top: `${50 - (i + 1) * 12.5}%`,
            left: `${50 - (i + 1) * 12.5}%`,
            borderColor: `rgba(57, 255, 20, ${0.12 - i * 0.02})`,
          }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.15, duration: 0.5 }}
        />
      ))}

      {/* Cross lines */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="w-full h-px bg-gradient-to-r from-transparent via-green-500/20 to-transparent" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="h-full w-px bg-gradient-to-b from-transparent via-green-500/20 to-transparent" />
      </div>

      {/* Scanning sweep */}
      <motion.div
        className="absolute inset-0"
        style={{ transformOrigin: 'center center' }}
        animate={{ rotate: 360 }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      >
        <div
          className="absolute top-1/2 left-1/2 origin-bottom-left"
          style={{
            width: '50%',
            height: 2,
            background: 'linear-gradient(90deg, rgba(57,255,20,0.6), transparent)',
            transformOrigin: 'left center',
          }}
        />
        {/* Sweep trail */}
        <div
          className="absolute top-0 left-1/2 w-1/2 h-1/2 origin-bottom-left"
          style={{
            background: 'conic-gradient(from 0deg, rgba(57,255,20,0.08), transparent 60deg)',
            transformOrigin: 'bottom left',
          }}
        />
      </motion.div>

      {/* Center dot */}
      <motion.div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-green-400"
        animate={{ 
          boxShadow: [
            '0 0 4px rgba(57,255,20,0.4)',
            '0 0 12px rgba(57,255,20,0.8)',
            '0 0 4px rgba(57,255,20,0.4)',
          ]
        }}
        transition={{ duration: 2, repeat: Infinity }}
      />

      {/* Random blips */}
      {[
        { x: '30%', y: '25%', delay: 0.5 },
        { x: '65%', y: '40%', delay: 1.2 },
        { x: '45%', y: '70%', delay: 2.1 },
        { x: '75%', y: '60%', delay: 3.0 },
      ].map((blip, i) => (
        <motion.div
          key={i}
          className="absolute w-1.5 h-1.5 rounded-full bg-green-400"
          style={{ left: blip.x, top: blip.y }}
          animate={{
            opacity: [0, 1, 1, 0],
            scale: [0.5, 1, 1, 0.5],
          }}
          transition={{
            duration: 4,
            delay: blip.delay,
            repeat: Infinity,
          }}
        />
      ))}
    </div>
  )
}
