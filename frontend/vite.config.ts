import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Ensures SPA route entrypoints and fallback HTML exist in the build output.
 * Static hosting providers (Render, S3, Cloudflare) serve physical index.html
 * files on direct navigation without returning a 404.
 */
function spaFallbackPlugin() {
  return {
    name: 'spa-fallback-plugin',
    closeBundle() {
      const rootDir = path.dirname(fileURLToPath(import.meta.url));
      const distDir = path.join(rootDir, 'dist');
      const indexPath = path.join(distDir, 'index.html');

      if (!fs.existsSync(indexPath)) return;
      const htmlContent = fs.readFileSync(indexPath, 'utf8');

      // 1. Generate 404.html for static site 404-fallback
      fs.writeFileSync(path.join(distDir, '404.html'), htmlContent);

      // 2. Pre-generate physical directory routes so direct GET returns 200 OK
      const routes = [
        'auth/google/callback',
        'login',
        'register',
        'catalogue',
        'dashboard',
        'admin',
        'faculty',
        'activate-faculty'
      ];
      for (const r of routes) {
        const routeDir = path.join(distDir, r);
        fs.mkdirSync(routeDir, { recursive: true });
        fs.writeFileSync(path.join(routeDir, 'index.html'), htmlContent);
      }
    }
  };
}

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
      spaFallbackPlugin(),
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

