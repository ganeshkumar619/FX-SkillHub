import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { Key, Lock, CheckCircle2, AlertCircle, Loader2, ShieldCheck, Mail, ArrowRight } from 'lucide-react';

interface InvitationDetails {
  valid: boolean;
  email: string;
  faculty_name: string;
  faculty_id: string;
  department?: string;
}

export const FacultyActivationPage: React.FC = () => {
  const { token: routeToken } = useParams<{ token?: string }>();
  const [searchParams] = useSearchParams();
  const token = routeToken || searchParams.get('token') || '';

  const navigate = useNavigate();
  const { login } = useAuth();

  const [verifying, setVerifying] = useState(true);
  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setVerifyError('No invitation token was provided in the link.');
      setVerifying(false);
      return;
    }

    const verifyToken = async () => {
      try {
        setVerifying(true);
        const res = await apiClient.get(`/auth/faculty/verify-invitation/?token=${encodeURIComponent(token)}`);
        setInvitation(res.data);
      } catch (err: any) {
        const msg =
          err?.response?.data?.error ||
          err?.response?.data?.detail ||
          'This invitation link is invalid or has expired.';
        setVerifyError(msg);
      } finally {
        setVerifying(false);
      }
    };

    verifyToken();
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    if (password.length < 8) {
      setSubmitError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== passwordConfirm) {
      setSubmitError('Passwords do not match. Please verify.');
      return;
    }

    try {
      setSubmitLoading(true);
      const res = await apiClient.post('/auth/faculty/activate/', {
        token,
        password,
        password_confirm: passwordConfirm,
      });

      setIsSuccess(true);
      if (res.data?.token && res.data?.user) {
        login(res.data.token, res.data.user);
      }

      setTimeout(() => {
        navigate('/faculty', { replace: true });
      }, 2500);
    } catch (err: any) {
      const resData = err?.response?.data;
      const errorMsg =
        (Array.isArray(resData?.password) && resData.password[0]) ||
        (Array.isArray(resData?.password_confirm) && resData.password_confirm[0]) ||
        (Array.isArray(resData?.token) && resData.token[0]) ||
        resData?.error ||
        resData?.detail ||
        'Failed to activate account. Please try again or contact administrator.';
      setSubmitError(errorMsg);
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="max-w-md w-full space-y-6 bg-white p-8 rounded-3xl shadow-xl border border-slate-200">
        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-900 text-accent-500 font-extrabold text-2xl shadow-lg mb-3">
            FX
          </div>
          <h2 className="text-2xl font-black text-primary-950 tracking-tight">
            Faculty Account Activation
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Francis Xavier Engineering College (Autonomous), Tirunelveli
          </p>
        </div>

        {/* Verifying Spinner */}
        {verifying && (
          <div className="text-center py-8 space-y-3">
            <Loader2 className="w-8 h-8 text-primary-900 animate-spin mx-auto" />
            <p className="text-xs text-slate-500 font-medium">Validating your invitation credentials...</p>
          </div>
        )}

        {/* Verification Error */}
        {!verifying && verifyError && (
          <div className="space-y-4">
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h3 className="text-xs font-bold text-rose-900">Activation Link Invalid or Expired</h3>
                <p className="text-xs text-rose-700 leading-relaxed">{verifyError}</p>
              </div>
            </div>
            <div className="text-center pt-2">
              <Link
                to="/login"
                className="inline-flex items-center justify-center px-5 py-2.5 rounded-xl bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold transition-all shadow-sm"
              >
                Go to Sign In
              </Link>
            </div>
          </div>
        )}

        {/* Success Screen */}
        {!verifying && !verifyError && isSuccess && (
          <div className="space-y-4 text-center py-4">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-inner border border-emerald-200">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Account Activated Successfully!</h3>
            <p className="text-xs text-slate-600">
              Your password has been securely configured. Redirecting you to the Faculty Studio...
            </p>
            <div className="pt-2">
              <Link
                to="/faculty"
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-primary-900 text-white text-xs font-bold hover:bg-primary-800 transition-colors"
              >
                <span>Enter Faculty Studio</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        )}

        {/* Password Setup Form */}
        {!verifying && !verifyError && !isSuccess && invitation && (
          <div className="space-y-5">
            {/* Faculty Info Card */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-500">
                <span className="font-semibold uppercase tracking-wider text-[10px]">Official Account</span>
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="font-bold text-slate-900 text-sm">{invitation.faculty_name}</div>
              <div className="flex items-center gap-1.5 text-slate-600 font-mono text-[11px]">
                <Mail className="w-3.5 h-3.5 text-slate-400" />
                <span>{invitation.email}</span>
              </div>
              {invitation.faculty_id && (
                <div className="text-slate-500 text-[11px]">
                  Faculty ID: <strong className="text-slate-700 font-mono">{invitation.faculty_id}</strong>
                  {invitation.department && ` • ${invitation.department}`}
                </div>
              )}
            </div>

            {submitError && (
              <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Create Password *
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  Confirm Password *
                </label>
                <div className="relative">
                  <Key className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    placeholder="Re-enter password"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:border-primary-900 text-xs"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitLoading}
                className="w-full py-2.5 px-4 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
              >
                {submitLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Activating Account...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 text-accent-400" />
                    <span>Activate Account &amp; Set Password</span>
                  </>
                )}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
