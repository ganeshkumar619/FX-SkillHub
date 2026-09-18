import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { AICourseGeneratePayload, AICourseGenerateResponse } from '../types';
import {
  Sparkles,
  X,
  Video,
  FileText,
  Brain,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
  ShieldCheck,
  Cpu
} from 'lucide-react';

interface AICourseGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (result: AICourseGenerateResponse) => void;
  defaultSkillName?: string;
}

const GENERATION_STEPS = [
  { id: 1, label: 'Curriculum & Module Topic Synthesis', desc: 'Structuring multi-module technical syllabus' },
  { id: 2, label: '4-Level Multi-Section Study Materials', desc: 'Crafting beginner, intermediate, quick revision, & advanced notes' },
  { id: 3, label: 'Mode B Video Storyboards & Narration', desc: 'Producing 4-scene video script packages & subtitles (zero fake URLs)' },
  { id: 4, label: 'Multi-Format Practice Tasks', desc: 'Generating MCQ, coding challenge, and debugging tasks' },
  { id: 5, label: '30-Question Bank & Semantic Deduplication', desc: 'Verifying difficulty balance & semantic distinctness (>70% threshold)' },
  { id: 6, label: 'Assessment Blueprint Lock', desc: 'Configuring per-attempt randomized blueprint & publishing course' },
];

export const AICourseGeneratorModal: React.FC<AICourseGeneratorModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  defaultSkillName = '',
}) => {
  const navigate = useNavigate();

  const [skillName, setSkillName] = useState(defaultSkillName);
  const [courseName, setCourseName] = useState('');
  const [level, setLevel] = useState<'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'>('INTERMEDIATE');
  const [targetAudience, setTargetAudience] = useState('FXEC Engineering Students and Aspirants');
  const [learningGoal, setLearningGoal] = useState('');
  const [durationHours, setDurationHours] = useState(24);
  const [publishImmediately, setPublishImmediately] = useState(true);

  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [generationResult, setGenerationResult] = useState<AICourseGenerateResponse | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillName.trim()) {
      setErrorMessage('Please specify the Skill or Topic name.');
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    setGenerationResult(null);
    setActiveStepIndex(0);

    // Simulated progress tick for visual feedback while waiting for backend response
    const interval = setInterval(() => {
      setActiveStepIndex((prev) => (prev < GENERATION_STEPS.length - 1 ? prev + 1 : prev));
    }, 1800);

    try {
      const payload: AICourseGeneratePayload = {
        skill_name: skillName.trim(),
        course_name: courseName.trim() || undefined,
        level,
        target_audience: targetAudience.trim() || undefined,
        learning_goal: learningGoal.trim() || undefined,
        duration_hours: durationHours,
        publish_immediately: publishImmediately,
      };

      const res = await apiClient.post<AICourseGenerateResponse>('/catalogue/courses/generate/', payload);
      clearInterval(interval);
      setActiveStepIndex(GENERATION_STEPS.length);
      setGenerationResult(res.data);
      if (onSuccess) {
        onSuccess(res.data);
      }
    } catch (err: any) {
      clearInterval(interval);
      const serverErr = err.response?.data?.error || err.response?.data?.detail || err.message || 'Course generation failed.';
      setErrorMessage(serverErr);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleReset = () => {
    setGenerationResult(null);
    setErrorMessage(null);
    setIsGenerating(false);
    setActiveStepIndex(0);
  };

  const handleViewCourse = () => {
    if (generationResult) {
      onClose();
      navigate(`/courses/${generationResult.slug}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in overflow-y-auto">
      <div className="relative w-full max-w-3xl my-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-indigo-50 via-purple-50 to-white dark:from-slate-800/80 dark:via-purple-950/20 dark:to-slate-900">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-indigo-600 rounded-xl text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                Autonomous AI Course Generator
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 font-medium">
                  FX SkillHub AI Studio
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                End-to-end curriculum, 4-level study notes, Mode B video storyboards, practice tasks, & 30-question bank
              </p>
            </div>
          </div>
          {!isGenerating && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {errorMessage && (
            <div className="mb-6 p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 flex items-start space-x-3 text-rose-800 dark:text-rose-200">
              <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
              <div className="text-sm">
                <p className="font-semibold">Generation Failed</p>
                <p className="text-xs mt-0.5 opacity-90">{errorMessage}</p>
                <button
                  onClick={handleReset}
                  className="mt-2 text-xs font-semibold text-rose-700 dark:text-rose-300 underline"
                >
                  Edit inputs & try again
                </button>
              </div>
            </div>
          )}

          {/* Success Result View */}
          {generationResult ? (
            <div className="space-y-6">
              <div className="p-5 rounded-2xl bg-gradient-to-br from-emerald-50 via-teal-50 to-emerald-100/50 dark:from-emerald-950/40 dark:via-slate-900 dark:to-emerald-900/30 border border-emerald-200 dark:border-emerald-800/60">
                <div className="flex items-center space-x-3 mb-2">
                  <div className="p-2 rounded-xl bg-emerald-600 text-white">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                      Generation Complete • Ready for Learning & Assessment
                    </span>
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                      {generationResult.title}
                    </h3>
                  </div>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">
                  Generated under official skill <span className="font-semibold text-slate-900 dark:text-white">{generationResult.skill_name}</span> at <span className="font-semibold text-indigo-600 dark:text-indigo-400">{generationResult.level}</span> level.
                </p>
              </div>

              {/* Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center space-x-2 text-indigo-600 dark:text-indigo-400 mb-1">
                    <Layers className="w-4 h-4" />
                    <span className="text-xs font-semibold">Modules & Lessons</span>
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white">
                    {generationResult.modules_count} <span className="text-xs font-normal text-slate-500">Modules</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {generationResult.lessons_count} structured lessons
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center space-x-2 text-purple-600 dark:text-purple-400 mb-1">
                    <Video className="w-4 h-4" />
                    <span className="text-xs font-semibold">Video Packages</span>
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white">
                    {generationResult.video_packages_count} <span className="text-xs font-normal text-slate-500">Mode B</span>
                  </div>
                  <div className="text-xs text-amber-600 dark:text-amber-400 mt-0.5 font-medium">
                    Storyboards & scripts ready
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center space-x-2 text-teal-600 dark:text-teal-400 mb-1">
                    <FileText className="w-4 h-4" />
                    <span className="text-xs font-semibold">4-Level Notes</span>
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white">
                    {generationResult.study_materials_count} <span className="text-xs font-normal text-slate-500">Docs</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    9-11 structured sections
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400 mb-1">
                    <Cpu className="w-4 h-4" />
                    <span className="text-xs font-semibold">Practice Tasks</span>
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-white">
                    {generationResult.practice_tasks_count} <span className="text-xs font-normal text-slate-500">Tasks</span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    MCQ, Coding & Debugging
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 col-span-2 sm:col-span-2">
                  <div className="flex items-center space-x-2 text-rose-600 dark:text-rose-400 mb-1">
                    <Brain className="w-4 h-4" />
                    <span className="text-xs font-semibold">Assessment & Question Bank</span>
                  </div>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-xl font-bold text-slate-900 dark:text-white">
                      {generationResult.question_bank_count} Questions
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 font-medium">
                      Zero Semantics Overlap
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Randomized Blueprint: 30% Easy, 50% Medium, 20% Hard per attempt
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
                >
                  Close
                </button>
                <button
                  type="button"
                  onClick={handleViewCourse}
                  className="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 rounded-xl shadow-md shadow-indigo-500/20 flex items-center space-x-2 transition"
                >
                  <span>Open Course Viewer</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : isGenerating ? (
            /* Generating Progress Screen */
            <div className="py-8 space-y-6">
              <div className="text-center space-y-2">
                <div className="inline-flex p-3 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 rounded-2xl shadow-inner animate-pulse">
                  <Brain className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Synthesizing & Grounding Course Architecture...
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                  Generating academic modules, 4-level study notes, Mode B storyboard scripts, interactive practice challenges, and a 30-question bank.
                </p>
              </div>

              {/* Progress Steps List */}
              <div className="space-y-3 max-w-lg mx-auto">
                {GENERATION_STEPS.map((step, idx) => {
                  const isDone = activeStepIndex > idx;
                  const isCurrent = activeStepIndex === idx;

                  return (
                    <div
                      key={step.id}
                      className={`flex items-start space-x-3 p-3 rounded-xl border transition-all ${
                        isDone
                          ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/40 text-emerald-900 dark:text-emerald-300'
                          : isCurrent
                          ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-700 text-indigo-950 dark:text-indigo-200 shadow-sm'
                          : 'bg-slate-50/40 dark:bg-slate-900/30 border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-600'
                      }`}
                    >
                      <div className="mt-0.5">
                        {isDone ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        ) : isCurrent ? (
                          <div className="w-5 h-5 border-2 border-indigo-600 dark:border-indigo-400 border-t-transparent rounded-full animate-spin shrink-0" />
                        ) : (
                          <div className="w-5 h-5 rounded-full border border-slate-300 dark:border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-400">
                            {idx + 1}
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold">{step.label}</p>
                        <p className="text-[11px] opacity-75">{step.desc}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-amber-800 dark:text-amber-300 text-xs flex items-center space-x-2 max-w-lg mx-auto">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                <span>Zero fake video URLs policy enforced: Mode B generates complete production scripts and storyboards.</span>
              </div>
            </div>
          ) : (
            /* Input Form */
            <form onSubmit={handleGenerate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Skill or Technology Topic <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={skillName}
                    onChange={(e) => setSkillName(e.target.value)}
                    placeholder="e.g. Distributed Systems with Go, React Performance Optimization, Docker DevOps"
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                  />
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                    The AI synthesizes modules, 4-level study notes, practice challenges, and a question bank based on this topic.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Course Title (Optional)
                  </label>
                  <input
                    type="text"
                    value={courseName}
                    onChange={(e) => setCourseName(e.target.value)}
                    placeholder="Leave blank to auto-generate title"
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Proficiency Level
                  </label>
                  <select
                    value={level}
                    onChange={(e) => setLevel(e.target.value as any)}
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                  >
                    <option value="BEGINNER">BEGINNER — Fundamentals & Core Concepts</option>
                    <option value="INTERMEDIATE">INTERMEDIATE — Practical Implementation & Patterns</option>
                    <option value="ADVANCED">ADVANCED — Deep Dives, Architecture & Optimization</option>
                    <option value="EXPERT">EXPERT — Production Hardening & Low-Level Internals</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Target Audience
                  </label>
                  <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="e.g. 3rd Year B.E. Computer Science students"
                    className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Curriculum Duration (Hours)
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      min={4}
                      max={120}
                      value={durationHours}
                      onChange={(e) => setDurationHours(parseInt(e.target.value) || 24)}
                      className="w-full pl-3.5 pr-10 py-2.5 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition"
                    />
                    <Clock className="w-4 h-4 text-slate-400 absolute right-3.5 top-3 pointer-events-none" />
                  </div>
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Core Learning Goal / Outcomes
                  </label>
                  <textarea
                    rows={2}
                    value={learningGoal}
                    onChange={(e) => setLearningGoal(e.target.value)}
                    placeholder="e.g. Master modern asynchronous patterns, architectural design principles, and production deployment."
                    className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 outline-none transition resize-none"
                  />
                </div>

                <div className="sm:col-span-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      id="publish_immediately"
                      checked={publishImmediately}
                      onChange={(e) => setPublishImmediately(e.target.checked)}
                      className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                    />
                    <label htmlFor="publish_immediately" className="text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                      <span className="font-semibold block">Publish course immediately to catalogue</span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        Students can immediately enroll, study, and take assessments.
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Footer Actions */}
              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 rounded-xl shadow-md shadow-indigo-500/25 flex items-center space-x-2 transition"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Full AI Course</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
