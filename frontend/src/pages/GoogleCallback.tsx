import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { AlertCircle, Loader2 } from 'lucide-react';

export const GoogleCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();

  const [statusText, setStatusText] = useState('Verifying Google credentials...');
  const [error, setError] = useState<string | null>(null);

  const processedRef = useRef(false);
  const completedRef = useRef(false);

  const redirectByRole = (role?: string) => {
    if (role === 'ADMIN') {
      navigate('/admin', { replace: true });
    } else if (role === 'FACULTY' || role === 'MENTOR') {
      navigate('/faculty', { replace: true });
    } else {
      navigate('/dashboard', { replace: true });
    }
  };

  useEffect(() => {
    // Prevent duplicate processing in React StrictMode or subsequent renders
    if (processedRef.current || completedRef.current) {
      return;
    }

    const code = searchParams.get('code');
    const googleError = searchParams.get('error');

    if (googleError) {
      setError(`Google authentication was cancelled or rejected: ${googleError}`);
      return;
    }

    if (!code) {
      // If user is already authenticated in this session, smoothly redirect
      const existingToken = localStorage.getItem('fx_token');
      const savedUserStr = localStorage.getItem('fx_user');
      if (existingToken && savedUserStr) {
        try {
          const parsed = JSON.parse(savedUserStr);
          redirectByRole(parsed.role);
          return;
        } catch {
          // ignore parsing error
        }
      }
      setError('No authorization code was received from Google.');
      return;
    }

    processedRef.current = true;

    const processCallback = async () => {
      try {
        setStatusText('Exchanging authorization code with FX SkillHub...');
        const redirectUri = window.location.origin + '/auth/google/callback';
        const res = await apiClient.post('/auth/google/callback/', {
          code,
          redirect_uri: redirectUri,
        });

        completedRef.current = true;
        login(res.data.token, res.data.user);
        setStatusText('Authentication successful! Redirecting...');

        // Smooth immediate navigation based on institutional role
        redirectByRole(res.data.user?.role);
      } catch (err: any) {
        // If authentication already completed or token already saved in local storage, do not display false-positive error
        if (completedRef.current || localStorage.getItem('fx_token')) {
          const savedUserStr = localStorage.getItem('fx_user');
          if (savedUserStr) {
            try {
              const parsed = JSON.parse(savedUserStr);
              redirectByRole(parsed.role);
              return;
            } catch {
              // ignore parsing error
            }
          }
          return;
        }
        setError(err.response?.data?.error || 'Failed to complete Google Sign-In.');
      }
    };

    processCallback();
  }, [searchParams, login, navigate]);

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-xl border border-slate-200 text-center space-y-4">
        {error ? (
          <>
            <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-slate-800">Google Sign-In Failed</h2>
            <p className="text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">
              {error}
            </p>
            <div className="pt-2">
              <Link
                to="/login"
                className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary-900 text-white text-xs font-semibold hover:bg-primary-800 transition-colors"
              >
                Back to Sign In
              </Link>
            </div>
          </>
        ) : (
          <>
            <div className="w-12 h-12 rounded-full bg-primary-50 text-primary-900 flex items-center justify-center mx-auto animate-pulse">
              <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">Completing Sign-In</h2>
            <p className="text-xs text-slate-500">{statusText}</p>
          </>
        )}
      </div>
    </div>
  );
};
