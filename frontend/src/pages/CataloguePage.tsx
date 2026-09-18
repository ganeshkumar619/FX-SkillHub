import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import type { Course, Department, SkillCategory, SkillDomain, AISkillSuggestion } from '../types';
import { 
  BookOpen, 
  ExternalLink, 
  ShieldCheck, 
  Clock, 
  Search, 
  Sparkles, 
  AlertCircle,
  CheckCircle2,
  X
} from 'lucide-react';
import { AICourseGeneratorModal } from '../components/AICourseGeneratorModal';

export const CataloguePage: React.FC = () => {
  const { user, isMentor, isAdmin } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<SkillCategory[]>([]);
  const [domains, setDomains] = useState<SkillDomain[]>([]);

  // Filter States
  const [selectedDept, setSelectedDept] = useState<string>('ALL');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedDomain, setSelectedDomain] = useState<string>('ALL');
  const [selectedLevel, setSelectedLevel] = useState<string>('ALL');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [selectedSource, setSelectedSource] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('newest');
  const [loading, setLoading] = useState(true);

  // AI Discovery Modal State
  const [showAiModal, setShowAiModal] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<{
    disclaimer: string;
    suggestions: AISkillSuggestion[];
  } | null>(null);

  // AI Course Generator Modal State
  const [isCourseGeneratorOpen, setIsCourseGeneratorOpen] = useState(false);
  const [generatorSkillName, setGeneratorSkillName] = useState('');
  const [skillAddingIdx, setSkillAddingIdx] = useState<number | null>(null);
  const [skillAddedMessage, setSkillAddedMessage] = useState<string | null>(null);

  const handleSaveSkillWithAi = async (sugg: AISkillSuggestion, idx: number) => {
    try {
      setSkillAddingIdx(idx);
      await apiClient.post('/catalogue/ai/skills/generate/', {
        skill_name: sugg.title,
        level: sugg.level,
        department_code: selectedDept !== 'ALL' ? selectedDept : null,
        preview_only: false
      });
      setSkillAddedMessage(`Skill "${sugg.title}" successfully synthesized & registered to catalogue!`);
      setTimeout(() => setSkillAddedMessage(null), 4000);
    } catch (err: any) {
      console.error('Failed to save skill', err);
      const msg = err.response?.data?.error || 'Failed to register skill.';
      setSkillAddedMessage(msg);
      setTimeout(() => setSkillAddedMessage(null), 4000);
    } finally {
      setSkillAddingIdx(null);
    }
  };

  const loadCatalogue = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (selectedDept !== 'ALL') params.append('department', selectedDept);
      if (selectedCategory !== 'ALL') params.append('category', selectedCategory);
      if (selectedDomain !== 'ALL') params.append('domain', selectedDomain);
      if (selectedLevel !== 'ALL') params.append('level', selectedLevel);
      if (selectedType !== 'ALL') params.append('course_type', selectedType);
      if (selectedSource !== 'ALL') params.append('source_type', selectedSource);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      if (sortBy) params.append('sort', sortBy);

      const [courseRes, deptRes, catRes, domRes] = await Promise.all([
        apiClient.get(`/catalogue/courses/?${params.toString()}`),
        apiClient.get('/catalogue/departments/'),
        apiClient.get('/catalogue/categories/'),
        apiClient.get('/catalogue/domains/'),
      ]);

      setCourses(courseRes.data.results || courseRes.data);
      setDepartments(deptRes.data.results || deptRes.data);
      setCategories(catRes.data.results || catRes.data);
      setDomains(domRes.data.results || domRes.data);
    } catch (err) {
      console.error('Failed to load catalogue', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalogue();
  }, [selectedDept, selectedCategory, selectedDomain, selectedLevel, selectedType, selectedSource, sortBy]);

  // Handle Enter on search input
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadCatalogue();
  };

  // AI Discovery Submission
  const handleDiscoverSkills = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiPrompt.trim()) return;
    try {
      setAiLoading(true);
      const res = await apiClient.post('/catalogue/ai/skill-suggestions/', {
        prompt: aiPrompt,
        department: selectedDept !== 'ALL' ? selectedDept : null,
      });
      setAiResult(res.data);
    } catch (err) {
      console.error('AI Discovery error', err);
    } finally {
      setAiLoading(false);
    }
  };

  // Helper for source verification badges
  const renderSourceBadge = (course: Course) => {
    switch (course.source_type) {
      case 'FXEC_OFFICIAL':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            Official FXEC
          </span>
        );
      case 'FACULTY_CREATED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200">
            Faculty Initiative
          </span>
        );
      case 'ADMIN_CREATED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-800 border border-purple-200">
            Institutional Admin
          </span>
        );
      case 'AI_SUGGESTED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
            <Sparkles className="w-3.5 h-3.5 text-amber-600" />
            AI Suggested
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
            External Reference
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[85vh] space-y-8">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-primary-950 via-primary-900 to-slate-900 rounded-3xl p-8 sm:p-10 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-black uppercase tracking-wider bg-accent-500/20 text-accent-300 border border-accent-400/30 px-3 py-1 rounded-full">
              Francis Xavier Engineering College (Autonomous)
            </span>
            <span className="text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 px-3 py-1 rounded-full flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              Verified Provenance System
            </span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
            Institutional Skill &amp; Course Catalogue
          </h1>

          <p className="text-sm text-slate-300 leading-relaxed">
            A dynamic, source-aware curriculum engine curated by FXEC Academic Departments, Applied Special Labs, and the Centre for Training &amp; Skills Development.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowAiModal(true)}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-accent-600 to-amber-500 hover:from-accent-500 hover:to-amber-400 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg transition-all cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              Discover Skills with AI
            </button>
            {user && (isMentor || isAdmin) && (
              <>
                <button
                  onClick={() => {
                    setGeneratorSkillName('');
                    setIsCourseGeneratorOpen(true);
                  }}
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-lg transition-all cursor-pointer"
                >
                  <Sparkles className="w-4 h-4 text-accent-300" />
                  Autonomous AI Course Studio
                </button>
                <span className="text-xs text-slate-400">
                  Generate instant 4-module courses, study materials &amp; assessments with AI
                </span>
              </>
            )}
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute right-0 top-0 -mt-10 -mr-10 w-96 h-96 bg-accent-500/10 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Advanced Filter Bar */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        {/* Search row */}
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-grow">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search by course title, skill, or keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-600 transition-all"
            />
          </div>
          <button
            type="submit"
            className="px-6 py-2.5 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-xl shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            <Search className="w-4 h-4" />
            Search
          </button>
        </form>

        {/* Filters grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          {/* Department */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Department</label>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="ALL">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.code}>{d.code} - {d.name}</option>
              ))}
            </select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Skill Pillar</label>
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setSelectedDomain('ALL');
              }}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="ALL">All Pillars</option>
              {categories.map((c) => (
                <option key={c.id} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Domain */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Domain</label>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="ALL">All Domains</option>
              {domains
                .filter((dm) => selectedCategory === 'ALL' || dm.category_name === selectedCategory)
                .map((dm) => (
                  <option key={dm.id} value={dm.name}>{dm.name}</option>
                ))}
            </select>
          </div>

          {/* Level */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Difficulty Level</label>
            <select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="ALL">All Levels</option>
              <option value="BEGINNER">Beginner</option>
              <option value="INTERMEDIATE">Intermediate</option>
              <option value="ADVANCED">Advanced</option>
              <option value="EXPERT">Expert</option>
            </select>
          </div>

          {/* Course Type */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Course Type</label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="ALL">All Types</option>
              <option value="CORE_SKILL">Core Skill</option>
              <option value="ELECTIVE_SKILL">Elective Skill</option>
              <option value="FACULTY_INITIATIVE">Faculty Initiative</option>
              <option value="VALUE_ADDED">Value Added</option>
              <option value="INTERDISCIPLINARY">Interdisciplinary</option>
              <option value="PLACEMENT">Placement Training</option>
              <option value="EMERGING">Emerging / Future</option>
            </select>
          </div>

          {/* Sort Order */}
          <div>
            <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600 font-semibold"
            >
              <option value="newest">Newest First</option>
              <option value="popular">Most Enrolled</option>
              <option value="beginner_friendly">Beginner Friendly</option>
              <option value="duration_asc">Shortest Duration</option>
            </select>
          </div>
        </div>
      </div>

      {/* Courses Grid */}
      {loading ? (
        <div className="text-center py-20">
          <div className="inline-block w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 mt-2 font-medium">Loading verified institutional catalogue...</p>
        </div>
      ) : courses.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-3xl border border-slate-200 p-8 space-y-3">
          <BookOpen className="w-12 h-12 text-slate-400 mx-auto" />
          <h3 className="text-base font-bold text-slate-800">No Courses Matching Filter Criteria</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            In adherence to the official FXEC Real-Data Policy, empty states are shown rather than synthetic placeholder courses.
          </p>
          <button
            onClick={() => {
              setSelectedDept('ALL');
              setSelectedCategory('ALL');
              setSelectedDomain('ALL');
              setSelectedLevel('ALL');
              setSelectedType('ALL');
              setSelectedSource('ALL');
              setSearchQuery('');
            }}
            className="mt-2 text-xs font-bold text-primary-700 hover:text-primary-900 underline"
          >
            Reset All Filters
          </button>

          {user && (isMentor || isAdmin) && searchQuery && (
            <div className="pt-4 border-t border-slate-100 mt-4 space-y-2">
              <p className="text-xs text-slate-600 font-medium">
                Want to synthesize a course on <strong>"{searchQuery}"</strong> right now?
              </p>
              <button
                onClick={() => {
                  setGeneratorSkillName(searchQuery);
                  setIsCourseGeneratorOpen(true);
                }}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-accent-300" />
                Generate "{searchQuery}" Course with AI in 60s
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => (
            <div
              key={course.id}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between overflow-hidden"
            >
              <div className="p-6 space-y-4">
                {/* Header Badges */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  {renderSourceBadge(course)}
                  <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                    <Clock className="w-3 h-3 text-slate-400" />
                    {course.estimated_hours} Hours
                  </span>
                </div>

                {/* Title & Level */}
                <div>
                  <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                    {course.departments && course.departments.length > 1 ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-800 border border-purple-200">
                        {course.departments.map(d => d.code).join(' + ')} (Interdisciplinary)
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-primary-50 text-primary-900 border border-primary-200">
                        {course.department?.code || 'INTER-DEPT'}
                      </span>
                    )}

                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {course.level || 'Beginner'}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 line-clamp-2 leading-snug">
                    {course.title}
                  </h3>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  {course.description}
                </p>

                {/* Course Type Tags */}
                {course.course_types && course.course_types.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {course.course_types.slice(0, 3).map((type, idx) => (
                      <span key={idx} className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                        {type.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                )}

                {/* Provenance Box */}
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-600 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700">Instructor:</span>
                    <span className="font-medium text-slate-900 text-right truncate max-w-[170px]">
                      {course.instructor_name || 'FXEC Faculty Team'}
                    </span>
                  </div>
                  {course.source_url && (
                    <div className="pt-1 flex items-center justify-between border-t border-slate-200/60">
                      <span className="text-slate-500">Official Provenance:</span>
                      <a
                        href={course.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary-700 hover:text-primary-900 font-semibold underline flex items-center gap-1 text-[10px]"
                      >
                        Verify Record <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Card Footer */}
              <div className="p-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-600 truncate max-w-[180px]">
                  {course.skill?.category?.name || 'Academic Course'}
                </span>
                <Link
                  to={`/course/${course.slug}`}
                  className="px-4 py-2 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs shadow-sm transition-colors"
                >
                  View Curriculum
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* AI Skill Discovery Modal */}
      {showAiModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white w-full max-w-2xl rounded-3xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-6 bg-gradient-to-r from-primary-950 to-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-accent-500/20 text-accent-400 border border-accent-400/30">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Discover Skills with AI</h3>
                  <p className="text-xs text-slate-300">
                    Explore emerging competencies &amp; suggested learning sequences
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowAiModal(false);
                  setAiResult(null);
                }}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              <form onSubmit={handleDiscoverSkills} className="space-y-3">
                <label className="block text-xs font-bold text-slate-700">
                  Enter your interests, target career, or a technical topic:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. Full Stack Developer, Autonomous Robotics, Cyber Defense..."
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    className="flex-grow px-4 py-2.5 text-xs bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary-600"
                  />
                  <button
                    type="submit"
                    disabled={aiLoading || !aiPrompt.trim()}
                    className="px-5 py-2.5 bg-primary-900 hover:bg-primary-800 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-sm flex items-center gap-2"
                  >
                    {aiLoading ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      'Generate Roadmap'
                    )}
                  </button>
                </div>
              </form>

              {/* AI Results */}
              {aiResult && (
                <div className="space-y-4 pt-2 border-t border-slate-100">
                  {/* Institutional Safety Disclaimer */}
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
                    <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <p className="leading-relaxed">
                      <strong>Institutional Notice:</strong> {aiResult.disclaimer}
                    </p>
                  </div>

                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Recommended Learning Sequence:
                  </h4>

                  <div className="space-y-3">
                    {aiResult.suggestions.map((sugg, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-primary-900 text-white text-[11px] font-bold flex items-center justify-center">
                              {idx + 1}
                            </span>
                            <span className="text-xs font-bold text-slate-900">{sugg.title}</span>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-primary-100 text-primary-900">
                            {sugg.level}
                          </span>
                        </div>

                        <p className="text-xs text-slate-600 pl-7">{sugg.justification}</p>

                        {sugg.learning_outcomes && sugg.learning_outcomes.length > 0 && (
                          <div className="pl-7 space-y-1">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                              Target Competencies:
                            </span>
                            <ul className="text-xs text-slate-600 list-disc list-inside space-y-0.5">
                              {sugg.learning_outcomes.map((out, oIdx) => (
                                <li key={oIdx}>{out}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="pl-7 pt-2 flex flex-wrap items-center gap-2">
                          {user && (isMentor || isAdmin) ? (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  setShowAiModal(false);
                                  setGeneratorSkillName(sugg.title);
                                  setIsCourseGeneratorOpen(true);
                                }}
                                className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-[11px] font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                              >
                                <Sparkles className="w-3.5 h-3.5 text-accent-300" />
                                ⚡ Generate Full Course with AI
                              </button>
                              <button
                                type="button"
                                onClick={() => handleSaveSkillWithAi(sugg, idx)}
                                disabled={skillAddingIdx === idx}
                                className="px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-800 text-[11px] font-bold flex items-center gap-1 transition-all cursor-pointer disabled:opacity-50"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                {skillAddingIdx === idx ? 'Registering...' : 'Save Skill to Catalogue'}
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setShowAiModal(false);
                                setSearchQuery(sugg.title);
                              }}
                              className="px-3 py-1.5 rounded-lg bg-primary-900 hover:bg-primary-800 text-white text-[11px] font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                            >
                              <Search className="w-3.5 h-3.5 text-accent-400" />
                              Search Courses on "{sugg.title}"
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              {skillAddedMessage ? (
                <div className="text-xs font-semibold text-emerald-700 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  {skillAddedMessage}
                </div>
              ) : <div />}
              <button
                onClick={() => setShowAiModal(false)}
                className="px-5 py-2 text-xs font-bold text-slate-700 hover:text-slate-900"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Autonomous AI Course Generator Modal - Only for Mentors & Administrators */}
      {user && (isMentor || isAdmin) && (
        <AICourseGeneratorModal
          isOpen={isCourseGeneratorOpen}
          onClose={() => setIsCourseGeneratorOpen(false)}
          defaultSkillName={generatorSkillName}
          onSuccess={() => {
            loadCatalogue();
          }}
        />
      )}
    </div>
  );
};
