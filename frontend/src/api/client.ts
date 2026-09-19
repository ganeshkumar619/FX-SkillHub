import axios from 'axios';

const PRODUCTION_API_URL = 'https://fx-skillhub.onrender.com/api';

const normalizeApiBaseUrl = (url: string): string => {
  let cleaned = url.trim().replace(/\/+$/, '');
  if (!cleaned.endsWith('/api')) {
    cleaned = `${cleaned}/api`;
  }
  return cleaned;
};

/**
 * Resolves the API Base URL with strict production rules:
 * 1. Production builds MUST NEVER use localhost, 127.0.0.1, or bare relative '/api'.
 * 2. Guarantees the /api suffix is present (preventing 404s if VITE_API_BASE_URL is set to origin only).
 * 3. If VITE_API_BASE_URL is unset, empty, or mistakenly contains localhost/127.0.0.1 in production,
 *    it strictly defaults to the deployed Render backend: https://fx-skillhub.onrender.com/api.
 * 4. Local development continues using '/api' (forwarded by Vite dev proxy) or custom dev URL.
 */
const resolveApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;

  if (import.meta.env.PROD) {
    if (envUrl && typeof envUrl === 'string') {
      const trimmed = envUrl.trim().replace(/\/+$/, '');
      if (!trimmed.includes('localhost') && !trimmed.includes('127.0.0.1') && trimmed.length > 0) {
        return normalizeApiBaseUrl(trimmed);
      }
    }
    return PRODUCTION_API_URL;
  }

  // Local development mode:
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return '/api';
};

export const API_BASE_URL: string = resolveApiBaseUrl();

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
