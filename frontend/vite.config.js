import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API calls to the FastAPI backend during local development
      // so the frontend can just call fetch('/health').
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/debug': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/explain': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ask': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/history': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
