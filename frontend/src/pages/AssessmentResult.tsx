import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { AssessmentResult as ResultType, Certificate, DetailedQuestionReview } from '../types';
import { 
  Award, 
  CheckCircle2, 
  XCircle, 
  ShieldCheck, 
  Download, 
  ExternalLink, 
  BarChart3, 
  BookOpen, 
  RefreshCw,
  PlayCircle,
  Sparkles,
  AlertTriangle,
  RotateCcw,
  Check, 
  HelpCircle, 
  Lightbulb,
  Eye
} from 'lucide-react';
import { CertificatePreviewModal } from '../components/CertificatePreviewModal';

export const AssessmentResult: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const [result, setResult] = useState<ResultType | null>(location.state?.result || null);
  const [loading, setLoading] = useState(!location.state?.result);
  const [error, setError] = useState<string | null>(null);

  // Review filter: 'wrong' (default if any) | 'all' | 'correct'
  const [reviewFilter, setReviewFilter] = useState<'wrong' | 'all' | 'correct'>('wrong');

  // Certificate issuance state
  const [issuingCert, setIssuingCert] = useState(false);
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [certError, setCertError] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  useEffect(() => {
    const fetchResult = async () => {
      if (result && result.review_data) return;
      try {
        setLoading(true);
        const res = await apiClient.get(`/assessments/attempts/${attemptId}/result/`);
        setResult(res.data);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to retrieve assessment evaluation.');
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [attemptId, result]);

  // Check if certificate already exists
  useEffect(() => {
    const checkCertificate = async () => {
      if (!result?.passed || result?.assessment?.assessment_type !== 'FINAL_ASSESSMENT') return;
      try {
        const res = await apiClient.get('/certificates/my/');
        const existing = res.data.find((c: any) => c.course_title === result.assessment.title);
        if (existing) {
          setCertificate(existing);
        }
      } catch {
        // Optional pre-check
      }
    };
    checkCertificate();
  }, [result]);

  // Adjust default filter when review_data loads
  useEffect(() => {
    if (result?.review_data) {
      if (result.review_data.wrong_count === 0) {
        setReviewFilter('all');
      } else {
        setReviewFilter('wrong');
      }
    }
  }, [result?.review_data]);

  const handleClaimCertificate = async () => {
    if (!attemptId) return;
    setIssuingCert(true);
    setCertError(null);

    try {
      const res = await apiClient.post('/certificates/generate/', {
        attempt_id: attemptId
      });
      setCertificate(res.data);
    } catch (err: any) {
      setCertError(err.response?.data?.error || 'Failed to issue certificate.');
    } finally {
      setIssuingCert(false);
    }
  };

  const handleRetakeAssessment = () => {
    if (!result?.assessment?.id) return;
    navigate(`/assessments/${result.assessment.id}/preflight`);
  };

  if (loading) {
    return (
      <div className="min-h-[75vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Evaluating performance &amp; topic mastery...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-100 text-red-700 flex items-center justify-center mx-auto">
          <XCircle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Result Error</h2>
        <p className="text-xs text-slate-600">{error || 'Could not load assessment result.'}</p>
        <button
          onClick={() => navigate('/catalogue')}
          className="px-4 py-2 bg-primary-900 text-white rounded-lg text-xs font-semibold"
        >
          Return to Catalogue
        </button>
      </div>
    );
  }

  const isFinal = result.assessment.assessment_type === 'FINAL_ASSESSMENT';
  const topicBreakdown = result.topic_breakdown || {};
  const risk = result.risk_assessment;
  const review = result.review_data;

  const totalQuestions = review?.total_questions || 0;
  const correctCount = review?.correct_count || 0;
  const wrongCount = review?.wrong_count || 0;
  const answeredCount = review?.answered_count || 0;

  // Filter questions for display
  const allQuestions = review?.detailed_questions || [];
  const filteredQuestions = allQuestions.filter((q: DetailedQuestionReview) => {
    if (reviewFilter === 'wrong') return !q.is_correct;
    if (reviewFilter === 'correct') return q.is_correct;
    return true;
  });

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* 1. Header Banner & High-level Status */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <span className="text-[11px] font-bold text-primary-900 bg-primary-50 px-2.5 py-1 rounded">
              {isFinal ? 'Official Certification Evaluation' : 'Diagnostic Skill Assessment'}
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-2">
              {result.assessment.title}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Francis Xavier Engineering College • Autonomous Certification Authority
            </p>
          </div>

          <div className="flex items-center gap-2">
            {result.passed ? (
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span>Passed &amp; Qualified</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 font-bold text-sm">
                <XCircle className="w-5 h-5 text-amber-600" />
                <span>Improvement Needed</span>
              </div>
            )}
          </div>
        </div>

        {/* High-level Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Score</span>
            <div className="text-xl font-black text-slate-900 mt-0.5">
              {result.score} <span className="text-[11px] font-normal text-slate-500">Marks</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Percentage</span>
            <div className="text-xl font-black text-primary-900 mt-0.5">
              {result.percentage}%
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Passing Mark</span>
            <div className="text-xl font-black text-slate-700 mt-0.5">
              {result.assessment.pass_percentage}%
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Questions</span>
            <div className="text-xl font-black text-slate-800 mt-0.5">
              {answeredCount}/{totalQuestions}
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-100">
            <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Correct</span>
            <div className="text-xl font-black text-emerald-700 mt-0.5">
              {correctCount}
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-rose-50/70 border border-rose-100">
            <span className="text-[10px] font-bold text-rose-600 uppercase tracking-wider">Wrong</span>
            <div className="text-xl font-black text-rose-700 mt-0.5">
              {wrongCount}
            </div>
          </div>
        </div>

        {/* AI Diagnostic Summary Banner */}
        {review?.ai_diagnostic_summary && (
          <div className="p-4 rounded-xl bg-primary-50/60 border border-primary-100 flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-primary-900 shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <span className="font-bold text-primary-950 uppercase tracking-wider text-[10px]">
                FXEC AI Performance Diagnostic
              </span>
              <p className="text-slate-700 leading-relaxed">
                {review.ai_diagnostic_summary}
              </p>
            </div>
          </div>
        )}

        {/* Certificate Issuance Section (When Passed) */}
        {isFinal && result.passed && (
          <div className="p-6 rounded-2xl bg-gradient-to-r from-primary-950 to-primary-900 text-white space-y-4 shadow-lg">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-accent-300 text-xs font-bold uppercase tracking-wider">
                  <Award className="w-4 h-4" />
                  Official FXEC Digital Certificate
                </div>
                <h3 className="text-lg font-bold">
                  🎉 Congratulations! You successfully passed {result.assessment.title}.
                </h3>
                <p className="text-xs text-slate-300 max-w-xl">
                  Your academic credential has been authorized by Francis Xavier Engineering College with embedded QR verification and official institutional seals.
                </p>
              </div>
            </div>

            {certError && (
              <div className="p-3 rounded-lg bg-red-500/20 border border-red-500/40 text-red-200 text-xs">
                {certError}
              </div>
            )}

            {certificate ? (
              <div className="bg-white/10 backdrop-blur-sm p-4 rounded-xl border border-white/20 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div>
                    <span className="text-slate-300">Certificate ID: </span>
                    <span className="font-mono font-bold text-white">{certificate.certificate_number}</span>
                  </div>
                  <div>
                    <span className="text-slate-300">Issued: </span>
                    <span className="text-white">{new Date(certificate.issued_at).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsPreviewOpen(true)}
                    className="px-4 py-2 bg-accent-400 hover:bg-accent-300 text-primary-950 text-xs font-bold rounded-lg shadow flex items-center gap-2 transition-all cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    View Certificate
                  </button>

                  <a
                    href={`/api/certificates/${certificate.certificate_id || certificate.id}/pdf/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white text-xs font-bold rounded-lg border border-white/30 flex items-center gap-2 transition-all cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5 text-accent-300" />
                    Download Official PDF
                  </a>

                  <Link
                    to={`/verify/${certificate.certificate_number || certificate.certificate_id || certificate.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-lg border border-white/20 flex items-center gap-2 transition-all cursor-pointer"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Verify Certificate
                  </Link>
                </div>
              </div>
            ) : (
              <button
                onClick={handleClaimCertificate}
                disabled={issuingCert}
                className="px-6 py-2.5 bg-accent-400 hover:bg-accent-300 text-primary-950 text-xs font-bold rounded-xl shadow-md hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {issuingCert ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" /> Generating Official Certificate...
                  </>
                ) : (
                  <>
                    <Award className="w-4 h-4" /> Claim FXEC Certificate Now
                  </>
                )}
              </button>
            )}
          </div>
        )}

        {/* Retake Section (When Not Passed) */}
        {!result.passed && (
          <div className="p-6 rounded-2xl bg-amber-50 border border-amber-200 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  Recommended Next Steps
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  Don't worry! Review your mistakes below and re-attempt when ready.
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed max-w-2xl">
                  Carefully inspect each question answered incorrectly in the <strong>Review Your Mistakes</strong> section below, revise the linked learning videos and notes, then retake the assessment.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={handleRetakeAssessment}
                  className="px-4 py-2 bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs rounded-xl shadow flex items-center gap-1.5 transition cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Retry Assessment</span>
                </button>

                <Link
                  to="/catalogue"
                  className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 font-bold text-xs rounded-xl border border-slate-300 flex items-center gap-1.5 transition"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Continue Learning</span>
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. AI WEAK AREA ANALYSIS & REAL YOUTUBE RECOMMENDATIONS */}
      {review?.weak_area_recommendations && review.weak_area_recommendations.length > 0 && (
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <Lightbulb className="w-5 h-5 text-amber-600" />
              <div>
                <h2 className="text-base font-bold text-slate-900">
                  AI Weak Area Analysis &amp; Targeted Resources
                </h2>
                <p className="text-xs text-slate-500">
                  Curated learning modules and verified YouTube video lectures matching your specific errors
                </p>
              </div>
            </div>

            {review.primary_weak_area && (
              <span className="text-[11px] font-bold px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-800">
                Primary Focus: {review.primary_weak_area}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {review.weak_area_recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="p-5 rounded-2xl bg-slate-50/70 border border-slate-200 space-y-4 hover:border-primary-300 transition"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
                      Module {rec.module_order} • {rec.topic_name}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 mt-0.5">
                      {rec.module_title}
                    </h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 shrink-0">
                    {rec.error_count} Error{rec.error_count > 1 ? 's' : ''}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {rec.ai_action_plan}
                </p>

                {/* Real YouTube Video Reference */}
                {rec.video_reference && (
                  <div className="p-3 rounded-xl bg-white border border-slate-200 flex items-center gap-3">
                    <div className="w-20 h-12 rounded-lg bg-black overflow-hidden relative shrink-0">
                      <img
                        src={rec.video_reference.thumbnail_url}
                        alt={rec.video_reference.title}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/30 flex items-center justify-center">
                        <PlayCircle className="w-5 h-5 text-white" />
                      </div>
                    </div>

                    <div className="min-w-0 flex-1">
                      <h4 className="text-xs font-bold text-slate-900 truncate">
                        {rec.video_reference.title}
                      </h4>
                      <p className="text-[10px] text-slate-500">
                        {rec.video_reference.channel_name} • {rec.video_reference.duration}
                      </p>
                      <a
                        href={rec.video_reference.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] font-bold text-primary-900 hover:text-primary-700 flex items-center gap-1 mt-0.5"
                      >
                        <span>Watch Video Lecture</span>
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    </div>
                  </div>
                )}

                {/* Study Notes & Practice Action Buttons */}
                <div className="pt-2 flex flex-wrap items-center gap-2 border-t border-slate-200/80">
                  <Link
                    to={`/courses/${rec.course_slug}`}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 text-[11px] font-semibold flex items-center gap-1 transition"
                  >
                    <BookOpen className="w-3 h-3 text-primary-900" />
                    <span>Read Study Notes</span>
                  </Link>

                  <Link
                    to={`/courses/${rec.course_slug}`}
                    className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 text-[11px] font-semibold flex items-center gap-1 transition"
                  >
                    <HelpCircle className="w-3 h-3 text-amber-600" />
                    <span>Try Practice Quiz</span>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3. WRONG ANSWER REVIEW ("REVIEW YOUR MISTAKES") (CRITICAL REQUIREMENT) */}
      <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-primary-900" />
              <h2 className="text-lg font-extrabold text-slate-900">
                Review Your Mistakes &amp; Question Explanations
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Inspect your answers against official solutions with AI diagnostic misconceptions
            </p>
          </div>

          {/* Segmented Filter Buttons */}
          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl border border-slate-200 text-xs font-bold">
            <button
              type="button"
              onClick={() => setReviewFilter('wrong')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                reviewFilter === 'wrong'
                  ? 'bg-rose-700 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Needs Improvement ({wrongCount})</span>
            </button>

            <button
              type="button"
              onClick={() => setReviewFilter('all')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                reviewFilter === 'all'
                  ? 'bg-primary-900 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>All Questions ({totalQuestions})</span>
            </button>

            <button
              type="button"
              onClick={() => setReviewFilter('correct')}
              className={`px-3 py-1.5 rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
                reviewFilter === 'correct'
                  ? 'bg-emerald-700 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Correct ({correctCount})</span>
            </button>
          </div>
        </div>

        {/* Questions List */}
        <div className="space-y-6">
          {filteredQuestions.length > 0 ? (
            filteredQuestions.map((q: DetailedQuestionReview) => (
              <div
                key={q.question_id}
                className={`p-6 rounded-2xl border transition space-y-4 ${
                  q.is_correct
                    ? 'bg-emerald-50/20 border-emerald-200'
                    : 'bg-rose-50/20 border-rose-200'
                }`}
              >
                {/* Question Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-700 bg-white px-2.5 py-1 rounded border border-slate-200">
                      Question {q.order} of {totalQuestions}
                    </span>
                    <span className="text-slate-500 font-medium">
                      {q.topic_label}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      q.difficulty === 'EASY' ? 'bg-emerald-100 text-emerald-800' :
                      q.difficulty === 'MEDIUM' ? 'bg-blue-100 text-blue-800' :
                      'bg-purple-100 text-purple-800'
                    }`}>
                      {q.difficulty}
                    </span>
                  </div>

                  <div>
                    {q.is_correct ? (
                      <span className="flex items-center gap-1 text-emerald-700 font-bold">
                        <CheckCircle2 className="w-4 h-4" /> Correct (+{q.marks} mark)
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-rose-700 font-bold">
                        <XCircle className="w-4 h-4" /> Incorrect (0/{q.marks} mark)
                      </span>
                    )}
                  </div>
                </div>

                {/* Question Prompt */}
                <div className="text-sm sm:text-base font-bold text-slate-900 leading-relaxed">
                  {q.question_text}
                </div>

                {/* Options Comparison */}
                <div className="space-y-2 pt-1">
                  {q.options.map((opt) => {
                    const isSelected = opt.is_selected;
                    const isCorrect = opt.is_correct;

                    let optStyle = "bg-white border-slate-200 text-slate-700";
                    let badge = null;

                    if (isSelected && isCorrect) {
                      optStyle = "bg-emerald-50 border-emerald-500 text-emerald-900 font-semibold";
                      badge = (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white flex items-center gap-1">
                          <Check className="w-3 h-3" /> Your Correct Choice
                        </span>
                      );
                    } else if (isSelected && !isCorrect) {
                      optStyle = "bg-rose-50 border-rose-500 text-rose-950 font-semibold";
                      badge = (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white flex items-center gap-1">
                          <XCircle className="w-3 h-3" /> Your Incorrect Choice
                        </span>
                      );
                    } else if (!isSelected && isCorrect) {
                      optStyle = "bg-emerald-50/70 border-emerald-300 text-emerald-900 font-medium";
                      badge = (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                          <Check className="w-3 h-3" /> Correct Answer
                        </span>
                      );
                    }

                    return (
                      <div
                        key={opt.id}
                        className={`p-3.5 rounded-xl border flex items-center justify-between gap-3 text-xs ${optStyle}`}
                      >
                        <div className="flex items-center gap-2.5">
                          <span className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 text-[10px] ${
                            isSelected ? 'bg-primary-900 text-white border-primary-900' : 'border-slate-300'
                          }`}>
                            {opt.order}
                          </span>
                          <span>{opt.text}</span>
                        </div>
                        {badge}
                      </div>
                    );
                  })}
                </div>

                {/* Institutional Pedagogical Explanation */}
                {q.explanation && (
                  <div className="p-4 rounded-xl bg-white border border-slate-200 text-xs text-slate-700 space-y-1">
                    <span className="font-bold text-slate-900 uppercase tracking-wider text-[10px] flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-primary-900" />
                      Pedagogical Explanation
                    </span>
                    <p className="leading-relaxed text-slate-600">{q.explanation}</p>
                  </div>
                )}

                {/* AI Mistake Diagnosis Box (Only for Wrong Answers) */}
                {!q.is_correct && q.ai_diagnosis && (
                  <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-xs space-y-2.5">
                    <div className="flex items-center gap-1.5 font-bold text-amber-900 text-[11px] uppercase tracking-wider">
                      <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                      AI Diagnostic Misconception Analysis
                    </div>

                    <p className="text-slate-700 leading-relaxed">
                      <strong>Why your answer was incorrect: </strong>
                      {q.ai_diagnosis.why_incorrect}
                    </p>

                    <p className="text-slate-700 leading-relaxed">
                      <strong>Why the correct answer is right: </strong>
                      {q.ai_diagnosis.why_correct}
                    </p>

                    {q.ai_diagnosis.small_example && (
                      <div className="pt-1">
                        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
                          Illustrative Practical Pattern:
                        </span>
                        <pre className="p-3 rounded-lg bg-slate-900 text-slate-100 font-mono text-[11px] overflow-x-auto mt-1">
                          {q.ai_diagnosis.small_example}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="p-12 text-center text-slate-500 text-xs">
              No questions found for the selected filter.
            </div>
          )}
        </div>
      </section>

      {/* 4. Topic Mastery Breakdown */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-900" />
            <h2 className="text-base font-bold text-slate-900">Topic Mastery Diagnostic</h2>
          </div>
          <span className="text-xs text-slate-500">Autonomous Curriculum Alignment</span>
        </div>

        <div className="space-y-4">
          {Object.keys(topicBreakdown).length > 0 ? (
            Object.entries(topicBreakdown).map(([topic, stats]) => (
              <div key={topic} className="p-4 rounded-xl border border-slate-100 bg-slate-50 space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-800">{topic}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">{stats.earned_marks}/{stats.total_marks} marks</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      stats.status === 'PROFICIENT' ? 'bg-emerald-100 text-emerald-800' :
                      stats.status === 'GROWTH_NEEDED' ? 'bg-amber-100 text-amber-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {stats.status}
                    </span>
                  </div>
                </div>

                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      stats.status === 'PROFICIENT' ? 'bg-emerald-600' :
                      stats.status === 'GROWTH_NEEDED' ? 'bg-amber-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, stats.percentage))}%` }}
                  />
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500">No topic-level breakdown recorded for this evaluation.</p>
          )}
        </div>
      </div>

      {/* 5. Proctoring & Institutional Integrity Details */}
      <div className="bg-slate-50 rounded-2xl border border-slate-200 p-6 space-y-3 text-xs text-slate-600">
        <div className="flex items-center gap-2 font-bold text-primary-950">
          <ShieldCheck className="w-4 h-4 text-primary-800" />
          Proctoring Audit &amp; Academic Integrity
        </div>
        <p className="leading-relaxed">
          This session was evaluated using FX SkillHub's transparent browser deterrent system. Events logged: <span className="font-bold text-slate-900">{risk?.event_count || 0}</span>. Final review status: <span className="font-bold text-slate-900">{result.review_status}</span>. In accordance with autonomous regulations, all alerts are subject to human faculty mentor review before institutional credential release.
        </p>

        <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
          <Link
            to="/catalogue"
            className="text-primary-900 font-bold hover:underline flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5" /> Back to Skill Catalogue
          </Link>
          <span className="text-[11px] text-slate-400">
            Francis Xavier Engineering College (Autonomous), Tirunelveli
          </span>
        </div>
      </div>

      {/* Certificate Preview Modal */}
      <CertificatePreviewModal
        certificate={certificate}
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        studentNameFallback={result?.student_name}
      />
    </div>
  );
};
