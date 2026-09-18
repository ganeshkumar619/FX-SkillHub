import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Award, 
  ShieldCheck, 
  CheckCircle2, 
  ArrowRight, 
  BookOpen, 
  Cpu, 
  Layers,
  GraduationCap,
  Check
} from 'lucide-react';

export const Home: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* 1. Dignified Institutional Hero Section */}
      <section className="bg-gradient-to-b from-[#0a2140] to-primary-900 text-white py-14 lg:py-20 border-b-4 border-accent-500 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            
            {/* Left Column: Official College Portal Info */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary-800/90 border border-primary-700 text-xs font-semibold text-accent-400">
                <GraduationCap className="w-4 h-4 text-accent-500" />
                Autonomous Institution • Affiliated to Anna University • Conferred 2019
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight leading-tight text-white">
                Official Student Skill Learning & <span className="text-accent-400">Certification Portal</span>
              </h1>

              <p className="text-base text-slate-200 leading-relaxed max-w-2xl font-normal">
                Welcome to <strong className="text-white">FX SkillHub</strong> — the institutional academic learning platform of <strong className="text-white">Francis Xavier Engineering College</strong>. Complete department-approved modular syllabi, build practical engineering competencies through interactive study notes, and achieve verified digital credentials.
              </p>

              <div className="flex flex-wrap gap-4 pt-1">
                <Link
                  to="/catalogue"
                  className="px-6 py-3.5 rounded-xl bg-accent-500 hover:bg-accent-400 text-primary-950 font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center gap-2"
                >
                  <BookOpen className="w-4 h-4 text-primary-950" />
                  Explore Skill Catalogue
                  <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/dashboard"
                  className="px-6 py-3.5 rounded-xl bg-primary-800 hover:bg-primary-700 text-white font-semibold text-sm border border-primary-700 transition-all flex items-center gap-2 shadow-xs"
                >
                  <GraduationCap className="w-4 h-4 text-accent-400" />
                  Student Learning Portal
                </Link>
              </div>

              {/* Institutional Accreditations Bar */}
              <div className="pt-6 border-t border-primary-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-slate-300 font-medium">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent-400 shrink-0" />
                  <span>AICTE Approved</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent-400 shrink-0" />
                  <span>Anna University Affiliated</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent-400 shrink-0" />
                  <span>NBA Accredited</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-accent-400 shrink-0" />
                  <span>MoE 4-Star IIC</span>
                </div>
              </div>
            </div>

            {/* Right Column: Authentic Academic Institution Profile Card */}
            <div className="lg:col-span-5">
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xl text-slate-900 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 pb-3.5">
                  <div>
                    <h3 className="font-bold text-base text-primary-950">Francis Xavier Engineering College</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Autonomous Institution • Estd. 2000</p>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Verified
                  </span>
                </div>

                <div className="space-y-2.5 text-xs text-slate-700">
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Affiliation:</span>
                    <span className="font-semibold text-slate-900">Anna University, Chennai</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">UGC Recognition:</span>
                    <span className="font-semibold text-slate-900">Section 2(f) & 12(B)</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Accreditation:</span>
                    <span className="font-semibold text-slate-900">NBA Accredited & NAAC</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Industry Survey:</span>
                    <span className="font-semibold text-slate-900">AICTE-CII Platinum Rating</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Support Status:</span>
                    <span className="font-semibold text-slate-900">DST-FIST Supported</span>
                  </div>
                  <div className="flex justify-between items-center py-1">
                    <span className="text-slate-500 font-medium">Campus Location:</span>
                    <span className="font-semibold text-slate-900 text-right">Vannarpettai, Tirunelveli-627003</span>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Official curriculum modules and proctored assessment standards administered by the <strong>Centre for Training & Skills Development (CTSD)</strong>.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Training Pillars Section (From Centre for Training & Skills Development) */}
      <section className="py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <span className="text-xs font-bold uppercase tracking-wider text-primary-900 bg-primary-100 px-3 py-1 rounded-full">
            FXEC Training & Skills Framework
          </span>
          <h2 className="text-3xl font-extrabold text-primary-950 mt-3 tracking-tight">
            Institutional Skill Learning Pillars
          </h2>
          <p className="text-sm text-slate-600 mt-2">
            Structured in accordance with the Centre for Training & Skills Development at FXEC to ensure job fit and technical excellence.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-800 flex items-center justify-center mb-4">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Foundation Courses</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Introduces first-year engineering students to fundamental engineering areas through rigorous practice to build core computational and algorithmic reasoning.
            </p>
            <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-primary-700">
              Source: FXEC TSD Framework
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center mb-4">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Mandatory Skills</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Core competencies essential for every engineering student to be job-fit in core industries and top IT enterprises, including clean coding and software engineering.
            </p>
            <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-primary-700">
              Source: FXEC TSD Framework
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center mb-4">
              <Award className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Placement Fit Training</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Equips students with technical interview problem solving, aptitude mastery, and holistic life skills to achieve high-tier placements in visiting campus recruiters.
            </p>
            <div className="mt-4 pt-3 border-t border-slate-100 text-xs font-semibold text-primary-700">
              Source: FXEC TSD Framework
            </div>
          </div>
        </div>
      </section>

      {/* Academic Engineering Departments & Tracks */}
      <section className="py-12 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h3 className="text-xl font-extrabold text-primary-950">Engineering Disciplines & Curricula</h3>
            <p className="text-xs text-slate-500 mt-1">Autonomous skill courses mapped to accredited engineering departments</p>
          </div>
          <Link
            to="/catalogue"
            className="text-xs font-bold text-primary-900 hover:text-primary-700 flex items-center gap-1"
          >
            <span>View All Department Courses</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { code: 'CSE', name: 'Computer Science & Engineering' },
            { code: 'IT', name: 'Information Technology' },
            { code: 'ECE', name: 'Electronics & Communication' },
            { code: 'EEE', name: 'Electrical & Electronics' },
            { code: 'MECH', name: 'Mechanical Engineering' },
            { code: 'AI&DS', name: 'AI & Data Science / Civil' },
          ].map((dept) => (
            <div
              key={dept.code}
              className="p-4 rounded-xl bg-white border border-slate-200 text-center space-y-1 shadow-xs hover:border-primary-900 hover:shadow-sm transition"
            >
              <div className="text-sm font-black text-primary-900">{dept.code}</div>
              <div className="text-[11px] text-slate-600 font-medium leading-tight">{dept.name}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Institutional Mission & Quality Policy */}
      <section className="bg-white py-14 border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-4">
              <h3 className="text-xl font-bold text-primary-950 flex items-center gap-2">
                <GraduationCap className="w-6 h-6 text-accent-600" />
                Institutional Vision
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
                "To be a globally recognized centre of transformative education that nurtures ethical professionals and innovative problem-solvers for sustainable societal development."
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-xl font-bold text-primary-950 flex items-center gap-2">
                <ShieldCheck className="w-6 h-6 text-accent-600" />
                Institutional Mission
              </h3>
              <div className="space-y-2 text-xs text-slate-700">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <strong>M1. Education & Teaching Quality:</strong> High-quality, learner-centric, industry-relevant education through transformative teaching-learning.
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <strong>M2. Research, Innovation & Sustainability:</strong> Fostering innovative problem-solvers contributing to sustainable societal development.
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                  <strong>M3. Ethics, Leadership & Social Responsibility:</strong> Cultivating ethical values and social responsibility through community engagement.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
