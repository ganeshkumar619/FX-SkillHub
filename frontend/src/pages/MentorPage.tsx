import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import type { 
  Course, 
  Skill, 
  Department, 
  SkillCategory, 
  SkillDomain, 
  DuplicateCheckResult 
} from '../types';
import { 
  ShieldAlert, 
  RefreshCw, 
  X,
  AlertTriangle,
  BookOpen,
  PlusCircle,
  Sparkles,
  CheckCircle2,
  Layers,
  Clock,
  Send,
  Edit3,
  Trash2
} from 'lucide-react';
import { AICourseGeneratorModal } from '../components/AICourseGeneratorModal';
import { CourseBuilderStudio } from '../components/CourseBuilderStudio';

interface AttemptItem {
  attempt_id: string;
  student_username: string;
  student_name: string;
  course_title: string;
  assessment_title: string;
  score: number;
  percentage: number;
  passed: boolean;
  status: string;
  review_status: string;
  risk_tier: string;
  risk_score: number;
  events_count: number;
  camera_violations?: number;
  multiple_face_violations?: number;
  screen_share_violations?: number;
  fullscreen_violations?: number;
  tab_switch_violations?: number;
  termination_reason?: string | null;
  terminated_at?: string | null;
  started_at: string;
}

interface AttemptEventsData {
  attempt_id: string;
  student_name: string;
  assessment_title: string;
  status?: string;
  review_status: string;
  risk_tier: string;
  risk_score: number;
  camera_violations?: number;
  multiple_face_violations?: number;
  screen_share_violations?: number;
  fullscreen_violations?: number;
  tab_switch_violations?: number;
  termination_reason?: string | null;
  terminated_at?: string | null;
  events: Array<{
    id: number;
    event_type: string;
    severity: string;
    timestamp: string;
    details: any;
  }>;
  existing_review?: {
    verdict: string;
    notes: string;
    reviewer: string;
    reviewed_at: string;
  } | null;
}

export const MentorPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'courses' | 'builder' | 'skills' | 'proctoring'>('courses');

  // --- Proctoring State ---
  const [attempts, setAttempts] = useState<AttemptItem[]>([]);
  const [loadingProctoring, setLoadingProctoring] = useState(false);
  const [filterMode, setFilterMode] = useState<'all' | 'flagged'>('all');
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [attemptDetail, setAttemptDetail] = useState<AttemptEventsData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [verdict, setVerdict] = useState<'VALID' | 'WARNING' | 'INVALID'>('VALID');
  const [notes, setNotes] = useState('');
  const [submittingVerdict, setSubmittingVerdict] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

  // --- Faculty Courses State ---
  const [myCourses, setMyCourses] = useState<Course[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [submittingReviewId, setSubmittingReviewId] = useState<number | null>(null);
  const [isGeneratorOpen, setIsGeneratorOpen] = useState(false);
  const [selectedBuilderCourseId, setSelectedBuilderCourseId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{
    type: 'course' | 'skill';
    id: number;
    title: string;
  } | null>(null);
  const [deletingItem, setDeletingItem] = useState(false);
  const [actionAlert, setActionAlert] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // --- Metadata for Builder & Skills ---
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [domains, setDomains] = useState<SkillDomain[]>([]);
  const [mySkills, setMySkills] = useState<Skill[]>([]);

  // --- Skill Creation Form State ---
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCatId, setNewSkillCatId] = useState<number | ''>('');
  const [newSkillDomId, setNewSkillDomId] = useState<number | ''>('');
  const [newSkillDeptId, setNewSkillDeptId] = useState<number | ''>('');
  const [newSkillLevel, setNewSkillLevel] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'>('BEGINNER');
  const [newSkillType, setNewSkillType] = useState('CORE');
  const [newSkillDesc, setNewSkillDesc] = useState('');
  const [newSkillDuration, setNewSkillDuration] = useState('4 Weeks');
  const [newSkillOutcomes, setNewSkillOutcomes] = useState<string[]>(['', '']);
  const [duplicateCheck, setDuplicateCheck] = useState<DuplicateCheckResult | null>(null);
  const [checkingDuplicate, setCheckingDuplicate] = useState(false);
  const [skillSubmitting, setSkillSubmitting] = useState(false);
  const [skillMessage, setSkillMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load Initial Metadata
  useEffect(() => {
    const loadMetadata = async () => {
      try {
        const [deptRes, catRes, domRes] = await Promise.all([
          apiClient.get('/catalogue/departments/'),
          apiClient.get('/catalogue/categories/'),
          apiClient.get('/catalogue/domains/'),
        ]);
        setDepartments(deptRes.data.results || deptRes.data);
        setCategories(catRes.data.results || catRes.data);
        setDomains(domRes.data.results || domRes.data);
      } catch (err) {
        console.error('Failed to load catalogue metadata', err);
      }
    };
    loadMetadata();
  }, []);

  // Fetch Proctoring Queue
  const fetchProctoringQueue = async () => {
    try {
      setLoadingProctoring(true);
      const res = await apiClient.get(`/proctoring/review-queue/?filter=${filterMode}`);
      setAttempts(res.data);
    } catch (err) {
      console.error('Failed to load review queue', err);
    } finally {
      setLoadingProctoring(false);
    }
  };

  // Fetch Faculty Courses & Skills
  const fetchFacultyData = async () => {
    try {
      setLoadingCourses(true);
      const [crsRes, skRes] = await Promise.all([
        apiClient.get('/catalogue/faculty/my-courses/'),
        apiClient.get('/catalogue/faculty/my-skills/'),
      ]);
      setMyCourses(crsRes.data.results || crsRes.data);
      setMySkills(skRes.data.results || skRes.data);
    } catch (err) {
      console.error('Failed to load faculty courses/skills', err);
    } finally {
      setLoadingCourses(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'proctoring') {
      fetchProctoringQueue();
    } else if (activeTab === 'courses' || activeTab === 'skills') {
      fetchFacultyData();
    }
  }, [activeTab, filterMode]);

  // Real-time Duplicate Skill Check
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (newSkillName.trim().length >= 3) {
        try {
          setCheckingDuplicate(true);
          const res = await apiClient.post('/catalogue/faculty/skills/check-duplicate/', {
            name: newSkillName.trim(),
            category_id: newSkillCatId || null,
          });
          setDuplicateCheck(res.data);
        } catch (err) {
          console.error('Duplicate check error', err);
        } finally {
          setCheckingDuplicate(false);
        }
      } else {
        setDuplicateCheck(null);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [newSkillName, newSkillCatId]);



  // Submit Skill Form
  const handleCreateSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSkillName.trim()) return;

    try {
      setSkillSubmitting(true);
      setSkillMessage(null);
      const payload = {
        name: newSkillName.trim(),
        category_id: newSkillCatId || categories[0]?.id,
        domain_id: newSkillDomId || null,
        department_id: newSkillDeptId || null,
        level: newSkillLevel,
        skill_type: newSkillType,
        description: newSkillDesc,
        estimated_duration: newSkillDuration,
        learning_outcomes: newSkillOutcomes.filter(o => o.trim().length > 0),
        force_create: false,
      };
      await apiClient.post('/catalogue/faculty/skills/', payload);
      setSkillMessage({ type: 'success', text: `Skill '${newSkillName}' submitted for institutional review!` });
      setNewSkillName('');
      setNewSkillDesc('');
      setDuplicateCheck(null);
      fetchFacultyData();
    } catch (err: any) {
      if (err.response?.status === 409) {
        setSkillMessage({ type: 'error', text: 'Duplicate skill detected in database. Review matching skills below.' });
      } else {
        setSkillMessage({ type: 'error', text: 'Failed to register skill. Please verify fields.' });
      }
    } finally {
      setSkillSubmitting(false);
    }
  };

  // AI Auto-Generate Skill Assistant
  const [aiSkillGenerating, setAiSkillGenerating] = useState(false);
  const handleAutoGenerateSkill = async (persist: boolean = false) => {
    if (!newSkillName.trim()) {
      setSkillMessage({ type: 'error', text: 'Please enter a Skill Name or Topic first to synthesize with AI.' });
      return;
    }
    try {
      setAiSkillGenerating(true);
      setSkillMessage(null);
      const res = await apiClient.post('/catalogue/ai/skills/generate/', {
        skill_name: newSkillName.trim(),
        department_code: newSkillDeptId ? departments.find(d => d.id === newSkillDeptId)?.code : null,
        level: newSkillLevel,
        skill_type: newSkillType,
        preview_only: !persist
      });
      const data = res.data;

      // Populate form fields
      if (data.category_id) setNewSkillCatId(data.category_id);
      if (data.domain_id) setNewSkillDomId(data.domain_id);
      if (data.department_id) setNewSkillDeptId(data.department_id);
      if (data.level) setNewSkillLevel(data.level);
      if (data.skill_type) setNewSkillType(data.skill_type);
      if (data.description) setNewSkillDesc(data.description);
      if (data.estimated_duration) setNewSkillDuration(data.estimated_duration);
      if (data.learning_outcomes && data.learning_outcomes.length > 0) {
        setNewSkillOutcomes(data.learning_outcomes);
      }

      if (persist) {
        setSkillMessage({ type: 'success', text: `Skill "${data.name}" successfully generated and registered into catalogue with AI!` });
        fetchFacultyData();
      } else {
        setSkillMessage({ type: 'success', text: 'AI synthesized complete skill attributes, outcomes, and descriptions! Review or adjust below.' });
      }
    } catch (err: any) {
      console.error('AI Skill generation failed', err);
      const errText = err.response?.data?.error || 'Failed to auto-generate skill with AI.';
      setSkillMessage({ type: 'error', text: errText });
    } finally {
      setAiSkillGenerating(false);
    }
  };



  // Submit Existing Draft Course for Review
  const handleSubmitReview = async (courseId: number) => {
    try {
      setSubmittingReviewId(courseId);
      await apiClient.post(`/catalogue/faculty/courses/${courseId}/submit-review/`, {
        notes: 'Submitted for institutional review.'
      });
      fetchFacultyData();
    } catch (err) {
      console.error('Submit review error', err);
    } finally {
      setSubmittingReviewId(null);
    }
  };

  // Delete Execution
  const handleExecuteDelete = async () => {
    if (!confirmDelete) return;
    try {
      setDeletingItem(true);
      if (confirmDelete.type === 'course') {
        await apiClient.delete(`/catalogue/faculty/courses/${confirmDelete.id}/`);
        if (selectedBuilderCourseId === confirmDelete.id) {
          setSelectedBuilderCourseId(null);
        }
        setActionAlert({ type: 'success', text: `Course "${confirmDelete.title}" permanently deleted.` });
      } else {
        await apiClient.delete(`/catalogue/faculty/skills/${confirmDelete.id}/`);
        setActionAlert({ type: 'success', text: `Skill "${confirmDelete.title}" permanently deleted.` });
      }
      setConfirmDelete(null);
      fetchFacultyData();
      setTimeout(() => setActionAlert(null), 4000);
    } catch (err: any) {
      const errMsg = err.response?.data?.error || `Failed to delete ${confirmDelete.type}.`;
      setActionAlert({ type: 'error', text: errMsg });
      setTimeout(() => setActionAlert(null), 5000);
    } finally {
      setDeletingItem(false);
    }
  };

  // Proctoring Modal Handlers
  const openReviewModal = async (attemptId: string) => {
    setSelectedAttemptId(attemptId);
    setReviewMessage(null);
    try {
      setDetailLoading(true);
      const res = await apiClient.get(`/proctoring/attempts/${attemptId}/events/`);
      setAttemptDetail(res.data);
      if (res.data.existing_review) {
        setVerdict(res.data.existing_review.verdict);
        setNotes(res.data.existing_review.notes);
      } else {
        if (res.data.status === 'TERMINATED_SECURITY_VIOLATION' || res.data.risk_tier === 'CRITICAL') {
          setVerdict('INVALID');
        } else if (res.data.risk_tier === 'HIGH') {
          setVerdict('WARNING');
        } else {
          setVerdict('VALID');
        }
        setNotes(res.data.termination_reason ? `Terminated: ${res.data.termination_reason}` : '');
      }
    } catch (err) {
      console.error('Failed to load attempt events', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const submitVerdict = async () => {
    if (!selectedAttemptId) return;
    try {
      setSubmittingVerdict(true);
      await apiClient.post(`/proctoring/attempts/${selectedAttemptId}/verdict/`, {
        verdict,
        notes
      });
      setReviewMessage('Review verdict successfully recorded and audit log updated.');
      fetchProctoringQueue();
      setTimeout(() => {
        setSelectedAttemptId(null);
        setAttemptDetail(null);
      }, 1500);
    } catch (err) {
      console.error('Failed to submit review verdict', err);
    } finally {
      setSubmittingVerdict(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[85vh] space-y-8">
      {/* Action Notification Alert */}
      {actionAlert && (
        <div className={`p-4 rounded-2xl border text-xs font-bold flex items-center justify-between shadow-sm animate-in fade-in ${
          actionAlert.type === 'success' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-rose-50 text-rose-800 border-rose-200'
        }`}>
          <span>{actionAlert.text}</span>
          <button type="button" onClick={() => setActionAlert(null)} className="text-slate-400 hover:text-slate-700 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Top Banner */}
      <div className="bg-gradient-to-r from-primary-950 via-primary-900 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-accent-400 bg-accent-500/20 px-2.5 py-1 rounded-full border border-accent-400/30">
            Faculty &amp; Mentor Hub
          </span>
          <h1 className="text-2xl sm:text-3xl font-black mt-2">
            Academic Curriculum &amp; Assessment Management
          </h1>
          <p className="text-xs text-slate-300 mt-1">
            Faculty: <strong className="text-white">{user?.first_name} {user?.last_name} ({user?.username})</strong> • Francis Xavier Engineering College
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 bg-slate-900/60 p-1.5 rounded-2xl border border-slate-700/60 text-xs">
          <button
            onClick={() => setActiveTab('courses')}
            className={`px-3.5 py-2 rounded-xl font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'courses' ? 'bg-primary-800 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            My Courses ({myCourses.length})
          </button>
          <button
            onClick={() => setActiveTab('builder')}
            className={`px-3.5 py-2 rounded-xl font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'builder' ? 'bg-accent-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Course Builder
          </button>
          <button
            onClick={() => setActiveTab('skills')}
            className={`px-3.5 py-2 rounded-xl font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'skills' ? 'bg-primary-800 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Skill Registry
          </button>
          <button
            onClick={() => setActiveTab('proctoring')}
            className={`px-3.5 py-2 rounded-xl font-bold transition-all flex items-center gap-1.5 ${
              activeTab === 'proctoring' ? 'bg-primary-800 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            Proctoring Queue
          </button>
        </div>
      </div>

      {/* ========================================================= */}
      {/* TAB 1: MY COURSES */}
      {/* ========================================================= */}
      {activeTab === 'courses' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-900" />
              My Created Courses &amp; Institutional Proposals
            </h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIsGeneratorOpen(true)}
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-md shadow-indigo-500/20 transition-all cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                Autonomous AI Course Generator
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('builder')}
                className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-sm cursor-pointer"
              >
                <PlusCircle className="w-4 h-4" />
                Manual Course Builder
              </button>
            </div>
          </div>

          {loadingCourses ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 mt-2">Loading faculty courses...</p>
            </div>
          ) : myCourses.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center space-y-3">
              <BookOpen className="w-12 h-12 text-slate-400 mx-auto" />
              <h3 className="text-base font-bold text-slate-800">No Courses Created Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Use the Course Builder Studio to design courses, configure sequential modules, and submit for institutional review.
              </p>
              <button
                onClick={() => setActiveTab('builder')}
                className="mt-2 px-5 py-2.5 bg-primary-900 text-white text-xs font-bold rounded-xl shadow"
              >
                Launch Course Builder
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {myCourses.map((c) => (
                <div key={c.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4 flex flex-col justify-between">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        c.approval_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                        c.approval_status === 'PENDING_REVIEW' ? 'bg-amber-50 text-amber-800 border-amber-200' :
                        c.approval_status === 'REJECTED' ? 'bg-rose-50 text-rose-800 border-rose-200' :
                        'bg-slate-100 text-slate-700 border-slate-200'
                      }`}>
                        {c.approval_status.replace('_', ' ')}
                      </span>
                      <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400" />
                        {c.estimated_hours} Hours
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 leading-snug">{c.title}</h3>
                    <p className="text-xs text-slate-600 line-clamp-2">{c.description}</p>

                    <div className="text-[11px] text-slate-500 space-y-0.5 pt-2 border-t border-slate-100">
                      <div>Skill: <strong>{c.skill?.name}</strong></div>
                      <div>Modules: <strong>{c.modules?.length || c.modules_count || 0} modules</strong></div>
                      <div>Department: <strong>{c.department?.code || 'Interdisciplinary'}</strong></div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedBuilderCourseId(c.id);
                        setActiveTab('builder');
                      }}
                      className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold flex items-center justify-center gap-1 cursor-pointer transition-all"
                      title="Open in Course Builder Studio"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      Studio
                    </button>

                    <button
                      type="button"
                      onClick={() => setConfirmDelete({ type: 'course', id: c.id, title: c.title })}
                      className="p-2 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-xl transition-all cursor-pointer border border-transparent hover:border-rose-200"
                      title="Delete Course"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>

                    {c.approval_status === 'DRAFT' && (
                      <button
                        onClick={() => handleSubmitReview(c.id)}
                        disabled={submittingReviewId === c.id}
                        className="flex-1 py-2 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold shadow flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer"
                      >
                        <Send className="w-3.5 h-3.5" />
                        {submittingReviewId === c.id ? 'Submitting...' : 'Submit for Review'}
                      </button>
                    )}
                    {c.approval_status === 'APPROVED' && (
                      <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Live in Student Catalogue
                      </span>
                    )}
                    {c.approval_status === 'PENDING_REVIEW' && (
                      <span className="text-xs font-semibold text-amber-700 flex items-center gap-1">
                        <Clock className="w-4 h-4" /> Awaiting Admin Approval
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 2: COURSE BUILDER STUDIO */}
      {/* ========================================================= */}
      {activeTab === 'builder' && (
        <div className="space-y-6">
          {/* Studio Context Bar: Switch or Create Courses */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary-900 text-white flex items-center justify-center font-bold shrink-0">
                <Edit3 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Faculty Course Builder Studio</h3>
                <p className="text-xs text-slate-500">
                  {selectedBuilderCourseId
                    ? `Working on: ${myCourses.find(c => c.id === selectedBuilderCourseId)?.title || `Course #${selectedBuilderCourseId}`}`
                    : 'Design and publish courses with rich video, study notes, and practice quizzes.'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedBuilderCourseId || ''}
                onChange={(e) => setSelectedBuilderCourseId(e.target.value ? Number(e.target.value) : null)}
                className="px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl font-medium focus:ring-2 focus:ring-primary-900"
              >
                <option value="">+ Create Brand New Course</option>
                {myCourses.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.title} ({c.approval_status})
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={() => setSelectedBuilderCourseId(null)}
                className="px-3 py-2 bg-primary-50 text-primary-900 hover:bg-primary-100 text-xs font-bold rounded-xl border border-primary-200 flex items-center gap-1 cursor-pointer transition-all"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                New Course
              </button>
            </div>
          </div>

          <CourseBuilderStudio
            key={selectedBuilderCourseId || 'new'}
            initialCourseId={selectedBuilderCourseId}
            onClose={() => setActiveTab('courses')}
            onCourseCreated={(newC) => {
              setSelectedBuilderCourseId(newC.id);
              fetchFacultyData();
            }}
          />
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 3: SKILL REGISTRY & CREATOR */}
      {/* ========================================================= */}
      {activeTab === 'skills' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left: Create Skill Form with Real-Time Duplicate Check */}
          <div className="lg:col-span-6 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-primary-800 bg-primary-50 px-2.5 py-1 rounded">
                  Faculty &amp; AI Synergy
                </span>
                <h2 className="text-lg font-bold text-slate-900 mt-1">
                  Register New Skill Competency
                </h2>
                <p className="text-xs text-slate-500">
                  Skills are vetted through institutional duplicate detection before submission.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleAutoGenerateSkill(false)}
                  disabled={aiSkillGenerating || !newSkillName.trim()}
                  className="px-3.5 py-2 bg-gradient-to-r from-accent-500 to-amber-400 hover:from-accent-400 hover:to-amber-300 text-slate-950 font-bold text-xs rounded-xl shadow flex items-center gap-1.5 disabled:opacity-50 transition-all cursor-pointer"
                  title="Auto-fills category, domain, level, description, and outcomes using AI"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {aiSkillGenerating ? 'Synthesizing...' : 'Auto-Fill with AI'}
                </button>
                <button
                  type="button"
                  onClick={() => handleAutoGenerateSkill(true)}
                  disabled={aiSkillGenerating || !newSkillName.trim()}
                  className="px-3.5 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs rounded-xl shadow flex items-center gap-1.5 disabled:opacity-50 transition-all cursor-pointer"
                  title="Instantly synthesizes and registers the skill in the official catalogue with AI"
                >
                  <Sparkles className="w-3.5 h-3.5 text-accent-300" />
                  Instant AI Register
                </button>
              </div>
            </div>

            {skillMessage && (
              <div className={`p-4 rounded-xl text-xs font-semibold ${
                skillMessage.type === 'success' ? 'bg-emerald-50 border border-emerald-200 text-emerald-800' : 'bg-rose-50 border border-rose-200 text-rose-800'
              }`}>
                {skillMessage.text}
              </div>
            )}

            <form onSubmit={handleCreateSkill} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Skill Name * {checkingDuplicate && <span className="text-[10px] text-slate-400 font-normal">(Checking duplicates...)</span>}
                </label>
                <input
                  type="text"
                  placeholder="e.g. Distributed Cloud Architectures"
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600"
                  required
                />
              </div>

              {/* Real-time Duplicate Detection Alert */}
              {duplicateCheck && duplicateCheck.is_duplicate && (
                <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-950 space-y-2 text-xs">
                  <div className="flex items-center gap-2 font-bold text-amber-900">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    Similar or Identical Skill Already Exists
                  </div>
                  <ul className="space-y-1.5 pl-5 list-disc text-[11px] text-amber-900">
                    {duplicateCheck.matches.map((m, idx) => (
                      <li key={idx}>
                        <strong>{m.name}</strong> ({m.category || 'General'}) — {m.similarity_reason}
                      </li>
                    ))}
                  </ul>
                  <p className="text-[10px] text-amber-700 italic">
                    To prevent catalogue fragmentation, consider attaching your course to the existing skill instead of duplicating.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Skill Pillar *</label>
                  <select
                    value={newSkillCatId}
                    onChange={(e) => setNewSkillCatId(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Domain</label>
                  <select
                    value={newSkillDomId}
                    onChange={(e) => setNewSkillDomId(e.target.value ? Number(e.target.value) : '')}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="">General / Interdisciplinary</option>
                    {domains.map((dom) => (
                      <option key={dom.id} value={dom.id}>{dom.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Department</label>
                  <select
                    value={newSkillDeptId}
                    onChange={(e) => setNewSkillDeptId(e.target.value ? Number(e.target.value) : '')}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="">Cross-Department</option>
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>{d.code}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Difficulty Level</label>
                  <select
                    value={newSkillLevel}
                    onChange={(e) => setNewSkillLevel(e.target.value as any)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="BEGINNER">Beginner</option>
                    <option value="INTERMEDIATE">Intermediate</option>
                    <option value="ADVANCED">Advanced</option>
                    <option value="EXPERT">Expert</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Skill Type</label>
                  <select
                    value={newSkillType}
                    onChange={(e) => setNewSkillType(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  >
                    <option value="CORE">Core</option>
                    <option value="ELECTIVE">Elective</option>
                    <option value="FACULTY_INITIATIVE">Faculty Initiative</option>
                    <option value="EMERGING">Emerging / Future</option>
                    <option value="PLACEMENT">Placement Training</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Estimated Duration</label>
                  <input
                    type="text"
                    value={newSkillDuration}
                    onChange={(e) => setNewSkillDuration(e.target.value)}
                    placeholder="e.g. 4 Weeks"
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Key Learning Outcome</label>
                  <input
                    type="text"
                    value={newSkillOutcomes[0] || ''}
                    onChange={(e) => setNewSkillOutcomes([e.target.value, newSkillOutcomes[1] || ''])}
                    placeholder="Primary target competency..."
                    className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Target competencies and engineering applications..."
                  value={newSkillDesc}
                  onChange={(e) => setNewSkillDesc(e.target.value)}
                  className="w-full p-2.5 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <button
                type="submit"
                disabled={skillSubmitting}
                className="w-full py-2.5 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl shadow disabled:opacity-50"
              >
                {skillSubmitting ? 'Registering...' : 'Submit Skill Proposal'}
              </button>
            </form>
          </div>

          {/* Right: List of Skills Created by Mentor */}
          <div className="lg:col-span-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-primary-900" />
              My Registered Skills ({mySkills.length})
            </h3>

            {mySkills.length === 0 ? (
              <div className="p-8 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">
                You haven't submitted any skill proposals yet.
              </div>
            ) : (
              <div className="space-y-3">
                {mySkills.map((sk) => (
                  <div key={sk.id} className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-900">{sk.name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          sk.approval_status === 'APPROVED' ? 'bg-emerald-50 text-emerald-800 border-emerald-200' :
                          'bg-amber-50 text-amber-800 border-amber-200'
                        }`}>
                          {sk.approval_status.replace('_', ' ')}
                        </span>
                        <button
                          type="button"
                          onClick={() => setConfirmDelete({ type: 'skill', id: sk.id, title: sk.name })}
                          className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-all cursor-pointer border border-transparent hover:border-rose-200"
                          title="Delete Skill"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2">{sk.description}</p>
                    <div className="text-[10px] text-slate-400">
                      Pillar: {sk.category?.name || 'Institutional'} • Level: {sk.level}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* TAB 4: PROCTORING QUEUE (Preserved Existing System) */}
      {/* ========================================================= */}
      {activeTab === 'proctoring' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-600" />
              Assessment Proctoring Integrity Queue
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  filterMode === 'all' ? 'bg-primary-900 text-white' : 'bg-slate-100 text-slate-700'
                }`}
              >
                All Attempts
              </button>
              <button
                onClick={() => setFilterMode('flagged')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  filterMode === 'flagged' ? 'bg-primary-900 text-white' : 'bg-slate-100 text-slate-700'
                }`}
              >
                Flagged Only
              </button>
              <button
                onClick={fetchProctoringQueue}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg flex items-center gap-1"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
            </div>
          </div>

          {loadingProctoring ? (
            <div className="text-center py-16">
              <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-slate-500 mt-2">Loading queue...</p>
            </div>
          ) : attempts.length === 0 ? (
            <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center text-xs text-slate-500">
              No attempts currently in proctoring queue.
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 font-bold">
                  <tr>
                    <th className="p-3.5">Student</th>
                    <th className="p-3.5">Assessment</th>
                    <th className="p-3.5">Score</th>
                    <th className="p-3.5">Risk Tier</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {attempts.map((att) => (
                    <tr key={att.attempt_id} className="hover:bg-slate-50/70">
                      <td className="p-3.5 font-semibold text-slate-900">{att.student_name} ({att.student_username})</td>
                      <td className="p-3.5 text-slate-700">{att.assessment_title}</td>
                      <td className="p-3.5 font-bold">{att.percentage}%</td>
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          att.risk_tier === 'HIGH' || att.risk_tier === 'CRITICAL' ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                        }`}>
                          {att.risk_tier} ({att.risk_score} pts)
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-600">{att.review_status}</td>
                      <td className="p-3.5 text-right">
                        <button
                          onClick={() => openReviewModal(att.attempt_id)}
                          className="px-3 py-1 bg-primary-900 hover:bg-primary-800 text-white rounded-lg text-xs font-bold"
                        >
                          Review Events
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Proctoring Event Review Modal */}
      {selectedAttemptId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="bg-white w-full max-w-2xl rounded-3xl border border-slate-200 shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                Audit Proctoring Events &amp; Verdict
              </h3>
              <button onClick={() => setSelectedAttemptId(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="py-8 text-center text-xs text-slate-500">Loading events...</div>
            ) : (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div>Student: <strong>{attemptDetail?.student_name}</strong></div>
                  <div>Assessment: <strong>{attemptDetail?.assessment_title}</strong></div>
                  <div>Risk Score: <strong>{attemptDetail?.risk_score} ({attemptDetail?.risk_tier})</strong></div>
                  {attemptDetail?.termination_reason && (
                    <div className="text-rose-700 font-bold">Termination: {attemptDetail.termination_reason}</div>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="block text-xs font-bold text-slate-700">Recorded Security Events ({attemptDetail?.events?.length || 0}):</label>
                  <div className="max-h-48 overflow-y-auto space-y-1.5 text-xs">
                    {attemptDetail?.events?.map((ev) => (
                      <div key={ev.id} className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                        <span className="font-semibold text-slate-800">{ev.event_type}</span>
                        <span className="text-[10px] text-slate-500">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <label className="block text-xs font-bold text-slate-700">Faculty Verdict:</label>
                  <div className="flex gap-2">
                    {(['VALID', 'WARNING', 'INVALID'] as const).map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() => setVerdict(v)}
                        className={`px-4 py-2 rounded-xl text-xs font-bold border ${
                          verdict === v ? 'bg-primary-900 text-white border-primary-900' : 'bg-slate-50 text-slate-700 border-slate-200'
                        }`}
                      >
                        {v}
                      </button>
                    ))}
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Audit reason..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full p-2.5 text-xs bg-slate-50 border border-slate-300 rounded-xl"
                  />
                  {reviewMessage && <div className="text-xs text-emerald-700 font-bold">{reviewMessage}</div>}
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button onClick={() => setSelectedAttemptId(null)} className="px-4 py-2 text-xs font-semibold text-slate-600">
                    Cancel
                  </button>
                  <button
                    onClick={submitVerdict}
                    disabled={submittingVerdict}
                    className="px-5 py-2 bg-primary-900 text-white text-xs font-bold rounded-xl shadow"
                  >
                    {submittingVerdict ? 'Submitting...' : 'Save Verdict'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Autonomous AI Course Generator Modal */}
      <AICourseGeneratorModal
        isOpen={isGeneratorOpen}
        onClose={() => setIsGeneratorOpen(false)}
        onSuccess={() => {
          fetchFacultyData();
        }}
      />

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4 animate-in fade-in">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-rose-100 text-rose-700 flex items-center justify-center shrink-0">
                <Trash2 className="w-5 h-5 text-rose-600" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Confirm Deletion
                </h3>
                <p className="text-xs text-slate-500">
                  This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="p-3 bg-rose-50/70 rounded-xl border border-rose-200 text-xs text-rose-900">
              Are you sure you want to permanently delete this {confirmDelete.type}:
              <strong className="block mt-1 font-bold text-slate-900">&ldquo;{confirmDelete.title}&rdquo;</strong>
              {confirmDelete.type === 'course' && (
                <span className="block mt-1 text-[11px] text-rose-700">All associated curriculum modules, lessons, videos, notes, and practice quizzes will be deleted.</span>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                disabled={deletingItem}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteDelete}
                disabled={deletingItem}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
              >
                {deletingItem ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                {deletingItem ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
