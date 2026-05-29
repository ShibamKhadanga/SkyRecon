import { motion } from 'framer-motion'
import RadarPulse from './RadarPulse'

export default function LoadingScreen({ message = 'Initializing AI Systems...' }) {
  return (
    <motion.div
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[var(--bg-primary)]"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Background grid */}
      <div className="absolute inset-0 bg-grid opacity-50" />

      {/* Gradient orbs */}
      <div className="gradient-orb gradient-orb-green absolute w-96 h-96 -top-20 -left-20" />
      <div className="gradient-orb gradient-orb-cyan absolute w-72 h-72 bottom-10 right-10" />

      {/* Radar */}
      <div className="relative mb-8">
        <RadarPulse size={180} />
      </div>

      {/* Logo text */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-center"
      >
        <h1 
          className="text-3xl font-bold mb-3 tracking-wider"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          <span className="text-gradient-green">SKY</span>
          <span className="text-white">RECON</span>
        </h1>

        {/* Loading bar */}
        <div className="w-48 h-1 rounded-full overflow-hidden bg-white/5 mx-auto mb-4">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-green-600 via-green-400 to-green-600"
            initial={{ x: '-100%' }}
            animate={{ x: '100%' }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            style={{ width: '60%' }}
          />
        </div>

        <motion.p
          className="text-sm text-[var(--text-muted)] font-mono"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          {message}
        </motion.p>
      </motion.div>
    </motion.div>
  )
}
