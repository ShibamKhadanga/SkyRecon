import { motion } from 'framer-motion'

export default function GlassCard({ 
  children, 
  className = '', 
  hover = true, 
  glow = false,
  delay = 0,
  ...props 
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.175, 0.885, 0.32, 1.275] }}
      whileHover={hover ? { y: -4, scale: 1.01 } : {}}
      className={`glass-card p-6 ${glow ? 'animate-pulse-glow' : ''} ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  )
}
