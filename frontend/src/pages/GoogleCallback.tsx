import React, { useEffect, useState } from 'react';
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

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get('code');
      const googleError = searchParams.get('error');

      if (googleError) {
        setError(`Google authentication was cancelled or rejected: ${googleError}`);
        return;
      }

      if (!code) {
        setError('No authorization code was received from Google.');
        return;
      }

      try {
        setStatusText('Exchanging authorization code with FX SkillHub...');
        const redirectUri = window.location.origin + '/auth/google/callback';
        const res = await apiClient.post('/auth/google/callback/', {
          code,
          redirect_uri: redirectUri,
        });

        login(res.data.token, res.data.user);
        setStatusText('Authentication successful! Redirecting...');

        setTimeout(() => {
          if (res.data.user.role === 'ADMIN') {
            navigate('/admin', { replace: true });
          } else if (res.data.user.role === 'MENTOR') {
            navigate('/mentor', { replace: true });
          } else {
            navigate('/dashboard', { replace: true });
          }
        }, 800);
      } catch (err: any) {
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
