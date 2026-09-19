import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { Course } from '../types';
import { 
  BookOpen, 
  Clock, 
  Award, 
  ShieldCheck, 
  CheckCircle2, 
  ArrowRight, 
  ExternalLink, 
  BrainCircuit, 
  FileText,
  Lock
} from 'lucide-react';

export const CourseDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [course, setCourse] = useState<Course | null>(null);
  const [progressInfo, setProgressInfo] = useState<any>(null);
  const [finalAssessment, setFinalAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    const fetchCourse = async () => {
      try {
        const res = await apiClient.get<Course>(`/catalogue/courses/${slug}/`);
        setCourse(res.data);

        if (user) {
          const [progRes, aRes] = await Promise.allSettled([
            apiClient.get(`/learning/course-progress/${slug}/`),
            apiClient.get(`/assessments/course/${res.data.id}/final-assessment/`)
          ]);
          if (progRes.status === 'fulfilled') setProgressInfo(progRes.value.data);
          if (aRes.status === 'fulfilled') setFinalAssessment(aRes.value.data);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchCourse();
  }, [slug, user]);

  const handleEnroll = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    if (!course) return;

    setEnrolling(true);
    try {
      await apiClient.post('/learning/enroll/', { course_id: course.id });
      navigate(`/learn/${course.slug}`);
    } catch (err) {
      console.error(err);
    } finally {
      setEnrolling(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center">
        <h2 className="text-xl font-bold text-slate-800">Course Not Found</h2>
        <p className="text-xs text-slate-500 mt-2">The requested course is not published or does not exist.</p>
        <Link to="/catalogue" className="text-xs text-primary-900 font-bold underline mt-4 inline-block">
          Return to Catalogue
        </Link>
      </div>
    );
  }

  const isEnrolled = progressInfo?.enrolled;

  return (
    <div className="bg-slate-50 min-h-[85vh] py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hierarchy Breadcrumb: Category -> Domain -> Skill -> Course */}
        <div className="flex items-center gap-2 text-xs text-slate-500 mb-6 flex-wrap">
          <Link to="/" className="hover:text-primary-900">Home</Link>
          <span>/</span>
          <Link to="/catalogue" className="hover:text-primary-900">Catalogue</Link>
          <span>/</span>
          <span className="text-slate-600">{course.skill?.category?.name || 'Curriculum'}</span>
          {course.skill?.domain && (
            <>
              <span>/</span>
              <span className="text-slate-600">{course.skill.domain.name}</span>
            </>
          )}
          <span>/</span>
          <span className="text-slate-800 font-semibold">{course.title}</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Main Course Content */}
          <div className="lg:col-span-8 space-y-8">
            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                {course.departments && course.departments.length > 1 ? (
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-900 border border-purple-200">
                    Interdisciplinary: {course.departments.map(d => d.code).join(' + ')}
                  </span>
                ) : (
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-primary-100 text-primary-900">
                    {course.department?.name || 'Institutional Course'}
                  </span>
                )}

                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-800">
                  {course.skill?.category?.name || 'Core Pillar'}
                </span>

                <span className="text-xs text-slate-500 font-medium flex items-center gap-1 ml-auto">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  {course.estimated_hours} Hours
                </span>
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight leading-snug">
                {course.title}
              </h1>

              <p className="text-sm text-slate-600 leading-relaxed">
                {course.description}
              </p>

              <div className="pt-3 flex flex-wrap items-center gap-4 text-xs text-slate-500 border-t border-slate-100">
                <span>Instructor: <strong className="text-slate-800">{course.instructor_name}</strong></span>
                <span>•</span>
                <span>Level: <strong className="text-slate-800">{course.level || course.skill?.level}</strong></span>
                <span>•</span>
                <span>Version: <strong className="text-slate-800">v{course.version || 1}</strong></span>
              </div>
            </div>

            {/* Learning Outcomes */}
            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Award className="w-5 h-5 text-accent-600" />
                Target Learning Outcomes &amp; Competencies
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {course.outcomes?.map((out, idx) => (
                  <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-700 bg-slate-50 p-3.5 rounded-2xl border border-slate-100">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{out}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Modules & Lessons Curriculum Breakdown */}
            <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-sm space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-primary-900" />
                  Sequential Curriculum &amp; Modules
                </h2>
                <span className="text-xs text-slate-500 font-semibold">
                  {course.modules?.length || 0} Modules
                </span>
              </div>

              <div className="space-y-4 pt-1">
                {course.modules?.map((m) => {
                  const isModuleDone = Boolean(progressInfo?.module_progress?.[m.id]);
                  const moduleUrl = `/courses/${course.id}/modules/${m.id}`;

                  return (
                    <div 
                      key={m.id}
                      className="p-6 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-4 transition-all hover:border-slate-300"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap">
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
                        <h4 className="text-base font-bold text-slate-900">{m.title}</h4>
                        {m.description && (
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">{m.description}</p>
                        )}
                      </div>

                      {/* Lessons list */}
                      {m.lessons && m.lessons.length > 0 && (
                        <div className="pt-2 space-y-1.5 border-t border-slate-200/60">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                            Included Lessons:
                          </span>
                          <div className="grid grid-cols-1 gap-1.5">
                            {m.lessons.map((lsn) => (
                              <div key={lsn.id} className="p-2.5 bg-white rounded-xl border border-slate-200 text-xs flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <FileText className="w-3.5 h-3.5 text-primary-700" />
                                  <span className="font-semibold text-slate-800">
                                    {lsn.order}. {lsn.title}
                                  </span>
                                </div>
                                <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                                  {lsn.duration_minutes || 15}m
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="pt-3 border-t border-slate-200/60 flex items-center justify-between flex-wrap gap-2">
                        <span className="text-xs text-slate-500 font-medium">
                          {m.duration_minutes || 60} mins • {m.lessons?.length || 0} Lessons
                        </span>
                        {isEnrolled ? (
                          <Link
                            to={moduleUrl}
                            className="px-5 py-2 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                          >
                            <span>Open Module</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        ) : (
                          <button
                            type="button"
                            onClick={handleEnroll}
                            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-all cursor-pointer"
                          >
                            <span>Enroll to Open</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Final Assessment Unlocked / Locked Card */}
              {isEnrolled && (
                <div className="pt-2">
                  {(progressInfo?.assessment_unlocked || progressInfo?.eligibility?.eligible) ? (
                    <div className="p-6 bg-gradient-to-r from-emerald-500/15 via-teal-500/15 to-emerald-500/15 border-2 border-emerald-500 rounded-3xl shadow-sm space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <Award className="w-5 h-5 text-emerald-700" />
                            <h3 className="text-base font-black text-emerald-950">
                              ✓ All Modules Completed
                            </h3>
                            <span className="px-2.5 py-0.5 rounded-full bg-emerald-600 text-white font-bold text-[10px]">
                              Final Assessment Unlocked
                            </span>
                          </div>
                          <p className="text-xs text-emerald-900 leading-relaxed max-w-xl">
                            All required modules are completed. Launch your proctored final assessment to earn your official institutional certificate.
                          </p>
                        </div>
                        {finalAssessment && (
                          <Link
                            to={`/assessments/${finalAssessment.id}/preflight`}
                            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-xl text-xs shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
                          >
                            <Award className="w-4 h-4" />
                            <span>Start Final Assessment</span>
                            <ArrowRight className="w-4 h-4" />
                          </Link>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-5 bg-slate-100/80 rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 text-slate-400" />
                        <span className="text-xs font-bold text-slate-700">Final Assessment Locked</span>
                        <span className="text-[11px] text-slate-500">• Complete all required modules above to unlock</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Action Sidebar & Provenance Card */}
          <div className="lg:col-span-4 space-y-6">
            <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-xl space-y-5 sticky top-24">
              <div className="text-center pb-3 border-b border-slate-100">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Institutional Skill Credential
                </div>
                <div className="text-2xl font-black text-primary-950 mt-1">
                  Verified Enrollment
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5">FXEC Centre for Training &amp; Skills Development</p>
              </div>

              {/* Action Buttons */}
              <div className="space-y-3">
                {isEnrolled ? (
                  <Link
                    to={`/learn/${course.slug}`}
                    className="w-full py-3.5 px-4 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2"
                  >
                    <BookOpen className="w-4 h-4 text-accent-400" />
                    <span>Open Course Modules</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                ) : (
                  <button
                    onClick={handleEnroll}
                    disabled={enrolling}
                    className="w-full py-3.5 px-4 rounded-xl bg-accent-500 hover:bg-accent-400 text-primary-950 font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-60"
                  >
                    <BookOpen className="w-4 h-4" />
                    {enrolling ? 'Enrolling...' : 'Enroll in Skill Track'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}

                {/* Pre-Assessment Diagnostic Button */}
                <Link
                  to={`/skill-gap/${course.id}`}
                  className="w-full py-3 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs border border-slate-300 transition-colors flex items-center justify-center gap-2"
                >
                  <BrainCircuit className="w-4 h-4 text-primary-800" />
                  Take Diagnostic Pre-Assessment
                </Link>
              </div>

              {/* Provenance Box */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5 text-xs text-slate-600">
                <div className="flex items-center gap-1.5 font-bold text-primary-950">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Authoritative Provenance Record
                </div>
                <div className="space-y-1.5 text-[11px]">
                  <div><strong>Source Authority:</strong> {course.source_type}</div>
                  <div><strong>Source Title:</strong> {course.source_title || 'FXEC Official Reference'}</div>
                  {course.last_verified_at && (
                    <div><strong>Last Verified:</strong> {new Date(course.last_verified_at).toLocaleDateString()}</div>
                  )}
                  {course.source_url && (
                    <div className="pt-1.5 border-t border-slate-200">
                      <a
                        href={course.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary-700 hover:text-primary-900 underline flex items-center gap-1 font-bold text-[11px]"
                      >
                        Inspect Official Reference <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
