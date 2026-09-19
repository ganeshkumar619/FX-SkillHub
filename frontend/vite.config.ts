import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load .env / .env.local / .env.[mode] from the project root.
  // Using '' as prefix loads ALL variables (not just VITE_* prefixed ones)
  // so VITE_BACKEND_URL is available here at config-resolution time.
  const env = loadEnv(mode, process.cwd(), '')

  // Fallback keeps existing behaviour: proxy to local Django dev server.
  const backendTarget = env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

  // Safeguard: In production builds, never allow localhost or 127.0.0.1 for API base URL
  if (mode === 'production') {
    const rawApi = env.VITE_API_BASE_URL || process.env.VITE_API_BASE_URL;
    if (!rawApi || rawApi.includes('localhost') || rawApi.includes('127.0.0.1')) {
      process.env.VITE_API_BASE_URL = 'https://fx-skillhub.onrender.com/api';
    }
  }

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        }
      }
    }
  }
})

