import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Course, Module } from '../types';
import {
  BookOpen,
  CheckCircle2,
  Clock,
  ArrowRight,
  Award,
  Lock,
  FileText,
  ChevronDown,
  ChevronUp,
  Search,
  BrainCircuit
} from 'lucide-react';

export const CourseViewer: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();

  const [course, setCourse] = useState<Course | null>(null);
  const [progressData, setProgressData] = useState<any>(null);
  const [finalAssessment, setFinalAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedModuleIds, setExpandedModuleIds] = useState<Record<number, boolean>>({});

  const fetchCourseData = async () => {
    try {
      setLoading(true);
      const cRes = await apiClient.get<Course>(`/catalogue/courses/${slug}/`);
      setCourse(cRes.data);

      const [pRes, aRes] = await Promise.allSettled([
        apiClient.get(`/learning/course-progress/${slug}/`),
        apiClient.get(`/assessments/course/${cRes.data.id}/final-assessment/`)
      ]);

      if (pRes.status === 'fulfilled') {
        setProgressData(pRes.value.data);
      }
      if (aRes.status === 'fulfilled') {
        setFinalAssessment(aRes.value.data);
      }
    } catch (err) {
      console.error('Failed to load course details:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourseData();
  }, [slug]);

  const toggleModuleExpand = (modId: number) => {
    setExpandedModuleIds((prev) => ({
      ...prev,
      [modId]: !prev[modId]
    }));
  };

  if (loading) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-semibold">Loading course curriculum...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center space-y-4">
        <BookOpen className="w-12 h-12 text-slate-300 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Course Not Found</h2>
        <p className="text-xs text-slate-500">The requested course does not exist or is not published.</p>
        <Link
          to="/catalogue"
          className="px-4 py-2 bg-primary-900 text-white rounded-xl text-xs font-bold inline-flex items-center gap-1.5"
        >
          Return to Catalogue
        </Link>
      </div>
    );
  }

  const modules: Module[] = [...(course.modules || [])].sort((a, b) => a.order - b.order);

  // Filter modules by search
  const filteredModules = modules.filter(
    (m) =>
      m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.description && m.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Final Assessment Unlock calculation
  const isAllModulesCompleted =
    progressData?.assessment_unlocked === true ||
    progressData?.eligibility?.eligible === true ||
    (progressData?.completed_modules !== undefined &&
      progressData?.total_required_modules !== undefined &&
      progressData.total_required_modules > 0 &&
      progressData.completed_modules >= progressData.total_required_modules);

  return (
    <div className="bg-slate-50 min-h-[90vh] py-8 text-slate-900">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">

        {/* 1. Breadcrumb Navigation */}
        <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
          <Link to="/" className="hover:text-primary-900">Home</Link>
          <span>/</span>
          <Link to="/catalogue" className="hover:text-primary-900">Catalogue</Link>
          <span>/</span>
          <span className="text-slate-800 font-bold">{course.title}</span>
        </div>

        {/* 2. Course Learning Header */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-primary-100 text-primary-900">
                {course.department?.code || 'INSTITUTIONAL'}
              </span>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                {course.skill?.category?.name || 'Core Engineering'}
              </span>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
                Level: {course.level || 'BEGINNER'}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Link
                to={`/skill-gap/${course.id}`}
                className="px-3.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center gap-1.5 transition-all"
              >
                <BrainCircuit className="w-3.5 h-3.5 text-primary-900" />
                <span>Diagnostic Pre-Assessment</span>
              </Link>
            </div>
          </div>

          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight leading-snug">
            {course.title}
          </h1>

          <p className="text-sm text-slate-600 leading-relaxed max-w-4xl">
            {course.description}
          </p>

          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-3 border-t border-slate-100">
            <span>Instructor: <strong className="text-slate-800">{course.instructor_name}</strong></span>
            <span>•</span>
            <span>Estimated Hours: <strong className="text-slate-800">{course.estimated_hours}h</strong></span>
            <span>•</span>
            <span>Total Modules: <strong className="text-slate-800">{modules.length}</strong></span>
          </div>
        </div>

        {/* 3. Modules List Header & Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div>
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-900" />
              Course Curriculum &amp; Modules
            </h2>
            <p className="text-xs text-slate-500">
              Open each individual module to view lessons, lecture videos, revision notes, and practice challenges.
            </p>
          </div>

          {modules.length > 3 && (
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search modules..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-primary-900 focus:outline-none"
              />
            </div>
          )}
        </div>

        {/* 4. Individual Clickable Module Cards */}
        <div className="space-y-4">
          {filteredModules.length === 0 ? (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-2">
              <BookOpen className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-500">No modules match your search query.</p>
            </div>
          ) : (
            filteredModules.map((m: Module) => {
              const isModuleDone = Boolean(progressData?.module_progress?.[m.id]);
              const isExpanded = Boolean(expandedModuleIds[m.id]);
              const moduleUrl = `/courses/${course.id}/modules/${m.id}`;

              return (
                <div
                  key={m.id}
                  className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all hover:border-slate-300"
                >
                  {/* Module Card Body */}
                  <div className="p-6 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded-lg bg-primary-950 text-accent-400 font-extrabold text-[11px] tracking-wider uppercase">
                          MODULE {m.order}
                        </span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${
                          m.is_required
                            ? 'bg-amber-50 text-amber-900 border-amber-200'
                            : 'bg-slate-100 text-slate-600 border-slate-200'
                        }`}>
                          {m.is_required ? 'Required' : 'Optional'}
                        </span>
                      </div>

                      {/* Status Indicator */}
                      {isModuleDone ? (
                        <span className="px-3 py-1 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-800 font-bold text-xs flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span>✓ Module Completed</span>
                        </span>
                      ) : (
                        <span className="px-3 py-1 rounded-xl bg-slate-100 text-slate-600 font-semibold text-xs flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>In Progress</span>
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="text-lg font-bold text-slate-900">
                        {m.title}
                      </h3>
                      {m.description && (
                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                          {m.description}
                        </p>
                      )}
                    </div>

                    {/* Footer Row with Lessons Count, Duration, and Open Module Action */}
                    <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>{m.lessons?.length || 0} Lessons</span>
                        <span>•</span>
                        <span>{m.duration_minutes || 60} mins</span>

                        {m.lessons && m.lessons.length > 0 && (
                          <button
                            type="button"
                            onClick={() => toggleModuleExpand(m.id)}
                            className="text-primary-900 hover:underline font-bold text-xs flex items-center gap-1 ml-2 cursor-pointer"
                          >
                            <span>{isExpanded ? 'Hide Lessons' : 'Preview Lessons'}</span>
                            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>

                      <Link
                        to={moduleUrl}
                        className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                      >
                        <span>Open Module</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>

                  {/* Expandable Lessons Preview Drawer */}
                  {isExpanded && m.lessons && m.lessons.length > 0 && (
                    <div className="bg-slate-50/80 px-6 py-4 border-t border-slate-100 space-y-2.5">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                        Included Lessons in Module {m.order}:
                      </span>
                      <div className="grid grid-cols-1 gap-2">
                        {m.lessons.map((lsn: any, lIdx: number) => (
                          <div
                            key={lsn.id || lIdx}
                            className="p-3 bg-white rounded-xl border border-slate-200 text-xs flex items-center justify-between gap-2"
                          >
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-primary-700 shrink-0" />
                              <span className="font-semibold text-slate-800">
                                Lesson {lsn.order || lIdx + 1}: {lsn.title}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                                lsn.is_required
                                  ? 'bg-amber-100 text-amber-900'
                                  : 'bg-slate-100 text-slate-600'
                              }`}>
                                {lsn.is_required ? 'Required' : 'Optional'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* 5. Final Assessment Unlocked / Locked Section */}
        <div className="pt-2">
          {isAllModulesCompleted ? (
            <div className="p-6 bg-gradient-to-r from-emerald-500/15 via-teal-500/15 to-emerald-500/15 border-2 border-emerald-500 rounded-3xl shadow-sm space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Award className="w-6 h-6 text-emerald-700" />
                    <h3 className="text-base font-black text-emerald-950">
                      ✓ All Modules Completed
                    </h3>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-600 text-white font-bold text-[11px]">
                      Final Assessment Unlocked
                    </span>
                  </div>
                  <p className="text-xs text-emerald-900 leading-relaxed max-w-2xl">
                    Congratulations! You have completed all required modules in this curriculum. You are now fully eligible to take the proctored final examination and earn your verified institutional digital certificate.
                  </p>
                </div>

                {finalAssessment && (
                  <Link
                    to={`/assessments/${finalAssessment.id}/preflight`}
                    className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-xl text-xs shadow-md flex items-center gap-2 transition-all cursor-pointer shrink-0"
                  >
                    <Award className="w-4 h-4" />
                    <span>Start Final Assessment</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                )}
              </div>
            </div>
          ) : (
            <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Lock className="w-5 h-5 text-slate-400" />
                  <h3 className="text-sm font-bold text-slate-800">
                    Final Assessment Locked
                  </h3>
                </div>
                <span className="px-3 py-1 rounded-xl bg-slate-100 text-slate-600 text-xs font-semibold">
                  Prerequisites Pending
                </span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                The institutional proctored evaluation assessment is locked. Complete all required modules above (including watching required video lectures and passing practice challenges) to unlock the final assessment.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
