import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { 
  UserPlus, 
  AlertCircle, 
  Building2, 
  Calendar, 
  Mail, 
  Hash, 
  Lock, 
  User, 
  KeyRound, 
  RotateCw, 
  ArrowLeft,
  CheckCircle2
} from 'lucide-react';
import type { Department } from '../types';

type RegisterStep = 'FORM' | 'OTP';

export const Register: React.FC = () => {
  const [step, setStep] = useState<RegisterStep>('FORM');
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    register_number: '',
    department: '' as string | number,
    year: '1' as string | number,
  });

  const [registeredEmail, setRegisteredEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadingDepts, setLoadingDepts] = useState<boolean>(true);
  const [deptsError, setDeptsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState<number>(0);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Handle URL params for direct verification navigation: ?step=verify&email=...
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const stepParam = searchParams.get('step');
    const emailParam = searchParams.get('email');
    if (stepParam === 'verify' && emailParam) {
      setRegisteredEmail(emailParam.trim().toLowerCase());
      setStep('OTP');
      setSuccessMsg('Please enter the 6-digit code sent to your institutional mailbox.');
    }
  }, [location.search]);

  // Load departments with robust error handling and retry support
  const fetchDepts = async () => {
    setLoadingDepts(true);
    setDeptsError(null);
    try {
      const res = await apiClient.get('/catalogue/departments/');
      const depts: Department[] = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setDepartments(depts);
      if (depts.length > 0) {
        setFormData(prev => ({
          ...prev,
          department: prev.department ? prev.department : depts[0].id
        }));
      }
    } catch (err: any) {
      console.error('Failed to load departments', err);
      setDeptsError('Unable to load academic departments. Please check connection and retry.');
    } finally {
      setLoadingDepts(false);
    }
  };

  useEffect(() => {
    fetchDepts();
  }, []);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown(prev => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const validateFrontend = (): string | null => {
    const cleanEmail = formData.email.trim().toLowerCase();
    if (!cleanEmail) {
      return "Institutional email is required.";
    }

    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(cleanEmail)) {
      return "Please provide a valid email address.";
    }

    const domain = cleanEmail.split('@')[1];
    const externalDomains = ['gmail.com', 'yahoo.com', 'outlook.com', 'protonmail.com', 'hotmail.com', 'icloud.com'];
    if (externalDomains.includes(domain)) {
      return `External email providers (@${domain}) are strictly forbidden. Student registration requires your institutional email ending in @francisxavier.ac.in.`;
    }

    if (domain !== 'francisxavier.ac.in' && domain !== 'fxec.ac.in') {
      return "Registration requires an institutional email ending with @francisxavier.ac.in.";
    }

    if (!formData.register_number.trim()) {
      return "Official Roll / Register Number is required.";
    }

    if (!formData.department) {
      return "Please select your academic department.";
    }

    if (formData.password.length < 8) {
      return "Password must be at least 8 characters.";
    }

    return null;
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const clientError = validateFrontend();
    if (clientError) {
      setError(clientError);
      return;
    }

    setLoading(true);

    try {
      const cleanEmail = formData.email.trim().toLowerCase();
      const payload = {
        ...formData,
        email: cleanEmail,
        register_number: formData.register_number.trim().toUpperCase(),
        department: Number(formData.department),
        year: Number(formData.year)
      };

      const res = await apiClient.post('/auth/register/', payload);
      
      // Successfully initiated registration with OTP dispatch
      setRegisteredEmail(cleanEmail);
      setStep('OTP');
      setCooldown(60); // 60s cooldown before resend
      setSuccessMsg(res.data.message || `A verification code was dispatched to ${cleanEmail}`);
    } catch (err: any) {
      const errData = err.response?.data;
      if (errData && typeof errData === 'object') {
        const firstKey = Object.keys(errData)[0];
        const val = errData[firstKey];
        const msg = Array.isArray(val) ? val[0] : (typeof val === 'string' ? val : JSON.stringify(val));
        setError(firstKey === 'non_field_errors' ? msg : `${firstKey.replace('_', ' ').toUpperCase()}: ${msg}`);
      } else {
        setError(err.response?.data?.error || 'Registration failed. Please check your inputs.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const cleanOtp = otpCode.trim();
    if (!cleanOtp || cleanOtp.length !== 6 || !/^\d+$/.test(cleanOtp)) {
      setError('Please enter the valid 6-digit verification code.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiClient.post('/auth/verify-otp/', {
        email: registeredEmail,
        otp: cleanOtp
      });

      // Verification successful: Account activated and JWT issued
      login(res.data.token, res.data.user);
      navigate('/dashboard');
    } catch (err: any) {
      const errMsg = err.response?.data?.error || err.response?.data?.otp?.[0] || 'Verification failed. Please check the code.';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    if (cooldown > 0 || resending) return;

    setError(null);
    setSuccessMsg(null);
    setResending(true);

    try {
      const res = await apiClient.post('/auth/resend-otp/', {
        email: registeredEmail
      });
      setCooldown(60);
      setSuccessMsg(res.data.message || 'A fresh verification code has been dispatched.');
    } catch (err: any) {
      const errMsg = err.response?.data?.error || 'Failed to resend verification code. Please try again.';
      setError(errMsg);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-slate-50">
      <div className="max-w-lg w-full space-y-6 bg-white p-8 rounded-2xl shadow-xl border border-slate-200">
        
        {/* Institutional Branding Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-900 text-accent-500 font-extrabold text-2xl shadow-lg mb-3">
            FX
          </div>
          <h2 className="text-2xl font-bold text-primary-950 tracking-tight">
            {step === 'FORM' ? 'Student Registration' : 'Institutional Email Verification'}
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Francis Xavier Engineering College (Autonomous), Tirunelveli
          </p>
        </div>

        {/* Feedback Alerts */}
        {error && (
          <div className="p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
            <span className="leading-relaxed">{successMsg}</span>
          </div>
        )}

        {/* STEP 1: REGISTRATION FORM */}
        {step === 'FORM' && (
          <form className="mt-4 space-y-4" onSubmit={handleRegisterSubmit}>
            {/* Name Row */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  required
                  name="first_name"
                  placeholder="e.g. Ananya"
                  value={formData.first_name}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  required
                  name="last_name"
                  placeholder="e.g. Krishnan"
                  value={formData.last_name}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                />
              </div>
            </div>

            {/* Roll / Register Number & Year */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Hash className="w-3 h-3 text-slate-500" />
                  Register / Roll Number
                </label>
                <input
                  type="text"
                  required
                  name="register_number"
                  placeholder="e.g. 950722104001"
                  value={formData.register_number}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 uppercase font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-500" />
                  Academic Year
                </label>
                <select
                  name="year"
                  value={formData.year}
                  onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 bg-white"
                >
                  <option value="1">1st Year (Freshman)</option>
                  <option value="2">2nd Year (Sophomore)</option>
                  <option value="3">3rd Year (Junior)</option>
                  <option value="4">4th Year (Senior)</option>
                </select>
              </div>
            </div>

            {/* Department */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-slate-500" />
                  Department <span className="text-red-500">*</span>
                </label>
                {deptsError && (
                  <button
                    type="button"
                    onClick={fetchDepts}
                    className="text-xs text-primary-600 hover:text-primary-700 font-medium underline flex items-center gap-1"
                  >
                    <RotateCw className="w-3 h-3" /> Retry
                  </button>
                )}
              </div>
              <select
                name="department"
                required
                disabled={loadingDepts || departments.length === 0}
                value={formData.department}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600 bg-white disabled:bg-slate-100 disabled:text-slate-400"
              >
                {loadingDepts ? (
                  <option value="">Loading departments...</option>
                ) : deptsError ? (
                  <option value="">Failed to load departments — click Retry above</option>
                ) : departments.length === 0 ? (
                  <option value="">No departments available</option>
                ) : (
                  <>
                    <option value="">Select your department</option>
                    {departments.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.code} - {d.name}
                      </option>
                    ))}
                  </>
                )}
              </select>
              {deptsError && (
                <p className="mt-1 text-xs text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3 flex-shrink-0" />
                  {deptsError}
                </p>
              )}
            </div>

            {/* Institutional Email */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Mail className="w-3 h-3 text-slate-500" />
                Institutional Student Email
              </label>
              <input
                type="email"
                required
                name="email"
                placeholder="studentname@francisxavier.ac.in"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
            </div>

            {/* Username (Optional / Default) */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                <User className="w-3 h-3 text-slate-500" />
                Username <span className="text-[10px] text-slate-400 font-normal lowercase">(optional)</span>
              </label>
              <input
                type="text"
                name="username"
                placeholder="Leave blank to auto-generate from Roll No"
                value={formData.username}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Lock className="w-3 h-3 text-slate-500" />
                Password
              </label>
              <input
                type="password"
                required
                name="password"
                minLength={8}
                placeholder="Minimum 8 characters"
                value={formData.password}
                onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {loading ? 'Validating Institutional Credentials...' : (
                <>
                  <UserPlus className="w-4 h-4 text-accent-400" />
                  Proceed to Institutional Email Verification
                </>
              )}
            </button>
          </form>
        )}

        {/* STEP 2: OTP VERIFICATION */}
        {step === 'OTP' && (
          <div className="mt-4 space-y-5">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-primary-100 text-primary-800 flex items-center justify-center mx-auto mb-1">
                <Mail className="w-5 h-5" />
              </div>
              <p className="text-xs text-slate-600">
                A 6-digit verification code has been dispatched to:
              </p>
              <p className="text-sm font-bold text-primary-950 font-mono bg-white py-1 px-3 rounded-lg border border-slate-200 inline-block">
                {registeredEmail}
              </p>
              <p className="text-[11px] text-slate-500">
                Please check your official mailbox (including Spam/Updates). The code is valid for <strong>10 minutes</strong>.
              </p>
            </div>

            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <div className="relative flex justify-center">
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    autoFocus
                    required
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    placeholder="••••••"
                    className="w-64 text-center tracking-[0.5em] text-2xl font-mono py-2.5 px-4 rounded-xl border-2 border-primary-600 focus:outline-none focus:ring-4 focus:ring-primary-100 font-bold text-slate-900 bg-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || otpCode.length !== 6}
                className="w-full py-3 px-4 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer"
              >
                {loading ? 'Verifying OTP...' : (
                  <>
                    <KeyRound className="w-4 h-4 text-accent-400" />
                    Verify & Activate Account
                  </>
                )}
              </button>
            </form>

            {/* Resend & Back Action Row */}
            <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
              <button
                type="button"
                onClick={() => {
                  setStep('FORM');
                  setError(null);
                  setSuccessMsg(null);
                }}
                className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900 cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Change Details
              </button>

              <button
                type="button"
                onClick={handleResendOTP}
                disabled={cooldown > 0 || resending}
                className="inline-flex items-center gap-1 font-semibold text-primary-700 hover:text-primary-900 disabled:text-slate-400 disabled:cursor-not-allowed cursor-pointer"
              >
                <RotateCw className={`w-3.5 h-3.5 ${resending ? 'animate-spin' : ''}`} />
                {cooldown > 0 ? `Resend Code in ${cooldown}s` : 'Resend Verification Code'}
              </button>
            </div>
          </div>
        )}

        <div className="text-center pt-2">
          <span className="text-xs text-slate-500">
            Already verified?{' '}
            <Link to="/login" className="font-semibold text-primary-700 hover:text-primary-900 underline">
              Sign In to FX SkillHub
            </Link>
          </span>
        </div>
      </div>
    </div>
  );
};
