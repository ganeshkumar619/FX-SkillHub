import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { User, LogIn, AlertCircle, UserCheck, ShieldAlert } from 'lucide-react';

export const Login: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<'STUDENT' | 'FACULTY' | 'ADMIN'>('STUDENT');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await apiClient.post('/auth/login/', {
        username: username.trim(),
        password,
        role: selectedRole
      });
      login(res.data.token, res.data.user);
      
      if (res.data.user.role === 'ADMIN') {
        navigate('/admin');
      } else if (res.data.user.role === 'FACULTY' || res.data.user.role === 'MENTOR') {
        navigate('/faculty');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      const resData = err.response?.data;
      const errorMsg =
        (Array.isArray(resData?.non_field_errors) && resData.non_field_errors[0]) ||
        (Array.isArray(resData?.username) && resData.username[0]) ||
        (Array.isArray(resData?.role) && resData.role[0]) ||
        (typeof resData === 'string' && resData) ||
        resData?.detail ||
        resData?.error ||
        'Authentication failed. Please verify credentials.';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError(null);
    setGoogleLoading(true);
    try {
      const res = await apiClient.get('/auth/google/url/');
      if (res.data?.auth_url) {
        window.location.href = res.data.auth_url;
      } else {
        setError('Google Sign-In is awaiting GOOGLE_OAUTH_CLIENT_ID configuration in backend/.env');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Unable to initiate Google Sign-In at this time.');
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleRoleSelect = (role: 'STUDENT' | 'FACULTY' | 'ADMIN') => {
    setSelectedRole(role);
    setError(null);
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="max-w-md w-full space-y-6 bg-white p-8 rounded-2xl shadow-xl border border-slate-200">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-900 text-accent-500 font-extrabold text-2xl shadow-lg mb-3">
            FX
          </div>
          <h2 className="text-2xl font-bold text-primary-950 tracking-tight">
            Sign In to FX SkillHub
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Francis Xavier Engineering College (Autonomous), Tirunelveli
          </p>
        </div>

        {/* Role Selection Buttons */}
        <div className="space-y-1.5">
          <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider text-center">
            Select Portal
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => handleRoleSelect('STUDENT')}
              className={`px-3 py-2.5 rounded-xl text-xs font-bold flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                selectedRole === 'STUDENT'
                  ? 'bg-blue-900 text-white shadow-md ring-2 ring-blue-600 ring-offset-1'
                  : 'bg-slate-100 hover:bg-slate-200/80 text-slate-700 border border-slate-200'
              }`}
            >
              <User className={`w-4 h-4 ${selectedRole === 'STUDENT' ? 'text-blue-300' : 'text-blue-600'}`} />
              <span>Student</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleSelect('FACULTY')}
              className={`px-3 py-2.5 rounded-xl text-xs font-bold flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                selectedRole === 'FACULTY'
                  ? 'bg-emerald-900 text-white shadow-md ring-2 ring-emerald-600 ring-offset-1'
                  : 'bg-slate-100 hover:bg-slate-200/80 text-slate-700 border border-slate-200'
              }`}
            >
              <UserCheck className={`w-4 h-4 ${selectedRole === 'FACULTY' ? 'text-emerald-300' : 'text-emerald-600'}`} />
              <span>Faculty</span>
            </button>

            <button
              type="button"
              onClick={() => handleRoleSelect('ADMIN')}
              className={`px-3 py-2.5 rounded-xl text-xs font-bold flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                selectedRole === 'ADMIN'
                  ? 'bg-purple-900 text-white shadow-md ring-2 ring-purple-600 ring-offset-1'
                  : 'bg-slate-100 hover:bg-slate-200/80 text-slate-700 border border-slate-200'
              }`}
            >
              <ShieldAlert className={`w-4 h-4 ${selectedRole === 'ADMIN' ? 'text-purple-300' : 'text-purple-600'}`} />
              <span>Admin</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="font-medium">{error}</span>
            </div>
            {error.includes("verify your institutional email") && (
              <div className="mt-1 pt-2 border-t border-red-200 flex items-center justify-between">
                <span className="text-[11px] text-red-600">Have an unverified account?</span>
                <Link
                  to={`/register?step=verify&email=${encodeURIComponent(username.includes('@') ? username : '')}`}
                  className="px-2.5 py-1 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg text-[11px] transition-colors"
                >
                  Verify OTP Code &rarr;
                </Link>
              </div>
            )}
          </div>
        )}

        <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              {selectedRole === 'FACULTY'
                ? 'Official Faculty Email'
                : selectedRole === 'STUDENT'
                ? 'Student Email / Username'
                : 'Admin Email / Username'}
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent transition-all"
              placeholder={
                selectedRole === 'STUDENT'
                  ? 'Enter student email or username'
                  : selectedRole === 'FACULTY'
                  ? 'Enter official faculty email'
                  : 'Enter admin email or username'
              }
              autoComplete="username"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent transition-all"
              placeholder="••••••••••••"
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-lg bg-primary-900 hover:bg-primary-800 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
          >
            {loading ? 'Authenticating...' : (
              <>
                <LogIn className="w-4 h-4 text-accent-400" />
                Sign In
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-3">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-2 text-slate-400 font-semibold tracking-wider">Or continue with</span>
          </div>
        </div>

        {/* Continue with Google Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={googleLoading}
          className="w-full py-2.5 px-4 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 hover:border-slate-400 text-slate-700 font-semibold text-sm shadow-sm transition-all flex items-center justify-center gap-3 disabled:opacity-60 cursor-pointer"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>{googleLoading ? 'Connecting to Google...' : 'Continue with Google'}</span>
        </button>

        <div className="text-center pt-2">
          <span className="text-xs text-slate-500">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-primary-700 hover:text-primary-900 underline">
              Register as Student
            </Link>
          </span>
        </div>
      </div>
    </div>
  );
};
