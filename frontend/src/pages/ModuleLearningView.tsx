import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Course, Module, Lesson, PracticeTask } from '../types';
import confetti from 'canvas-confetti';
import {
  CheckCircle2,
  FileText,
  Award,
  ArrowRight,
  ArrowLeft,
  Check,
  Copy,
  Flag,
  AlertTriangle,
  BookOpen,
  X,
  Video,
  HelpCircle,
  Clock,
  ExternalLink,
  Sparkles,
  Terminal,
  BookmarkCheck
} from 'lucide-react';

export const ModuleLearningView: React.FC = () => {
  const { courseId, moduleId, slug } = useParams<{ courseId?: string; moduleId?: string; slug?: string }>();

  const [course, setCourse] = useState<Course | null>(null);
  const [currentModule, setCurrentModule] = useState<Module | null>(null);
  const [modulesList, setModulesList] = useState<Module[]>([]);
  const [progressData, setProgressData] = useState<any>(null);
  const [moduleStatus, setModuleStatus] = useState<any>(null);
  const [finalAssessment, setFinalAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Active resource tab per lesson: { [lessonId]: 'video' | 'ai_notes' | 'faculty_notes' | 'practice' }
  const [activeLessonTabs, setActiveLessonTabs] = useState<Record<number, string>>({});

  // Video playback and confirmation state
  const [confirmingVideoId, setConfirmingVideoId] = useState<number | null>(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingVideoId, setReportingVideoId] = useState<number | null>(null);
  const [reportingIssueType, setReportingIssueType] = useState('UNAVAILABLE');
  const [reportingNotes, setReportingNotes] = useState('');
  const [submittingReport, setSubmittingReport] = useState(false);
  const [reportSuccessMessage, setReportSuccessMessage] = useState<string | null>(null);

  // Notes & Interactive state
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const [revealedQuestions, setRevealedQuestions] = useState<{ [key: string]: boolean }>({});
  const [completingMaterialId, setCompletingMaterialId] = useState<number | null>(null);

  // Practice task state: { [practiceId]: { answers: Record<string, string>, submitted: boolean, score: any } }
  const [practiceStates, setPracticeStates] = useState<Record<number, {
    answers: Record<string, string>;
    submitted: boolean;
    score: { score: number; passed: boolean; earned: number; total: number } | null;
  }>>({});
  const [submittingPracticeId, setSubmittingPracticeId] = useState<number | null>(null);

  const fetchModuleData = async () => {
    try {
      setLoading(true);

      // 1. Fetch Course info
      let courseData: Course | null = null;
      if (courseId) {
        const cRes = await apiClient.get<Course>(`/catalogue/courses/by-id/${courseId}/`);
        courseData = cRes.data;
      } else if (slug) {
        const cRes = await apiClient.get<Course>(`/catalogue/courses/${slug}/`);
        courseData = cRes.data;
      }

      if (!courseData) {
        throw new Error('Course could not be identified');
      }
      setCourse(courseData);
      setModulesList(courseData.modules || []);

      // 2. Identify target module
      const targetModId = Number(moduleId);
      let targetModule: Module | undefined = courseData.modules?.find((m) => m.id === targetModId);

      // If not in courseData modules list, fetch directly from module endpoint
      if (!targetModule && targetModId) {
        const mRes = await apiClient.get<Module>(`/catalogue/modules/${targetModId}/`);
        targetModule = mRes.data;
      }

      if (!targetModule && courseData.modules && courseData.modules.length > 0) {
        targetModule = courseData.modules[0];
      }
      setCurrentModule(targetModule || null);

      // 3. Fetch progress and assessment
      if (courseData.slug) {
        const [pRes, aRes] = await Promise.allSettled([
          apiClient.get(`/learning/course-progress/${courseData.slug}/`),
          apiClient.get(`/assessments/course/${courseData.id}/final-assessment/`)
        ]);

        if (pRes.status === 'fulfilled') {
          setProgressData(pRes.value.data);
        }
        if (aRes.status === 'fulfilled') {
          setFinalAssessment(aRes.value.data);
        }
      }

      // 4. Fetch module-specific progress
      if (targetModule) {
        try {
          const modProgRes = await apiClient.get(`/learning/modules/${targetModule.id}/progress/`);
          setModuleStatus(modProgRes.data);
        } catch {
          // Handled gracefully
        }
      }

      // 5. Initialize active tabs for lessons
      if (targetModule?.lessons) {
        const initialTabs: Record<number, string> = {};
        targetModule.lessons.forEach((lsn) => {
          if (lsn.videos && lsn.videos.length > 0) {
            initialTabs[lsn.id] = 'video';
          } else if (lsn.materials && lsn.materials.some(m => m.resource_type === 'AI_STUDY_NOTES')) {
            initialTabs[lsn.id] = 'ai_notes';
          } else if (lsn.materials && lsn.materials.length > 0) {
            initialTabs[lsn.id] = 'faculty_notes';
          } else if (lsn.practice_tasks && lsn.practice_tasks.length > 0) {
            initialTabs[lsn.id] = 'practice';
          } else {
            initialTabs[lsn.id] = 'ai_notes';
          }
        });
        setActiveLessonTabs(initialTabs);
      }
    } catch (err) {
      console.error('Failed to load module learning data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModuleData();
  }, [courseId, moduleId, slug]);

  // Copy code snippet helper
  const handleCopyCode = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(id);
    setTimeout(() => setCopiedSnippet(null), 2500);
  };

  // Video confirmation handler
  const handleConfirmVideo = async (videoId: number) => {
    setConfirmingVideoId(videoId);
    try {
      // 1. Mark video as started if not yet recorded
      try {
        await apiClient.post(`/learning/video/${videoId}/start/`, { video_id: videoId });
      } catch {
        // Safe fallback
      }

      // 2. Confirm completion
      await apiClient.post(`/learning/video/${videoId}/confirm-complete/`, {
        video_id: videoId
      });

      // Update progress state
      setProgressData((prev: any) => ({
        ...prev,
        video_progress: {
          ...(prev?.video_progress || {}),
          [videoId]: { ...(prev?.video_progress?.[videoId] || {}), is_completed: true }
        }
      }));

      // Refresh module status
      if (currentModule) {
        const modRes = await apiClient.get(`/learning/modules/${currentModule.id}/progress/`);
        setModuleStatus(modRes.data);
        if (modRes.data.is_completed) {
          confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } });
        }
      }
    } catch (err) {
      console.error('Failed to confirm video completion:', err);
    } finally {
      setConfirmingVideoId(null);
    }
  };

  // Study material completion handler
  const handleCompleteMaterial = async (materialId: number) => {
    setCompletingMaterialId(materialId);
    try {
      await apiClient.post('/learning/material/complete/', {
        material_id: materialId
      });

      setProgressData((prev: any) => ({
        ...prev,
        material_progress: {
          ...(prev?.material_progress || {}),
          [materialId]: { ...(prev?.material_progress?.[materialId] || {}), is_completed: true }
        }
      }));

      if (currentModule) {
        const modRes = await apiClient.get(`/learning/modules/${currentModule.id}/progress/`);
        setModuleStatus(modRes.data);
        if (modRes.data.is_completed) {
          confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } });
        }
      }
    } catch (err) {
      console.error('Failed to complete study material:', err);
    } finally {
      setCompletingMaterialId(null);
    }
  };

  // Practice answer selection
  const handleSelectPracticeAnswer = (practiceId: number, questionId: string, answer: string) => {
    setPracticeStates((prev) => {
      const existing = prev[practiceId] || { answers: {}, submitted: false, score: null };
      return {
        ...prev,
        [practiceId]: {
          ...existing,
          answers: { ...existing.answers, [questionId]: answer }
        }
      };
    });
  };

  // Submit Practice task
  const handleSubmitPractice = async (task: PracticeTask) => {
    const pState = practiceStates[task.id] || { answers: {}, submitted: false, score: null };
    const questions = task.content?.questions || [];

    if (questions.length === 0) return;
    if (Object.keys(pState.answers).length < questions.length) {
      alert('Please answer all questions before submitting your practice evaluation.');
      return;
    }

    setSubmittingPracticeId(task.id);
    try {
      const res = await apiClient.post('/learning/practice/submit/', {
        practice_id: task.id,
        answers: pState.answers
      });

      setPracticeStates((prev) => ({
        ...prev,
        [task.id]: {
          answers: pState.answers,
          submitted: true,
          score: res.data
        }
      }));

      setProgressData((prev: any) => ({
        ...prev,
        practice_progress: {
          ...(prev?.practice_progress || {}),
          [task.id]: { ...(prev?.practice_progress?.[task.id] || {}), is_completed: res.data.passed }
        }
      }));

      if (currentModule) {
        const modRes = await apiClient.get(`/learning/modules/${currentModule.id}/progress/`);
        setModuleStatus(modRes.data);
        if (modRes.data.is_completed) {
          confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } });
        }
      }
    } catch (err) {
      console.error('Failed to submit practice task:', err);
    } finally {
      setSubmittingPracticeId(null);
    }
  };

  // Handle Video Issue Reporting
  const handleReportVideoIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportingVideoId) return;
    setSubmittingReport(true);
    try {
      await apiClient.post(`/learning/video/${reportingVideoId}/report-unavailable/`, {
        video_id: reportingVideoId,
        issue_type: reportingIssueType,
        notes: reportingNotes
      });
      setReportSuccessMessage('Video issue reported to departmental academic coordinators.');
      setTimeout(() => {
        setIsReportModalOpen(false);
        setReportSuccessMessage(null);
        setReportingNotes('');
      }, 2000);
    } catch (err) {
      console.error('Failed to report video issue:', err);
    } finally {
      setSubmittingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-semibold">Loading module curriculum...</p>
        </div>
      </div>
    );
  }

  if (!currentModule || !course) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center space-y-4">
        <BookOpen className="w-12 h-12 text-slate-300 mx-auto" />
        <h2 className="text-xl font-bold text-slate-800">Module Not Found</h2>
        <p className="text-xs text-slate-500">The requested learning module does not exist or is not published.</p>
        <Link
          to={course?.slug ? `/learn/${course.slug}` : '/catalogue'}
          className="px-4 py-2 bg-primary-900 text-white rounded-xl text-xs font-bold inline-flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Course Modules
        </Link>
      </div>
    );
  }

  // Find next module
  const sortedModules = [...modulesList].sort((a, b) => a.order - b.order);
  const currentIdx = sortedModules.findIndex((m) => m.id === currentModule.id);
  const nextModule = currentIdx >= 0 && currentIdx < sortedModules.length - 1 ? sortedModules[currentIdx + 1] : null;

  // Module completion evaluation
  const isModuleDone =
    moduleStatus?.is_completed ||
    Boolean(progressData?.module_progress?.[currentModule.id]);

  // Overall course assessment unlock check
  const isAllModulesCompleted =
    progressData?.assessment_unlocked === true ||
    progressData?.eligibility?.eligible === true ||
    (progressData?.completed_modules !== undefined &&
      progressData?.total_required_modules !== undefined &&
      progressData.total_required_modules > 0 &&
      progressData.completed_modules >= progressData.total_required_modules);

  const courseReturnUrl = course.slug ? `/learn/${course.slug}` : `/course/${course.id}`;

  return (
    <div className="bg-slate-50 min-h-[90vh] py-8 text-slate-900">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">

        {/* 1. Breadcrumb & Navigation Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-500 flex-wrap">
            <Link to={courseReturnUrl} className="hover:text-primary-900 font-semibold flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{course.title}</span>
            </Link>
            <span>/</span>
            <span className="font-bold text-slate-800">
              Module {currentModule.order}: {currentModule.title}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={courseReturnUrl}
              className="px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold flex items-center gap-1.5 transition-all shadow-2xs"
            >
              <BookOpen className="w-3.5 h-3.5 text-slate-500" />
              <span>All Modules</span>
            </Link>
            {nextModule && (
              <Link
                to={`/courses/${course.id}/modules/${nextModule.id}`}
                className="px-3.5 py-1.5 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold flex items-center gap-1.5 transition-all shadow-xs"
              >
                <span>Next Module: {nextModule.title}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </div>
        </div>

        {/* 2. Module Header Card */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-xl bg-primary-950 text-accent-400 font-extrabold text-xs tracking-wider uppercase">
                Module {currentModule.order}
              </span>
              <span className={`px-2.5 py-0.5 rounded-lg text-xs font-bold border ${
                currentModule.is_required
                  ? 'bg-amber-50 text-amber-900 border-amber-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}>
                {currentModule.is_required ? 'Required for Final Assessment' : 'Optional Module'}
              </span>
            </div>

            {/* Module Completion Badge */}
            {isModuleDone ? (
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 font-bold text-xs shadow-2xs">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>✓ Module Completed</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 font-semibold text-xs">
                <Clock className="w-4 h-4 text-slate-400" />
                <span>In Progress (Complete required activities below)</span>
              </div>
            )}
          </div>

          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            {currentModule.title}
          </h1>

          {currentModule.description && (
            <p className="text-sm text-slate-600 leading-relaxed max-w-4xl">
              {currentModule.description}
            </p>
          )}

          <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-100">
            <span>{currentModule.lessons?.length || 0} Lessons in sequence</span>
            <span>•</span>
            <span>Estimated Duration: {currentModule.duration_minutes || 60} mins</span>
          </div>
        </div>

        {/* 3. Lessons & Structured Curriculum Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-900" />
              Lesson Sequence &amp; Learning Activities
            </h2>
          </div>

          {(!currentModule.lessons || currentModule.lessons.length === 0) ? (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-2">
              <BookOpen className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="font-bold text-slate-800 text-sm">No Lessons Formatted for this Module</h3>
              <p className="text-xs text-slate-500">Learning materials are currently being published by departmental faculty.</p>
            </div>
          ) : (
            currentModule.lessons.map((lesson: Lesson, lIdx: number) => {
              const activeTab = activeLessonTabs[lesson.id] || 'video';
              const setActiveTab = (tab: string) => {
                setActiveLessonTabs((prev) => ({ ...prev, [lesson.id]: tab }));
              };

              // Collect resources
              const video = lesson.videos?.[0];
              const aiNotes = lesson.materials?.find(m => m.resource_type === 'AI_STUDY_NOTES') || lesson.materials?.[0];
              const facultyNotes = lesson.materials?.find(m => m.resource_type !== 'AI_STUDY_NOTES');
              const practice = lesson.practice_tasks?.[0];

              // Resource completion statuses
              const isVidDone = video ? Boolean(progressData?.video_progress?.[video.id]?.is_completed) : true;
              const isNotesDone = aiNotes ? Boolean(progressData?.material_progress?.[aiNotes.id]?.is_completed) : true;
              const isFacultyNotesDone = facultyNotes ? Boolean(progressData?.material_progress?.[facultyNotes.id]?.is_completed) : true;
              const isPracDone = practice ? Boolean(progressData?.practice_progress?.[practice.id]?.is_completed) : true;

              const isLessonFullyDone = isVidDone && isNotesDone && isFacultyNotesDone && isPracDone;

              return (
                <div
                  key={lesson.id}
                  className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden space-y-4"
                >
                  {/* Lesson Header */}
                  <div className="p-6 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100 flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-primary-900 text-white font-bold text-xs flex items-center justify-center">
                          {lesson.order || lIdx + 1}
                        </span>
                        <h3 className="text-base font-bold text-slate-900">
                          {lesson.title}
                        </h3>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${
                          lesson.is_required
                            ? 'bg-amber-50 text-amber-800 border-amber-200'
                            : 'bg-slate-100 text-slate-600 border-slate-200'
                        }`}>
                          {lesson.is_required ? 'Required' : 'Optional'}
                        </span>
                      </div>
                      {lesson.description && (
                        <p className="text-xs text-slate-500 pl-8 leading-relaxed">
                          {lesson.description}
                        </p>
                      )}
                    </div>

                    {isLessonFullyDone ? (
                      <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Lesson Completed
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 font-semibold text-[11px]">
                        In Progress
                      </span>
                    )}
                  </div>

                  {/* Resource Selection Tabs */}
                  <div className="px-6 flex items-center gap-2 border-b border-slate-100 overflow-x-auto text-xs">
                    {video && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('video')}
                        className={`pb-3 px-3 font-bold border-b-2 flex items-center gap-1.5 transition-all cursor-pointer ${
                          activeTab === 'video'
                            ? 'border-primary-900 text-primary-900'
                            : 'border-transparent text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <Video className="w-4 h-4" />
                        <span>Video Lecture</span>
                        {isVidDone && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                      </button>
                    )}

                    {aiNotes && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('ai_notes')}
                        className={`pb-3 px-3 font-bold border-b-2 flex items-center gap-1.5 transition-all cursor-pointer ${
                          activeTab === 'ai_notes'
                            ? 'border-primary-900 text-primary-900'
                            : 'border-transparent text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <Sparkles className="w-4 h-4 text-violet-600" />
                        <span>AI Revision Notes</span>
                        {isNotesDone && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                      </button>
                    )}

                    {facultyNotes && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('faculty_notes')}
                        className={`pb-3 px-3 font-bold border-b-2 flex items-center gap-1.5 transition-all cursor-pointer ${
                          activeTab === 'faculty_notes'
                            ? 'border-primary-900 text-primary-900'
                            : 'border-transparent text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <FileText className="w-4 h-4 text-amber-600" />
                        <span>Faculty Notes &amp; PDF</span>
                        {isFacultyNotesDone && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                      </button>
                    )}

                    {practice && (
                      <button
                        type="button"
                        onClick={() => setActiveTab('practice')}
                        className={`pb-3 px-3 font-bold border-b-2 flex items-center gap-1.5 transition-all cursor-pointer ${
                          activeTab === 'practice'
                            ? 'border-primary-900 text-primary-900'
                            : 'border-transparent text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        <BookmarkCheck className="w-4 h-4 text-emerald-600" />
                        <span>Practice Challenge</span>
                        {isPracDone && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                      </button>
                    )}
                  </div>

                  {/* Active Resource Content Box */}
                  <div className="p-6 pt-2">
                    {/* TAB 1: VIDEO */}
                    {activeTab === 'video' && video && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <h4 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                            <Video className="w-4 h-4 text-primary-900" />
                            {video.title}
                          </h4>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                setReportingVideoId(video.id);
                                setIsReportModalOpen(true);
                              }}
                              className="text-[11px] text-slate-400 hover:text-rose-600 font-semibold flex items-center gap-1"
                            >
                              <Flag className="w-3 h-3" /> Report Issue
                            </button>
                          </div>
                        </div>

                        {/* Video Player */}
                        <div className="relative aspect-video rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shadow-md">
                          {video.youtube_video_id ? (
                            <iframe
                              src={`https://www.youtube-nocookie.com/embed/${video.youtube_video_id}?rel=0&enablejsapi=1`}
                              title={video.title}
                              className="w-full h-full border-0"
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowFullScreen
                            />
                          ) : video.external_url ? (
                            <video
                              src={video.external_url}
                              controls
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-slate-400 gap-2">
                              <Video className="w-10 h-10" />
                              <span className="text-xs">Video content being formatted</span>
                            </div>
                          )}
                        </div>

                        {/* Video Actions & Completion Bar */}
                        <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-2xl border border-slate-200">
                          <div className="flex items-center gap-2">
                            {isVidDone ? (
                              <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100/80 px-2.5 py-1 rounded-xl">
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                Video Lecture Watched &amp; Completed
                              </span>
                            ) : (
                              <span className="text-xs text-slate-600 font-medium">
                                Watch the complete lecture to unlock learning progress.
                              </span>
                            )}
                          </div>

                          <button
                            type="button"
                            onClick={() => handleConfirmVideo(video.id)}
                            disabled={confirmingVideoId === video.id || isVidDone}
                            className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-xs ${
                              isVidDone
                                ? 'bg-slate-100 text-slate-400 cursor-default'
                                : 'bg-primary-900 hover:bg-primary-800 text-white'
                            }`}
                          >
                            <Check className="w-3.5 h-3.5" />
                            {confirmingVideoId === video.id
                              ? 'Confirming...'
                              : isVidDone
                              ? 'Completed'
                              : 'Confirm Video Watched'}
                          </button>
                        </div>
                      </div>
                    )}

                    {/* TAB 2: AI STUDY NOTES */}
                    {activeTab === 'ai_notes' && aiNotes && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="space-y-0.5">
                            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                              <Sparkles className="w-4 h-4 text-violet-600" />
                              {aiNotes.title}
                            </h4>
                            <span className="text-[10px] text-slate-400 font-medium">
                              Curriculum-grounded high-distraction elimination &amp; engineering notes
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleCompleteMaterial(aiNotes.id)}
                            disabled={completingMaterialId === aiNotes.id || isNotesDone}
                            className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-xs ${
                              isNotesDone
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
                                : 'bg-primary-900 hover:bg-primary-800 text-white'
                            }`}
                          >
                            <Check className="w-3.5 h-3.5" />
                            {completingMaterialId === aiNotes.id
                              ? 'Saving...'
                              : isNotesDone
                              ? '✓ AI Notes Completed'
                              : 'Mark AI Notes as Read'}
                          </button>
                        </div>

                        {/* Structured AI Notes Sections */}
                        {aiNotes.structured_content ? (
                          <div className="space-y-4 text-xs leading-relaxed text-slate-700 bg-slate-50 p-5 rounded-2xl border border-slate-200">
                            {/* Key Concept Summary */}
                            {aiNotes.structured_content.key_takeaways && (
                              <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-2">
                                <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                                  <BookmarkCheck className="w-4 h-4 text-primary-800" />
                                  Essential Takeaways
                                </h5>
                                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                                  {aiNotes.structured_content.key_takeaways.map((t: string, tIdx: number) => (
                                    <li key={tIdx}>{t}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Detailed Text / Theory */}
                            {aiNotes.text_content && (
                              <div className="prose prose-sm max-w-none text-slate-800 whitespace-pre-wrap font-sans">
                                {aiNotes.text_content}
                              </div>
                            )}

                            {/* Code Snippets */}
                            {aiNotes.structured_content.code_snippets && aiNotes.structured_content.code_snippets.length > 0 && (
                              <div className="space-y-2">
                                <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                                  <Terminal className="w-4 h-4 text-accent-500" />
                                  Implementation Code Examples
                                </h5>
                                {aiNotes.structured_content.code_snippets.map((snip: any, sIdx: number) => (
                                  <div key={sIdx} className="bg-slate-950 text-slate-100 rounded-xl overflow-hidden border border-slate-800">
                                    <div className="bg-slate-900 px-4 py-2 flex items-center justify-between text-[11px] text-slate-400">
                                      <span>{snip.title || `Snippet #${sIdx + 1}`} ({snip.language || 'code'})</span>
                                      <button
                                        type="button"
                                        onClick={() => handleCopyCode(snip.code, `snip-${sIdx}`)}
                                        className="hover:text-white flex items-center gap-1 cursor-pointer font-semibold"
                                      >
                                        <Copy className="w-3.5 h-3.5" />
                                        {copiedSnippet === `snip-${sIdx}` ? 'Copied!' : 'Copy'}
                                      </button>
                                    </div>
                                    <pre className="p-4 overflow-x-auto text-xs font-mono text-emerald-400">
                                      {snip.code}
                                    </pre>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Common Pitfalls & Traps */}
                            {aiNotes.structured_content.common_mistakes && aiNotes.structured_content.common_mistakes.length > 0 && (
                              <div className="p-4 bg-amber-50/70 rounded-xl border border-amber-200 space-y-2">
                                <h5 className="font-bold text-amber-950 flex items-center gap-1.5">
                                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                                  Common Engineering Pitfalls &amp; Exam Traps
                                </h5>
                                <div className="space-y-2">
                                  {aiNotes.structured_content.common_mistakes.map((mistake: any, mIdx: number) => (
                                    <div key={mIdx} className="text-[11px] space-y-1 bg-white p-3 rounded-lg border border-amber-200">
                                      <div><strong className="text-rose-700">Mistake:</strong> {mistake.common_pitfall || mistake.mistake}</div>
                                      <div><strong className="text-emerald-700">Resolution:</strong> {mistake.recommended_solution || mistake.correct}</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Self-check questions */}
                            {aiNotes.structured_content.self_check_questions && (
                              <div className="space-y-2 pt-2">
                                <h5 className="font-bold text-slate-900 flex items-center gap-1.5">
                                  <HelpCircle className="w-4 h-4 text-primary-900" />
                                  Concept Self-Check Questions
                                </h5>
                                <div className="space-y-2">
                                  {aiNotes.structured_content.self_check_questions.map((sc: any, scIdx: number) => {
                                    const qKey = `${aiNotes.id}-${scIdx}`;
                                    const isRev = Boolean(revealedQuestions[qKey]);
                                    return (
                                      <div key={scIdx} className="p-3 bg-white rounded-xl border border-slate-200 text-xs space-y-2">
                                        <div className="font-semibold text-slate-800">
                                          Q{scIdx + 1}: {sc.question}
                                        </div>
                                        <button
                                          type="button"
                                          onClick={() => setRevealedQuestions(prev => ({ ...prev, [qKey]: !isRev }))}
                                          className="text-[11px] font-bold text-primary-900 hover:underline cursor-pointer"
                                        >
                                          {isRev ? 'Hide Answer' : 'Reveal Solution & Explanation'}
                                        </button>
                                        {isRev && (
                                          <div className="p-2.5 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-900 font-medium">
                                            {sc.answer}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-700 whitespace-pre-wrap font-mono">
                            {aiNotes.text_content || 'Comprehensive study notes available.'}
                          </div>
                        )}
                      </div>
                    )}

                    {/* TAB 3: FACULTY NOTES / HANDBOOK */}
                    {activeTab === 'faculty_notes' && facultyNotes && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <h4 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                            <FileText className="w-4 h-4 text-amber-600" />
                            {facultyNotes.title}
                          </h4>

                          <button
                            type="button"
                            onClick={() => handleCompleteMaterial(facultyNotes.id)}
                            disabled={completingMaterialId === facultyNotes.id || isFacultyNotesDone}
                            className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-xs ${
                              isFacultyNotesDone
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
                                : 'bg-primary-900 hover:bg-primary-800 text-white'
                            }`}
                          >
                            <Check className="w-3.5 h-3.5" />
                            {isFacultyNotesDone ? '✓ Faculty Notes Completed' : 'Mark Notes as Read'}
                          </button>
                        </div>

                        <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 space-y-4 text-xs">
                          {facultyNotes.description && (
                            <p className="text-slate-600 leading-relaxed">{facultyNotes.description}</p>
                          )}

                          {facultyNotes.text_content && (
                            <div className="p-4 bg-white rounded-xl border border-slate-200 whitespace-pre-wrap font-sans text-slate-800">
                              {facultyNotes.text_content}
                            </div>
                          )}

                          {facultyNotes.external_url && (
                            <div className="pt-2">
                              <a
                                href={facultyNotes.external_url}
                                target="_blank"
                                rel="noreferrer"
                                className="px-4 py-2 bg-white border border-slate-300 hover:bg-slate-100 rounded-xl font-bold text-primary-900 inline-flex items-center gap-1.5 shadow-2xs"
                              >
                                <ExternalLink className="w-4 h-4" /> Open Institutional Handbook / Resource
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* TAB 4: PRACTICE TASK */}
                    {activeTab === 'practice' && practice && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div>
                            <h4 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                              <BookmarkCheck className="w-4 h-4 text-emerald-600" />
                              {practice.title}
                            </h4>
                            <span className="text-[10px] text-slate-500 font-semibold">
                              Passing Criterion: {practice.pass_score || 70}% required
                            </span>
                          </div>

                          {isPracDone && (
                            <span className="px-3 py-1 rounded-xl bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center gap-1">
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              Practice Evaluation Passed
                            </span>
                          )}
                        </div>

                        {/* Questions list */}
                        <div className="space-y-4 text-xs">
                          {(practice.content?.questions || []).map((q: any, qIdx: number) => {
                            const pState = practiceStates[practice.id] || { answers: {}, submitted: false, score: null };
                            const selectedAnswer = pState.answers[q.id];
                            return (
                              <div key={q.id || qIdx} className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                                <div className="font-bold text-slate-800 text-xs">
                                  Question {qIdx + 1}: {q.question}
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                  {(q.options || []).map((opt: string, oIdx: number) => {
                                    const optLabel = String.fromCharCode(65 + oIdx);
                                    const isSelected = selectedAnswer === opt;
                                    return (
                                      <button
                                        key={oIdx}
                                        type="button"
                                        onClick={() => handleSelectPracticeAnswer(practice.id, q.id, opt)}
                                        className={`p-3 rounded-xl border text-left flex items-center gap-2 transition-all cursor-pointer ${
                                          isSelected
                                            ? 'bg-primary-900 text-white border-primary-900 shadow-xs'
                                            : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700'
                                        }`}
                                      >
                                        <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] ${
                                          isSelected ? 'bg-white text-primary-900' : 'bg-slate-200 text-slate-600'
                                        }`}>
                                          {optLabel}
                                        </span>
                                        <span className="font-medium text-xs flex-grow">{opt}</span>
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })}

                          {/* Submit practice button */}
                          <div className="flex items-center justify-between pt-2">
                            <div className="text-xs">
                              {practiceStates[practice.id]?.score && (
                                <span className={`font-bold px-3 py-1 rounded-xl ${
                                  practiceStates[practice.id]?.score?.passed
                                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                    : 'bg-rose-100 text-rose-800 border border-rose-300'
                                }`}>
                                  Score: {practiceStates[practice.id]?.score?.score}% • {practiceStates[practice.id]?.score?.passed ? 'PASSED' : 'RETRY REQUIRED'}
                                </span>
                              )}
                            </div>

                            <button
                              type="button"
                              onClick={() => handleSubmitPractice(practice)}
                              disabled={submittingPracticeId === practice.id}
                              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-xs flex items-center gap-1.5 transition-all cursor-pointer text-xs"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                              {submittingPracticeId === practice.id ? 'Evaluating...' : 'Submit Practice Challenge'}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* 4. Bottom Completion & Progression Card */}
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                {isModuleDone ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>✓ Module Completed</span>
                  </>
                ) : (
                  <>
                    <Clock className="w-5 h-5 text-slate-400" />
                    <span>Module In Progress</span>
                  </>
                )}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {isModuleDone
                  ? 'All required lessons and activities in this module have been verified.'
                  : 'Complete all required lessons, watch lecture videos, and finish practice tasks to complete this module.'}
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                to={courseReturnUrl}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs flex items-center gap-1.5 transition-all"
              >
                <BookOpen className="w-4 h-4" /> Return to Course Modules
              </Link>
              {nextModule && (
                <Link
                  to={`/courses/${course.id}/modules/${nextModule.id}`}
                  className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md transition-all"
                >
                  <span>Next Module ({nextModule.order})</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              )}
            </div>
          </div>

          {/* If all modules in the course are completed, show Final Assessment Unlocked banner */}
          {isAllModulesCompleted && (
            <div className="mt-4 p-5 bg-gradient-to-r from-emerald-500/15 via-teal-500/15 to-emerald-500/15 border-2 border-emerald-500 rounded-2xl flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5 text-emerald-700" />
                  <span className="font-extrabold text-emerald-950 text-sm">
                    ✓ All Modules Completed
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-600 text-white font-bold text-[10px]">
                    Final Assessment Unlocked
                  </span>
                </div>
                <p className="text-xs text-emerald-800">
                  You have fulfilled all required curriculum standards. You are now eligible to attempt the proctored final examination and earn your verified certificate.
                </p>
              </div>

              {finalAssessment && (
                <Link
                  to={`/assessments/${finalAssessment.id}/preflight`}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-black rounded-xl text-xs shadow-md flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
                >
                  <Award className="w-4 h-4" />
                  <span>Start Final Assessment</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Video Issue Report Modal */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Flag className="w-4 h-4 text-rose-600" />
                <h3 className="font-bold text-slate-900 text-sm">Report Video Lecture Issue</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsReportModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {reportSuccessMessage ? (
              <div className="p-4 bg-emerald-50 text-emerald-800 font-bold rounded-xl text-center">
                {reportSuccessMessage}
              </div>
            ) : (
              <form onSubmit={handleReportVideoIssue} className="space-y-4">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Issue Category</label>
                  <select
                    value={reportingIssueType}
                    onChange={(e) => setReportingIssueType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-semibold"
                  >
                    <option value="UNAVAILABLE">Video Removed / Video Unavailable</option>
                    <option value="GEO_BLOCKED">Geographically Restricted</option>
                    <option value="LOW_AUDIO">Inaudible / Low Quality Audio</option>
                    <option value="OFF_TOPIC">Content Mismatch / Out of Syllabus</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Additional Details (Optional)</label>
                  <textarea
                    rows={3}
                    value={reportingNotes}
                    onChange={(e) => setReportingNotes(e.target.value)}
                    placeholder="Describe what error appears on playback..."
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsReportModalOpen(false)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 font-bold rounded-xl cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReport}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-xs cursor-pointer"
                  >
                    {submittingReport ? 'Reporting...' : 'Submit Report'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
