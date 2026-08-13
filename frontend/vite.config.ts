import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server proxies /api to FastAPI so the browser never needs CORS
// and the API key never leaves the backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
