import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend port is env-controllable (dev server & preview). Default 5173.
const port = Number(process.env.FRONTEND_PORT) || 5173

// In dev, /api is proxied to the backend so the SPA and API share an origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port,
  },
})
