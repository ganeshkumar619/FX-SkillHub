import React from 'react';
import { Shield, ExternalLink, MapPin, Award, CheckCircle } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-primary-950 text-slate-300 border-t-4 border-accent-500 pt-12 pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Institutional Overview */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-accent-500 text-primary-950 font-black flex items-center justify-center text-lg">
                FX
              </div>
              <span className="font-extrabold text-lg text-white">FX SkillHub</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Institutional AI-Powered Skill Learning, Secure Assessment and Digital Certification Platform for Francis Xavier Engineering College.
            </p>
            <div className="text-xs text-slate-400 flex items-start gap-2 pt-2">
              <MapPin className="w-4 h-4 text-accent-500 shrink-0 mt-0.5" />
              <span>103/G2, Bypass Road, Vannarpettai, Tirunelveli-627003, Tamil Nadu, India</span>
            </div>
          </div>

          {/* Institutional Approvals & Accreditations */}
          <div>
            <h4 className="text-white font-bold text-sm tracking-wide mb-3 flex items-center gap-2">
              <Award className="w-4 h-4 text-accent-500" />
              Official Recognition
            </h4>
            <ul className="text-xs space-y-2 text-slate-400">
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                Autonomous Institution (Conferred 2019)
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                Approved by AICTE, New Delhi
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                Affiliated to Anna University, Chennai
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                NBA Accredited (CSE, ECE, EEE, Mech)
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                UGC Recognized under 2(f) & 12(B)
              </li>
              <li className="flex items-center gap-1.5">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                MoE IIC 4-Star Innovation Rating
              </li>
            </ul>
          </div>

          {/* Quick Links with Provenance */}
          <div>
            <h4 className="text-white font-bold text-sm tracking-wide mb-3">Authoritative Sources</h4>
            <ul className="text-xs space-y-2 text-slate-400">
              <li>
                <a 
                  href="https://www.francisxavier.ac.in/" 
                  target="_blank" 
                  rel="noreferrer"
                  className="hover:text-accent-400 flex items-center gap-1 transition-colors"
                >
                  FXEC Official Portal <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a 
                  href="https://francisxavier.ac.in/centre/training?page=activities" 
                  target="_blank" 
                  rel="noreferrer"
                  className="hover:text-accent-400 flex items-center gap-1 transition-colors"
                >
                  Centre for Training & Skills Development <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a 
                  href="https://francisxavier.ac.in/nptel" 
                  target="_blank" 
                  rel="noreferrer"
                  className="hover:text-accent-400 flex items-center gap-1 transition-colors"
                >
                  NPTEL Local Chapter (Discipline 106) <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a 
                  href="https://www.francisxavier.ac.in/departments" 
                  target="_blank" 
                  rel="noreferrer"
                  className="hover:text-accent-400 flex items-center gap-1 transition-colors"
                >
                  Academic Departments & Labs <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Non-negotiable Real-Data Policy Banner */}
          <div className="bg-primary-900/60 p-4 rounded-lg border border-primary-800 space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-accent-400">
              <Shield className="w-4 h-4 text-accent-500" />
              Real Data Guarantee
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Every course, department, and institutional metric traces to official FXEC records. No synthetic student records are counted in production analytics.
            </p>
            <div className="text-[10px] text-slate-500 pt-1">
              Build: 2026.09-rc1 • Expo Ready
            </div>
          </div>
        </div>

        <div className="border-t border-primary-900 pt-6 text-center text-xs text-slate-500">
          © {new Date().getFullYear()} Francis Xavier Engineering College. All rights reserved. Managed by St. Xavier's Educational Trust.
        </div>
      </div>
    </footer>
  );
};
