import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/

// Vite's dev proxy matches these keys as PATH PREFIXES, not exact paths.
// That collides with the app's own routes now that there are real pages
// at those same paths: '/debug' is a prefix of the '/debugger' page
// route, and '/history' *is* both the History page's route and the
// history-list API path. Without this guard, loading/refreshing
// /debugger or /history directly would get proxied straight to the
// FastAPI backend and come back as raw JSON (or a 404) instead of the
// SPA's index.html.
//
// A top-level browser navigation sends `Accept: text/html...`; the
// app's own fetch() calls to these same paths don't. bypass() lets an
// HTML-accepting request fall through to Vite's normal SPA handling
// (which serves index.html) instead of being proxied to the backend.
function bypassNavigations(req) {
  if (req.headers.accept && req.headers.accept.includes('text/html')) {
    return '/index.html'
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API calls to the FastAPI backend during local development
      // so the frontend can just call fetch('/health').
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: bypassNavigations,
      },
      '/debug': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: bypassNavigations,
      },
      '/explain': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: bypassNavigations,
      },
      '/ask': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: bypassNavigations,
      },
      '/history': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass: bypassNavigations,
      },
    },
  },
})
