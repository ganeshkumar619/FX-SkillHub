import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { HealthBadge } from './HealthBadge';
import { 
  BookOpen, 
  ShieldAlert, 
  UserCheck, 
  LogOut, 
  Menu, 
  X,
  Compass,
  Sparkles
} from 'lucide-react';
import { AICourseGeneratorModal } from './AICourseGeneratorModal';

export const Navbar: React.FC = () => {
  const { user, logout, isStudent, isFaculty, isMentor, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isAiStudioOpen, setIsAiStudioOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-primary-900 text-white shadow-md border-b-2 border-accent-500">
      {/* Top Institutional Banner */}
      <div className="bg-primary-950/80 px-4 py-1 text-xs border-b border-primary-800/60 hidden md:block">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-slate-300">
          <div className="flex items-center gap-3">
            <span>Francis Xavier Engineering College (Autonomous)</span>
            <span className="text-accent-500">•</span>
            <span>AICTE Approved & Anna University Affiliated</span>
            <span className="text-accent-500">•</span>
            <span>NBA Accredited (CSE, ECE, EEE, MECH)</span>
          </div>
          <div className="flex items-center gap-4">
            <HealthBadge />
            <span className="text-slate-400">Tirunelveli, Tamil Nadu</span>
          </div>
        </div>
      </div>

      {/* Main Nav */}
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Name */}
          <Link to="/" className="flex items-center gap-3 group">
            <img 
              src="/fxec_crest.png" 
              alt="FXEC Crest" 
              className="w-10 h-10 rounded-full object-contain bg-white p-0.5 shadow-md group-hover:scale-105 transition-transform" 
            />
            <div>
              <div className="font-extrabold text-lg tracking-tight flex items-center gap-1.5 text-white">
                FX SkillHub
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-accent-500 text-primary-950">
                  Institutional
                </span>
              </div>
              <p className="text-[11px] text-slate-300 hidden sm:block">Francis Xavier Engineering College</p>
            </div>
          </Link>

          {/* Desktop Nav Links */}
          <div className="hidden md:flex items-center gap-6">
            <Link 
              to="/catalogue" 
              className="flex items-center gap-1.5 text-sm font-medium text-slate-200 hover:text-accent-400 transition-colors"
            >
              <Compass className="w-4 h-4 text-accent-500" />
              Skill Catalogue
            </Link>

            {/* AI Studio Action - Only accessible to Faculty Mentors & Administrators */}
            {user && (isFaculty || isMentor || isAdmin) && (
              <button
                onClick={() => setIsAiStudioOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-accent-500 to-amber-400 text-slate-950 font-bold text-xs shadow hover:brightness-105 transition-all cursor-pointer"
                title="Autonomous AI Skill & Course Studio"
              >
                <Sparkles className="w-3.5 h-3.5 text-slate-950" />
                AI Studio
                <span className="text-[9px] uppercase tracking-wider bg-slate-950/15 px-1 py-0.5 rounded font-black">
                  AUTO
                </span>
              </button>
            )}

            {user && (
              <>
                {isStudent && (
                  <Link 
                    to="/dashboard" 
                    className="flex items-center gap-1.5 text-sm font-medium text-slate-200 hover:text-accent-400 transition-colors"
                  >
                    <BookOpen className="w-4 h-4 text-accent-500" />
                    My Learning
                  </Link>
                )}

                {(isFaculty || isMentor) && (
                  <Link 
                    to="/faculty" 
                    className="flex items-center gap-1.5 text-sm font-medium text-slate-200 hover:text-accent-400 transition-colors"
                  >
                    <UserCheck className="w-4 h-4 text-accent-500" />
                    Faculty Studio
                  </Link>
                )}

                {isAdmin && (
                  <Link 
                    to="/admin" 
                    className="flex items-center gap-1.5 text-sm font-medium text-slate-200 hover:text-accent-400 transition-colors"
                  >
                    <ShieldAlert className="w-4 h-4 text-accent-500" />
                    Admin Portal
                  </Link>
                )}
              </>
            )}
          </div>

          {/* User Auth Section */}
          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-sm font-semibold text-white leading-tight">
                    {user.first_name || user.username}
                  </div>
                  <span className="inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-primary-800 text-accent-400 border border-primary-700">
                    {user.role} {user.is_demo && '(DEMO)'}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg bg-primary-800 hover:bg-red-900/40 text-slate-300 hover:text-red-400 border border-primary-700 transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-4 py-2 text-sm font-semibold text-white hover:text-accent-400 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-accent-500 hover:bg-accent-400 text-primary-950 transition-colors shadow-sm"
                >
                  Register
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu toggle */}
          <div className="md:hidden flex items-center gap-2">
            <HealthBadge />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-primary-800 space-y-3">
            <Link
              to="/catalogue"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded text-base font-medium text-slate-200 hover:bg-primary-800"
            >
              Skill Catalogue
            </Link>

            {user && (isFaculty || isMentor || isAdmin) && (
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setIsAiStudioOpen(true);
                }}
                className="w-full text-left px-3 py-2 rounded text-base font-bold text-accent-400 hover:bg-primary-800 flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-accent-400" />
                Autonomous AI Studio
              </button>
            )}

            {user ? (
              <>
                {isStudent && (
                  <Link
                    to="/dashboard"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 rounded text-base font-medium text-slate-200 hover:bg-primary-800"
                  >
                    My Learning
                  </Link>
                )}
                {(isFaculty || isMentor) && (
                  <Link
                    to="/faculty"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 rounded text-base font-medium text-slate-200 hover:bg-primary-800"
                  >
                    Faculty Studio
                  </Link>
                )}
                {isAdmin && (
                  <Link
                    to="/admin"
                    onClick={() => setMobileMenuOpen(false)}
                    className="block px-3 py-2 rounded text-base font-medium text-slate-200 hover:bg-primary-800"
                  >
                    Admin Portal
                  </Link>
                )}
                <div className="pt-3 border-t border-primary-800 flex justify-between items-center px-3">
                  <div>
                    <div className="font-semibold text-white">{user.username}</div>
                    <div className="text-xs text-accent-400">{user.role} {user.is_demo && '(DEMO)'}</div>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-3 py-1.5 text-xs font-semibold bg-red-900/60 text-red-300 rounded border border-red-700"
                  >
                    Sign Out
                  </button>
                </div>
              </>
            ) : (
              <div className="pt-3 border-t border-primary-800 grid grid-cols-2 gap-2 px-3">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-center py-2 text-sm font-semibold rounded bg-primary-800 text-white"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-center py-2 text-sm font-semibold rounded bg-accent-500 text-primary-950"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        )}
      </nav>

      {/* Global AI Course Generator Modal - Only for Mentors & Administrators */}
      {user && (isMentor || isAdmin) && (
        <AICourseGeneratorModal
          isOpen={isAiStudioOpen}
          onClose={() => setIsAiStudioOpen(false)}
          onSuccess={(result) => {
            navigate(`/course/${result.slug}`);
          }}
        />
      )}
    </header>
  );
};
