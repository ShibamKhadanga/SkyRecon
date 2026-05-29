import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring, useInView } from 'framer-motion'

export default function AnimatedCounter({ 
  value = 0, 
  duration = 2, 
  prefix = '', 
  suffix = '',
  className = '' 
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  const motionValue = useMotionValue(0)
  const springValue = useSpring(motionValue, { 
    damping: 40, 
    stiffness: 100,
    duration: duration * 1000
  })

  useEffect(() => {
    if (isInView) {
      motionValue.set(value)
    }
  }, [isInView, value, motionValue])

  useEffect(() => {
    const unsubscribe = springValue.on('change', (latest) => {
      if (ref.current) {
        const formatted = Math.floor(latest).toLocaleString()
        ref.current.textContent = `${prefix}${formatted}${suffix}`
      }
    })
    return unsubscribe
  }, [springValue, prefix, suffix])

  return (
    <motion.span
      ref={ref}
      className={`tabular-nums ${className}`}
      initial={{ opacity: 0, y: 10 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5 }}
    >
      {prefix}0{suffix}
    </motion.span>
  )
}
