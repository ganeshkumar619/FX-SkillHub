import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { Course, Module, Lesson, VideoResource, StudyMaterial, PracticeTask } from '../types';
import confetti from 'canvas-confetti';
import {
  CheckCircle2,
  Circle,
  PlayCircle,
  FileText,
  Award,
  Lock,
  AlertCircle,
  HelpCircle,
  Clock,
  ArrowRight,
  ArrowLeft,
  Check,
  Target,
  Copy,
  Flag,
  AlertTriangle,
  BookOpen,
  X,
  Layers,
  Code2,
  RotateCcw,
  Menu,
  ChevronRight,
  ChevronLeft,
  Search,
  Sparkles,
  Video
} from 'lucide-react';

export const CourseViewer: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [activeModuleIndex, setActiveModuleIndex] = useState<number>(0);
  const [activeLessonIndex, setActiveLessonIndex] = useState<number>(0);
  const [progressData, setProgressData] = useState<any>(null);
  const [finalAssessment, setFinalAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Active resource tab: 'material' (default) | 'video' | 'practice'
  const [activeTab, setActiveTab] = useState<'material' | 'video' | 'practice'>('material');

  // Sidebar toggle & search
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Video playback state
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [confirmingVideo, setConfirmingVideo] = useState(false);

  // Video issue reporting modal
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportingIssueType, setReportingIssueType] = useState('UNAVAILABLE');
  const [reportingNotes, setReportingNotes] = useState('');
  const [submittingReport, setSubmittingReport] = useState(false);
  const [reportSuccessMessage, setReportSuccessMessage] = useState<string | null>(null);

  // Study material interactive helpers
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const [revealedQuestions, setRevealedQuestions] = useState<{ [key: number]: boolean }>({});

  // Practice quiz state
  const [practiceAnswers, setPracticeAnswers] = useState<Record<string, string>>({});
  const [practiceSubmitted, setPracticeSubmitted] = useState(false);
  const [practiceScore, setPracticeScore] = useState<{ score: number; passed: boolean; earned: number; total: number } | null>(null);
  const [submittingPractice, setSubmittingPractice] = useState(false);
  const [completingMaterial, setCompletingMaterial] = useState(false);
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);

  const fetchCourseData = async () => {
    try {
      const cRes = await apiClient.get<Course>(`/catalogue/courses/${slug}/`);
      setCourse(cRes.data);

      const pRes = await apiClient.get(`/learning/course-progress/${slug}/`);
      setProgressData(pRes.data);

      // Auto-select first incomplete module on load
      if (pRes.data?.current_module_id && cRes.data?.modules) {
        const targetIdx = cRes.data.modules.findIndex((m: any) => m.id === pRes.data.current_module_id);
        if (targetIdx >= 0) {
          setActiveModuleIndex(targetIdx);
        }
      }

      try {
        const aRes = await apiClient.get(`/assessments/course/${cRes.data.id}/final-assessment/`);
        setFinalAssessment(aRes.data);
      } catch {
        setFinalAssessment(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourseData();
  }, [slug]);

  // Reset practice, scene state, and lesson index when switching modules
  useEffect(() => {
    setPracticeAnswers({});
    setPracticeSubmitted(false);
    setPracticeScore(null);
    setRevealedQuestions({});
    setActiveSceneIndex(0);
    setActiveLessonIndex(0);
  }, [activeModuleIndex]);

  // Reset practice and scene state when switching lessons
  useEffect(() => {
    setPracticeAnswers({});
    setPracticeSubmitted(false);
    setPracticeScore(null);
    setRevealedQuestions({});
    setActiveSceneIndex(0);
  }, [activeLessonIndex]);

  const modules: Module[] = course?.modules || [];
  const activeModule: Module | undefined = modules[activeModuleIndex];
  const lessons: Lesson[] = activeModule?.lessons || [];
  const currentLesson: Lesson | undefined = lessons[activeLessonIndex] || lessons[0];

  // Current lesson/module resources (prioritize currentLesson, fall back to activeModule)
  const currentVideo: VideoResource | undefined = currentLesson?.videos?.[0] || activeModule?.videos?.[0];
  const availableMaterials: StudyMaterial[] = (currentLesson?.materials && currentLesson.materials.length > 0)
    ? currentLesson.materials
    : (activeModule?.materials || []);
  const currentMaterial: StudyMaterial | undefined =
    availableMaterials.find(
      (m) => (m.structured_content && Object.keys(m.structured_content).length > 0) || Boolean(m.text_content)
    ) || availableMaterials[0];
  const currentPractice: PracticeTask | undefined = currentLesson?.practice_tasks?.[0] || activeModule?.practice_tasks?.[0];

  // Helper to determine if a lesson has all required components complete
  const isLessonDone = (l: Lesson) => {
    const lVid = l.videos?.[0];
    const lMat = l.materials?.[0];
    const lPrac = l.practice_tasks?.[0];
    const vDone = lVid ? (l.requires_video ? Boolean(progressData?.video_progress?.[lVid.id]?.is_completed) : true) : true;
    const mDone = lMat ? (l.requires_notes ? Boolean(progressData?.material_progress?.[lMat.id]?.is_completed) : true) : true;
    const pDone = lPrac ? (l.requires_practice ? Boolean(progressData?.practice_progress?.[lPrac.id]?.is_completed) : true) : true;
    return vDone && mDone && pDone;
  };

  // Completion statuses
  const isVideoDone = currentVideo ? Boolean(progressData?.video_progress?.[currentVideo.id]?.is_completed) : true;
  const isMaterialDone = currentMaterial ? Boolean(progressData?.material_progress?.[currentMaterial.id]?.is_completed) : true;
  const isPracticeDone = currentPractice ? Boolean(progressData?.practice_progress?.[currentPractice.id]?.is_completed) : true;
  const isCurrentModuleComplete =
    Boolean(progressData?.module_progress?.[activeModule?.id || 0]) ||
    (isMaterialDone && isPracticeDone && (!currentVideo?.is_required || isVideoDone));

  const totalCourseProgress = progressData?.progress_percent || 0;
  const isAssessmentUnlocked =
    progressData?.eligibility?.eligible === true ||
    progressData?.assessment_unlocked === true ||
    totalCourseProgress >= 100;

  // Filter modules by search
  const filteredModules = modules.filter(m =>
    m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.topic_tag.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Copy code helper
  const handleCopyCode = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(id);
    setTimeout(() => setCopiedSnippet(null), 2500);
  };

  // Complete study material
  const handleCompleteMaterial = async () => {
    if (!currentMaterial) return;
    setCompletingMaterial(true);
    try {
      const res = await apiClient.post('/learning/material/complete/', {
        material_id: currentMaterial.id
      });
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 }
      });
      setProgressData((prev: any) => {
        const matDone = true;
        const pracDone = currentPractice ? Boolean(prev?.practice_progress?.[currentPractice.id]?.is_completed) : true;
        const vidDone = currentVideo ? Boolean(prev?.video_progress?.[currentVideo.id]?.is_completed) : true;
        const modDone = Boolean(res.data.module_completed) || (matDone && pracDone && (!currentVideo?.is_required || vidDone));
        const newProgress = res.data.course_progress ?? prev?.progress_percent;
        const unlocked = Boolean(res.data.assessment_unlocked) || newProgress >= 100;
        return {
          ...prev,
          material_progress: {
            ...prev?.material_progress,
            [currentMaterial.id]: {
              is_completed: true,
              completed_at: new Date().toISOString()
            }
          },
          module_progress: {
            ...prev?.module_progress,
            [activeModule?.id || 0]: modDone || prev?.module_progress?.[activeModule?.id || 0]
          },
          progress_percent: newProgress,
          assessment_unlocked: unlocked,
          eligibility: { eligible: unlocked }
        };
      });
    } catch (err) {
      console.error('Error completing material:', err);
    } finally {
      setCompletingMaterial(false);
    }
  };

  // Complete video
  const handleConfirmVideoWatched = async () => {
    if (!currentVideo) return;
    setConfirmingVideo(true);
    try {
      const res = await apiClient.post('/learning/video/progress/', {
        video_id: currentVideo.id,
        current_seconds: currentVideo.duration_seconds || 300,
        watched_seconds: currentVideo.duration_seconds || 300,
        watch_percentage: 100,
        is_completed: true
      });
      confetti({
        particleCount: 40,
        spread: 50,
        origin: { y: 0.7 }
      });
      setProgressData((prev: any) => {
        const matDone = currentMaterial ? Boolean(prev?.material_progress?.[currentMaterial.id]?.is_completed) : true;
        const pracDone = currentPractice ? Boolean(prev?.practice_progress?.[currentPractice.id]?.is_completed) : true;
        const vidDone = true;
        const modDone = Boolean(res.data.module_completed) || (matDone && pracDone && vidDone);
        const newProgress = res.data.course_progress ?? prev?.progress_percent;
        const unlocked = Boolean(res.data.assessment_unlocked) || newProgress >= 100;
        return {
          ...prev,
          video_progress: {
            ...prev?.video_progress,
            [currentVideo.id]: {
              is_completed: true,
              watch_percentage: 100
            }
          },
          module_progress: {
            ...prev?.module_progress,
            [activeModule?.id || 0]: modDone || prev?.module_progress?.[activeModule?.id || 0]
          },
          progress_percent: newProgress,
          assessment_unlocked: unlocked,
          eligibility: { eligible: unlocked }
        };
      });
    } catch (err) {
      console.error('Error completing video:', err);
    } finally {
      setConfirmingVideo(false);
    }
  };

  // Helper to resolve question key
  const getQuestionKey = (q: any, idx: number): string => {
    if (q.id !== undefined && q.id !== null) return String(q.id);
    return String(idx);
  };

  // Helper to resolve correct option details (index, text, letter, raw value)
  const getCorrectOptionDetails = (q: any) => {
    const options: string[] = Array.isArray(q.options) ? q.options : [];
    const rawCorrect =
      q.correct_option !== undefined && q.correct_option !== null
        ? String(q.correct_option).trim()
        : q.correct_answer !== undefined && q.correct_answer !== null
        ? String(q.correct_answer).trim()
        : '';

    let correctIndex = -1;

    // 1. Single letter 'A', 'B', 'C', 'D' (or lowercase)
    if (/^[A-Za-z]$/.test(rawCorrect)) {
      const idx = rawCorrect.toUpperCase().charCodeAt(0) - 65;
      if (idx >= 0 && idx < options.length) {
        correctIndex = idx;
      }
    }

    // 2. Numeric 0-based index
    if (correctIndex === -1 && !isNaN(Number(rawCorrect)) && rawCorrect !== '') {
      const idx = Number(rawCorrect);
      if (idx >= 0 && idx < options.length) {
        correctIndex = idx;
      }
    }

    // 3. Match against option text
    if (correctIndex === -1) {
      const idx = options.findIndex((o) => String(o).trim().toLowerCase() === rawCorrect.toLowerCase());
      if (idx !== -1) {
        correctIndex = idx;
      }
    }

    const correctText = correctIndex >= 0 ? options[correctIndex] : rawCorrect;
    const correctLetter = correctIndex >= 0 ? String.fromCharCode(65 + correctIndex) : '';

    return { correctIndex, correctText, correctLetter, rawCorrect };
  };

  // Helper to check if a student answer is correct for question q
  const isStudentAnswerCorrect = (q: any, studentAns: any): boolean => {
    if (studentAns === undefined || studentAns === null) return false;
    const details = getCorrectOptionDetails(q);
    const ansStr = String(studentAns).trim().toLowerCase();

    // Direct match with raw correct
    if (ansStr === details.rawCorrect.toLowerCase()) return true;

    // Match with correctText
    if (details.correctText && ansStr === details.correctText.trim().toLowerCase()) return true;

    // Match with correctLetter
    if (details.correctLetter && ansStr === details.correctLetter.toLowerCase()) return true;

    // If studentAns is option text, check if its index matches correctIndex
    if (details.correctIndex >= 0 && Array.isArray(q.options)) {
      const selectedIdx = q.options.findIndex((o: string) => String(o).trim().toLowerCase() === ansStr);
      if (selectedIdx === details.correctIndex) return true;
    }

    return false;
  };

  // Submit practice task
  const handleSubmitPractice = async () => {
    if (!currentPractice) return;
    const questions = currentPractice.content?.questions || [];
    if (questions.length === 0) return;

    // Verify all questions are answered
    const unanswered = questions.some((q: any, idx: number) => {
      const key = getQuestionKey(q, idx);
      return practiceAnswers[key] === undefined || practiceAnswers[key] === null;
    });

    if (unanswered) {
      alert('Please answer all questions before submitting.');
      return;
    }

    setSubmittingPractice(true);
    try {
      let earned = 0;
      const formattedAnswers: Record<string, any> = {};

      questions.forEach((q: any, idx: number) => {
        const qKey = getQuestionKey(q, idx);
        const selected = practiceAnswers[qKey];
        if (isStudentAnswerCorrect(q, selected)) {
          earned += 1;
        }
        formattedAnswers[qKey] = selected;
        if (q.id !== undefined && q.id !== null) {
          formattedAnswers[String(q.id)] = selected;
        }
        formattedAnswers[String(idx)] = selected;
      });

      const score = Math.round((earned / questions.length) * 100);
      const passed = score >= (currentPractice.pass_score || 70);

      const res = await apiClient.post('/learning/practice/submit/', {
        practice_id: currentPractice.id,
        score,
        is_completed: passed,
        answers: formattedAnswers
      });

      setPracticeScore({ score, passed, earned, total: questions.length });
      setPracticeSubmitted(true);

      if (passed) {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 }
        });
        setProgressData((prev: any) => {
          const matDone = currentMaterial ? Boolean(prev?.material_progress?.[currentMaterial.id]?.is_completed) : true;
          const pracDone = true;
          const vidDone = currentVideo ? Boolean(prev?.video_progress?.[currentVideo.id]?.is_completed) : true;
          const modDone = Boolean(res.data.module_completed) || (matDone && pracDone && (!currentVideo?.is_required || vidDone));
          const newProgress = res.data.course_progress ?? prev?.progress_percent;
          const unlocked = Boolean(res.data.assessment_unlocked) || newProgress >= 100;
          return {
            ...prev,
            practice_progress: {
              ...prev?.practice_progress,
              [currentPractice.id]: {
                is_completed: true,
                score
              }
            },
            module_progress: {
              ...prev?.module_progress,
              [activeModule?.id || 0]: modDone || prev?.module_progress?.[activeModule?.id || 0]
            },
            progress_percent: newProgress,
            assessment_unlocked: unlocked,
            eligibility: { eligible: unlocked }
          };
        });
      }
    } catch (err) {
      console.error('Error submitting practice:', err);
    } finally {
      setSubmittingPractice(false);
    }
  };

  // Navigation handlers (lesson-aware)
  const handleNext = () => {
    if (lessons.length > 0 && activeLessonIndex < lessons.length - 1) {
      setActiveLessonIndex(activeLessonIndex + 1);
      setActiveTab('material');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (activeModuleIndex < modules.length - 1) {
      setActiveModuleIndex(activeModuleIndex + 1);
      setActiveLessonIndex(0);
      setActiveTab('material');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    if (lessons.length > 0 && activeLessonIndex > 0) {
      setActiveLessonIndex(activeLessonIndex - 1);
      setActiveTab('material');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (activeModuleIndex > 0) {
      const prevIdx = activeModuleIndex - 1;
      setActiveModuleIndex(prevIdx);
      const prevLessons = modules[prevIdx]?.lessons || [];
      setActiveLessonIndex(prevLessons.length > 0 ? prevLessons.length - 1 : 0);
      setActiveTab('material');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };


  // Report video issue handler
  const handleReportVideoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentVideo) return;
    setSubmittingReport(true);
    try {
      await apiClient.post('/catalogue/admin/reported-videos/', {
        video: currentVideo.id,
        issue_type: reportingIssueType,
        notes: reportingNotes
      });
      setReportSuccessMessage('Issue reported successfully. Faculty will review.');
      setTimeout(() => {
        setIsReportModalOpen(false);
        setReportSuccessMessage(null);
        setReportingNotes('');
      }, 2000);
    } catch (err) {
      console.error(err);
    } finally {
      setSubmittingReport(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center text-slate-800">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-sm font-semibold tracking-wide text-slate-500">Loading Interactive Learning Workspace...</p>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-6 text-center">
        <div className="max-w-md space-y-4">
          <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
          <h2 className="text-xl font-bold text-slate-800">Course Not Found</h2>
          <Link to="/catalogue" className="inline-block px-4 py-2 bg-primary-900 text-white rounded-lg font-bold text-sm">
            Return to Catalogue
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-primary-900 selection:text-white">
      {/* 1. TOP INSTITUTIONAL APP BAR */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 lg:px-8 py-3 flex items-center justify-between gap-4 shadow-xs">
        {/* Left: Sidebar Toggle & Course Info */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition cursor-pointer shrink-0"
            title="Toggle Curriculum Drawer"
          >
            <Menu className="w-4 h-4" />
          </button>

          <Link
            to="/catalogue"
            className="text-xs font-semibold text-primary-900 hover:text-primary-700 transition flex items-center gap-1 shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Catalogue</span>
          </Link>

          <span className="text-slate-300 hidden sm:inline">•</span>

          <div className="min-w-0">
            <h1 className="text-sm font-bold text-slate-900 truncate max-w-xs md:max-w-md">
              {course.title}
            </h1>
            <div className="text-[11px] text-slate-500 flex items-center gap-2 truncate">
              <span className="text-primary-900 font-bold">Module {activeModule?.order || 1} of {modules.length}:</span>
              <span className="truncate text-slate-700 font-medium">{activeModule?.title}</span>
            </div>
          </div>
        </div>

        {/* Right: Progress & Assessment Unlock CTA */}
        <div className="flex items-center gap-3 sm:gap-5 shrink-0">
          {/* Progress Bar Gauge & Breakdown */}
          <div className="hidden md:flex items-center gap-3 bg-slate-100 px-3.5 py-1.5 rounded-full border border-slate-200">
            <div className="text-[11px] font-semibold text-slate-700 flex items-center gap-2">
              <span>Modules: <strong className="text-primary-900">{progressData?.completed_modules || 0}/{modules.length}</strong></span>
              <span className="text-slate-300">•</span>
              <span>Progress: <strong className="text-emerald-700 font-black">{totalCourseProgress}%</strong></span>
            </div>
            <div className="w-24 bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${totalCourseProgress}%` }}
              />
            </div>
          </div>

          {/* Certification Exam Button */}
          {isAssessmentUnlocked ? (
            <Link
              to={`/assessments/${finalAssessment?.id}/preflight`}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-black text-xs flex items-center gap-1.5 shadow-md hover:shadow-lg ring-2 ring-emerald-400/50 animate-pulse transition-all cursor-pointer"
            >
              <Award className="w-4 h-4 text-amber-300" />
              <span>Final Exam Ready</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <div className="px-3 py-1.5 rounded-xl bg-slate-100 text-slate-600 border border-slate-200 text-xs font-semibold flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-amber-600" />
              <span className="hidden sm:inline">Final Exam Locked ({totalCourseProgress}%)</span>
              <span className="sm:hidden">{totalCourseProgress}%</span>
            </div>
          )}
        </div>
      </header>

      {/* 2. BODY WORKSPACE: SIDEBAR + MAIN LEARNING CANVAS */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SYLLABUS DRAWER */}
        <aside
          className={`fixed inset-y-0 left-0 z-30 lg:static w-80 bg-white border-r border-slate-200 flex flex-col transition-all duration-300 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:-ml-80'
          }`}
        >
          {/* Drawer Header & Search */}
          <div className="p-4 border-b border-slate-200 space-y-3 bg-slate-50/60">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-primary-900" />
                Course Curriculum
              </span>
              <span className="text-xs font-bold text-primary-900 bg-primary-50 px-2 py-0.5 rounded border border-primary-200">
                {Object.values(progressData?.module_progress || {}).filter(Boolean).length}/{modules.length} Done
              </span>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search topics..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-2 rounded-lg bg-white border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-900/20 focus:border-primary-900 transition"
              />
            </div>
          </div>

          {/* Modules List */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {filteredModules.map((m) => {
              const origIdx = modules.findIndex((x) => x.id === m.id);
              const mMat = m.materials?.[0];
              const mPrac = m.practice_tasks?.[0];
              const mVid = m.videos?.[0];

              const isMatDone = mMat ? Boolean(progressData?.material_progress?.[mMat.id]?.is_completed) : true;
              const isPracDone = mPrac ? Boolean(progressData?.practice_progress?.[mPrac.id]?.is_completed) : true;
              const isVidDone = mVid ? Boolean(progressData?.video_progress?.[mVid.id]?.is_completed) : false;

              // Module is completed if backend says so or if both notes & quiz are finished
              const isDone = Boolean(progressData?.module_progress?.[m.id]) || (isMatDone && isPracDone);
              const isActive = origIdx === activeModuleIndex;

              return (
                <div key={m.id} className="space-y-1">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveModuleIndex(origIdx);
                      setActiveLessonIndex(0);
                      if (window.innerWidth < 1024) setSidebarOpen(false);
                    }}
                    className={`w-full text-left p-3.5 rounded-xl transition-all flex items-start gap-3 border cursor-pointer ${
                      isActive
                        ? 'bg-primary-50/90 border-primary-900 text-primary-950 font-bold shadow-xs ring-1 ring-primary-900/30'
                        : isDone
                        ? 'bg-white hover:bg-slate-50 border-slate-200 text-slate-800'
                        : 'bg-white hover:bg-slate-50 border-slate-200/60 text-slate-600'
                    }`}
                  >
                    {/* Status Indicator Icon */}
                    <div className="mt-0.5 shrink-0">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : isActive ? (
                        <div className="w-4 h-4 rounded-full border-2 border-primary-900 border-t-transparent animate-spin" />
                      ) : (
                        <Circle className="w-4 h-4 text-slate-300" />
                      )}
                    </div>

                    {/* Module Details */}
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-bold leading-tight truncate">
                        {m.order}. {m.title}
                      </div>

                      {/* Meta Pills */}
                      <div className="mt-1.5 flex items-center gap-2 text-[10px] text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {m.duration_minutes}m
                        </span>
                        <span>•</span>
                        <span className={`flex items-center gap-1 ${isMatDone ? 'text-emerald-700 font-semibold' : 'text-slate-500'}`}>
                          {isMatDone ? <Check className="w-2.5 h-2.5 text-emerald-600" /> : <FileText className="w-2.5 h-2.5 text-primary-900" />}
                          Notes
                        </span>
                        <span>•</span>
                        <span className={`flex items-center gap-1 ${isPracDone ? 'text-emerald-700 font-semibold' : 'text-slate-500'}`}>
                          {isPracDone ? <Check className="w-2.5 h-2.5 text-emerald-600" /> : <HelpCircle className="w-2.5 h-2.5 text-amber-600" />}
                          Quiz
                        </span>
                        <span>•</span>
                        <span className={`flex items-center gap-1 ${isVidDone ? 'text-emerald-700 font-semibold' : 'text-slate-400'}`}>
                          {isVidDone ? <Check className="w-2.5 h-2.5 text-emerald-600" /> : <PlayCircle className="w-2.5 h-2.5 text-slate-400" />}
                          Video
                        </span>
                      </div>
                    </div>
                  </button>

                  {/* Nested Lessons if active module */}
                  {isActive && m.lessons && m.lessons.length > 0 && (
                    <div className="ml-4 pl-3 border-l-2 border-primary-200 space-y-1 py-1">
                      {m.lessons.map((l, lIdx) => {
                        const isLActive = lIdx === activeLessonIndex;
                        const lDone = isLessonDone(l);
                        return (
                          <button
                            key={l.id}
                            type="button"
                            onClick={() => {
                              setActiveLessonIndex(lIdx);
                              if (window.innerWidth < 1024) setSidebarOpen(false);
                            }}
                            className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition flex items-center justify-between gap-2 cursor-pointer ${
                              isLActive
                                ? 'bg-primary-900 text-white font-bold shadow-xs'
                                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                            }`}
                          >
                            <span className="truncate">{lIdx + 1}. {l.title}</span>
                            {lDone ? (
                              <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${isLActive ? 'text-emerald-300' : 'text-emerald-600'}`} />
                            ) : isLActive ? (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-300 shrink-0" />
                            ) : (
                              <Circle className="w-3 h-3 text-slate-300 shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Exam Status at Sidebar Bottom */}
          <div className="p-4 border-t border-slate-200 bg-slate-50/80">
            {isAssessmentUnlocked ? (
              <Link
                to={`/assessments/${finalAssessment?.id}/preflight`}
                className="w-full py-2.5 px-3 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-sm transition"
              >
                <Award className="w-4 h-4" />
                <span>Start Certification Exam</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            ) : (
              <div className="text-center p-2.5 rounded-lg bg-white border border-slate-200 text-slate-600 text-xs">
                <Lock className="w-3.5 h-3.5 inline mr-1 text-amber-600" />
                Finish all {modules.length} modules to unlock Certificate Exam
              </div>
            )}
          </div>
        </aside>

        {/* MAIN LEARNING VIEW (INSTITUTIONAL CANVAS) */}
        <main className="flex-1 overflow-y-auto bg-[#f8fafc] pb-28">
          {activeModule ? (
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
              {/* CLEAN MODULE HEADER & DIRECT NAVIGATION TABS */}
              <div className="p-6 sm:p-8 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-semibold text-slate-800">{course.title}</span>
                    <span>/</span>
                    <span className="text-primary-900 font-bold">Module {activeModule.order}</span>
                    {currentLesson && (
                      <>
                        <span>/</span>
                        <span className="text-slate-800 font-bold">Lesson {activeLessonIndex + 1}: {currentLesson.title}</span>
                      </>
                    )}
                    <span className="text-slate-300">•</span>
                    <span className="text-slate-500 flex items-center gap-1 font-medium">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {currentLesson?.duration_minutes || activeModule.duration_minutes} Mins
                    </span>
                  </div>

                  {/* 3 Activity Switcher Tabs */}
                  <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl border border-slate-200">
                    <button
                      type="button"
                      onClick={() => setActiveTab('material')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'material'
                          ? 'bg-primary-900 text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                      }`}
                    >
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>Study Notes</span>
                      {currentLesson?.requires_notes === false ? (
                        <span className="text-[10px] opacity-75 font-normal">(Optional)</span>
                      ) : null}
                      {isMaterialDone && <span className="w-2 h-2 rounded-full bg-emerald-400" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveTab('video')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'video'
                          ? 'bg-primary-900 text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                      }`}
                    >
                      <PlayCircle className="w-3.5 h-3.5" />
                      <span>Video</span>
                      {currentVideo?.is_required || currentLesson?.requires_video ? null : (
                        <span className="text-[10px] opacity-75 font-normal">(Optional)</span>
                      )}
                      {isVideoDone && <span className="w-2 h-2 rounded-full bg-emerald-400" />}
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveTab('practice')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 cursor-pointer ${
                        activeTab === 'practice'
                          ? 'bg-primary-900 text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                      }`}
                    >
                      <HelpCircle className="w-3.5 h-3.5" />
                      <span>Quiz</span>
                      {currentPractice?.is_required || currentLesson?.requires_practice ? null : (
                        <span className="text-[10px] opacity-75 font-normal">(Optional)</span>
                      )}
                      {isPracticeDone && <span className="w-2 h-2 rounded-full bg-emerald-400" />}
                    </button>
                  </div>
                </div>

                <div>
                  <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                    {currentLesson ? currentLesson.title : activeModule.title}
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-600 mt-1.5 leading-relaxed max-w-3xl">
                    {currentLesson?.description || activeModule.description}
                  </p>
                </div>

                {/* Lesson Switcher Bar (if module has lessons) */}
                {lessons.length > 0 && (
                  <div className="pt-3 border-t border-slate-100 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-600 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-primary-900" />
                        Lessons in Module {activeModule.order} ({lessons.length})
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        Active: Lesson {activeLessonIndex + 1}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {lessons.map((lesson, lIdx) => {
                        const isCurrent = lIdx === activeLessonIndex;
                        const done = isLessonDone(lesson);
                        return (
                          <button
                            key={lesson.id}
                            type="button"
                            onClick={() => setActiveLessonIndex(lIdx)}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-2 border transition cursor-pointer ${
                              isCurrent
                                ? 'bg-primary-900 border-primary-900 text-white shadow-xs'
                                : done
                                ? 'bg-emerald-50 border-emerald-200 text-emerald-900 hover:bg-emerald-100'
                                : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                            }`}
                          >
                            <span>{lIdx + 1}. {lesson.title}</span>
                            {done ? (
                              <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${isCurrent ? 'text-emerald-300' : 'text-emerald-600'}`} />
                            ) : isCurrent ? (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-300" />
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* ========================================================================= */}
              {/* TAB 1: STUDY NOTES (CLEAN TEXTBOOK NOTES DOCUMENT) */}
              {/* ========================================================================= */}
              {activeTab === 'material' && (
                <div className="space-y-6 animate-fadeIn">
                  {currentMaterial ? (
                    <article className="space-y-6 text-slate-800">
                      {/* Attached Document File (PDF/DOC/PPT) */}
                      {currentMaterial.file && (
                        <section className="p-5 rounded-2xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 flex flex-wrap items-center justify-between gap-4 shadow-xs">
                          <div className="flex items-center gap-3">
                            <div className="w-11 h-11 rounded-xl bg-blue-600 text-white flex items-center justify-center font-black text-sm shrink-0 shadow-sm">
                              📄
                            </div>
                            <div>
                              <div className="text-xs font-bold text-blue-950">Official Study Material & Handout Attached</div>
                              <p className="text-[11px] text-blue-700 font-medium">Format: {currentMaterial.resource_type || 'Document'} • Uploaded by Faculty</p>
                            </div>
                          </div>
                          <a
                            href={currentMaterial.file.startsWith('http') ? currentMaterial.file : `http://127.0.0.1:8000${currentMaterial.file}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 rounded-xl bg-blue-700 hover:bg-blue-600 text-white font-bold text-xs shadow-xs transition inline-flex items-center gap-2"
                          >
                            <span>Open / Download Document</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </a>
                        </section>
                      )}

                      {/* 1. OVERVIEW & INTRODUCTION */}
                      <section className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                        <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                          <Target className="w-4 h-4 text-primary-900" />
                          <span>1. Overview & Learning Objectives</span>
                        </div>
                        <p className="text-sm sm:text-base text-slate-700 leading-relaxed">
                          {currentMaterial.structured_content?.introduction || currentMaterial.description || currentLesson?.description}
                        </p>

                        {currentMaterial.structured_content?.key_points && currentMaterial.structured_content.key_points.length > 0 && (
                          <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {currentMaterial.structured_content.key_points.map((pt: string, idx: number) => (
                              <div
                                key={idx}
                                className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-start gap-2.5 font-medium"
                              >
                                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                                <span className="leading-relaxed">{pt}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </section>

                      {/* Comprehensive Markdown Notes (when text_content is present from Faculty or AI) */}
                      {currentMaterial.text_content && (
                        <section className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                          <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                            <BookOpen className="w-4 h-4 text-primary-900" />
                            <span>Detailed Study Notes & Lecture Transcript</span>
                          </div>
                          <div className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap font-sans space-y-3">
                            {currentMaterial.text_content}
                          </div>
                        </section>
                      )}

                      {/* 2. CORE CONCEPT DEEP DIVE */}
                      <section className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                        <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                          <BookOpen className="w-4 h-4 text-primary-900" />
                          <span>2. Core Concept & Detailed Notes</span>
                        </div>
                        <div className="text-sm sm:text-base text-slate-700 leading-relaxed whitespace-pre-line space-y-4">
                          {currentMaterial.structured_content?.concept_explanation || currentMaterial.text_content}
                        </div>
                      </section>

                      {/* 3. SYNTAX REFERENCE */}
                      {currentMaterial.structured_content?.syntax && (
                        <section className="rounded-2xl bg-white border border-slate-200 overflow-hidden shadow-sm">
                          <div className="px-5 py-3 bg-slate-100 border-b border-slate-200 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Code2 className="w-4 h-4 text-primary-900" />
                              <span className="text-xs font-mono font-bold text-slate-800">Syntax & Specifications</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleCopyCode(currentMaterial.structured_content?.syntax || '', 'syntax')}
                              className="px-3 py-1 rounded bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition cursor-pointer shadow-xs"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              <span>{copiedSnippet === 'syntax' ? 'Copied!' : 'Copy Code'}</span>
                            </button>
                          </div>
                          <pre className="p-5 font-mono text-xs sm:text-sm text-emerald-400 overflow-x-auto leading-relaxed whitespace-pre bg-slate-900">
                            {currentMaterial.structured_content.syntax}
                          </pre>
                        </section>
                      )}

                      {/* 4. PRACTICAL CODE EXAMPLES */}
                      {currentMaterial.structured_content?.examples && currentMaterial.structured_content.examples.length > 0 && (
                        <section className="space-y-4">
                          <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                            <Code2 className="w-4 h-4 text-primary-900" />
                            <span>3. Code Examples & Expected Output</span>
                          </div>

                          {currentMaterial.structured_content.examples.map((ex: any, exIdx: number) => (
                            <div key={exIdx} className="rounded-2xl bg-white border border-slate-200 overflow-hidden shadow-sm space-y-0">
                              <div className="px-5 py-3 bg-slate-100 border-b border-slate-200 flex items-center justify-between">
                                <div className="flex items-center gap-2 font-bold text-xs text-slate-900">
                                  <span className="w-2 h-2 rounded-full bg-primary-900" />
                                  <span>{ex.title}</span>
                                </div>
                                <button
                                  type="button"
                                  onClick={() => handleCopyCode(ex.code, `ex-${exIdx}`)}
                                  className="px-3 py-1 rounded bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 flex items-center gap-1.5 transition cursor-pointer shadow-xs"
                                >
                                  <Copy className="w-3.5 h-3.5" />
                                  <span>{copiedSnippet === `ex-${exIdx}` ? 'Copied!' : 'Copy'}</span>
                                </button>
                              </div>
                              <pre className="p-5 font-mono text-xs sm:text-sm text-amber-200 overflow-x-auto leading-relaxed whitespace-pre bg-slate-950">
                                {ex.code}
                              </pre>
                              {ex.output && (
                                <div className="p-4 bg-slate-900 border-t border-slate-800 space-y-1">
                                  <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                                    Terminal Output:
                                  </div>
                                  <pre className="font-mono text-xs text-emerald-400 whitespace-pre">
                                    {ex.output}
                                  </pre>
                                </div>
                              )}
                              {ex.explanation && (
                                <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-600">
                                  {ex.explanation}
                                </div>
                              )}
                            </div>
                          ))}
                        </section>
                      )}

                      {/* 5. COMMON PITFALLS & HOW TO FIX */}
                      {currentMaterial.structured_content?.common_mistakes && currentMaterial.structured_content.common_mistakes.length > 0 && (
                        <section className="space-y-4">
                          <div className="flex items-center gap-2 text-rose-700 text-xs font-bold uppercase tracking-wider">
                            <AlertTriangle className="w-4 h-4" />
                            <span>4. Common Mistakes & Best Practice Fixes</span>
                          </div>

                          <div className="grid grid-cols-1 gap-4">
                            {currentMaterial.structured_content.common_mistakes.map((cm: any, cmIdx: number) => {
                              const pitfall = (cm.common_pitfall || cm.mistake || '').trim();
                              const solution = (cm.recommended_solution || cm.correct || cm.good_code || '').trim();
                              const rationale = (cm.technical_rationale || cm.reason || cm.explanation || '').trim();

                              if (!pitfall && !solution && !rationale) return null;

                              const displayPitfall = pitfall || "Learning recommendation is being updated.";
                              const displaySolution = solution || "Learning recommendation is being updated.";
                              const displayRationale = rationale || "Learning recommendation is being updated.";

                              return (
                                <div key={cmIdx} className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-3">
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 space-y-1.5">
                                      <div className="text-[11px] font-bold text-rose-800 flex items-center gap-1.5">
                                        <X className="w-3.5 h-3.5" />
                                        Common Pitfall:
                                      </div>
                                      <div className="text-xs text-rose-950 font-medium whitespace-pre-wrap leading-relaxed">
                                        {displayPitfall}
                                      </div>
                                    </div>

                                    <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 space-y-1.5">
                                      <div className="text-[11px] font-bold text-emerald-800 flex items-center gap-1.5">
                                        <Check className="w-3.5 h-3.5" />
                                        Recommended Solution:
                                      </div>
                                      <div className="text-xs text-emerald-950 font-medium whitespace-pre-wrap leading-relaxed">
                                        {displaySolution}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs text-slate-700 leading-relaxed">
                                    <strong className="text-slate-900">Technical Rationale: </strong> {displayRationale}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      )}

                      {/* 6. GLOSSARY */}
                      {currentMaterial.structured_content?.important_terms && currentMaterial.structured_content.important_terms.length > 0 && (
                        <section className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                          <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                            <Layers className="w-4 h-4 text-primary-900" />
                            <span>5. Essential Terminology Glossary</span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {currentMaterial.structured_content.important_terms.map((term: any, tIdx: number) => (
                              <div key={tIdx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                                <div className="text-xs font-bold text-primary-900">{term.term}</div>
                                <div className="text-xs text-slate-600 leading-relaxed">{term.definition}</div>
                              </div>
                            ))}
                          </div>
                        </section>
                      )}

                      {/* 7. SELF-CHECK QUESTIONS */}
                      {currentMaterial.structured_content?.practice_questions && currentMaterial.structured_content.practice_questions.length > 0 && (
                        <section className="space-y-3">
                          <div className="flex items-center gap-2 text-primary-900 text-xs font-bold uppercase tracking-wider">
                            <HelpCircle className="w-4 h-4 text-primary-900" />
                            <span>6. Test Your Understanding (Self-Check Questions)</span>
                          </div>

                          <div className="space-y-2.5">
                            {currentMaterial.structured_content.practice_questions.map((pq: any, qIdx: number) => {
                              const isRevealed = Boolean(revealedQuestions[qIdx]);
                              return (
                                <div key={qIdx} className="rounded-xl bg-white border border-slate-200 shadow-xs overflow-hidden">
                                  <button
                                    type="button"
                                    onClick={() => setRevealedQuestions((prev) => ({ ...prev, [qIdx]: !prev[qIdx] }))}
                                    className="w-full text-left p-4 flex items-center justify-between gap-3 text-xs font-bold text-slate-900 hover:bg-slate-50 transition cursor-pointer"
                                  >
                                    <div className="flex items-center gap-2.5">
                                      <span className="w-5 h-5 rounded-full bg-primary-50 text-primary-900 border border-primary-200 flex items-center justify-center text-[10px] shrink-0 font-mono">
                                        Q{qIdx + 1}
                                      </span>
                                      <span>{pq.question}</span>
                                    </div>
                                    <span className="text-[11px] text-primary-900 shrink-0 font-semibold">
                                      {isRevealed ? 'Hide Answer ▲' : 'Reveal Answer ▼'}
                                    </span>
                                  </button>

                                  {isRevealed && (
                                    <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs space-y-1.5 animate-fadeIn">
                                      <div className="font-bold text-emerald-700">Answer: {pq.answer}</div>
                                      <p className="text-slate-600">{pq.explanation}</p>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      )}

                      {/* COMPLETE STUDY MATERIAL CTA CARD */}
                      <div className="p-6 rounded-2xl bg-primary-900 text-white flex flex-wrap items-center justify-between gap-4 shadow-sm">
                        <div>
                          <h4 className="text-base font-bold text-white">Finished Reading These Notes?</h4>
                          <p className="text-xs text-slate-300 mt-1">
                            Click to complete this module's reading progress and move on.
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={handleCompleteMaterial}
                          disabled={completingMaterial || isMaterialDone}
                          className={`px-6 py-3 rounded-xl font-bold text-xs flex items-center gap-2 transition cursor-pointer ${
                            isMaterialDone
                              ? 'bg-emerald-600 text-white cursor-default'
                              : 'bg-accent-500 hover:bg-accent-400 text-primary-950 shadow'
                          }`}
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{isMaterialDone ? '✓ Notes Read & Completed' : completingMaterial ? 'Saving...' : 'Mark Notes as Completed'}</span>
                        </button>
                      </div>
                    </article>
                  ) : (
                    <div className="p-12 text-center text-slate-500 text-xs">No study materials configured for this module.</div>
                  )}
                </div>
              )}

              {/* ========================================================================= */}
              {/* TAB 2: VIDEO LECTURE */}
              {/* ========================================================================= */}
              {activeTab === 'video' && (
                <div className="space-y-6 animate-fadeIn">
                  {currentVideo ? (
                    <div className="space-y-6">
                      {/* Video Player Card */}
                      <div className="rounded-2xl bg-white border border-slate-200 overflow-hidden shadow-sm">
                        <div className="aspect-video w-full bg-black relative flex items-center justify-center">
                          {currentVideo.youtube_video_id ? (
                            <iframe
                              src={`https://www.youtube-nocookie.com/embed/${currentVideo.youtube_video_id}?enablejsapi=1`}
                              title={currentVideo.title}
                              className="w-full h-full border-0"
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowFullScreen
                            />
                          ) : currentVideo.external_url ? (
                            <video
                              ref={videoRef}
                              src={currentVideo.external_url}
                              controls
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="w-full h-full bg-gradient-to-br from-[#0b1e3d] via-[#122e5a] to-[#071326] text-white p-6 sm:p-8 flex flex-col justify-between overflow-y-auto">
                              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
                                <div className="flex items-center gap-2">
                                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                                    FXEC AI Multimedia Studio • Interactive Lecture & Storyboard
                                  </span>
                                </div>
                                <span className="text-xs font-mono font-bold bg-white/10 px-2.5 py-1 rounded-md text-amber-300 border border-white/10">
                                  Scene {activeSceneIndex + 1} of {(currentVideo as any).script_package?.storyboard?.length || 4}
                                </span>
                              </div>

                              {/* Storyboard Scene Display */}
                              {(currentVideo as any).script_package?.storyboard && (currentVideo as any).script_package.storyboard.length > 0 ? (
                                (() => {
                                  const sb = (currentVideo as any).script_package.storyboard;
                                  const scene = sb[activeSceneIndex] || sb[0];
                                  return (
                                    <div className="my-auto py-4 space-y-4">
                                      <div className="space-y-1">
                                        <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                                          {scene.timestamp_range || 'Production Segment'} • {scene.scene_title}
                                        </div>
                                        <h3 className="text-lg sm:text-xl font-black text-white">
                                          {scene.scene_title}
                                        </h3>
                                      </div>

                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                                          <div className="text-[11px] font-bold text-slate-400 uppercase flex items-center gap-1.5">
                                            <PlayCircle className="w-3.5 h-3.5 text-emerald-400" />
                                            Visual Instructions & On-Screen Action
                                          </div>
                                          <p className="text-xs text-slate-200 leading-relaxed font-sans">
                                            {scene.visual_instructions}
                                          </p>
                                          {scene.code_preview && (
                                            <div className="mt-2 p-2.5 rounded-lg bg-black/50 border border-white/10 font-mono text-[11px] text-emerald-300 overflow-x-auto whitespace-pre">
                                              {scene.code_preview}
                                            </div>
                                          )}
                                        </div>

                                        <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
                                          <div className="text-[11px] font-bold text-slate-400 uppercase flex items-center gap-1.5">
                                            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                                            Narration & Audio Transcript
                                          </div>
                                          <p className="text-xs text-slate-100 leading-relaxed italic">
                                            "{scene.narration_cue}"
                                          </p>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })()
                              ) : (
                                <div className="my-auto py-6 text-center space-y-3">
                                  <Video className="w-10 h-10 text-slate-400 mx-auto" />
                                  <h4 className="text-base font-bold text-white">Structured AI Video Script & Storyboard</h4>
                                  <p className="text-xs text-slate-300 max-w-lg mx-auto">
                                    {currentVideo.description || 'This module includes comprehensive AI lecture notes, scene scripts, and practice challenges.'}
                                  </p>
                                </div>
                              )}

                              {/* Storyboard Scene Stepper Bar */}
                              {(currentVideo as any).script_package?.storyboard && (currentVideo as any).script_package.storyboard.length > 1 && (
                                <div className="pt-4 border-t border-white/10 flex items-center justify-between gap-2">
                                  <button
                                    type="button"
                                    onClick={() => setActiveSceneIndex((prev) => Math.max(0, prev - 1))}
                                    disabled={activeSceneIndex === 0}
                                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-30 text-xs font-bold text-white flex items-center gap-1 cursor-pointer transition"
                                  >
                                    <ChevronLeft className="w-3.5 h-3.5" /> Previous Scene
                                  </button>

                                  <div className="flex items-center gap-1.5">
                                    {(currentVideo as any).script_package.storyboard.map((_: any, sIdx: number) => (
                                      <button
                                        key={sIdx}
                                        type="button"
                                        onClick={() => setActiveSceneIndex(sIdx)}
                                        className={`w-2.5 h-2.5 rounded-full transition-all cursor-pointer ${
                                          sIdx === activeSceneIndex ? 'bg-amber-400 w-6' : 'bg-white/30 hover:bg-white/60'
                                        }`}
                                      />
                                    ))}
                                  </div>

                                  <button
                                    type="button"
                                    onClick={() => setActiveSceneIndex((prev) => Math.min(((currentVideo as any).script_package?.storyboard?.length || 1) - 1, prev + 1))}
                                    disabled={activeSceneIndex === ((currentVideo as any).script_package?.storyboard?.length || 1) - 1}
                                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 disabled:opacity-30 text-xs font-bold text-white flex items-center gap-1 cursor-pointer transition"
                                  >
                                    Next Scene <ChevronRight className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Video Controls Bar */}
                        <div className="p-5 flex flex-wrap items-center justify-between gap-4 bg-slate-50 border-t border-slate-200">
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-bold text-slate-900">{currentVideo.title}</h3>
                              {currentVideo.is_required || currentLesson?.requires_video ? (
                                <span className="px-2 py-0.5 rounded bg-rose-50 text-rose-700 text-[10px] font-bold border border-rose-200">Required</span>
                              ) : (
                                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-medium border border-slate-200">Optional</span>
                              )}
                            </div>
                            <p className="text-xs text-slate-600 mt-1">
                              {currentVideo.channel_name ? <span className="font-semibold text-slate-800 mr-2">Channel: {currentVideo.channel_name}</span> : null}
                              {currentVideo.description}
                            </p>
                          </div>

                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => setIsReportModalOpen(true)}
                              className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 text-xs font-semibold flex items-center gap-1.5 transition shadow-xs"
                            >
                              <Flag className="w-3.5 h-3.5 text-rose-500" />
                              <span>Report Issue</span>
                            </button>

                            <button
                              type="button"
                              onClick={handleConfirmVideoWatched}
                              disabled={confirmingVideo || isVideoDone}
                              className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer ${
                                isVideoDone
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-default'
                                  : 'bg-primary-900 hover:bg-primary-800 text-white shadow-xs'
                              }`}
                            >
                              <CheckCircle2 className="w-4 h-4" />
                              <span>{isVideoDone ? '✓ Watched' : confirmingVideo ? 'Updating...' : 'Mark Video Complete'}</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="p-12 text-center text-slate-500 text-xs bg-white rounded-2xl border border-slate-200 shadow-sm">
                      No video lecture attached to this lesson.
                    </div>
                  )}
                </div>
              )}

              {/* ========================================================================= */}
              {/* TAB 3: INTERACTIVE PRACTICE QUIZ */}
              {/* ========================================================================= */}
              {activeTab === 'practice' && (
                <div className="space-y-6 animate-fadeIn">
                  {currentPractice ? (
                    <div className="space-y-6">
                      {/* Practice Header Card */}
                      <div className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-wrap items-center justify-between gap-3 shadow-sm">
                        <div>
                          <h3 className="text-base font-bold text-slate-900">{currentPractice.title}</h3>
                          <p className="text-xs text-slate-600 mt-1">
                            Pass Requirement: <strong className="text-emerald-700">{currentPractice.pass_score}% score</strong>. Instant academic evaluation.
                          </p>
                        </div>

                        <div className={`px-3 py-1.5 rounded-xl text-xs font-bold border ${
                          isPracticeDone
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                            : 'bg-amber-50 border-amber-200 text-amber-800'
                        }`}>
                          {isPracticeDone ? '✓ Practice Passed' : 'Pending Verification'}
                        </div>
                      </div>

                      {/* Question Cards */}
                      {currentPractice.content?.questions?.map((q: any, qIdx: number) => {
                        const qKey = getQuestionKey(q, qIdx);
                        const selected = practiceAnswers[qKey];
                        const isAnswerSubmitted = practiceSubmitted;
                        const details = getCorrectOptionDetails(q);
                        const isStudentCorrect = isStudentAnswerCorrect(q, selected);

                        return (
                          <div key={q.id || qIdx} className="p-6 rounded-2xl bg-white border border-slate-200 space-y-4 shadow-sm">
                            <div className="flex items-center justify-between text-xs text-slate-500">
                              <span className="font-bold text-primary-900">Question {qIdx + 1} of {currentPractice.content?.questions?.length || 0}</span>
                              <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 text-[10px] font-mono">1 Mark</span>
                            </div>

                            <p className="text-sm font-bold text-slate-900 leading-relaxed">
                              {q.question}
                            </p>

                            {/* Radio Options Grid */}
                            <div className="space-y-2 pt-2">
                              {q.options?.map((opt: string, optIdx: number) => {
                                const optLetter = String.fromCharCode(65 + optIdx);
                                const isChecked = selected === opt || selected === optLetter;
                                const isThisCorrect = details.correctIndex === optIdx || opt.trim().toLowerCase() === details.correctText.trim().toLowerCase();

                                let optClasses = 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300';

                                if (isAnswerSubmitted) {
                                  if (isThisCorrect) {
                                    optClasses = 'bg-emerald-50 border-emerald-500 text-emerald-950 font-bold ring-1 ring-emerald-500/30';
                                  } else if (isChecked && !isThisCorrect) {
                                    optClasses = 'bg-rose-50 border-rose-400 text-rose-900';
                                  }
                                } else if (isChecked) {
                                  optClasses = 'bg-primary-50/70 border-primary-900 text-primary-950 ring-1 ring-primary-900/30';
                                }

                                return (
                                  <label
                                    key={optIdx}
                                    className={`w-full p-3.5 rounded-xl border text-xs font-semibold flex items-center gap-3 transition cursor-pointer ${optClasses}`}
                                  >
                                    <input
                                      type="radio"
                                      name={`question-${qKey}`}
                                      value={opt}
                                      disabled={isAnswerSubmitted}
                                      checked={isChecked}
                                      onChange={() => setPracticeAnswers((prev) => ({ ...prev, [qKey]: opt }))}
                                      className="text-primary-900 focus:ring-primary-900 cursor-pointer"
                                    />
                                    <span className="w-5 h-5 rounded-md bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center font-bold text-[11px] shrink-0">
                                      {optLetter}
                                    </span>
                                    <span className="flex-1">{opt}</span>
                                    {isAnswerSubmitted && isThisCorrect && (
                                      <span className="text-emerald-700 text-[11px] font-bold shrink-0">✓ Correct</span>
                                    )}
                                    {isAnswerSubmitted && isChecked && !isThisCorrect && (
                                      <span className="text-rose-700 text-[11px] font-bold shrink-0">✗ Your Choice</span>
                                    )}
                                  </label>
                                );
                              })}
                            </div>

                            {/* Post-Submission Feedback */}
                            {isAnswerSubmitted && (
                              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                                <div className="font-bold">
                                  {isStudentCorrect ? (
                                    <span className="text-emerald-700 flex items-center gap-1.5">
                                      <Check className="w-4 h-4 text-emerald-600" />
                                      <span>✓ Correct Answer! Well done.</span>
                                    </span>
                                  ) : (
                                    <span className="text-rose-700 flex items-center gap-1.5">
                                      <AlertCircle className="w-4 h-4 text-rose-600" />
                                      <span>
                                        ✗ Incorrect. Correct: {details.correctLetter ? `Option ${details.correctLetter}` : ''} {details.correctText ? `(${details.correctText})` : ''}
                                      </span>
                                    </span>
                                  )}
                                </div>
                                {q.explanation && (
                                  <p className="text-slate-600 text-[11px] pt-1 border-t border-slate-200/60 mt-1">
                                    <span className="font-semibold text-slate-800">Explanation: </span>
                                    {q.explanation}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}

                      {/* Result Banner or Submit Button */}
                      {practiceScore ? (
                        <div className={`p-6 rounded-2xl border text-center space-y-3 ${
                          practiceScore.passed
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                            : 'bg-rose-50 border-rose-200 text-rose-900'
                        }`}>
                          <h4 className="text-xl font-bold">
                            {practiceScore.passed ? '🎉 Practice Requirement Satisfied' : 'Need Review! Try Again'}
                          </h4>
                          <p className="text-xs">
                            You scored <strong>{practiceScore.score}%</strong> ({practiceScore.earned}/{practiceScore.total} correct).
                            {practiceScore.passed ? ' You may proceed to the next module.' : ' Review the study notes and attempt the questions again.'}
                          </p>

                          {!practiceScore.passed && (
                            <button
                              type="button"
                              onClick={() => {
                                setPracticeSubmitted(false);
                                setPracticeAnswers({});
                                setPracticeScore(null);
                              }}
                              className="px-4 py-2 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs cursor-pointer inline-flex items-center gap-2 shadow-xs"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              Retry Quiz
                            </button>
                          )}
                        </div>
                      ) : (
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={handleSubmitPractice}
                            disabled={submittingPractice}
                            className="px-6 py-3 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs shadow-xs transition cursor-pointer flex items-center gap-2"
                          >
                            <Check className="w-4 h-4" />
                            <span>{submittingPractice ? 'Evaluating...' : 'Submit Answers'}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-12 text-center text-slate-500 text-xs bg-white rounded-2xl border border-slate-200 shadow-sm">
                      No practice tasks configured for this module.
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-24 text-slate-500 text-xs">Select a module from the curriculum sidebar to start.</div>
          )}
        </main>
      </div>

      {/* 3. STICKY INSTITUTIONAL FOOTER NAVIGATION */}
      <footer className="fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 px-4 sm:px-8 py-3.5 shadow-lg flex items-center justify-between gap-4">
        {/* Left: Previous Module/Lesson Button */}
        <button
          type="button"
          onClick={handlePrev}
          disabled={activeModuleIndex === 0 && activeLessonIndex === 0}
          className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer ${
            activeModuleIndex === 0 && activeLessonIndex === 0
              ? 'opacity-40 cursor-not-allowed text-slate-400 bg-slate-100 border border-slate-200'
              : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs'
          }`}
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="hidden sm:inline">
            {lessons.length > 1 && activeLessonIndex > 0 ? 'Previous Lesson' : 'Previous Module'}
          </span>
          <span className="sm:hidden">Prev</span>
        </button>

        {/* Center: Module/Lesson Completion Badge */}
        <div className="text-xs text-center">
          <span className="text-slate-500 hidden md:inline">
            {currentLesson ? `Lesson ${activeLessonIndex + 1} of ${lessons.length || 1} • Module ${activeModule?.order || 1}: ` : `Module ${activeModule?.order || 1} Status: `}
          </span>
          <strong className={currentLesson ? (isLessonDone(currentLesson) ? 'text-emerald-700' : 'text-amber-700') : (isCurrentModuleComplete ? 'text-emerald-700' : 'text-amber-700')}>
            {currentLesson
              ? (isLessonDone(currentLesson) ? '✓ Lesson Completed' : 'In Progress')
              : (isCurrentModuleComplete ? '✓ Module Completed' : 'In Progress (Complete Notes & Quiz)')}
          </strong>
        </div>

        {/* Right: Next Lesson / Next Module or Start Exam */}
        {lessons.length > 0 && activeLessonIndex < lessons.length - 1 ? (
          <button
            type="button"
            onClick={handleNext}
            className="px-5 py-2 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition cursor-pointer"
          >
            <span className="hidden sm:inline">Next Lesson</span>
            <span className="sm:hidden">Next</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : activeModuleIndex < modules.length - 1 ? (
          <button
            type="button"
            onClick={handleNext}
            className="px-5 py-2 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs flex items-center gap-2 shadow-xs transition cursor-pointer"
          >
            <span className="hidden sm:inline">Next Module</span>
            <span className="sm:hidden">Next</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : isAssessmentUnlocked ? (
          <Link
            to={`/assessments/${finalAssessment?.id}/preflight`}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs flex items-center gap-2 shadow-sm transition"
          >
            <Award className="w-4 h-4" />
            <span>Take Final Certification Exam</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        ) : (
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-amber-600" />
            <span>Finish all modules for exam</span>
          </div>
        )}
      </footer>

      {/* 4. REPORT BROKEN VIDEO MODAL */}
      {isReportModalOpen && currentVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Flag className="w-4 h-4 text-rose-500" />
                <h3 className="text-sm font-bold text-slate-900">Report Video Issue</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsReportModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {reportSuccessMessage ? (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <span>{reportSuccessMessage}</span>
              </div>
            ) : (
              <form onSubmit={handleReportVideoSubmit} className="space-y-4 text-xs">
                <p className="text-slate-600">
                  Reporting video: <strong className="text-slate-900">{currentVideo.title}</strong>
                </p>

                <div className="space-y-1.5">
                  <label className="font-bold text-slate-700">Issue Category:</label>
                  <select
                    value={reportingIssueType}
                    onChange={(e) => setReportingIssueType(e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-slate-300 text-slate-900 bg-white focus:border-primary-900 focus:outline-none"
                  >
                    <option value="UNAVAILABLE">Video is unavailable or removed</option>
                    <option value="EMBEDDING_DISABLED">Embedding disabled by YouTube owner</option>
                    <option value="PRIVATE">Video marked private</option>
                    <option value="BROKEN_CONTENT">Broken stream or audio issues</option>
                    <option value="TOPIC_MISMATCH">Content mismatch with curriculum topic</option>
                    <option value="OTHER">Other technical issue</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-bold text-slate-700">Notes (Optional):</label>
                  <textarea
                    rows={3}
                    value={reportingNotes}
                    onChange={(e) => setReportingNotes(e.target.value)}
                    placeholder="Provide details to help faculty resolve..."
                    className="w-full p-2.5 rounded-lg border border-slate-300 text-slate-900 bg-white focus:border-primary-900 focus:outline-none resize-none"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                  <button
                    type="button"
                    onClick={() => setIsReportModalOpen(false)}
                    className="px-4 py-2 rounded-lg text-slate-600 hover:bg-slate-100 font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReport}
                    className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold shadow-xs disabled:opacity-50"
                  >
                    {submittingReport ? 'Submitting...' : 'Submit Report'}
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
