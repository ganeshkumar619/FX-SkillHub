import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { 
  BrainCircuit, 
  ArrowRight, 
  BookOpen
} from 'lucide-react';

export const SkillGapAnalysis: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();
  const [preAssessment, setPreAssessment] = useState<any>(null);
  const [attempt, setAttempt] = useState<any>(null);
  const [selectedAnswers, setSelectedAnswers] = useState<{ [qId: number]: number[] }>({});
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const initPreAssessment = async () => {
      try {
        const pRes = await apiClient.get(`/assessments/course/${courseId}/pre-assessment/`);
        setPreAssessment(pRes.data);

        // Start pre-assessment attempt
        const attRes = await apiClient.post(`/assessments/${pRes.data.id}/start/`);
        setAttempt(attRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    initPreAssessment();
  }, [courseId]);

  const handleSelectOption = async (questionId: number, optionId: number) => {
    const updated = { ...selectedAnswers, [questionId]: [optionId] };
    setSelectedAnswers(updated);

    if (attempt) {
      try {
        await apiClient.post(`/assessments/attempts/${attempt.id}/answers/`, {
          question_id: questionId,
          option_ids: [optionId]
        });
      } catch (err) {
        console.error(err);
      }
    }
  };

  const handleSubmitDiagnostic = async () => {
    if (!attempt) return;
    setSubmitting(true);
    try {
      const res = await apiClient.post(`/assessments/attempts/${attempt.id}/submit/`);
      setAnalysisResult(res.data.skill_gap_analysis);
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[85vh]">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm mb-8 space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-primary-800 bg-primary-50 px-2.5 py-1 rounded w-fit">
          <BrainCircuit className="w-4 h-4 text-primary-900" />
          Transparent AI Skill Gap Analysis
        </div>
        <h1 className="text-2xl font-bold text-slate-900">
          {preAssessment?.title || 'Diagnostic Pre-Assessment & Adaptive Roadmap'}
        </h1>
        <p className="text-xs text-slate-600 leading-relaxed">
          This diagnostic pre-assessment evaluates your topic-level baseline mastery. The system identifies specific conceptual gaps and maps them to active syllabus modules without hallucinations.
        </p>
      </div>

      {/* Analysis Result View */}
      {analysisResult ? (
        <div className="space-y-6">
          <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Diagnostic Result</span>
                <h2 className="text-2xl font-black text-slate-900 mt-1">
                  Overall Score: {analysisResult.overall_diagnostic_percentage}%
                </h2>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-primary-100 text-primary-900">
                {analysisResult.ai_engine}
              </span>
            </div>

            <p className="text-xs text-slate-700 bg-slate-50 p-4 rounded-xl border border-slate-200 leading-relaxed">
              {analysisResult.diagnostic_summary}
            </p>

            {/* Topic Breakdown */}
            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Topic Mastery Breakdown
              </h3>
              <div className="space-y-2.5">
                {Object.entries(analysisResult.topic_breakdown).map(([topic, pct]: any) => (
                  <div key={topic} className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-slate-800 capitalize">
                        {topic.replace('_', ' ')}
                      </div>
                      <span className={`text-[10px] font-bold ${pct < 70 ? 'text-amber-600' : 'text-emerald-600'}`}>
                        {pct < 70 ? 'Needs Reinforcement (<70%)' : 'Proficient (>=70%)'}
                      </span>
                    </div>
                    <span className="text-sm font-black text-slate-900">{pct}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Modules */}
            <div className="space-y-3 pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-primary-900 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-accent-600" />
                Tailored Module Recommendations
              </h3>

              <div className="space-y-3">
                {analysisResult.recommended_modules?.map((m: any) => (
                  <div key={m.module_id} className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900">
                        Module {m.order}: {m.title}
                      </h4>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900">
                        {m.priority} PRIORITY
                      </span>
                    </div>
                    <p className="text-xs text-slate-600">{m.reason}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <Link
                to="/catalogue"
                className="px-5 py-2.5 rounded-xl bg-primary-900 text-white text-xs font-bold shadow-md hover:bg-primary-800 flex items-center gap-2"
              >
                Go to Course Learning Room
                <ArrowRight className="w-4 h-4 text-accent-400" />
              </Link>
            </div>
          </div>
        </div>
      ) : (
        /* Questions Form */
        <div className="space-y-6">
          {attempt?.questions?.map((q: any, qIdx: number) => (
            <div key={q.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="font-bold text-primary-900">Question {qIdx + 1} of {attempt.questions.length}</span>
                <span className="bg-slate-100 px-2 py-0.5 rounded text-[11px] font-medium">{q.topic_tag}</span>
              </div>

              <h3 className="text-sm font-bold text-slate-900 leading-snug">{q.text}</h3>

              <div className="space-y-2 pt-1">
                {q.options?.map((opt: any) => {
                  const isSelected = selectedAnswers[q.id]?.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => handleSelectOption(q.id, opt.id)}
                      className={`w-full text-left p-3 rounded-xl text-xs font-medium border transition-all flex items-center gap-3 ${
                        isSelected 
                          ? 'bg-primary-50 border-primary-600 text-primary-950 font-bold shadow-sm' 
                          : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <span className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                        isSelected ? 'border-primary-600 bg-primary-600 text-white' : 'border-slate-300'
                      }`}>
                        {isSelected ? '✓' : ''}
                      </span>
                      <span>{opt.text}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          <div className="bg-white p-4 rounded-xl border border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              {Object.keys(selectedAnswers).length} of {attempt?.questions?.length} answered
            </span>

            <button
              onClick={handleSubmitDiagnostic}
              disabled={submitting}
              className="px-6 py-2.5 rounded-xl bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold shadow-md transition-all disabled:opacity-60 flex items-center gap-2"
            >
              {submitting ? 'Analyzing Responses...' : 'Submit Diagnostic Assessment'}
              <ArrowRight className="w-4 h-4 text-accent-400" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
