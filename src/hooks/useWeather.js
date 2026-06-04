import { useState, useEffect } from 'react'

// Drone flying safety thresholds
const LIMITS = {
  wind_speed:   10,   // m/s  — above this: unsafe
  visibility:   1000, // metres — below this: unsafe  (derived from cloud cover heuristic)
  precipitation: 0.5, // mm/h — above this: unsafe
  temperature:  { min: 0, max: 45 }, // °C
}

function evaluate(w) {
  const issues = []
  if (w.wind_speed > LIMITS.wind_speed)
    issues.push(`High winds ${w.wind_speed} m/s (limit ${LIMITS.wind_speed} m/s)`)
  if (w.precipitation > LIMITS.precipitation)
    issues.push(`Rain/precipitation ${w.precipitation} mm/h`)
  if (w.temperature < LIMITS.temperature.min)
    issues.push(`Too cold ${w.temperature}°C`)
  if (w.temperature > LIMITS.temperature.max)
    issues.push(`Too hot ${w.temperature}°C`)
  if (w.cloud_cover > 90)
    issues.push(`Heavy cloud cover ${w.cloud_cover}%`)
  return issues
}

export default function useWeather() {
  const [weather, setWeather]   = useState(null)
  const [issues, setIssues]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [location, setLocation] = useState(null)
  const [error, setError]       = useState(null)

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      pos => setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      ()  => {
        // fallback: NIT Rourkela coordinates
        setLocation({ lat: 22.2540, lon: 84.9027 })
      }
    )
  }, [])

  useEffect(() => {
    if (!location) return
    const { lat, lon } = location

    fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,wind_speed_10m,precipitation,cloud_cover,weather_code` +
      `&wind_speed_unit=ms&timezone=auto`
    )
      .then(r => r.json())
      .then(data => {
        const c = data.current
        const w = {
          temperature:  c.temperature_2m,
          wind_speed:   c.wind_speed_10m,
          precipitation: c.precipitation,
          cloud_cover:  c.cloud_cover,
          weather_code: c.weather_code,
        }
        setWeather(w)
        setIssues(evaluate(w))
        setLoading(false)
      })
      .catch(() => { setError('Weather unavailable'); setLoading(false) })
  }, [location])

  return { weather, issues, loading, error, safe: issues.length === 0 }
}
