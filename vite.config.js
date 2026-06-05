import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Backend API URL: use env var in production (set on Vercel/Netlify), fallback to localhost
const BACKEND_URL = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/uploads': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/screenshots': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/reports': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'map-vendor': ['leaflet', 'react-leaflet'],
          'chart-vendor': ['recharts'],
          'animation-vendor': ['framer-motion'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
})
