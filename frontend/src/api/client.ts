import axios from 'axios';

// VITE_API_BASE_URL must be set in .env.production for all production builds.
// Local development falls back to '/api' (Vite dev proxy handles forwarding).
// In production, a missing VITE_API_BASE_URL causes an EXPLICIT ERROR so Render's
// build/runtime logs immediately show the misconfiguration — no silent /api fallback.
const _rawBase = import.meta.env.VITE_API_BASE_URL;
if (import.meta.env.PROD && !_rawBase) {
  throw new Error(
    '[FX SkillHub] VITE_API_BASE_URL is not set. ' +
    'Add it to frontend/.env.production before building for production. ' +
    'Expected value: https://fx-skillhub.onrender.com/api'
  );
}
const API_BASE_URL: string = (_rawBase ? _rawBase.replace(/\/+$/, '') : '') || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});


apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('fx_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('fx_token');
      localStorage.removeItem('fx_user');
    }
    return Promise.reject(error);
  }
);
