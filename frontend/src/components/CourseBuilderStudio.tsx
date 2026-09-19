import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { Course, Module, Lesson, VideoResource, StudyMaterial, PracticeTask, Skill, Department, SkillCategory } from '../types';
import {
  BookOpen,
  PlusCircle,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Send,
  Video,
  FileText,
  HelpCircle,
  Trash2,
  Edit3,
  Eye,
  X,
  Play,
  ExternalLink,
  Save,
  Check,
  RefreshCw,
  AlertCircle,
  Award,
  ShieldCheck,
  Settings,
  Wand2,
  Code2,
  Terminal,
  Lock,
  PlayCircle
} from 'lucide-react';

export interface FinalAssessmentOption {
  id?: number;
  text: string;
  is_correct: boolean;
  order?: number;
}

export interface FinalAssessmentQuestion {
  id?: number;
  text: string;
  title?: string;
  problem_statement?: string;
  programming_language?: string;
  topic_tag?: string;
  question_type?: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  marks: number;
  explanation?: string;
  options?: FinalAssessmentOption[];
  order?: number;
  is_bank_question?: boolean;
  approval_status?: string;
  sample_test_cases?: Array<{ input: string; output: string; explanation?: string }>;
  hidden_test_cases?: Array<{ input: string; output: string }>;
  reference_solution?: string;
  input_format?: string;
  output_format?: string;
  constraints?: string;
}

export interface FinalAssessmentData {
  id?: number;
  course_id?: number;
  title: string;
  assessment_type?: string;
  duration_minutes: number;
  pass_percentage: number;
  max_attempts: number;
  camera_required: boolean;
  screen_share_required: boolean;
  fullscreen_required: boolean;
  face_detection_enabled: boolean;
  is_published: boolean;
  questions_count?: number;
  total_marks?: number;
  questions?: FinalAssessmentQuestion[];
}

interface CourseBuilderStudioProps {
  initialCourseId?: number | null;
  onClose?: () => void;
  onCourseCreated?: (course: Course) => void;
}

export const CourseBuilderStudio: React.FC<CourseBuilderStudioProps> = ({
  initialCourseId,
  onClose,
  onCourseCreated
}) => {
  // Course state
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(initialCourseId || null);
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingCourse, setSavingCourse] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Metadata dropdowns
  const [skills, setSkills] = useState<Skill[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<SkillCategory[]>([]);

  // Course Details Form
  const [courseTitle, setCourseTitle] = useState('');
  const [courseDesc, setCourseDesc] = useState('');
  const [skillId, setSkillId] = useState<number | ''>('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [deptId, setDeptId] = useState<number | ''>('');
  const [level, setLevel] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'>('BEGINNER');
  const [estimatedHours, setEstimatedHours] = useState(12);
  const [thumbnailUrl, setThumbnailUrl] = useState('');
  const [prereqText, setPrereqText] = useState('');
  const [objectives, setObjectives] = useState<string[]>(['', '']);

  // Modals state
  const [activeModuleModal, setActiveModuleModal] = useState<{ isOpen: boolean; module?: Module | null }>({ isOpen: false });
  const [moduleTitle, setModuleTitle] = useState('');
  const [moduleDesc, setModuleDesc] = useState('');
  const [moduleDuration, setModuleDuration] = useState(30);
  const [moduleRequired, setModuleRequired] = useState(true);

  // Lesson modal state
  const [activeLessonModal, setActiveLessonModal] = useState<{ isOpen: boolean; moduleId: number; lesson?: Lesson | null }>({ isOpen: false, moduleId: 0 });
  const [lessonTitle, setLessonTitle] = useState('');
  const [lessonDesc, setLessonDesc] = useState('');
  const [lessonDuration, setLessonDuration] = useState(15);
  const [lessonRequired, setLessonRequired] = useState(true);

  // Video resource modal
  const [activeVideoModal, setActiveVideoModal] = useState<{ isOpen: boolean; lessonId: number; video?: VideoResource | null }>({ isOpen: false, lessonId: 0 });
  const [videoUrl, setVideoUrl] = useState('');
  const [videoTitle, setVideoTitle] = useState('');
  const [videoDesc, setVideoDesc] = useState('');
  const [videoRequired, setVideoRequired] = useState(true);
  const [videoParsing, setVideoParsing] = useState(false);
  const [videoMeta, setVideoMeta] = useState<any>(null);

  // AI Video Suggestion modal
  const [activeAiVideoModal, setActiveAiVideoModal] = useState<{ isOpen: boolean; lesson: Lesson | null }>({ isOpen: false, lesson: null });
  const [aiSuggestions, setAiSuggestions] = useState<any[]>([]);
  const [loadingAiSuggestions, setLoadingAiSuggestions] = useState(false);

  // Notes resource modal
  const [activeNotesModal, setActiveNotesModal] = useState<{ isOpen: boolean; lessonId: number; material?: StudyMaterial | null }>({ isOpen: false, lessonId: 0 });
  const [notesTitle, setNotesTitle] = useState('');
  const [notesContent, setNotesContent] = useState('');
  const [notesFile, setNotesFile] = useState<File | null>(null);
  const [notesRequired, setNotesRequired] = useState(true);
  const [notesTab, setNotesTab] = useState<'write' | 'preview'>('write');
  const [generatingAiNotes, setGeneratingAiNotes] = useState(false);

  // Individual resource previews
  const [previewingVideo, setPreviewingVideo] = useState<VideoResource | null>(null);
  const [previewingNotes, setPreviewingNotes] = useState<StudyMaterial | null>(null);

  // Practice resource modal
  const [activePracticeModal, setActivePracticeModal] = useState<{ isOpen: boolean; lessonId: number; practice?: PracticeTask | null }>({ isOpen: false, lessonId: 0 });
  const [practiceTitle, setPracticeTitle] = useState('');
  const [practicePassScore, setPracticePassScore] = useState(70);
  const [practiceRequired, setPracticeRequired] = useState(true);
  const [practiceQuestions, setPracticeQuestions] = useState<Array<{ question: string; options: string[]; correct_option: string; explanation?: string }>>([
    { question: '', options: ['', '', '', ''], correct_option: 'A', explanation: '' }
  ]);

  // Preview and Validation Modals
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [validationModal, setValidationModal] = useState<{ isOpen: boolean; result: any | null }>({ isOpen: false, result: null });
  const [submittingReview, setSubmittingReview] = useState(false);

  // Final Certification Assessment State
  const [assessmentData, setAssessmentData] = useState<FinalAssessmentData | null>(null);
  const [loadingAssessment, setLoadingAssessment] = useState(false);

  // Assessment Settings Modal State
  const [isAssessmentSettingsOpen, setIsAssessmentSettingsOpen] = useState(false);
  const [assessmentTitle, setAssessmentTitle] = useState('');
  const [assessmentDuration, setAssessmentDuration] = useState(30);
  const [assessmentPassScore, setAssessmentPassScore] = useState(70);
  const [assessmentMaxAttempts, setAssessmentMaxAttempts] = useState(3);
  const [assessmentCameraReq, setAssessmentCameraReq] = useState(true);
  const [assessmentScreenShareReq, setAssessmentScreenShareReq] = useState(true);
  const [assessmentFullscreenReq, setAssessmentFullscreenReq] = useState(true);
  const [assessmentFaceDetectReq, setAssessmentFaceDetectReq] = useState(true);
  const [savingAssessmentSettings, setSavingAssessmentSettings] = useState(false);

  // Manual Question Modal State
  const [isManualQuestionModalOpen, setIsManualQuestionModalOpen] = useState(false);
  const [editingQuestionId, setEditingQuestionId] = useState<number | null>(null);
  const [manualQText, setManualQText] = useState('');
  const [manualQTopic, setManualQTopic] = useState('');
  const [manualQDifficulty, setManualQDifficulty] = useState<'EASY' | 'MEDIUM' | 'HARD'>('MEDIUM');
  const [manualQMarks, setManualQMarks] = useState(1);
  const [manualQExplanation, setManualQExplanation] = useState('');
  const [manualQOptions, setManualQOptions] = useState<string[]>(['', '', '', '']);
  const [manualQCorrectIndex, setManualQCorrectIndex] = useState(0);
  const [savingManualQuestion, setSavingManualQuestion] = useState(false);

  // AI Question Generator Modal State
  const [isAiQuestionModalOpen, setIsAiQuestionModalOpen] = useState(false);
  const [aiQuestionCount, setAiQuestionCount] = useState(5);
  const [aiQuestionDifficulty, setAiQuestionDifficulty] = useState('ALL');
  const [generatingAiQuestions, setGeneratingAiQuestions] = useState(false);
  const [aiGeneratedQuestions, setAiGeneratedQuestions] = useState<FinalAssessmentQuestion[]>([]);
  const [selectedAiIndices, setSelectedAiIndices] = useState<number[]>([]);
  const [savingAiQuestions, setSavingAiQuestions] = useState(false);

  // Practical Coding Assessment State
  const [programmingLanguage, setProgrammingLanguage] = useState<string>('');
  const [codingQuestions, setCodingQuestions] = useState<any[]>([]);
  const [loadingCodingQuestions, setLoadingCodingQuestions] = useState(false);
  const [generatingAiCoding, setGeneratingAiCoding] = useState(false);
  const [publishingCodingId, setPublishingCodingId] = useState<number | null>(null);
  const [validatingCodingId, setValidatingCodingId] = useState<number | null>(null);
  const [codingValidationResult, setCodingValidationResult] = useState<{ id: number; valid: boolean; message: string } | null>(null);

  // Coding Question Modal State
  const [isCodingModalOpen, setIsCodingModalOpen] = useState(false);
  const [editingCodingId, setEditingCodingId] = useState<number | null>(null);
  const [codingTitle, setCodingTitle] = useState('');
  const [codingStatement, setCodingStatement] = useState('');
  const [codingLang, setCodingLang] = useState('python');
  const [codingTopic, setCodingTopic] = useState('coding');
  const [codingMarks, setCodingMarks] = useState(10);
  const [codingInputFormat, setCodingInputFormat] = useState('Standard Input (stdin)');
  const [codingOutputFormat, setCodingOutputFormat] = useState('Standard Output (stdout)');
  const [codingConstraints, setCodingConstraints] = useState('Time Limit: 4.0s | Memory: 256MB');
  const [sampleCases, setSampleCases] = useState<Array<{ input: string; output: string }>>([
    { input: '', output: '' },
    { input: '', output: '' }
  ]);
  const [hiddenCases, setHiddenCases] = useState<Array<{ input: string; output: string }>>([
    { input: '', output: '' },
    { input: '', output: '' },
    { input: '', output: '' },
    { input: '', output: '' }
  ]);
  const [referenceSolution, setReferenceSolution] = useState('');
  const [savingCodingQuestion, setSavingCodingQuestion] = useState(false);
  const [modalValidating, setModalValidating] = useState(false);
  const [modalValidationMsg, setModalValidationMsg] = useState<{ valid: boolean; text: string } | null>(null);

  // Unified Delete Confirmation Modal State
  const [confirmDeleteModal, setConfirmDeleteModal] = useState<{
    type: 'course' | 'module' | 'lesson' | 'video' | 'notes' | 'practice' | 'question';
    id: number;
    title: string;
  } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Show Toast
  const showToast = (type: 'success' | 'error', text: string) => {
    setToastMessage({ type, text });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Fetch Metadata dropdowns
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [skRes, dpRes, catRes] = await Promise.all([
          apiClient.get('/catalogue/skills/'),
          apiClient.get('/catalogue/departments/'),
          apiClient.get('/catalogue/categories/')
        ]);
        setSkills(skRes.data.results || skRes.data);
        setDepartments(dpRes.data.results || dpRes.data);
        setCategories(catRes.data.results || catRes.data);
      } catch (err) {
        console.error('Failed to load metadata', err);
      }
    };
    fetchMetadata();
  }, []);

  // Fetch Course details if courseId given
  const fetchCourse = async (id: number) => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/catalogue/faculty/courses/manage/${id}/`);
      const c = res.data;
      setCourse(c);
      setCourseTitle(c.title || '');
      setCourseDesc(c.description || '');
      setSkillId(c.skill?.id || c.skill || '');
      setCategoryId(c.category?.id || c.category || '');
      setDeptId(c.department?.id || c.department || '');
      setLevel(c.level || 'BEGINNER');
      setEstimatedHours(c.estimated_hours || 10);
      setThumbnailUrl(c.thumbnail_url || '');
      setPrereqText(c.prerequisites_text || '');
      setObjectives(c.learning_objectives || c.outcomes || ['', '']);
      setProgrammingLanguage(c.programming_language || '');
    } catch (err) {
      console.error('Failed to load course', err);
      showToast('error', 'Failed to load course details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedCourseId) {
      fetchCourse(selectedCourseId);
      fetchAssessment(selectedCourseId);
    }
  }, [selectedCourseId]);

  // Save / Update Course Header
  const handleSaveCourseHeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!courseTitle.trim()) {
      showToast('error', 'Course title is required.');
      return;
    }
    if (!skillId) {
      showToast('error', 'Please select a target skill pillar.');
      return;
    }

    try {
      setSavingCourse(true);
      const payload = {
        title: courseTitle.trim(),
        description: courseDesc.trim(),
        skill_id: skillId,
        category_id: categoryId || undefined,
        department_id: deptId || undefined,
        level,
        estimated_hours: estimatedHours,
        thumbnail_url: thumbnailUrl.trim() || undefined,
        prerequisites_text: prereqText.trim(),
        learning_objectives: objectives.filter(o => o.trim().length > 0),
        programming_language: programmingLanguage || null
      };

      if (selectedCourseId) {
        const res = await apiClient.put(`/catalogue/faculty/courses/manage/${selectedCourseId}/`, payload);
        setCourse(res.data);
        showToast('success', 'Course details updated successfully.');
      } else {
        const res = await apiClient.post('/catalogue/faculty/courses/manage/', payload);
        const newCourse = res.data;
        setCourse(newCourse);
        setSelectedCourseId(newCourse.id);
        if (onCourseCreated) onCourseCreated(newCourse);
        showToast('success', `Course '${newCourse.title}' created! Now add modules & lessons.`);
      }
    } catch (err: any) {
      console.error('Failed to save course', err);
      const errMsg = err?.response?.data?.error || 'Failed to save course details.';
      showToast('error', errMsg);
    } finally {
      setSavingCourse(false);
    }
  };

  // -------------------------------------------------------------
  // MODULE HANDLERS
  // -------------------------------------------------------------
  const openAddModuleModal = () => {
    setModuleTitle('');
    setModuleDesc('');
    setModuleDuration(30);
    setModuleRequired(true);
    setActiveModuleModal({ isOpen: true, module: null });
  };

  const openEditModuleModal = (m: Module) => {
    setModuleTitle(m.title);
    setModuleDesc(m.description || '');
    setModuleDuration(m.duration_minutes || 30);
    setModuleRequired(m.is_required !== false);
    setActiveModuleModal({ isOpen: true, module: m });
  };

  const handleSaveModule = async () => {
    if (!selectedCourseId || !moduleTitle.trim()) return;
    try {
      const payload = {
        title: moduleTitle.trim(),
        description: moduleDesc.trim(),
        duration_minutes: moduleDuration,
        is_required: moduleRequired
      };

      if (activeModuleModal.module) {
        await apiClient.put(`/catalogue/faculty/modules/${activeModuleModal.module.id}/`, payload);
        showToast('success', 'Module updated successfully.');
      } else {
        await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/modules/`, payload);
        showToast('success', 'New module added.');
      }
      setActiveModuleModal({ isOpen: false });
      fetchCourse(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to save module.');
    }
  };

  const handleDeleteModule = (moduleId: number, title: string) => {
    setConfirmDeleteModal({ type: 'module', id: moduleId, title });
  };

  // -------------------------------------------------------------
  // LESSON HANDLERS
  // -------------------------------------------------------------
  const openAddLessonModal = (moduleId: number) => {
    setLessonTitle('');
    setLessonDesc('');
    setLessonDuration(15);
    setLessonRequired(true);
    setActiveLessonModal({ isOpen: true, moduleId, lesson: null });
  };

  const openEditLessonModal = (moduleId: number, l: Lesson) => {
    setLessonTitle(l.title);
    setLessonDesc(l.description || '');
    setLessonDuration(l.duration_minutes || 15);
    setLessonRequired(l.is_required !== false);
    setActiveLessonModal({ isOpen: true, moduleId, lesson: l });
  };

  const handleSaveLesson = async () => {
    if (!lessonTitle.trim()) return;
    try {
      const payload = {
        title: lessonTitle.trim(),
        description: lessonDesc.trim(),
        duration_minutes: lessonDuration,
        is_required: lessonRequired
      };

      if (activeLessonModal.lesson) {
        await apiClient.put(`/catalogue/faculty/lessons/${activeLessonModal.lesson.id}/`, payload);
        showToast('success', 'Lesson updated successfully.');
      } else {
        await apiClient.post(`/catalogue/faculty/modules/${activeLessonModal.moduleId}/lessons/`, payload);
        showToast('success', 'Lesson created.');
      }
      setActiveLessonModal({ isOpen: false, moduleId: 0 });
      if (selectedCourseId) fetchCourse(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to save lesson.');
    }
  };

  const handleDeleteLesson = (lessonId: number, title: string) => {
    setConfirmDeleteModal({ type: 'lesson', id: lessonId, title });
  };

  // -------------------------------------------------------------
  // YOUTUBE VIDEO RESOURCE HANDLERS
  // -------------------------------------------------------------
  const openAddVideoModal = (lessonId: number) => {
    setVideoUrl('');
    setVideoTitle('');
    setVideoDesc('');
    setVideoRequired(true);
    setVideoMeta(null);
    setActiveVideoModal({ isOpen: true, lessonId, video: null });
  };

  const openEditVideoModal = (lessonId: number, v: VideoResource) => {
    setVideoUrl(v.youtube_url || '');
    setVideoTitle(v.title);
    setVideoDesc(v.description || '');
    setVideoRequired(v.is_required);
    setVideoMeta({
      valid: true,
      video_id: v.youtube_video_id,
      title: v.title,
      author_name: v.channel_name,
      thumbnail_url: v.thumbnail_url,
      embed_url: v.embed_url
    });
    setActiveVideoModal({ isOpen: true, lessonId, video: v });
  };

  const handleParseVideoUrl = async (url: string) => {
    if (!url.trim()) return;
    try {
      setVideoParsing(true);
      const res = await apiClient.post('/catalogue/videos/parse/', { url: url.trim() });
      if (res.data && res.data.valid) {
        setVideoMeta(res.data);
        if (!videoTitle) setVideoTitle(res.data.title || '');
      } else {
        setVideoMeta(null);
        showToast('error', 'Invalid YouTube URL. Please provide a standard watch or share link.');
      }
    } catch (err) {
      setVideoMeta(null);
      showToast('error', 'Could not verify YouTube URL.');
    } finally {
      setVideoParsing(false);
    }
  };

  const handleSaveVideo = async () => {
    if (!videoUrl.trim() || !videoMeta?.video_id) {
      showToast('error', 'Please enter and verify a valid YouTube URL first.');
      return;
    }
    try {
      const payload = {
        youtube_url: videoUrl.trim(),
        title: videoTitle.trim() || videoMeta.title,
        description: videoDesc.trim(),
        is_required: videoRequired
      };

      if (activeVideoModal.video) {
        await apiClient.put(`/catalogue/faculty/resources/${activeVideoModal.video.id}/`, {
          resource_type: 'video',
          ...payload
        });
        showToast('success', 'YouTube video updated.');
      } else {
        await apiClient.post(`/catalogue/faculty/lessons/${activeVideoModal.lessonId}/youtube/`, payload);
        showToast('success', 'YouTube learning video attached to lesson.');
      }
      setActiveVideoModal({ isOpen: false, lessonId: 0 });
      if (selectedCourseId) fetchCourse(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to save YouTube video resource.');
    }
  };

  // AI Video Suggestions
  const handleOpenAiVideoSuggestions = async (lesson: Lesson) => {
    setActiveAiVideoModal({ isOpen: true, lesson });
    try {
      setLoadingAiSuggestions(true);
      const res = await apiClient.post('/catalogue/ai/youtube-suggestions/', {
        skill: course?.skill?.name || courseTitle,
        course: courseTitle,
        module: course?.modules?.find(m => m.id === lesson.module)?.title || '',
        lesson: lesson.title,
        level: level
      });
      setAiSuggestions(res.data.suggestions || []);
    } catch (err) {
      showToast('error', 'Failed to fetch AI video suggestions.');
    } finally {
      setLoadingAiSuggestions(false);
    }
  };

  const handleSelectSuggestedVideo = (sugg: any) => {
    if (!activeAiVideoModal.lesson) return;
    setActiveAiVideoModal({ isOpen: false, lesson: null });
    setVideoUrl(sugg.youtube_url);
    setVideoTitle(sugg.title);
    setVideoDesc(sugg.reason_for_recommendation || '');
    setVideoRequired(true);
    setVideoMeta({
      valid: true,
      video_id: sugg.video_id,
      title: sugg.title,
      author_name: sugg.channel,
      thumbnail_url: sugg.thumbnail_url,
      embed_url: sugg.embed_url
    });
    setActiveVideoModal({ isOpen: true, lessonId: activeAiVideoModal.lesson.id, video: null });
  };

  // -------------------------------------------------------------
  // STUDY NOTES HANDLERS
  // -------------------------------------------------------------
  const openAddNotesModal = (lessonId: number) => {
    setNotesTitle('');
    setNotesContent('');
    setNotesFile(null);
    setNotesRequired(true);
    setNotesTab('write');
    setActiveNotesModal({ isOpen: true, lessonId, material: null });
  };

  const openEditNotesModal = (lessonId: number, m: StudyMaterial) => {
    setNotesTitle(m.title);
    setNotesContent(m.text_content || '');
    setNotesFile(null);
    setNotesRequired(m.is_required);
    setNotesTab('write');
    setActiveNotesModal({ isOpen: true, lessonId, material: m });
  };

  const handleGenerateAiNotes = async (lessonId: number) => {
    try {
      setGeneratingAiNotes(true);
      const res = await apiClient.post(`/catalogue/faculty/lessons/${lessonId}/ai-notes/`);
      const mat = res.data.material;
      setNotesTitle(mat.title);
      setNotesContent(mat.text_content || '');
      setActiveNotesModal(prev => ({ ...prev, material: mat }));
      showToast('success', '10-section AI study notes generated in editable mode! Review before saving.');
    } catch (err) {
      showToast('error', 'AI notes generation failed.');
    } finally {
      setGeneratingAiNotes(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!notesContent.trim() && !notesFile) {
      showToast('error', 'Please provide notes content or attach a study material file.');
      return;
    }
    try {
      if (notesFile) {
        const formData = new FormData();
        formData.append('title', notesTitle.trim() || 'Study Notes');
        formData.append('text_content', notesContent);
        formData.append('is_required', String(notesRequired));
        formData.append('file', notesFile);

        if (activeNotesModal.material) {
          formData.append('resource_type', 'material');
          await apiClient.put(`/catalogue/faculty/resources/${activeNotesModal.material.id}/`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          showToast('success', 'Study notes and document updated.');
        } else {
          await apiClient.post(`/catalogue/faculty/lessons/${activeNotesModal.lessonId}/notes/`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          });
          showToast('success', 'Study notes and document saved to lesson.');
        }
      } else {
        const payload = {
          title: notesTitle.trim() || 'Study Notes',
          text_content: notesContent,
          is_required: notesRequired
        };

        if (activeNotesModal.material) {
          await apiClient.put(`/catalogue/faculty/resources/${activeNotesModal.material.id}/`, {
            resource_type: 'material',
            ...payload
          });
          showToast('success', 'Study notes updated.');
        } else {
          await apiClient.post(`/catalogue/faculty/lessons/${activeNotesModal.lessonId}/notes/`, payload);
          showToast('success', 'Study notes saved to lesson.');
        }
      }
      setNotesFile(null);
      setActiveNotesModal({ isOpen: false, lessonId: 0 });
      if (selectedCourseId) fetchCourse(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to save study notes.');
    }
  };

  // -------------------------------------------------------------
  // PRACTICE QUIZ HANDLERS
  // -------------------------------------------------------------
  const openAddPracticeModal = (lessonId: number) => {
    setPracticeTitle('Concept Check Practice');
    setPracticePassScore(70);
    setPracticeRequired(true);
    setPracticeQuestions([
      { question: '', options: ['', '', '', ''], correct_option: 'A', explanation: '' }
    ]);
    setActivePracticeModal({ isOpen: true, lessonId, practice: null });
  };

  const openEditPracticeModal = (lessonId: number, p: PracticeTask) => {
    setPracticeTitle(p.title);
    setPracticePassScore(p.pass_score || 70);
    setPracticeRequired(p.is_required);
    const qs = (p.content?.questions || []).map((q: any, idx: number) => {
      let cOpt = q.correct_option || 'A';
      if (Array.isArray(q.options) && q.options.length > 0 && !['A', 'B', 'C', 'D'].includes(cOpt)) {
        const found = q.options.findIndex((opt: string) => String(opt).trim().toLowerCase() === String(cOpt).trim().toLowerCase());
        if (found !== -1) {
          cOpt = String.fromCharCode(65 + found);
        }
      }
      return {
        id: q.id || idx + 1,
        question: q.question || '',
        options: Array.isArray(q.options) ? q.options : ['', '', '', ''],
        correct_option: cOpt,
        explanation: q.explanation || ''
      };
    });

    setPracticeQuestions(qs.length > 0 ? qs as any : [
      { id: 1, question: '', options: ['', '', '', ''], correct_option: 'A', explanation: '' }
    ]);
    setActivePracticeModal({ isOpen: true, lessonId, practice: p });
  };

  const handleSavePractice = async () => {
    const validQuestions = practiceQuestions
      .filter(q => q.question.trim().length > 0)
      .map((q, idx) => ({
        id: (q as any).id || (idx + 1),
        question: q.question.trim(),
        options: (q.options || []).map(opt => (opt || '').trim()),
        correct_option: q.correct_option || 'A',
        explanation: q.explanation ? q.explanation.trim() : ''
      }));

    if (validQuestions.length === 0) {
      showToast('error', 'Add at least one complete question.');
      return;
    }
    try {
      const payload = {
        title: practiceTitle.trim() || 'Lesson Practice Quiz',
        task_type: 'MCQ_PRACTICE',
        pass_score: practicePassScore,
        is_required: practiceRequired,
        content: {
          questions: validQuestions
        }
      };

      if (activePracticeModal.practice) {
        await apiClient.put(`/catalogue/faculty/resources/${activePracticeModal.practice.id}/`, {
          resource_type: 'practice',
          ...payload
        });
        showToast('success', 'Practice quiz updated.');
      } else {
        await apiClient.post(`/catalogue/faculty/lessons/${activePracticeModal.lessonId}/practice/`, payload);
        showToast('success', 'Practice quiz attached to lesson.');
      }
      setActivePracticeModal({ isOpen: false, lessonId: 0 });
      if (selectedCourseId) fetchCourse(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to save practice quiz.');
    }
  };

  // -------------------------------------------------------------
  // FINAL CERTIFICATION ASSESSMENT HANDLERS
  // -------------------------------------------------------------
  const fetchAssessment = async (courseId: number) => {
    try {
      setLoadingAssessment(true);
      const res = await apiClient.get(`/catalogue/faculty/courses/${courseId}/final-assessment/`);
      if (res.data.exists && res.data.assessment) {
        setAssessmentData(res.data.assessment);
        setAssessmentTitle(res.data.assessment.title || '');
        setAssessmentDuration(res.data.assessment.duration_minutes || 30);
        setAssessmentPassScore(res.data.assessment.pass_percentage || 70);
        setAssessmentMaxAttempts(res.data.assessment.max_attempts || 3);
        setAssessmentCameraReq(res.data.assessment.camera_required ?? true);
        setAssessmentScreenShareReq(res.data.assessment.screen_share_required ?? true);
        setAssessmentFullscreenReq(res.data.assessment.fullscreen_required ?? true);
        setAssessmentFaceDetectReq(res.data.assessment.face_detection_enabled ?? true);
      } else {
        const defaultTitle = res.data.default_title || `${courseTitle || 'Course'} Final Certification Assessment`;
        setAssessmentData({
          title: defaultTitle,
          duration_minutes: 30,
          pass_percentage: 70,
          max_attempts: 3,
          camera_required: true,
          screen_share_required: true,
          fullscreen_required: true,
          face_detection_enabled: true,
          is_published: true,
          questions: [],
          questions_count: 0,
          total_marks: 0
        });
        setAssessmentTitle(defaultTitle);
        setAssessmentDuration(30);
        setAssessmentPassScore(70);
        setAssessmentMaxAttempts(3);
        setAssessmentCameraReq(true);
        setAssessmentScreenShareReq(true);
        setAssessmentFullscreenReq(true);
        setAssessmentFaceDetectReq(true);
      }

      // Also fetch dedicated practical coding questions for this course
      try {
        setLoadingCodingQuestions(true);
        const codingRes = await apiClient.get(`/assessments/courses/${courseId}/coding-questions/`);
        setCodingQuestions(codingRes.data.questions || []);
      } catch (cErr) {
        console.error('Failed to load coding questions', cErr);
      } finally {
        setLoadingCodingQuestions(false);
      }
    } catch (err) {
      console.error('Failed to load final assessment', err);
    } finally {
      setLoadingAssessment(false);
    }
  };

  const handleSaveAssessmentSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId) return;
    try {
      setSavingAssessmentSettings(true);
      const payload = {
        title: assessmentTitle.trim() || `${courseTitle} Final Certification Assessment`,
        duration_minutes: assessmentDuration,
        pass_percentage: assessmentPassScore,
        max_attempts: assessmentMaxAttempts,
        camera_required: assessmentCameraReq,
        screen_share_required: assessmentScreenShareReq,
        fullscreen_required: assessmentFullscreenReq,
        face_detection_enabled: assessmentFaceDetectReq,
        is_published: true
      };
      const res = await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/`, payload);
      setAssessmentData(res.data.assessment);
      showToast('success', 'Final assessment settings saved successfully.');
      setIsAssessmentSettingsOpen(false);
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to save assessment settings.');
    } finally {
      setSavingAssessmentSettings(false);
    }
  };

  const openAddManualQuestionModal = () => {
    setEditingQuestionId(null);
    setManualQText('');
    setManualQTopic('');
    setManualQDifficulty('MEDIUM');
    setManualQMarks(1);
    setManualQExplanation('');
    setManualQOptions(['', '', '', '']);
    setManualQCorrectIndex(0);
    setIsManualQuestionModalOpen(true);
  };

  const openEditManualQuestionModal = (q: FinalAssessmentQuestion) => {
    setEditingQuestionId(q.id || null);
    setManualQText(q.text || '');
    setManualQTopic(q.topic_tag || '');
    setManualQDifficulty(q.difficulty || 'MEDIUM');
    setManualQMarks(q.marks || 1);
    setManualQExplanation(q.explanation || '');
    const opts = (q.options || []).map(o => o.text);
    while (opts.length < 4) opts.push('');
    setManualQOptions(opts.slice(0, 4));
    const corrIdx = (q.options || []).findIndex(o => o.is_correct);
    setManualQCorrectIndex(corrIdx >= 0 ? corrIdx : 0);
    setIsManualQuestionModalOpen(true);
  };

  const handleSaveManualQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId) return;
    if (!manualQText.trim()) {
      showToast('error', 'Question prompt is required.');
      return;
    }
    const filledOptions = manualQOptions.map(o => o.trim()).filter(Boolean);
    if (filledOptions.length < 2) {
      showToast('error', 'At least two answer options are required.');
      return;
    }
    if (!manualQOptions[manualQCorrectIndex]?.trim()) {
      showToast('error', 'The correct option cannot be blank.');
      return;
    }

    try {
      setSavingManualQuestion(true);
      const optionsPayload = manualQOptions
        .filter(o => o.trim().length > 0)
        .map((text, idx) => ({
          text: text.trim(),
          is_correct: idx === manualQCorrectIndex,
          order: idx + 1
        }));

      const payload = {
        text: manualQText.trim(),
        topic_tag: manualQTopic.trim() || 'core',
        difficulty: manualQDifficulty,
        marks: manualQMarks,
        explanation: manualQExplanation.trim(),
        options: optionsPayload
      };

      if (editingQuestionId) {
        await apiClient.put(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/questions/${editingQuestionId}/`, payload);
        showToast('success', 'Question updated successfully.');
      } else {
        await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/questions/`, payload);
        showToast('success', 'Question added to Final Assessment.');
      }
      setIsManualQuestionModalOpen(false);
      fetchAssessment(selectedCourseId);
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to save question.');
    } finally {
      setSavingManualQuestion(false);
    }
  };

  const handleDeleteAssessmentQuestion = (qId: number, qText: string) => {
    setConfirmDeleteModal({ type: 'question', id: qId, title: qText.length > 60 ? qText.slice(0, 60) + '...' : qText });
  };

  // -------------------------------------------------------------
  // PRACTICAL CODING ASSESSMENT HANDLERS
  // -------------------------------------------------------------
  const openAddCodingModal = () => {
    setEditingCodingId(null);
    setCodingTitle('');
    setCodingStatement('');
    setCodingLang(programmingLanguage || course?.programming_language || 'python');
    setCodingTopic('coding');
    setCodingMarks(10);
    setCodingInputFormat('Standard Input (stdin)');
    setCodingOutputFormat('Standard Output (stdout)');
    setCodingConstraints('Time Limit: 4.0s | Memory: 256MB');
    setSampleCases([
      { input: '', output: '' },
      { input: '', output: '' }
    ]);
    setHiddenCases([
      { input: '', output: '' },
      { input: '', output: '' },
      { input: '', output: '' },
      { input: '', output: '' }
    ]);
    setReferenceSolution('');
    setModalValidationMsg(null);
    setIsCodingModalOpen(true);
  };

  const openEditCodingModal = (q: any) => {
    setEditingCodingId(q.id);
    setCodingTitle(q.title || q.text || '');
    setCodingStatement(q.problem_statement || q.text || '');
    setCodingLang(q.programming_language || 'python');
    setCodingTopic(q.topic_tag || 'coding');
    setCodingMarks(q.marks || 10);
    setCodingInputFormat(q.input_format || 'Standard Input (stdin)');
    setCodingOutputFormat(q.output_format || 'Standard Output (stdout)');
    setCodingConstraints(q.constraints || 'Time Limit: 4.0s | Memory: 256MB');

    const sc = q.sample_test_cases || [];
    setSampleCases([
      { input: sc[0]?.input || '', output: sc[0]?.output || '' },
      { input: sc[1]?.input || '', output: sc[1]?.output || '' }
    ]);

    const hc = q.hidden_test_cases || [];
    setHiddenCases([
      { input: hc[0]?.input || '', output: hc[0]?.output || '' },
      { input: hc[1]?.input || '', output: hc[1]?.output || '' },
      { input: hc[2]?.input || '', output: hc[2]?.output || '' },
      { input: hc[3]?.input || '', output: hc[3]?.output || '' }
    ]);

    setReferenceSolution(q.reference_solution || '');
    setModalValidationMsg(null);
    setIsCodingModalOpen(true);
  };

  const handleModalValidateSolution = async () => {
    if (!referenceSolution.trim()) {
      setModalValidationMsg({ valid: false, text: 'Please enter a reference solution first.' });
      return;
    }
    try {
      setModalValidating(true);
      setModalValidationMsg(null);
      if (editingCodingId) {
        const res = await apiClient.post(`/assessments/coding-questions/${editingCodingId}/validate/`, {
          reference_solution: referenceSolution,
          language: codingLang
        });
        if (res.data.valid) {
          setModalValidationMsg({ valid: true, text: 'Sandbox Verification PASSED: Reference solution passed all 6 test cases!' });
        } else {
          setModalValidationMsg({ valid: false, text: res.data.error || 'Validation failed in sandbox.' });
        }
      } else {
        setModalValidationMsg({ valid: true, text: 'Solution is formatted. Full automated sandbox verification will execute upon saving.' });
      }
    } catch (err: any) {
      setModalValidationMsg({ valid: false, text: err?.response?.data?.error || 'Validation failed in sandbox.' });
    } finally {
      setModalValidating(false);
    }
  };

  const handleSaveCodingQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCourseId) return;
    if (!codingTitle.trim() || !codingStatement.trim()) {
      showToast('error', 'Problem title and problem statement are required.');
      return;
    }
    for (let i = 0; i < 2; i++) {
      if (!sampleCases[i]?.input && !sampleCases[i]?.output) {
        showToast('error', `Sample test case ${i + 1} must have input and output.`);
        return;
      }
    }
    for (let i = 0; i < 4; i++) {
      if (!hiddenCases[i]?.input && !hiddenCases[i]?.output) {
        showToast('error', `Hidden test case ${i + 1} must have input and output.`);
        return;
      }
    }

    try {
      setSavingCodingQuestion(true);
      const payload = {
        title: codingTitle.trim(),
        problem_statement: codingStatement.trim(),
        programming_language: codingLang,
        topic_tag: codingTopic.trim() || 'coding',
        difficulty: 'EASY',
        marks: Number(codingMarks) || 10,
        input_format: codingInputFormat.trim(),
        output_format: codingOutputFormat.trim(),
        constraints: codingConstraints.trim(),
        sample_test_cases: sampleCases,
        hidden_test_cases: hiddenCases,
        reference_solution: referenceSolution.trim(),
        approval_status: 'APPROVED'
      };

      if (editingCodingId) {
        await apiClient.put(`/assessments/coding-questions/${editingCodingId}/`, payload);
        showToast('success', 'Practical coding problem updated.');
      } else {
        await apiClient.post(`/assessments/courses/${selectedCourseId}/coding-questions/`, payload);
        showToast('success', 'Practical coding problem created and approved for Final Assessment.');
      }

      setIsCodingModalOpen(false);
      fetchAssessment(selectedCourseId);
    } catch (err: any) {
      const errMsg = err?.response?.data?.error || err?.response?.data?.programming_language || 'Failed to save coding problem.';
      showToast('error', typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
    } finally {
      setSavingCodingQuestion(false);
    }
  };

  const handleGenerateAiCoding = async () => {
    if (!selectedCourseId) return;
    try {
      setGeneratingAiCoding(true);
      const lang = programmingLanguage || course?.programming_language || 'python';
      const res = await apiClient.post('/assessments/coding-questions/ai-generate/', {
        course_id: selectedCourseId,
        programming_language: lang
      });
      showToast('success', `AI generated '${res.data.title}' (EASY difficulty)! Please review and publish it.`);
      fetchAssessment(selectedCourseId);
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to generate AI coding problem.');
    } finally {
      setGeneratingAiCoding(false);
    }
  };

  const handlePublishCoding = async (id: number) => {
    try {
      setPublishingCodingId(id);
      const res = await apiClient.post(`/assessments/coding-questions/${id}/publish/`);
      showToast('success', res.data.message || 'Coding problem reviewed and published! Active for Final Assessment.');
      if (selectedCourseId) fetchAssessment(selectedCourseId);
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to publish coding problem.');
    } finally {
      setPublishingCodingId(null);
    }
  };

  const handleValidateCodingInSandbox = async (id: number) => {
    try {
      setValidatingCodingId(id);
      setCodingValidationResult(null);
      const res = await apiClient.post(`/assessments/coding-questions/${id}/validate/`);
      setCodingValidationResult({
        id,
        valid: res.data.valid,
        message: res.data.valid ? 'Passed all 6 test cases in sandbox!' : (res.data.error || 'Failed sandbox test')
      });
      if (res.data.valid) {
        showToast('success', 'Sandbox Verification PASSED: Reference solution passed all 6 test cases (2 sample + 4 hidden)!');
      } else {
        showToast('error', `Sandbox Verification FAILED: ${res.data.error}`);
      }
    } catch (err: any) {
      setCodingValidationResult({
        id,
        valid: false,
        message: err?.response?.data?.error || 'Validation failed.'
      });
      showToast('error', err?.response?.data?.error || 'Sandbox execution error.');
    } finally {
      setValidatingCodingId(null);
    }
  };

  const handleDeleteCoding = async (id: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete the coding problem '${title}'?`)) return;
    try {
      await apiClient.delete(`/assessments/coding-questions/${id}/`);
      showToast('success', 'Coding problem deleted.');
      if (selectedCourseId) fetchAssessment(selectedCourseId);
    } catch (err) {
      showToast('error', 'Failed to delete coding problem.');
    }
  };

  const handleOpenAiModal = () => {
    setAiGeneratedQuestions([]);
    setSelectedAiIndices([]);
    setGeneratingAiQuestions(false);
    setIsAiQuestionModalOpen(true);
  };

  const handleGenerateAiQuestions = async (autoSave: boolean = false) => {
    if (!selectedCourseId) return;
    try {
      setGeneratingAiQuestions(true);
      const res = await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/generate-ai-questions/`, {
        count: aiQuestionCount,
        difficulty: aiQuestionDifficulty,
        auto_save: autoSave
      });

      if (autoSave) {
        showToast('success', `${res.data.generated_count || aiQuestionCount} questions generated and added to Final Assessment!`);
        setIsAiQuestionModalOpen(false);
        fetchAssessment(selectedCourseId);
      } else {
        const questions: FinalAssessmentQuestion[] = res.data.questions || [];
        setAiGeneratedQuestions(questions);
        setSelectedAiIndices(questions.map((_, idx) => idx));
        showToast('success', `${questions.length} questions generated! Review and pick below.`);
      }
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to generate questions with AI.');
    } finally {
      setGeneratingAiQuestions(false);
    }
  };

  const handleToggleAiCandidate = (index: number) => {
    setSelectedAiIndices(prev =>
      prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
    );
  };

  const handleSelectAllAi = () => {
    if (selectedAiIndices.length === aiGeneratedQuestions.length) {
      setSelectedAiIndices([]);
    } else {
      setSelectedAiIndices(aiGeneratedQuestions.map((_, idx) => idx));
    }
  };

  const handleSaveSelectedAiQuestions = async () => {
    if (!selectedCourseId) return;
    const selectedQuestions = selectedAiIndices.map(i => aiGeneratedQuestions[i]);
    if (selectedQuestions.length === 0) {
      showToast('error', 'Please select at least one question to add.');
      return;
    }
    try {
      setSavingAiQuestions(true);
      await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/questions/`, {
        questions: selectedQuestions
      });
      showToast('success', `Added ${selectedQuestions.length} AI questions to Final Assessment!`);
      setIsAiQuestionModalOpen(false);
      fetchAssessment(selectedCourseId);
    } catch (err: any) {
      showToast('error', err?.response?.data?.error || 'Failed to save selected questions.');
    } finally {
      setSavingAiQuestions(false);
    }
  };

  // Delete Handlers & Execution
  const handleDeleteCourse = (courseId: number, title: string) => {
    setConfirmDeleteModal({ type: 'course', id: courseId, title });
  };

  const handleDeleteResource = (type: 'video' | 'material' | 'practice', id: number, title: string) => {
    setConfirmDeleteModal({ type: type === 'material' ? 'notes' : type, id, title });
  };

  const handleExecuteDelete = async () => {
    if (!confirmDeleteModal) return;
    try {
      setIsDeleting(true);
      const { type, id, title } = confirmDeleteModal;
      if (type === 'course') {
        await apiClient.delete(`/catalogue/faculty/courses/${id}/`);
        showToast('success', `Course '${title}' permanently deleted.`);
        setConfirmDeleteModal(null);
        setCourse(null);
        setSelectedCourseId(null);
        if (onClose) onClose();
      } else if (type === 'module') {
        await apiClient.delete(`/catalogue/faculty/modules/${id}/`);
        showToast('success', `Module '${title}' deleted.`);
        setConfirmDeleteModal(null);
        setActiveModuleModal({ isOpen: false });
        if (selectedCourseId) fetchCourse(selectedCourseId);
      } else if (type === 'lesson') {
        await apiClient.delete(`/catalogue/faculty/lessons/${id}/`);
        showToast('success', `Lesson '${title}' deleted.`);
        setConfirmDeleteModal(null);
        setActiveLessonModal({ isOpen: false, moduleId: 0 });
        if (selectedCourseId) fetchCourse(selectedCourseId);
      } else if (type === 'video') {
        await apiClient.delete(`/catalogue/faculty/resources/${id}/?resource_type=video`);
        showToast('success', 'Video resource deleted.');
        setConfirmDeleteModal(null);
        setActiveVideoModal({ isOpen: false, lessonId: 0 });
        if (selectedCourseId) fetchCourse(selectedCourseId);
      } else if (type === 'notes') {
        await apiClient.delete(`/catalogue/faculty/resources/${id}/?resource_type=material`);
        showToast('success', 'Study notes deleted.');
        setConfirmDeleteModal(null);
        setActiveNotesModal({ isOpen: false, lessonId: 0 });
        if (selectedCourseId) fetchCourse(selectedCourseId);
      } else if (type === 'practice') {
        await apiClient.delete(`/catalogue/faculty/resources/${id}/?resource_type=practice`);
        showToast('success', 'Practice quiz deleted.');
        setConfirmDeleteModal(null);
        setActivePracticeModal({ isOpen: false, lessonId: 0 });
        if (selectedCourseId) fetchCourse(selectedCourseId);
      } else if (type === 'question') {
        if (selectedCourseId) {
          await apiClient.delete(`/catalogue/faculty/courses/${selectedCourseId}/final-assessment/questions/${id}/`);
          showToast('success', 'Question deleted from Final Assessment.');
          setConfirmDeleteModal(null);
          fetchAssessment(selectedCourseId);
        }
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.error || `Failed to delete ${confirmDeleteModal.type}.`;
      showToast('error', errMsg);
    } finally {
      setIsDeleting(false);
    }
  };

  // -------------------------------------------------------------
  // VALIDATE & SUBMIT FOR REVIEW
  // -------------------------------------------------------------
  const handleValidateCurriculum = async () => {
    if (!selectedCourseId) return;
    try {
      const res = await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/validate/`);
      setValidationModal({ isOpen: true, result: res.data });
    } catch (err: any) {
      setValidationModal({ isOpen: true, result: err?.response?.data || { valid: false, errors: ['Validation check failed.'] } });
    }
  };

  const handleSubmitForReview = async () => {
    if (!selectedCourseId) return;
    if (!window.confirm("Submit course proposal for Institutional Administration review? Once submitted, it cannot be modified until reviewed.")) return;
    try {
      setSubmittingReview(true);
      const res = await apiClient.post(`/catalogue/faculty/courses/${selectedCourseId}/submit-review/`);
      showToast('success', res.data.message || 'Course submitted for review!');
      fetchCourse(selectedCourseId);
    } catch (err: any) {
      const errors = err?.response?.data?.validation_errors || [err?.response?.data?.error || 'Validation failed.'];
      setValidationModal({ isOpen: true, result: { valid: false, errors } });
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toastMessage && (
        <div className={`fixed top-5 right-5 z-50 px-5 py-3 rounded-2xl shadow-xl border text-xs font-bold flex items-center gap-2 animate-in fade-in slide-in-from-top-4 ${
          toastMessage.type === 'success'
            ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500/50 backdrop-blur-md'
            : 'bg-rose-950/90 text-rose-300 border-rose-500/50 backdrop-blur-md'
        }`}>
          {toastMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <AlertTriangle className="w-4 h-4 text-rose-400" />}
          {toastMessage.text}
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-primary-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-accent-400 bg-accent-500/20 px-2.5 py-1 rounded-full border border-accent-400/30">
              Interactive Curriculum Studio
            </span>
            {course && (
              <span className={`text-[10px] font-bold uppercase px-2.5 py-1 rounded-full border ${
                course.approval_status === 'APPROVED' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                course.approval_status === 'PENDING_REVIEW' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' :
                'bg-slate-700/40 text-slate-300 border-slate-600/40'
              }`}>
                {course.approval_status}
              </span>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-black mt-2">
            {course ? course.title : 'Create New Course Curriculum'}
          </h1>
          <p className="text-xs text-slate-300 mt-1">
            Build structured modules and lessons. Enrich every lesson with real YouTube videos, editable AI notes, and practice quizzes.
          </p>
        </div>

        {/* Global Studio Actions */}
        {course && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setIsPreviewOpen(true)}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
            >
              <Eye className="w-3.5 h-3.5 text-accent-400" />
              Preview Course
            </button>
            <button
              type="button"
              onClick={handleValidateCurriculum}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
            >
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              Validate Curriculum
            </button>
            <button
              type="button"
              onClick={handleSubmitForReview}
              disabled={submittingReview || course.approval_status === 'PENDING_REVIEW'}
              className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              {course.approval_status === 'PENDING_REVIEW' ? 'Pending Review' : 'Submit for Review'}
            </button>
            <button
              type="button"
              onClick={() => handleDeleteCourse(course.id, course.title)}
              className="px-4 py-2 bg-rose-950/80 hover:bg-rose-900 text-rose-300 text-xs font-bold rounded-xl border border-rose-800/80 flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
              title="Permanently Delete Course"
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
              Delete Course
            </button>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="p-2 bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white rounded-xl"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 p-3 bg-primary-50 text-primary-900 rounded-2xl text-xs font-semibold animate-pulse border border-primary-200">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Loading course curriculum and resources...</span>
        </div>
      )}

      {/* SECTION 1: COURSE DETAILS ACCORDION / FORM */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary-900" />
              Step 1: Course Specification &amp; Engineering Details
            </h2>
            <p className="text-xs text-slate-500">Configure institutional metadata, skill category, level, and prerequisites.</p>
          </div>
        </div>

        <form onSubmit={handleSaveCourseHeader} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Course Title *</label>
              <input
                type="text"
                placeholder="e.g. Industrial Python Programming & Microservices Architecture"
                value={courseTitle}
                onChange={(e) => setCourseTitle(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs font-semibold"
                required
              />
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Target Skill Pillar *</label>
              <select
                value={skillId}
                onChange={(e) => setSkillId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs font-semibold"
                required
              >
                <option value="">Select Target Skill...</option>
                {skills.map((sk) => (
                  <option key={sk.id} value={sk.id}>{sk.name} ({sk.level})</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Skill Category</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs"
              >
                <option value="">Select Category...</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Department</label>
              <select
                value={deptId}
                onChange={(e) => setDeptId(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs"
              >
                <option value="">Interdisciplinary / All</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.code} - {d.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Proficiency Level</label>
              <select
                value={level}
                onChange={(e) => setLevel(e.target.value as any)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs font-semibold"
              >
                <option value="BEGINNER">Beginner</option>
                <option value="INTERMEDIATE">Intermediate</option>
                <option value="ADVANCED">Advanced</option>
                <option value="EXPERT">Expert</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Estimated Hours</label>
              <input
                type="number"
                min="2"
                max="160"
                value={estimatedHours}
                onChange={(e) => setEstimatedHours(Number(e.target.value))}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs font-semibold text-center"
              />
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1">Course Description *</label>
            <textarea
              rows={3}
              placeholder="In-depth outline of syllabus, academic outcomes, and industry readiness..."
              value={courseDesc}
              onChange={(e) => setCourseDesc(e.target.value)}
              className="w-full p-3 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block font-bold text-slate-700 mb-1">Course Thumbnail Image URL</label>
              <input
                type="url"
                placeholder="https://images.unsplash.com/photo-..."
                value={thumbnailUrl}
                onChange={(e) => setThumbnailUrl(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1">Prerequisites</label>
              <input
                type="text"
                placeholder="e.g. Basic programming logic, discrete math"
                value={prereqText}
                onChange={(e) => setPrereqText(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 mb-1 flex items-center gap-1">
                <Code2 className="w-3.5 h-3.5 text-primary-900" />
                Programming Language
              </label>
              <select
                value={programmingLanguage}
                onChange={(e) => setProgrammingLanguage(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-600 text-xs font-semibold"
              >
                <option value="">None (Non-Programming Course)</option>
                <option value="python">Python (Hands-on Coding Assessment)</option>
                <option value="java">Java (Hands-on Coding Assessment)</option>
                <option value="c">C Programming (Hands-on Coding Assessment)</option>
                <option value="cpp">C++ (Hands-on Coding Assessment)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="submit"
              disabled={savingCourse}
              className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              {savingCourse ? 'Saving Course...' : selectedCourseId ? 'Update Course Details' : 'Create & Proceed to Modules'}
            </button>
          </div>
        </form>
      </div>

      {/* SECTION 2: MODULES & LESSONS TREE (RESOURCES INCLUDED) */}
      {selectedCourseId && course && (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-accent-600" />
                Step 2: Modules, Lessons &amp; Learning Resources
              </h2>
              <p className="text-xs text-slate-500">
                Organize curriculum hierarchically: Module &rarr; Lesson &rarr; 🎥 Video, 📝 Notes, 🧪 Practice.
              </p>
            </div>
            <button
              type="button"
              onClick={openAddModuleModal}
              className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              Add Module
            </button>
          </div>

          {(!course.modules || course.modules.length === 0) ? (
            <div className="border-2 border-dashed border-slate-200 rounded-2xl p-12 text-center space-y-3">
              <Layers className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-sm font-bold text-slate-700">No Modules Added Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Begin structuring your curriculum by clicking &ldquo;Add Module&rdquo; above.
              </p>
              <button
                type="button"
                onClick={openAddModuleModal}
                className="px-4 py-2 bg-primary-900 text-white text-xs font-bold rounded-xl shadow-sm cursor-pointer"
              >
                + Create Module 1
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {course.modules.map((mod, mIdx) => (
                <div key={mod.id} className="border border-slate-200 rounded-2xl overflow-hidden bg-slate-50/50 shadow-sm">
                  {/* Module Header Bar */}
                  <div className="bg-slate-100/80 px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-full bg-primary-900 text-white text-[11px] font-bold flex items-center justify-center">
                        {mIdx + 1}
                      </span>
                      <h3 className="text-sm font-bold text-slate-900">{mod.title}</h3>
                      <span className="text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200 font-medium">
                        {mod.duration_minutes || 30} mins
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        mod.is_required ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-slate-50 text-slate-500 border-slate-200'
                      }`}>
                        {mod.is_required ? 'Required Module' : 'Optional Module'}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => openAddLessonModal(mod.id)}
                        className="px-3 py-1 bg-white hover:bg-primary-50 text-primary-900 border border-primary-200 text-xs font-bold rounded-lg flex items-center gap-1 transition-all cursor-pointer"
                      >
                        <PlusCircle className="w-3.5 h-3.5" />
                        Add Lesson
                      </button>
                      <button
                        type="button"
                        onClick={() => openEditModuleModal(mod)}
                        className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-white rounded-lg transition-all"
                        title="Edit Module"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteModule(mod.id, mod.title)}
                        className="p-1.5 text-rose-500 hover:text-rose-700 hover:bg-white rounded-lg transition-all"
                        title="Delete Module"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Module Lessons Container */}
                  <div className="p-4 sm:p-5 space-y-4">
                    {(!mod.lessons || mod.lessons.length === 0) ? (
                      <div className="p-4 bg-white rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
                        No lessons in this module. Click <strong>Add Lesson</strong> to begin adding topics and learning resources.
                      </div>
                    ) : (
                      mod.lessons.map((lsn, lIdx) => (
                        <div key={lsn.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 space-y-3 transition-all hover:border-slate-300">
                          {/* Lesson Title Bar */}
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-extrabold text-slate-700">
                                Lesson {lIdx + 1}:
                              </span>
                              <span className="text-xs font-bold text-slate-900">{lsn.title}</span>
                              <span className="text-[10px] text-slate-400">({lsn.duration_minutes || 15}m)</span>
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                lsn.is_required ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500'
                              }`}>
                                {lsn.is_required ? 'Required' : 'Optional'}
                              </span>
                            </div>

                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => openEditLessonModal(mod.id, lsn)}
                                className="p-1 text-slate-400 hover:text-slate-700"
                                title="Edit Lesson"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteLesson(lsn.id, lsn.title)}
                                className="p-1 text-rose-400 hover:text-rose-600"
                                title="Delete Lesson"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>

                          {/* EXACT RESOURCES TREE: Video, Notes, Practice */}
                          <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 text-xs">
                            {/* 1. 🎥 VIDEO RESOURCE CARD */}
                            <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
                              <div>
                                <div className="flex items-center justify-between font-bold text-slate-800 text-[11px] mb-1.5">
                                  <span className="flex items-center gap-1 text-rose-600">
                                    <Video className="w-3.5 h-3.5" />
                                    🎥 Video Lecture
                                  </span>
                                  {lsn.videos && lsn.videos.length > 0 && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 font-bold border border-rose-200">
                                      YouTube
                                    </span>
                                  )}
                                </div>

                                {lsn.videos && lsn.videos.length > 0 ? (
                                  <div className="space-y-2">
                                    {lsn.videos.map((vid) => (
                                      <div key={vid.id} className="bg-white p-2 rounded-lg border border-slate-200 space-y-1.5">
                                        <div className="flex items-start gap-2">
                                          {vid.thumbnail_url && (
                                            <img src={vid.thumbnail_url} alt="" className="w-14 h-9 object-cover rounded shadow-xs shrink-0" />
                                          )}
                                          <div className="min-w-0">
                                            <p className="font-bold text-slate-900 truncate text-[11px]">{vid.title}</p>
                                            <p className="text-[10px] text-slate-500 truncate">{vid.channel_name || 'YouTube Creator'}</p>
                                          </div>
                                        </div>
                                        <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-100">
                                          <span className={vid.is_required ? 'text-indigo-600 font-bold' : 'text-slate-400'}>
                                            {vid.is_required ? 'Required Video' : 'Optional Video'}
                                          </span>
                                          <div className="flex items-center gap-1">
                                            <button
                                              type="button"
                                              onClick={() => setPreviewingVideo(vid)}
                                              className="text-rose-600 font-bold hover:underline flex items-center gap-0.5"
                                            >
                                              <Play className="w-2.5 h-2.5" /> Preview
                                            </button>
                                            <span className="text-slate-300">|</span>
                                            <button
                                              type="button"
                                              onClick={() => openEditVideoModal(lsn.id, vid)}
                                              className="text-primary-800 hover:underline"
                                            >
                                              Edit
                                            </button>
                                            <span className="text-slate-300">|</span>
                                            <button
                                              type="button"
                                              onClick={() => handleDeleteResource('video', vid.id, vid.title)}
                                              className="text-rose-600 hover:underline"
                                            >
                                              Remove
                                            </button>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-[11px] text-slate-400 italic">No video assigned to this lesson yet.</p>
                                )}
                              </div>

                              <div className="flex items-center gap-1.5 pt-1">
                                <button
                                  type="button"
                                  onClick={() => openAddVideoModal(lsn.id)}
                                  className="flex-1 py-1 px-2 bg-white hover:bg-rose-50 text-rose-700 border border-rose-200 text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1"
                                >
                                  <PlusCircle className="w-3 h-3" />
                                  Add Video
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleOpenAiVideoSuggestions(lsn)}
                                  className="py-1 px-2 bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 text-purple-700 border border-purple-200 text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1"
                                  title="Suggest YouTube Videos with AI"
                                >
                                  <Sparkles className="w-3 h-3 text-purple-600" />
                                  AI Suggest
                                </button>
                              </div>
                            </div>

                            {/* 2. 📝 STUDY NOTES RESOURCE CARD */}
                            <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
                              <div>
                                <div className="flex items-center justify-between font-bold text-slate-800 text-[11px] mb-1.5">
                                  <span className="flex items-center gap-1 text-primary-900">
                                    <FileText className="w-3.5 h-3.5" />
                                    📝 Study Notes
                                  </span>
                                  {lsn.materials && lsn.materials.length > 0 && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary-50 text-primary-800 font-bold border border-primary-200">
                                      {lsn.materials[0].source_type === 'AI_GENERATED' ? 'AI Notes' : 'Faculty Notes'}
                                    </span>
                                  )}
                                </div>

                                {lsn.materials && lsn.materials.length > 0 ? (
                                  <div className="space-y-2">
                                    {lsn.materials.map((mat) => (
                                      <div key={mat.id} className="bg-white p-2 rounded-lg border border-slate-200 space-y-1.5">
                                        <p className="font-bold text-slate-900 truncate text-[11px]">{mat.title}</p>
                                        <p className="text-[10px] text-slate-500 line-clamp-2">
                                          {mat.text_content?.substring(0, 100) || 'Structured study guide.'}
                                        </p>
                                        <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-100">
                                          <span className={mat.is_required ? 'text-indigo-600 font-bold' : 'text-slate-400'}>
                                            {mat.is_required ? 'Required Notes' : 'Optional Notes'}
                                          </span>
                                          <div className="flex items-center gap-1">
                                            <button
                                              type="button"
                                              onClick={() => setPreviewingNotes(mat)}
                                              className="text-primary-900 font-bold hover:underline flex items-center gap-0.5"
                                            >
                                              <Eye className="w-2.5 h-2.5" /> Preview
                                            </button>
                                            <span className="text-slate-300">|</span>
                                            <button
                                              type="button"
                                              onClick={() => openEditNotesModal(lsn.id, mat)}
                                              className="text-primary-800 hover:underline"
                                            >
                                              Edit Notes
                                            </button>
                                            <span className="text-slate-300">|</span>
                                            <button
                                              type="button"
                                              onClick={() => handleDeleteResource('material', mat.id, mat.title)}
                                              className="text-rose-600 hover:underline"
                                            >
                                              Remove
                                            </button>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-[11px] text-slate-400 italic">No notes attached to this lesson yet.</p>
                                )}
                              </div>

                              <div className="flex items-center gap-1.5 pt-1">
                                <button
                                  type="button"
                                  onClick={() => openAddNotesModal(lsn.id)}
                                  className="flex-1 py-1 px-2 bg-white hover:bg-primary-50 text-primary-900 border border-primary-200 text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1"
                                >
                                  <PlusCircle className="w-3 h-3" />
                                  Add Notes
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleGenerateAiNotes(lsn.id)}
                                  disabled={generatingAiNotes}
                                  className="py-1 px-2 bg-gradient-to-r from-indigo-50 to-purple-50 hover:from-indigo-100 hover:to-purple-100 text-indigo-700 border border-indigo-200 text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1"
                                  title="Generate 10-Section AI Study Notes"
                                >
                                  <Sparkles className="w-3 h-3 text-indigo-600" />
                                  AI Notes
                                </button>
                              </div>
                            </div>

                            {/* 3. 🧪 PRACTICE RESOURCE CARD */}
                            <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200 flex flex-col justify-between space-y-2">
                              <div>
                                <div className="flex items-center justify-between font-bold text-slate-800 text-[11px] mb-1.5">
                                  <span className="flex items-center gap-1 text-emerald-700">
                                    <HelpCircle className="w-3.5 h-3.5" />
                                    🧪 Practice Quiz
                                  </span>
                                  {lsn.practice_tasks && lsn.practice_tasks.length > 0 && (
                                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                                      MCQ Practice
                                    </span>
                                  )}
                                </div>

                                {lsn.practice_tasks && lsn.practice_tasks.length > 0 ? (
                                  <div className="space-y-2">
                                    {lsn.practice_tasks.map((prac) => (
                                      <div key={prac.id} className="bg-white p-2 rounded-lg border border-slate-200 space-y-1.5">
                                        <p className="font-bold text-slate-900 truncate text-[11px]">{prac.title}</p>
                                        <p className="text-[10px] text-slate-500">
                                          {prac.content?.questions?.length || 0} Questions • Pass: {prac.pass_score}%
                                        </p>
                                        <div className="flex items-center justify-between text-[10px] pt-1 border-t border-slate-100">
                                          <span className={prac.is_required ? 'text-indigo-600 font-bold' : 'text-slate-400'}>
                                            {prac.is_required ? 'Required Quiz' : 'Optional Quiz'}
                                          </span>
                                          <div className="flex items-center gap-1">
                                            <button
                                              type="button"
                                              onClick={() => openEditPracticeModal(lsn.id, prac)}
                                              className="text-primary-800 hover:underline"
                                            >
                                              Edit
                                            </button>
                                            <span className="text-slate-300">|</span>
                                            <button
                                              type="button"
                                              onClick={() => handleDeleteResource('practice', prac.id, prac.title)}
                                              className="text-rose-600 hover:underline"
                                            >
                                              Remove
                                            </button>
                                          </div>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-[11px] text-slate-400 italic">No practice quiz attached to this lesson yet.</p>
                                )}
                              </div>

                              <div className="pt-1">
                                <button
                                  type="button"
                                  onClick={() => openAddPracticeModal(lsn.id)}
                                  className="w-full py-1 px-2 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1"
                                >
                                  <PlusCircle className="w-3 h-3" />
                                  Add Practice
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION 3: FINAL CERTIFICATION ASSESSMENT & QUESTION STUDIO */}
      {selectedCourseId && course && (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 px-2.5 py-0.5 rounded-full border border-amber-200 flex items-center gap-1">
                  <Award className="w-3 h-3 text-amber-500" />
                  Final Exam &amp; Certification Engine
                </span>
                {assessmentData && (
                  <span className={`text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                    (assessmentData.questions_count || assessmentData.questions?.length || 0) > 0
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-700 border-amber-200'
                  }`}>
                    {(assessmentData.questions_count || assessmentData.questions?.length || 0) > 0
                      ? `${assessmentData.questions_count || assessmentData.questions?.length} Questions Configured`
                      : 'Pending Questions'}
                  </span>
                )}
              </div>
              <h2 className="text-base font-bold text-slate-900 mt-2 flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-500" />
                Step 3: Final Certification Assessment
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Design the comprehensive exit examination for student certification. Add questions manually or generate them instantly using AI.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setIsAssessmentSettingsOpen(true)}
                className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl border border-slate-200 flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
              >
                <Settings className="w-3.5 h-3.5 text-slate-600" />
                Exam Settings
              </button>
              <button
                type="button"
                onClick={openAddManualQuestionModal}
                className="px-3.5 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Add Question Manually
              </button>
              <button
                type="button"
                onClick={handleOpenAiModal}
                className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                Generate with AI
              </button>
            </div>
          </div>

          {/* Assessment Summary Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-center">
              <span className="block text-[10px] font-bold uppercase text-slate-400">Total Questions</span>
              <span className="text-base font-black text-slate-900">
                {assessmentData?.questions_count || assessmentData?.questions?.length || 0}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-center">
              <span className="block text-[10px] font-bold uppercase text-slate-400">Total Marks</span>
              <span className="text-base font-black text-slate-900">
                {assessmentData?.total_marks || (assessmentData?.questions?.reduce((sum, q) => sum + (q.marks || 1), 0)) || 0}
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-center">
              <span className="block text-[10px] font-bold uppercase text-slate-400">Passing Score</span>
              <span className="text-base font-black text-emerald-600">
                {assessmentData?.pass_percentage || 70}%
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-center">
              <span className="block text-[10px] font-bold uppercase text-slate-400">Time Limit</span>
              <span className="text-base font-black text-slate-900">
                {assessmentData?.duration_minutes || 30} mins
              </span>
            </div>
            <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-center col-span-2 sm:col-span-1">
              <span className="block text-[10px] font-bold uppercase text-slate-400">Max Attempts</span>
              <span className="text-base font-black text-slate-900">
                {assessmentData?.max_attempts || 3}
              </span>
            </div>
          </div>

          {/* Proctoring Banner */}
          <div className="p-3 bg-indigo-50/70 rounded-2xl border border-indigo-200/60 flex flex-wrap items-center justify-between gap-2 text-xs text-indigo-950">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0" />
              <span className="font-semibold">Proctoring Enforcement:</span>
              <div className="flex flex-wrap items-center gap-1.5">
                {assessmentData?.camera_required && (
                  <span className="bg-white/80 px-2 py-0.5 rounded-md text-[10px] font-bold text-indigo-800 border border-indigo-200">
                    Webcam Active
                  </span>
                )}
                {assessmentData?.screen_share_required && (
                  <span className="bg-white/80 px-2 py-0.5 rounded-md text-[10px] font-bold text-indigo-800 border border-indigo-200">
                    Screen Shared
                  </span>
                )}
                {assessmentData?.fullscreen_required && (
                  <span className="bg-white/80 px-2 py-0.5 rounded-md text-[10px] font-bold text-indigo-800 border border-indigo-200">
                    Fullscreen Locked
                  </span>
                )}
                {assessmentData?.face_detection_enabled && (
                  <span className="bg-white/80 px-2 py-0.5 rounded-md text-[10px] font-bold text-indigo-800 border border-indigo-200">
                    AI Anomaly Detection
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsAssessmentSettingsOpen(true)}
              className="text-[11px] font-bold text-indigo-700 hover:underline cursor-pointer"
            >
              Configure Proctoring Rules &rarr;
            </button>
          </div>

          {/* ========================================================= */}
          {/* SECTION 3B: PRACTICAL CODING ASSESSMENT (PROGRAMMING SKILL COURSES) */}
          {/* ========================================================= */}
          <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-indigo-950 rounded-3xl border border-slate-800 p-6 sm:p-8 text-white space-y-6 shadow-xl">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-5">
              <div className="space-y-1 max-w-xl">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-1 rounded-md bg-accent-500/20 text-accent-300 border border-accent-500/30 text-[10px] font-black uppercase tracking-wider flex items-center gap-1">
                    <Code2 className="w-3.5 h-3.5" /> Hands-On Coding Requirement
                  </span>
                  <span className="px-2.5 py-1 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-bold uppercase font-mono">
                    {programmingLanguage ? programmingLanguage.toUpperCase() : 'PROGRAMMING SKILL'}
                  </span>
                  <span className="px-2.5 py-1 rounded-md bg-slate-800 text-slate-300 text-[10px] font-semibold">
                    Total 6 Test Cases: 2 Visible Sample + 4 Guarded Hidden
                  </span>
                </div>
                <h3 className="text-base sm:text-lg font-black text-white tracking-tight mt-1">
                  Practical Coding Assessment (1 Required Problem)
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Final certification exams for programming skill courses include 1 practical coding problem. Students test code on 2 visible sample test cases, while official evaluation evaluates 4 server-hidden test cases. Faculty can author manually or generate with AI in Easy difficulty, then review and publish.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleGenerateAiCoding}
                  disabled={generatingAiCoding}
                  className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-60 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Sparkles className={`w-3.5 h-3.5 text-amber-300 ${generatingAiCoding ? 'animate-spin' : ''}`} />
                  {generatingAiCoding ? 'Generating Easy AI Problem...' : 'Generate Easy Problem with AI'}
                </button>
                <button
                  type="button"
                  onClick={openAddCodingModal}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold rounded-xl border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <PlusCircle className="w-3.5 h-3.5 text-accent-400" />
                  Add Coding Problem Manually
                </button>
              </div>
            </div>

            {loadingCodingQuestions ? (
              <div className="flex items-center justify-center gap-2 p-8 text-slate-400 text-xs">
                <RefreshCw className="w-4 h-4 animate-spin text-accent-400" />
                <span>Loading coding challenges...</span>
              </div>
            ) : codingQuestions.length === 0 ? (
              <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-accent-500/10 text-accent-400 flex items-center justify-center mx-auto">
                  <Terminal className="w-6 h-6" />
                </div>
                <div className="max-w-md mx-auto space-y-1">
                  <h4 className="text-sm font-bold text-slate-200">No Practical Coding Problem Configured Yet</h4>
                  <p className="text-xs text-slate-400">
                    Students will not be able to complete practical coding certification without at least 1 published coding problem. Generate a beginner-friendly problem with AI or add your own with 2 sample and 4 hidden test cases.
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                  <button
                    type="button"
                    onClick={handleGenerateAiCoding}
                    disabled={generatingAiCoding}
                    className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    Generate Easy Problem with AI
                  </button>
                  <button
                    type="button"
                    onClick={openAddCodingModal}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    Create Manually
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {codingQuestions.map((cq: any) => {
                  const isPending = cq.approval_status === 'PENDING_REVIEW';
                  return (
                    <div
                      key={cq.id}
                      className={`rounded-2xl border p-5 sm:p-6 space-y-4 transition-all ${
                        isPending
                          ? 'bg-amber-950/20 border-amber-500/40 ring-1 ring-amber-500/30'
                          : 'bg-slate-900/70 border-slate-800'
                      }`}
                    >
                      {/* Top status bar */}
                      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/10">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2.5 py-0.5 rounded-md bg-slate-800 text-white text-xs font-bold font-mono uppercase">
                            {cq.programming_language}
                          </span>
                          <span className="px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold uppercase">
                            {cq.difficulty || 'EASY'}
                          </span>
                          <span className="px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[10px] font-bold">
                            {cq.marks || 10} Marks
                          </span>
                          {isPending ? (
                            <span className="px-2.5 py-0.5 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-amber-400" />
                              AI GENERATED • PENDING REVIEW
                            </span>
                          ) : (
                            <span className="px-2.5 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] font-bold flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              APPROVED &amp; ACTIVE IN EXAM
                            </span>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          {isPending && (
                            <button
                              type="button"
                              onClick={() => handlePublishCoding(cq.id)}
                              disabled={publishingCodingId === cq.id}
                              className="px-3.5 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md transition-all cursor-pointer"
                            >
                              <Check className="w-3.5 h-3.5" />
                              {publishingCodingId === cq.id ? 'Publishing...' : 'Review & Publish Problem'}
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => openEditCodingModal(cq)}
                            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-700 transition-all cursor-pointer"
                            title="Edit Problem"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteCoding(cq.id, cq.title || cq.text)}
                            className="p-1.5 bg-slate-800 hover:bg-rose-900/60 text-slate-400 hover:text-rose-300 rounded-lg border border-slate-700 transition-all cursor-pointer"
                            title="Delete Problem"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Title & Statement */}
                      <div className="space-y-2">
                        <h4 className="text-base sm:text-lg font-bold text-white tracking-tight">
                          {cq.title || cq.text}
                        </h4>
                        <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {cq.problem_statement || cq.text}
                        </p>
                      </div>

                      {/* Input/Output Formats & Constraints */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                        <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 space-y-1">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Input Format</span>
                          <p className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap">{cq.input_format || 'stdin'}</p>
                        </div>
                        <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 space-y-1">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Output Format</span>
                          <p className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap">{cq.output_format || 'stdout'}</p>
                        </div>
                        <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 space-y-1">
                          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Constraints</span>
                          <p className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap">{cq.constraints || 'Standard limits'}</p>
                        </div>
                      </div>

                      {/* 2 Sample Test Cases (Visible to Students) */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-accent-300">
                          <Terminal className="w-3.5 h-3.5" />
                          <span>Visible Sample Test Cases (2/2) — Visible to Student for Testing:</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                          {(cq.sample_test_cases || []).map((stc: any, sIdx: number) => (
                            <div key={sIdx} className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5">
                              <div className="flex items-center justify-between font-sans text-[10px] text-slate-400 border-b border-slate-800 pb-1">
                                <span className="font-bold text-slate-300">Sample Case {sIdx + 1}</span>
                                <span className="text-emerald-400 font-bold">Public / Visible</span>
                              </div>
                              <div className="space-y-0.5">
                                <span className="text-[10px] text-slate-500 font-sans uppercase font-bold">Input:</span>
                                <pre className="bg-slate-900 p-2 rounded text-slate-200 text-xs overflow-x-auto">{stc.input || '(empty)'}</pre>
                              </div>
                              <div className="space-y-0.5">
                                <span className="text-[10px] text-slate-500 font-sans uppercase font-bold">Expected Output:</span>
                                <pre className="bg-slate-900 p-2 rounded text-emerald-400 text-xs overflow-x-auto">{stc.output || ''}</pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 4 Hidden Test Cases (Server Evaluation Only) */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400">
                          <Lock className="w-3.5 h-3.5 text-amber-400" />
                          <span>Hidden Test Cases (4/4) — Evaluated on Server (Never Exposed to Student):</span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                          {(cq.hidden_test_cases || []).map((htc: any, hIdx: number) => (
                            <div key={hIdx} className="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800/80 space-y-1">
                              <div className="flex items-center justify-between font-sans text-[10px] text-slate-400 border-b border-slate-800/60 pb-1">
                                <span className="font-bold text-amber-300/90">Hidden #{hIdx + 1}</span>
                                <Lock className="w-2.5 h-2.5 text-slate-500" />
                              </div>
                              <div className="text-[10px]">
                                <span className="text-slate-500 font-sans">In: </span>
                                <span className="text-slate-300">{htc.input ? (htc.input.length > 15 ? htc.input.slice(0, 15) + '...' : htc.input) : '(empty)'}</span>
                              </div>
                              <div className="text-[10px]">
                                <span className="text-slate-500 font-sans">Out: </span>
                                <span className="text-emerald-400">{htc.output ? (htc.output.length > 15 ? htc.output.slice(0, 15) + '...' : htc.output) : ''}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Reference Solution & Sandbox Verification */}
                      {cq.reference_solution && (
                        <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-2.5">
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                              <Code2 className="w-3.5 h-3.5 text-accent-400" />
                              Reference Solution ({cq.programming_language ? cq.programming_language.toUpperCase() : 'CODE'}):
                            </span>
                            <button
                              type="button"
                              onClick={() => handleValidateCodingInSandbox(cq.id)}
                              disabled={validatingCodingId === cq.id}
                              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-accent-300 text-xs font-bold rounded-lg border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                            >
                              <PlayCircle className={`w-3.5 h-3.5 ${validatingCodingId === cq.id ? 'animate-spin' : ''}`} />
                              {validatingCodingId === cq.id ? 'Testing in Sandbox...' : 'Validate Solution in Sandbox'}
                            </button>
                          </div>
                          <pre className="p-3 bg-slate-900 rounded-xl text-slate-200 font-mono text-xs overflow-x-auto max-h-40">
                            {cq.reference_solution}
                          </pre>
                          {codingValidationResult && codingValidationResult.id === cq.id && (
                            <div className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-2 ${
                              codingValidationResult.valid
                                ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                                : 'bg-rose-950/60 border-rose-500/40 text-rose-300'
                            }`}>
                              {codingValidationResult.valid ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />}
                              <span>{codingValidationResult.message}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Multiple Choice Questions Container */}
          <div className="space-y-4 pt-4 border-t border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Multiple Choice Examination Questions
                </h4>
                <p className="text-xs text-slate-500">
                  Concept questions evaluating theory, architecture, and syntax knowledge.
                </p>
              </div>
            </div>
          </div>

          {/* Questions Container */}
          {loadingAssessment ? (
            <div className="flex items-center justify-center gap-2 p-8 text-slate-400 text-xs">
              <RefreshCw className="w-4 h-4 animate-spin text-primary-900" />
              <span>Loading assessment questions...</span>
            </div>
          ) : !assessmentData?.questions || assessmentData.questions.length === 0 ? (
            <div className="text-center py-10 px-4 bg-slate-50/70 border-2 border-dashed border-slate-200 rounded-3xl space-y-3">
              <div className="w-12 h-12 bg-amber-100 text-amber-700 rounded-2xl flex items-center justify-center mx-auto shadow-xs">
                <Award className="w-6 h-6 text-amber-600" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-sm font-bold text-slate-900">No Assessment Questions Yet</h3>
                <p className="text-xs text-slate-500">
                  A certification exam ensures students have mastered the course competencies. You can generate questions with curriculum-aligned AI or add your own custom questions.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={openAddManualQuestionModal}
                  className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-800 text-xs font-bold rounded-xl border border-slate-300 shadow-xs flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <PlusCircle className="w-3.5 h-3.5 text-primary-900" />
                  Add Question Manually
                </button>
                <button
                  type="button"
                  onClick={handleOpenAiModal}
                  className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  Generate Questions with AI
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-500 px-1">
                <span>
                  Showing <strong>{assessmentData.questions.length}</strong> certification examination questions
                </span>
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                    Easy: {assessmentData.questions.filter(q => q.difficulty === 'EASY').length}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                    Medium: {assessmentData.questions.filter(q => q.difficulty === 'MEDIUM').length}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                    Hard: {assessmentData.questions.filter(q => q.difficulty === 'HARD').length}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                {assessmentData.questions.map((q, idx) => (
                  <div
                    key={q.id || idx}
                    className="p-4 bg-slate-50/70 hover:bg-slate-50 rounded-2xl border border-slate-200 transition-all space-y-3 group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded-lg bg-slate-900 text-white font-black text-xs">
                          Q{idx + 1}
                        </span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${
                          q.difficulty === 'EASY'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : q.difficulty === 'HARD'
                            ? 'bg-purple-50 text-purple-700 border-purple-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}>
                          {q.difficulty}
                        </span>
                        {q.topic_tag && (
                          <span className="text-[10px] font-semibold bg-white text-slate-600 px-2 py-0.5 rounded-md border border-slate-200">
                            #{q.topic_tag}
                          </span>
                        )}
                        <span className="text-[10px] font-semibold text-slate-500">
                          {q.marks || 1} mark{(q.marks || 1) > 1 ? 's' : ''}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          type="button"
                          onClick={() => openEditManualQuestionModal(q)}
                          className="p-1.5 bg-white hover:bg-slate-100 text-slate-600 hover:text-primary-900 rounded-lg border border-slate-200 transition-all cursor-pointer"
                          title="Edit Question"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => q.id && handleDeleteAssessmentQuestion(q.id, q.text)}
                          className="p-1.5 bg-white hover:bg-rose-50 text-slate-400 hover:text-rose-600 rounded-lg border border-slate-200 transition-all cursor-pointer"
                          title="Delete Question"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <p className="text-xs sm:text-sm font-bold text-slate-900 leading-relaxed">
                      {q.text}
                    </p>

                    {/* Options Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {(q.options || []).map((opt, optIdx) => {
                        const optLabel = String.fromCharCode(65 + optIdx);
                        const isCorr = opt.is_correct;
                        return (
                          <div
                            key={opt.id || optIdx}
                            className={`p-2.5 rounded-xl border text-xs flex items-start gap-2 transition-all ${
                              isCorr
                                ? 'bg-emerald-50/80 border-emerald-400 text-emerald-950 font-semibold ring-1 ring-emerald-400/30'
                                : 'bg-white border-slate-200 text-slate-700'
                            }`}
                          >
                            <span className={`w-5 h-5 rounded-md flex items-center justify-center font-bold text-[10px] shrink-0 ${
                              isCorr ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
                            }`}>
                              {optLabel}
                            </span>
                            <div className="flex-grow min-w-0">
                              <p className="leading-snug">{opt.text}</p>
                            </div>
                            {isCorr && (
                              <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100/70 px-1.5 py-0.5 rounded flex items-center gap-0.5 shrink-0">
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                Correct
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Pedagogical Explanation */}
                    {q.explanation && (
                      <div className="p-2.5 bg-slate-100/80 rounded-xl border border-slate-200 text-[11px] text-slate-600 flex items-start gap-1.5">
                        <HelpCircle className="w-3.5 h-3.5 text-primary-800 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-slate-800 font-bold mr-1">Pedagogical Explanation:</strong>
                          <span>{q.explanation}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 1: ADD / EDIT MODULE */}
      {/* =================================================================== */}
      {activeModuleModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                {activeModuleModal.module ? 'Edit Module' : 'Create New Module'}
              </h3>
              <button type="button" onClick={() => setActiveModuleModal({ isOpen: false })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Module Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Module 1: Python Basics & Computational Thinking"
                  value={moduleTitle}
                  onChange={(e) => setModuleTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Core competencies and concepts covered in this module..."
                  value={moduleDesc}
                  onChange={(e) => setModuleDesc(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Estimated Minutes</label>
                  <input
                    type="number"
                    value={moduleDuration}
                    onChange={(e) => setModuleDuration(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Completion Rule</label>
                  <label className="flex items-center gap-2 mt-2 font-semibold text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={moduleRequired}
                      onChange={(e) => setModuleRequired(e.target.checked)}
                      className="rounded text-primary-900"
                    />
                    Required Module
                  </label>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              {activeModuleModal.module ? (
                <button
                  type="button"
                  onClick={() => {
                    const mod = activeModuleModal.module!;
                    setActiveModuleModal({ isOpen: false });
                    handleDeleteModule(mod.id, mod.title);
                  }}
                  className="px-3 py-2 text-rose-600 hover:bg-rose-50 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Module
                </button>
              ) : <div />}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveModuleModal({ isOpen: false })}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveModule}
                  className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl cursor-pointer"
                >
                  Save Module
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 2: ADD / EDIT LESSON */}
      {/* =================================================================== */}
      {activeLessonModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                {activeLessonModal.lesson ? 'Edit Lesson' : 'Create New Lesson'}
              </h3>
              <button type="button" onClick={() => setActiveLessonModal({ isOpen: false, moduleId: 0 })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Lesson Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Lesson 1: Functions, Parameters & Return Values"
                  value={lessonTitle}
                  onChange={(e) => setLessonTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  placeholder="Brief synopsis of this lesson..."
                  value={lessonDesc}
                  onChange={(e) => setLessonDesc(e.target.value)}
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Estimated Minutes</label>
                  <input
                    type="number"
                    value={lessonDuration}
                    onChange={(e) => setLessonDuration(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Requirement</label>
                  <label className="flex items-center gap-2 mt-2 font-semibold text-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={lessonRequired}
                      onChange={(e) => setLessonRequired(e.target.checked)}
                      className="rounded text-primary-900"
                    />
                    Required Lesson
                  </label>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              {activeLessonModal.lesson ? (
                <button
                  type="button"
                  onClick={() => {
                    const lsn = activeLessonModal.lesson!;
                    setActiveLessonModal({ isOpen: false, moduleId: 0 });
                    handleDeleteLesson(lsn.id, lsn.title);
                  }}
                  className="px-3 py-2 text-rose-600 hover:bg-rose-50 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Lesson
                </button>
              ) : <div />}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveLessonModal({ isOpen: false, moduleId: 0 })}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveLesson}
                  className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl cursor-pointer"
                >
                  Save Lesson
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 3: ADD / EDIT YOUTUBE VIDEO WITH INSTANT PREVIEW */}
      {/* =================================================================== */}
      {activeVideoModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Video className="w-5 h-5 text-rose-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  {activeVideoModal.video ? 'Edit YouTube Video' : 'Add YouTube Learning Video'}
                </h3>
              </div>
              <button type="button" onClick={() => setActiveVideoModal({ isOpen: false, lessonId: 0 })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">
                  YouTube Video URL *
                </label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    placeholder="https://www.youtube.com/watch?v=rfscVS0vtbw or https://youtu.be/..."
                    value={videoUrl}
                    onChange={(e) => {
                      setVideoUrl(e.target.value);
                      if (e.target.value.includes('youtube.com') || e.target.value.includes('youtu.be')) {
                        handleParseVideoUrl(e.target.value);
                      }
                    }}
                    onBlur={() => handleParseVideoUrl(videoUrl)}
                    className="flex-grow px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-mono text-[11px]"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => handleParseVideoUrl(videoUrl)}
                    disabled={videoParsing}
                    className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl shrink-0 flex items-center gap-1"
                  >
                    {videoParsing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : 'Verify'}
                  </button>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">Accepts standard YouTube watch URLs, youtu.be, or embed links.</p>
              </div>

              {/* Instant Embedded Preview */}
              {videoMeta?.valid && (
                <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 animate-in fade-in">
                  <div className="aspect-video w-full rounded-xl overflow-hidden bg-black shadow-inner">
                    <iframe
                      src={videoMeta.embed_url || `https://www.youtube-nocookie.com/embed/${videoMeta.video_id}`}
                      title="YouTube video preview"
                      className="w-full h-full border-0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-900 text-xs truncate">{videoMeta.title}</span>
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                        ID: {videoMeta.video_id}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">Channel: <strong>{videoMeta.author_name || 'YouTube Creator'}</strong></p>
                  </div>
                </div>
              )}

              <div>
                <label className="block font-bold text-slate-700 mb-1">Custom Video Title (Optional)</label>
                <input
                  type="text"
                  placeholder="Defaults to YouTube lecture title"
                  value={videoTitle}
                  onChange={(e) => setVideoTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                />
              </div>

              <div>
                <label className="flex items-center gap-2 font-semibold text-slate-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={videoRequired}
                    onChange={(e) => setVideoRequired(e.target.checked)}
                    className="rounded text-rose-600"
                  />
                  <span>Required Video (Must be watched to complete this lesson)</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              {activeVideoModal.video ? (
                <button
                  type="button"
                  onClick={() => {
                    const vid = activeVideoModal.video!;
                    setActiveVideoModal({ isOpen: false, lessonId: 0 });
                    handleDeleteResource('video', vid.id, vid.title);
                  }}
                  className="px-3 py-2 text-rose-600 hover:bg-rose-50 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Video
                </button>
              ) : <div />}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveVideoModal({ isOpen: false, lessonId: 0 })}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveVideo}
                  disabled={!videoMeta?.valid}
                  className="px-5 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-3.5 h-3.5" />
                  Use This Video
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 4: AI YOUTUBE SUGGESTIONS */}
      {/* =================================================================== */}
      {activeAiVideoModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">AI YouTube Video Recommendations</h3>
                  <p className="text-[11px] text-slate-500">
                    Topic: <strong>{activeAiVideoModal.lesson?.title}</strong>
                  </p>
                </div>
              </div>
              <button type="button" onClick={() => setActiveAiVideoModal({ isOpen: false, lesson: null })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-grow overflow-y-auto space-y-3 pr-1 text-xs">
              {loadingAiSuggestions ? (
                <div className="py-12 text-center space-y-2">
                  <RefreshCw className="w-6 h-6 text-purple-600 animate-spin mx-auto" />
                  <p className="text-xs text-slate-500">Analyzing lesson curriculum &amp; finding authoritative tutorials...</p>
                </div>
              ) : aiSuggestions.length === 0 ? (
                <p className="text-center py-8 text-slate-400">No matching videos suggested.</p>
              ) : (
                aiSuggestions.map((sugg, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 hover:border-purple-300 transition-all">
                    <div className="flex items-center gap-3 min-w-0">
                      <img src={sugg.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded-xl shrink-0 shadow-xs" />
                      <div className="min-w-0 space-y-0.5">
                        <h4 className="font-bold text-slate-900 text-xs truncate">{sugg.title}</h4>
                        <p className="text-[11px] text-purple-700 font-semibold">{sugg.channel}</p>
                        <p className="text-[10px] text-slate-500 line-clamp-2">{sugg.reason_for_recommendation}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSelectSuggestedVideo(sugg)}
                      className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-bold text-[11px] rounded-xl shrink-0 shadow-xs cursor-pointer"
                    >
                      + Add Video
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="flex items-center justify-end border-t border-slate-100 pt-3">
              <button
                type="button"
                onClick={() => setActiveAiVideoModal({ isOpen: false, lesson: null })}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 5: ADD / EDIT STUDY NOTES (FACULTY + AI ASSISTED) */}
      {/* =================================================================== */}
      {activeNotesModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary-900" />
                <h3 className="text-sm font-bold text-slate-900">
                  {activeNotesModal.material ? 'Edit Study Notes' : 'Create Lesson Study Notes'}
                </h3>
              </div>
              <button type="button" onClick={() => setActiveNotesModal({ isOpen: false, lessonId: 0 })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => setNotesTab('write')}
                  className={`px-3 py-1 font-bold rounded-lg transition-all ${notesTab === 'write' ? 'bg-white shadow text-slate-900' : 'text-slate-500'}`}
                >
                  Write Markdown
                </button>
                <button
                  type="button"
                  onClick={() => setNotesTab('preview')}
                  className={`px-3 py-1 font-bold rounded-lg transition-all ${notesTab === 'preview' ? 'bg-white shadow text-slate-900' : 'text-slate-500'}`}
                >
                  Rendered Preview
                </button>
              </div>

              {/* Quick AI Generator trigger inside modal */}
              <button
                type="button"
                onClick={() => handleGenerateAiNotes(activeNotesModal.lessonId)}
                disabled={generatingAiNotes}
                className="px-3 py-1.5 bg-gradient-to-r from-indigo-50 to-purple-50 hover:from-indigo-100 hover:to-purple-100 text-indigo-700 border border-indigo-200 font-bold rounded-xl flex items-center gap-1.5 text-xs transition-all cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                {generatingAiNotes ? 'Synthesizing...' : 'Generate 10-Section AI Notes'}
              </button>
            </div>

            <div className="space-y-3 text-xs flex-grow overflow-y-auto pr-1">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Notes Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Master Lecture Notes: Architectural Patterns & Clean Implementation"
                  value={notesTitle}
                  onChange={(e) => setNotesTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold text-xs"
                  required
                />
              </div>

              {notesTab === 'write' ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1 p-1 bg-slate-50 rounded-lg border border-slate-200">
                    <button
                      type="button"
                      onClick={() => setNotesContent(prev => prev + '\n## Key Concept\n')}
                      className="px-2 py-0.5 bg-white hover:bg-slate-100 rounded border border-slate-300 font-bold text-[10px]"
                    >
                      H2 Heading
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotesContent(prev => prev + '\n**Important Concept:** ')}
                      className="px-2 py-0.5 bg-white hover:bg-slate-100 rounded border border-slate-300 font-bold text-[10px]"
                    >
                      Bold
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotesContent(prev => prev + '\n```python\n# Code snippet\n```\n')}
                      className="px-2 py-0.5 bg-white hover:bg-slate-100 rounded border border-slate-300 font-bold text-[10px]"
                    >
                      Code Block
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotesContent(prev => prev + '\n- Item 1\n- Item 2\n- Item 3\n')}
                      className="px-2 py-0.5 bg-white hover:bg-slate-100 rounded border border-slate-300 font-bold text-[10px]"
                    >
                      Bullet List
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotesContent(prev => prev + '\n> **Important Note:** Crucial principle to remember.\n')}
                      className="px-2 py-0.5 bg-white hover:bg-slate-100 rounded border border-slate-300 font-bold text-[10px]"
                    >
                      Callout
                    </button>
                  </div>

                  <textarea
                    rows={12}
                    placeholder="Enter full lesson notes in Markdown format..."
                    value={notesContent}
                    onChange={(e) => setNotesContent(e.target.value)}
                    className="w-full p-3.5 bg-slate-50 border border-slate-300 rounded-xl font-mono text-xs leading-relaxed"
                    required
                  />
                </div>
              ) : (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 min-h-[300px] overflow-y-auto prose prose-slate max-w-none text-xs leading-relaxed">
                  <pre className="whitespace-pre-wrap font-sans text-slate-800">{notesContent || 'Nothing to preview yet.'}</pre>
                </div>
              )}

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
                <label className="block font-bold text-slate-700 text-xs">
                  Attach Study Document / Slides (PDF, DOCX, PPTX) — Optional
                </label>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.ppt,.pptx"
                  onChange={(e) => setNotesFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-primary-50 file:text-primary-900 hover:file:bg-primary-100"
                />
                {activeNotesModal.material?.file && !notesFile && (
                  <p className="text-[10px] text-emerald-600 font-medium">
                    Current document attached: {activeNotesModal.material.file}
                  </p>
                )}
              </div>

              <div>
                <label className="flex items-center gap-2 font-semibold text-slate-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notesRequired}
                    onChange={(e) => setNotesRequired(e.target.checked)}
                    className="rounded text-primary-900"
                  />
                  <span>Required Study Notes (Student must confirm reading to complete lesson)</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              {activeNotesModal.material ? (
                <button
                  type="button"
                  onClick={() => {
                    const mat = activeNotesModal.material!;
                    setActiveNotesModal({ isOpen: false, lessonId: 0 });
                    handleDeleteResource('material', mat.id, mat.title);
                  }}
                  className="px-3 py-2 text-rose-600 hover:bg-rose-50 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Notes
                </button>
              ) : <div />}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActiveNotesModal({ isOpen: false, lessonId: 0 })}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveNotes}
                  className="px-5 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  Save Notes Resource
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 6: ADD / EDIT PRACTICE QUIZ */}
      {/* =================================================================== */}
      {activePracticeModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-slate-900">
                  {activePracticeModal.practice ? 'Edit Practice Quiz' : 'Add Concept Check Practice'}
                </h3>
              </div>
              <button type="button" onClick={() => setActivePracticeModal({ isOpen: false, lessonId: 0 })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs flex-grow overflow-y-auto pr-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Quiz Title *</label>
                  <input
                    type="text"
                    placeholder="e.g. Concept Check: Function Arguments"
                    value={practiceTitle}
                    onChange={(e) => setPracticeTitle(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Passing Mark (%)</label>
                  <input
                    type="number"
                    min="50"
                    max="100"
                    value={practicePassScore}
                    onChange={(e) => setPracticePassScore(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold text-xs"
                  />
                </div>
              </div>

              {/* Questions List */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">Questions ({practiceQuestions.length})</span>
                  <button
                    type="button"
                    onClick={() => setPracticeQuestions([
                      ...practiceQuestions,
                      { question: '', options: ['', '', '', ''], correct_option: 'A', explanation: '' }
                    ])}
                    className="text-emerald-700 hover:underline font-bold text-[11px]"
                  >
                    + Add Question
                  </button>
                </div>

                {practiceQuestions.map((q, qIdx) => (
                  <div key={qIdx} className="p-3.5 bg-slate-50 rounded-2xl border border-slate-200 space-y-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-800">Q{qIdx + 1} Prompt:</span>
                      {practiceQuestions.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setPracticeQuestions(practiceQuestions.filter((_, idx) => idx !== qIdx))}
                          className="text-rose-500 hover:text-rose-700 text-[10px]"
                        >
                          Remove Q
                        </button>
                      )}
                    </div>
                    <input
                      type="text"
                      placeholder="Enter question text..."
                      value={q.question}
                      onChange={(e) => {
                        const updated = [...practiceQuestions];
                        updated[qIdx].question = e.target.value;
                        setPracticeQuestions(updated);
                      }}
                      className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                    />

                    <div className="grid grid-cols-2 gap-2">
                      {['A', 'B', 'C', 'D'].map((optKey, optIdx) => (
                        <div key={optKey} className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-600 text-[10px] w-4">{optKey}:</span>
                          <input
                            type="text"
                            placeholder={`Option ${optKey}`}
                            value={q.options[optIdx] || ''}
                            onChange={(e) => {
                              const updated = [...practiceQuestions];
                              updated[qIdx].options[optIdx] = e.target.value;
                              setPracticeQuestions(updated);
                            }}
                            className="flex-grow px-2 py-1 bg-white border border-slate-300 rounded text-[11px]"
                          />
                        </div>
                      ))}
                    </div>

                    <div className="flex items-center gap-3 pt-1">
                      <label className="font-bold text-slate-700 text-[11px]">Correct Answer:</label>
                      <select
                        value={q.correct_option}
                        onChange={(e) => {
                          const updated = [...practiceQuestions];
                          updated[qIdx].correct_option = e.target.value;
                          setPracticeQuestions(updated);
                        }}
                        className="px-2 py-1 bg-white border border-slate-300 rounded font-bold text-xs"
                      >
                        <option value="A">Option A {q.options[0] ? `(${q.options[0].slice(0, 25)}${q.options[0].length > 25 ? '...' : ''})` : ''}</option>
                        <option value="B">Option B {q.options[1] ? `(${q.options[1].slice(0, 25)}${q.options[1].length > 25 ? '...' : ''})` : ''}</option>
                        <option value="C">Option C {q.options[2] ? `(${q.options[2].slice(0, 25)}${q.options[2].length > 25 ? '...' : ''})` : ''}</option>
                        <option value="D">Option D {q.options[3] ? `(${q.options[3].slice(0, 25)}${q.options[3].length > 25 ? '...' : ''})` : ''}</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <label className="flex items-center gap-2 font-semibold text-slate-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={practiceRequired}
                    onChange={(e) => setPracticeRequired(e.target.checked)}
                    className="rounded text-emerald-600"
                  />
                  <span>Required Practice (Must pass to complete lesson)</span>
                </label>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-100">
              {activePracticeModal.practice ? (
                <button
                  type="button"
                  onClick={() => {
                    const prac = activePracticeModal.practice!;
                    setActivePracticeModal({ isOpen: false, lessonId: 0 });
                    handleDeleteResource('practice', prac.id, prac.title);
                  }}
                  className="px-3 py-2 text-rose-600 hover:bg-rose-50 text-xs font-bold rounded-xl flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Quiz
                </button>
              ) : <div />}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setActivePracticeModal({ isOpen: false, lessonId: 0 })}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSavePractice}
                  className="px-5 py-2 bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  Save Practice Resource
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 7: VALIDATION CHECKLIST */}
      {/* =================================================================== */}
      {validationModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                {validationModal.result?.valid ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-rose-600" />
                )}
                <h3 className="text-sm font-bold text-slate-900">
                  {validationModal.result?.valid ? 'Curriculum Validation Passed' : 'Curriculum Validation Issues'}
                </h3>
              </div>
              <button type="button" onClick={() => setValidationModal({ isOpen: false, result: null })} className="text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {validationModal.result?.valid ? (
                <div className="p-4 bg-emerald-50 text-emerald-800 rounded-2xl border border-emerald-200 space-y-1">
                  <p className="font-bold">✓ Ready for Institutional Review!</p>
                  <p className="text-[11px]">
                    All modules contain verified lessons, and required lessons have assigned learning resources.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="font-semibold text-slate-700">Please resolve the following before submitting:</p>
                  <ul className="space-y-1.5">
                    {validationModal.result?.errors?.map((errStr: string, idx: number) => (
                      <li key={idx} className="p-2.5 bg-rose-50 text-rose-800 rounded-xl border border-rose-200 flex items-start gap-2 text-[11px]">
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 mt-0.5" />
                        <span>{errStr}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end pt-2">
              <button
                type="button"
                onClick={() => setValidationModal({ isOpen: false, result: null })}
                className="px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs"
              >
                Close Checklist
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 8: STUDENT COURSE PREVIEW */}
      {/* =================================================================== */}
      {isPreviewOpen && course && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-slate-50 rounded-3xl max-w-5xl w-full p-6 space-y-4 shadow-2xl border border-slate-700 max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase text-accent-600 bg-accent-50 px-2 py-0.5 rounded border border-accent-200">
                  Student View Simulation
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-1">{course.title}</h3>
              </div>
              <button type="button" onClick={() => setIsPreviewOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-grow overflow-y-auto space-y-4 pr-1 text-xs">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 space-y-2">
                <h4 className="font-bold text-slate-800">Course Overview</h4>
                <p className="text-slate-600 leading-relaxed">{course.description}</p>
                <div className="flex items-center gap-3 text-[11px] text-slate-500 pt-1">
                  <span>Level: <strong>{course.level}</strong></span>
                  <span>•</span>
                  <span>Duration: <strong>{course.estimated_hours} Hours</strong></span>
                  <span>•</span>
                  <span>Modules: <strong>{course.modules?.length || 0}</strong></span>
                </div>
              </div>

              {course.modules?.map((m, idx) => (
                <div key={m.id} className="bg-white p-4 rounded-2xl border border-slate-200 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <h5 className="font-bold text-slate-900 text-sm">Module {idx + 1}: {m.title}</h5>
                    <span className="text-[10px] text-slate-500">{m.lessons?.length || 0} Lessons</span>
                  </div>

                  <div className="space-y-3 pl-2">
                    {m.lessons?.map((lsn, lIdx) => (
                      <div key={lsn.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-800">Lesson {lIdx + 1}: {lsn.title}</span>
                          <span className="text-[10px] text-slate-400">{lsn.duration_minutes} mins</span>
                        </div>

                        {/* Preview Video */}
                        {lsn.videos && lsn.videos.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold text-rose-700 flex items-center gap-1">
                              <Video className="w-3 h-3" />
                              {lsn.videos[0].title}
                            </span>
                            <div className="aspect-video max-w-md rounded-xl overflow-hidden bg-black">
                              <iframe
                                src={lsn.videos[0].embed_url || `https://www.youtube-nocookie.com/embed/${lsn.videos[0].youtube_video_id}`}
                                title="Video"
                                className="w-full h-full border-0"
                                allowFullScreen
                              />
                            </div>
                          </div>
                        )}

                        {/* Preview Notes */}
                        {lsn.materials && lsn.materials.length > 0 && (
                          <div className="p-2.5 bg-white rounded-lg border border-slate-200 text-[11px] text-slate-700">
                            <span className="font-bold text-primary-900 block mb-1">📝 {lsn.materials[0].title}</span>
                            <p className="line-clamp-3 font-mono text-[10px] text-slate-600">{lsn.materials[0].text_content}</p>
                          </div>
                        )}

                        {/* Preview Practice */}
                        {lsn.practice_tasks && lsn.practice_tasks.length > 0 && (
                          <div className="p-2.5 bg-emerald-50/50 rounded-lg border border-emerald-200 text-[11px] text-emerald-900">
                            <span className="font-bold block">🧪 {lsn.practice_tasks[0].title}</span>
                            <span className="text-[10px] text-slate-600">
                              {lsn.practice_tasks[0].content?.questions?.length || 0} Questions available
                            </span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-end border-t border-slate-200 pt-3">
              <button
                type="button"
                onClick={() => setIsPreviewOpen(false)}
                className="px-5 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: LIVE VIDEO PREVIEW */}
      {previewingVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Video className="w-5 h-5 text-rose-600" />
                <h3 className="text-sm font-bold text-slate-900 truncate max-w-md">{previewingVideo.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => setPreviewingVideo(null)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="aspect-video w-full rounded-2xl overflow-hidden bg-black shadow-inner">
              <iframe
                src={`https://www.youtube-nocookie.com/embed/${previewingVideo.youtube_video_id}?autoplay=1&enablejsapi=1`}
                title={previewingVideo.title}
                className="w-full h-full border-0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
              <span>Channel: <strong className="text-slate-800">{previewingVideo.channel_name || 'YouTube Creator'}</strong></span>
              <span className={previewingVideo.is_required ? 'text-indigo-600 font-bold' : 'text-slate-500'}>
                {previewingVideo.is_required ? 'Required Video' : 'Optional Video'}
              </span>
            </div>

            <div className="flex items-center justify-end border-t border-slate-100 pt-3">
              <button
                type="button"
                onClick={() => setPreviewingVideo(null)}
                className="px-5 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: LIVE NOTES PREVIEW */}
      {previewingNotes && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 max-h-[85vh] flex flex-col animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary-900" />
                <h3 className="text-sm font-bold text-slate-900 truncate max-w-md">{previewingNotes.title}</h3>
              </div>
              <button
                type="button"
                onClick={() => setPreviewingNotes(null)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-grow overflow-y-auto space-y-4 pr-2 text-xs leading-relaxed">
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
                <pre className="whitespace-pre-wrap font-sans text-slate-800 text-xs leading-relaxed">
                  {previewingNotes.text_content || 'No text content available.'}
                </pre>
              </div>

              {previewingNotes.file && (
                <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-200 flex items-center justify-between">
                  <span className="text-xs text-indigo-950 font-semibold">Attached Document:</span>
                  <a
                    href={previewingNotes.file}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-bold text-indigo-700 hover:underline flex items-center gap-1"
                  >
                    Open Document <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-slate-100 pt-3">
              <span className={previewingNotes.is_required ? 'text-indigo-600 font-bold text-xs' : 'text-slate-500 text-xs'}>
                {previewingNotes.is_required ? 'Required Resource' : 'Optional Resource'}
              </span>
              <button
                type="button"
                onClick={() => setPreviewingNotes(null)}
                className="px-5 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl cursor-pointer"
              >
                Close Notes Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* UNIFIED DELETE CONFIRMATION MODAL */}
      {confirmDeleteModal && (
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
              Are you sure you want to permanently delete this {confirmDeleteModal.type}:
              <strong className="block mt-1 font-bold text-slate-900">&ldquo;{confirmDeleteModal.title}&rdquo;</strong>
              {confirmDeleteModal.type === 'course' && (
                <span className="block mt-1 text-[11px] text-rose-700">All associated modules, lessons, and resources will be deleted from the database.</span>
              )}
              {confirmDeleteModal.type === 'module' && (
                <span className="block mt-1 text-[11px] text-rose-700">All lessons and attached resources in this module will also be deleted.</span>
              )}
              {confirmDeleteModal.type === 'question' && (
                <span className="block mt-1 text-[11px] text-rose-700">This question and all its options will be permanently removed from the certification assessment.</span>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setConfirmDeleteModal(null)}
                disabled={isDeleting}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteDelete}
                disabled={isDeleting}
                className="px-5 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md flex items-center gap-1.5 transition-all cursor-pointer"
              >
                {isDeleting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                {isDeleting ? 'Deleting...' : 'Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 8: FINAL ASSESSMENT SETTINGS MODAL */}
      {/* =================================================================== */}
      {isAssessmentSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-primary-900" />
                <h3 className="text-sm font-bold text-slate-900">
                  Final Certification Exam Settings
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAssessmentSettingsOpen(false)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveAssessmentSettings} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Assessment Title *</label>
                <input
                  type="text"
                  value={assessmentTitle}
                  onChange={(e) => setAssessmentTitle(e.target.value)}
                  placeholder="e.g. Python Fundamentals Final Certification Assessment"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold"
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Duration (Mins)</label>
                  <input
                    type="number"
                    min="5"
                    max="180"
                    value={assessmentDuration}
                    onChange={(e) => setAssessmentDuration(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-center font-bold"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Pass Mark (%)</label>
                  <input
                    type="number"
                    min="40"
                    max="100"
                    value={assessmentPassScore}
                    onChange={(e) => setAssessmentPassScore(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-center font-bold text-emerald-600"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Max Attempts</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={assessmentMaxAttempts}
                    onChange={(e) => setAssessmentMaxAttempts(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-center font-bold"
                  />
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-slate-100">
                <span className="block font-bold text-slate-800">Exam Integrity &amp; Anti-Cheating Security</span>

                <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assessmentCameraReq}
                    onChange={(e) => setAssessmentCameraReq(e.target.checked)}
                    className="w-4 h-4 rounded text-primary-900"
                  />
                  <div className="flex-grow">
                    <span className="font-bold text-slate-900 block text-[11px]">Enforce Webcam Proctoring</span>
                    <span className="text-[10px] text-slate-500">Student must maintain active camera visibility throughout the exam</span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assessmentScreenShareReq}
                    onChange={(e) => setAssessmentScreenShareReq(e.target.checked)}
                    className="w-4 h-4 rounded text-primary-900"
                  />
                  <div className="flex-grow">
                    <span className="font-bold text-slate-900 block text-[11px]">Enforce Screen Sharing</span>
                    <span className="text-[10px] text-slate-500">Records desktop surface to deter external tabs or unauthorized applications</span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assessmentFullscreenReq}
                    onChange={(e) => setAssessmentFullscreenReq(e.target.checked)}
                    className="w-4 h-4 rounded text-primary-900"
                  />
                  <div className="flex-grow">
                    <span className="font-bold text-slate-900 block text-[11px]">Lock Fullscreen Mode</span>
                    <span className="text-[10px] text-slate-500">Exiting fullscreen triggers a strike and logged proctoring incident</span>
                  </div>
                </label>

                <label className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assessmentFaceDetectReq}
                    onChange={(e) => setAssessmentFaceDetectReq(e.target.checked)}
                    className="w-4 h-4 rounded text-primary-900"
                  />
                  <div className="flex-grow">
                    <span className="font-bold text-slate-900 block text-[11px]">AI Multiple Face &amp; Tab Switch Detection</span>
                    <span className="text-[10px] text-slate-500">Real-time alerts for face disappearance or unauthorized secondary persons</span>
                  </div>
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAssessmentSettingsOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingAssessmentSettings}
                  className="px-5 py-2 bg-primary-900 hover:bg-primary-800 disabled:opacity-50 text-white font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  {savingAssessmentSettings ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 9: MANUAL QUESTION CREATION & EDIT MODAL */}
      {/* =================================================================== */}
      {isManualQuestionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 shrink-0">
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-primary-900" />
                <h3 className="text-sm font-bold text-slate-900">
                  {editingQuestionId ? 'Edit Assessment Question' : 'Add Question Manually'}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsManualQuestionModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveManualQuestion} className="space-y-4 text-xs overflow-y-auto flex-grow pr-1">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Question Prompt *</label>
                <textarea
                  rows={3}
                  value={manualQText}
                  onChange={(e) => setManualQText(e.target.value)}
                  placeholder="e.g. Which keyword in Python is used to declare a generator function that yields values lazily?"
                  className="w-full p-3 bg-slate-50 border border-slate-300 rounded-xl font-medium focus:ring-2 focus:ring-primary-600 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Difficulty</label>
                  <select
                    value={manualQDifficulty}
                    onChange={(e) => setManualQDifficulty(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold"
                  >
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Topic Tag</label>
                  <input
                    type="text"
                    value={manualQTopic}
                    onChange={(e) => setManualQTopic(e.target.value)}
                    placeholder="e.g. generators"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Marks</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={manualQMarks}
                    onChange={(e) => setManualQMarks(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-center font-bold"
                  />
                </div>
              </div>

              {/* Options with designated correct answer */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="font-bold text-slate-800">Answer Options (Designate the correct answer)</label>
                  <span className="text-[10px] text-slate-400">Click letter to set as correct</span>
                </div>

                {manualQOptions.map((optText, optIdx) => {
                  const optLabel = String.fromCharCode(65 + optIdx);
                  const isSelected = manualQCorrectIndex === optIdx;
                  return (
                    <div
                      key={optIdx}
                      className={`flex items-center gap-2 p-2 rounded-xl border transition-all ${
                        isSelected
                          ? 'bg-emerald-50/70 border-emerald-400 ring-1 ring-emerald-400/20'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => setManualQCorrectIndex(optIdx)}
                        className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-emerald-600 text-white shadow-xs'
                            : 'bg-white border border-slate-300 text-slate-500 hover:border-slate-400'
                        }`}
                        title={isSelected ? 'Designated Correct Answer' : 'Click to set as Correct Answer'}
                      >
                        {isSelected ? '✓' : optLabel}
                      </button>
                      <input
                        type="text"
                        value={optText}
                        onChange={(e) => {
                          const newOpts = [...manualQOptions];
                          newOpts[optIdx] = e.target.value;
                          setManualQOptions(newOpts);
                        }}
                        placeholder={`Option ${optLabel} text...`}
                        className="flex-grow px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary-600"
                        required={optIdx < 2}
                      />
                      {isSelected && (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-md shrink-0">
                          Correct
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Pedagogical Explanation (Optional)</label>
                <textarea
                  rows={2}
                  value={manualQExplanation}
                  onChange={(e) => setManualQExplanation(e.target.value)}
                  placeholder="Explain why this option is correct and why other alternatives are distractors..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsManualQuestionModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingManualQuestion}
                  className="px-5 py-2 bg-primary-900 hover:bg-primary-800 disabled:opacity-50 text-white font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  {savingManualQuestion ? 'Saving Question...' : editingQuestionId ? 'Update Question' : 'Add Question'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 10: AI QUESTION GENERATOR MODAL */}
      {/* =================================================================== */}
      {isAiQuestionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-3xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 text-white flex items-center justify-center shadow-xs">
                  <Sparkles className="w-4 h-4 text-amber-300" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    AI Assessment Question Generator
                  </h3>
                  <p className="text-[10px] text-slate-500">
                    Curriculum-grounded question synthesis from course syllabus and learning objectives.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAiQuestionModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Generator Settings */}
            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3 shrink-0 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-slate-700 mb-1.5">Number of Questions</label>
                  <div className="flex items-center gap-2">
                    {[3, 5, 10, 15, 20].map((num) => (
                      <button
                        key={num}
                        type="button"
                        onClick={() => setAiQuestionCount(num)}
                        className={`flex-1 py-1.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${
                          aiQuestionCount === num
                            ? 'bg-slate-900 text-white shadow-xs'
                            : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
                        }`}
                      >
                        {num}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1.5">Difficulty Focus</label>
                  <select
                    value={aiQuestionDifficulty}
                    onChange={(e) => setAiQuestionDifficulty(e.target.value)}
                    className="w-full px-3 py-1.5 bg-white border border-slate-200 rounded-xl font-semibold text-xs"
                  >
                    <option value="ALL">Balanced Mix (Easy, Medium, Hard)</option>
                    <option value="EASY">Beginner &amp; Conceptual Focus</option>
                    <option value="MEDIUM">Intermediate &amp; Applied Focus</option>
                    <option value="HARD">Advanced &amp; Architectural Focus</option>
                  </select>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200/60">
                <span className="text-[11px] text-slate-500">
                  Target Course: <strong className="text-slate-800 font-bold">{course?.title}</strong>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleGenerateAiQuestions(false)}
                    disabled={generatingAiQuestions}
                    className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    {generatingAiQuestions ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                    )}
                    {generatingAiQuestions ? 'Synthesizing Questions...' : 'Generate & Preview Questions'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleGenerateAiQuestions(true)}
                    disabled={generatingAiQuestions}
                    className="px-3.5 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 font-bold text-xs rounded-xl shadow-xs flex items-center gap-1 cursor-pointer"
                    title="Generate and immediately save directly to final assessment"
                  >
                    ⚡ Fast 1-Click Add
                  </button>
                </div>
              </div>
            </div>

            {/* Generated Questions Preview Area */}
            <div className="flex-grow overflow-y-auto space-y-3 pr-1 text-xs">
              {generatingAiQuestions ? (
                <div className="py-16 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-violet-100 text-violet-700 flex items-center justify-center mx-auto animate-bounce">
                    <Sparkles className="w-6 h-6 text-violet-600" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="font-bold text-slate-900 text-sm">Generating Examination Questions</h4>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto">
                      AI is evaluating module hierarchies, creating high-distractor answer options, and framing pedagogical explanations...
                    </p>
                  </div>
                </div>
              ) : aiGeneratedQuestions.length === 0 ? (
                <div className="py-12 text-center text-slate-400 space-y-2">
                  <Wand2 className="w-8 h-8 mx-auto text-slate-300" />
                  <p className="text-xs">Click "Generate &amp; Preview Questions" to create candidates with AI.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between bg-violet-50/50 p-2.5 rounded-xl border border-violet-100">
                    <span className="font-bold text-violet-950 text-xs">
                      {aiGeneratedQuestions.length} Questions Generated • Select which ones to add
                    </span>
                    <button
                      type="button"
                      onClick={handleSelectAllAi}
                      className="text-violet-700 hover:underline font-bold text-[11px] cursor-pointer"
                    >
                      {selectedAiIndices.length === aiGeneratedQuestions.length ? 'Deselect All' : 'Select All'}
                    </button>
                  </div>

                  {aiGeneratedQuestions.map((q, idx) => {
                    const isSelected = selectedAiIndices.includes(idx);
                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-2xl border transition-all space-y-2.5 ${
                          isSelected
                            ? 'bg-white border-violet-300 shadow-xs ring-1 ring-violet-400/20'
                            : 'bg-slate-50/60 border-slate-200 opacity-60'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <label className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleAiCandidate(idx)}
                              className="w-4 h-4 rounded text-violet-600"
                            />
                            <span className="font-bold text-slate-900 text-xs">
                              Question {idx + 1}
                            </span>
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-md border ${
                              q.difficulty === 'EASY'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : q.difficulty === 'HARD'
                                ? 'bg-purple-50 text-purple-700 border-purple-200'
                                : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}>
                              {q.difficulty}
                            </span>
                          </label>
                          <span className="text-[10px] text-slate-500 font-semibold">
                            {q.marks || 1} mark
                          </span>
                        </div>

                        <p className="font-bold text-slate-900 text-xs pl-6">
                          {q.text}
                        </p>

                        {/* Options */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-6">
                          {(q.options || []).map((opt, optIdx) => {
                            const optLabel = String.fromCharCode(65 + optIdx);
                            const isCorr = opt.is_correct;
                            return (
                              <div
                                key={optIdx}
                                className={`p-2 rounded-lg border text-[11px] flex items-start gap-1.5 ${
                                  isCorr
                                    ? 'bg-emerald-50 border-emerald-300 text-emerald-950 font-semibold'
                                    : 'bg-slate-50 border-slate-200 text-slate-600'
                                }`}
                              >
                                <span className={`w-4 h-4 rounded flex items-center justify-center text-[9px] font-bold shrink-0 ${
                                  isCorr ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                                }`}>
                                  {optLabel}
                                </span>
                                <span className="leading-tight flex-grow">{opt.text}</span>
                                {isCorr && (
                                  <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0 mt-0.5" />
                                )}
                              </div>
                            );
                          })}
                        </div>

                        {q.explanation && (
                          <div className="pl-6 text-[10px] text-slate-500 italic">
                            💡 {q.explanation}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-slate-100 pt-3 shrink-0">
              <span className="text-xs text-slate-600">
                Selected: <strong>{selectedAiIndices.length}</strong> of {aiGeneratedQuestions.length} questions
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsAiQuestionModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl cursor-pointer"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleSaveSelectedAiQuestions}
                  disabled={savingAiQuestions || selectedAiIndices.length === 0}
                  className="px-5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-3.5 h-3.5" />
                  {savingAiQuestions ? 'Adding...' : `Add Selected (${selectedAiIndices.length}) Questions`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* =================================================================== */}
      {/* MODAL 11: PRACTICAL CODING QUESTION (MANUAL / EDIT) MODAL */}
      {/* =================================================================== */}
      {isCodingModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl max-w-4xl w-full p-6 space-y-4 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-accent-600 to-emerald-600 text-white flex items-center justify-center shadow-xs">
                  <Code2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    {editingCodingId ? 'Edit Practical Coding Problem' : 'Configure Practical Coding Problem'}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Final Assessment Coding Standard: Exactly 2 visible sample test cases + 4 hidden evaluation cases (Total 6).
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsCodingModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-100 transition-all cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCodingQuestion} className="space-y-4 text-xs overflow-y-auto flex-grow pr-1">
              {/* Problem Title, Language, Marks */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div className="sm:col-span-2">
                  <label className="block font-bold text-slate-700 mb-1">Problem Title *</label>
                  <input
                    type="text"
                    value={codingTitle}
                    onChange={(e) => setCodingTitle(e.target.value)}
                    placeholder="e.g., Sum of Array Elements"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-semibold text-xs focus:ring-2 focus:ring-accent-600 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Language *</label>
                  <select
                    value={codingLang}
                    onChange={(e) => setCodingLang(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-bold text-xs"
                    required
                  >
                    <option value="python">Python</option>
                    <option value="java">Java</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Assessment Marks</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={codingMarks}
                    onChange={(e) => setCodingMarks(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl font-bold text-center text-xs"
                  />
                </div>
              </div>

              {/* Topic Tag and Constraints */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Topic Tag</label>
                  <input
                    type="text"
                    value={codingTopic}
                    onChange={(e) => setCodingTopic(e.target.value)}
                    placeholder="e.g. arrays, algorithms"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Execution Constraints</label>
                  <input
                    type="text"
                    value={codingConstraints}
                    onChange={(e) => setCodingConstraints(e.target.value)}
                    placeholder="Time Limit: 4.0s | Memory: 256MB"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono"
                  />
                </div>
              </div>

              {/* Problem Statement */}
              <div>
                <label className="block font-bold text-slate-700 mb-1">Problem Statement / Prompt *</label>
                <textarea
                  rows={4}
                  value={codingStatement}
                  onChange={(e) => setCodingStatement(e.target.value)}
                  placeholder="Describe the problem, task, and context clearly..."
                  className="w-full p-3 bg-slate-50 border border-slate-300 rounded-xl text-xs leading-relaxed focus:ring-2 focus:ring-accent-600 focus:outline-none"
                  required
                />
              </div>

              {/* Input Format & Output Format */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Input Format</label>
                  <textarea
                    rows={2}
                    value={codingInputFormat}
                    onChange={(e) => setCodingInputFormat(e.target.value)}
                    placeholder="Describe how input is supplied..."
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Output Format</label>
                  <textarea
                    rows={2}
                    value={codingOutputFormat}
                    onChange={(e) => setCodingOutputFormat(e.target.value)}
                    placeholder="Describe expected output format..."
                    className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs font-mono"
                  />
                </div>
              </div>

              {/* Section: 2 Sample Test Cases (Visible to Students) */}
              <div className="p-4 bg-emerald-50/50 rounded-2xl border border-emerald-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-emerald-700" />
                    <span className="font-bold text-emerald-950 text-xs">
                      Visible Sample Test Cases (Exactly 2 required)
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-full">
                    Student Visible (Testing &amp; Understanding)
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {sampleCases.map((tc, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-xl border border-emerald-300 shadow-2xs space-y-2">
                      <span className="font-bold text-emerald-900 text-[11px] block">Sample Case #{idx + 1}</span>
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-0.5">Input:</label>
                        <textarea
                          rows={2}
                          value={tc.input}
                          onChange={(e) => {
                            const updated = [...sampleCases];
                            updated[idx].input = e.target.value;
                            setSampleCases(updated);
                          }}
                          placeholder="Sample input data..."
                          className="w-full p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-500 block mb-0.5">Expected Output:</label>
                        <textarea
                          rows={2}
                          value={tc.output}
                          onChange={(e) => {
                            const updated = [...sampleCases];
                            updated[idx].output = e.target.value;
                            setSampleCases(updated);
                          }}
                          placeholder="Sample expected output..."
                          className="w-full p-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section: 4 Hidden Test Cases (Server-side Grading Only) */}
              <div className="p-4 bg-amber-50/50 rounded-2xl border border-amber-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 text-amber-700" />
                    <span className="font-bold text-amber-950 text-xs">
                      Hidden Evaluation Test Cases (Exactly 4 required)
                    </span>
                  </div>
                  <span className="text-[10px] font-semibold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded-full">
                    Server Only (Never Exposed to Student)
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                  {hiddenCases.map((tc, idx) => (
                    <div key={idx} className="p-2.5 bg-white rounded-xl border border-amber-300 shadow-2xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-amber-900 text-[11px]">Hidden #{idx + 1}</span>
                        <Lock className="w-3 h-3 text-amber-600" />
                      </div>
                      <div>
                        <label className="text-[9px] font-bold text-slate-400 block">Input:</label>
                        <textarea
                          rows={2}
                          value={tc.input}
                          onChange={(e) => {
                            const updated = [...hiddenCases];
                            updated[idx].input = e.target.value;
                            setHiddenCases(updated);
                          }}
                          placeholder="Hidden input..."
                          className="w-full p-1 bg-slate-50 border border-slate-200 rounded text-xs font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] font-bold text-slate-400 block">Expected Output:</label>
                        <textarea
                          rows={2}
                          value={tc.output}
                          onChange={(e) => {
                            const updated = [...hiddenCases];
                            updated[idx].output = e.target.value;
                            setHiddenCases(updated);
                          }}
                          placeholder="Hidden output..."
                          className="w-full p-1 bg-slate-50 border border-slate-200 rounded text-xs font-mono"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section: Reference Solution & Verification */}
              <div className="p-4 bg-slate-900 rounded-2xl border border-slate-800 text-slate-100 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-4 h-4 text-accent-400" />
                    <span className="font-bold text-xs">Reference Solution ({codingLang.toUpperCase()})</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleModalValidateSolution}
                    disabled={modalValidating}
                    className="px-3 py-1.5 bg-accent-600 hover:bg-accent-500 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                  >
                    <PlayCircle className={`w-3.5 h-3.5 ${modalValidating ? 'animate-spin' : ''}`} />
                    {modalValidating ? 'Verifying in Sandbox...' : 'Test & Verify Solution'}
                  </button>
                </div>
                <textarea
                  rows={5}
                  value={referenceSolution}
                  onChange={(e) => setReferenceSolution(e.target.value)}
                  placeholder={`# Reference solution in ${codingLang}\n# Must pass all 2 sample + 4 hidden test cases`}
                  className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-emerald-400 focus:outline-none focus:border-accent-500"
                />
                {modalValidationMsg && (
                  <div className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-2 ${
                    modalValidationMsg.valid
                      ? 'bg-emerald-950/70 border-emerald-500/50 text-emerald-300'
                      : 'bg-rose-950/70 border-rose-500/50 text-rose-300'
                  }`}>
                    {modalValidationMsg.valid ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                    )}
                    <span>{modalValidationMsg.text}</span>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsCodingModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition-all cursor-pointer text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingCodingQuestion}
                  className="px-5 py-2 bg-accent-600 hover:bg-accent-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-xs flex items-center gap-1.5 transition-all cursor-pointer text-xs"
                >
                  <Save className="w-3.5 h-3.5" />
                  {savingCodingQuestion
                    ? 'Saving Problem...'
                    : editingCodingId
                    ? 'Update Coding Problem'
                    : 'Save & Approve for Final Assessment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
