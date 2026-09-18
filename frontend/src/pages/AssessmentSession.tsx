import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { AssessmentAttempt, Question } from '../types';
import { FaceDetectionEngine } from '../utils/faceDetector';
import { 
  Clock, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowLeft, 
  ArrowRight, 
  Send, 
  HelpCircle, 
  Maximize2, 
  Camera, 
  Monitor, 
  Lock, 
  ExternalLink,
  Smartphone,
  EyeOff,
  RefreshCw,
  Sparkles
} from 'lucide-react';

interface ActiveWarningInfo {
  eventType: string;
  warningType: string;
  currentCount: number;
  maxWarnings: number;
  message: string;
}

export const AssessmentSession: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number[]>>({});
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error' | 'locked'>('saved');

  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [currentRiskTier, setCurrentRiskTier] = useState<string>('NORMAL');
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Security warning & termination states
  const [activeWarning, setActiveWarning] = useState<ActiveWarningInfo | null>(null);
  const [isTerminated, setIsTerminated] = useState(false);
  const [terminationReason, setTerminationReason] = useState<string | null>(null);
  const [violationCounts, setViolationCounts] = useState({
    camera: 0,
    multipleFace: 0,
    screenShare: 0,
    fullscreen: 0,
    tabSwitch: 0,
  });

  // Live Proctoring Verification & Continuous Alert States
  const [liveFaceState, setLiveFaceState] = useState<'CONFIRMED_SINGLE_FACE' | 'NO_FACE_BLANK' | 'CAMERA_CLOSED' | 'MOBILE_DETECTED'>('CONFIRMED_SINGLE_FACE');
  const [continuousAlert, setContinuousAlert] = useState<{
    type: 'CAMERA_CLOSED' | 'NO_FACE_BLANK' | 'MOBILE_DETECTED' | 'AI_TOOL';
    title: string;
    message: string;
    actionLabel?: string;
    onAction?: () => void;
  } | null>(null);

  // Floating PiP camera stream & screen share
  const videoPipRef = useRef<HTMLVideoElement | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [screenStream, setScreenStream] = useState<MediaStream | null>(null);
  const [screenActive, setScreenActive] = useState(false);

  const attemptIdRef = useRef<string | null>(null);
  const hasAutoSubmittedRef = useRef<boolean>(false);
  const faceDetectorRef = useRef<FaceDetectionEngine>(new FaceDetectionEngine(1.5));
  const simCleanupRef = useRef<(() => void) | null>(null);

  // 1. Initialize or load attempt
  useEffect(() => {
    const initAttempt = async () => {
      try {
        setLoading(true);
        let currentAttemptId = location.state?.attemptId;

        // If not in state, start/fetch active attempt
        if (!currentAttemptId) {
          const startRes = await apiClient.post(`/assessments/${assessmentId}/start/`);
          currentAttemptId = startRes.data.id;
        }

        const res = await apiClient.get(`/assessments/attempts/${currentAttemptId}/`);
        const data: AssessmentAttempt = res.data;

        // Handle already submitted / completed
        if (data.status === 'SUBMITTED' || data.status === 'EXPIRED' || data.status === 'EVALUATED') {
          navigate(`/assessments/${data.id}/result`, { replace: true });
          return;
        }

        // Handle already terminated attempt
        if (data.status === 'TERMINATED_SECURITY_VIOLATION') {
          setAttempt(data);
          attemptIdRef.current = data.id;
          setIsTerminated(true);
          setTerminationReason(data.termination_reason || 'Security violation limit exceeded.');
          setSaveStatus('locked');
          setViolationCounts({
            camera: data.camera_warning_count || 0,
            multipleFace: data.multiple_face_warning_count || 0,
            screenShare: data.screen_share_warning_count || 0,
            fullscreen: data.fullscreen_warning_count || 0,
            tabSwitch: data.tab_switch_warning_count || 0,
          });
          setLoading(false);
          return;
        }

        setAttempt(data);
        attemptIdRef.current = data.id;
        setViolationCounts({
          camera: data.camera_warning_count || 0,
          multipleFace: data.multiple_face_warning_count || 0,
          screenShare: data.screen_share_warning_count || 0,
          fullscreen: data.fullscreen_warning_count || 0,
          tabSwitch: data.tab_switch_warning_count || 0,
        });

        // Populate initial answers
        const formattedAnswers: Record<number, number[]> = {};
        if (data.answers) {
          Object.entries(data.answers).forEach(([qId, optIds]) => {
            formattedAnswers[Number(qId)] = optIds;
          });
        }
        setAnswers(formattedAnswers);

        // Compute remaining time
        const deadline = new Date(data.server_deadline).getTime();
        const diff = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
        setRemainingSeconds(diff);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to initialize assessment session.');
      } finally {
        setLoading(false);
      }
    };

    initAttempt();
  }, [assessmentId, location.state, navigate]);

  // 2. Initialize camera feed in exam room (hardware or simulated canvas stream)
  const initCameraFeed = useCallback(async () => {
    try {
      if (location.state?.isSimulatedCamera) {
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 240;
        const ctx = canvas.getContext('2d');
        let frame = 0;
        const interval = setInterval(() => {
          if (!ctx) return;
          frame++;
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(0, 0, 320, 240);
          ctx.fillStyle = '#334155';
          ctx.beginPath();
          ctx.ellipse(160, 190, 60, 45, 0, 0, Math.PI * 2);
          ctx.fill();
          // Candidate face with realistic skin tone for optical validation
          ctx.fillStyle = '#d4976a';
          ctx.beginPath();
          ctx.arc(160, 100, 35, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = 1.5;
          ctx.strokeRect(110, 60, 100, 110);
          ctx.fillStyle = '#38bdf8';
          ctx.font = '10px sans-serif';
          ctx.fillText('FXEC CANDIDATE', 10, 20);
          if (frame % 2 === 0) {
            ctx.fillStyle = '#ef4444';
            ctx.beginPath();
            ctx.arc(300, 15, 4, 0, Math.PI * 2);
            ctx.fill();
          }
        }, 300);
        simCleanupRef.current = () => clearInterval(interval);
        const stream = (canvas as any).captureStream ? (canvas as any).captureStream(30) : null;
        if (stream) {
          setCameraStream(stream);
        }
      } else if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 320 }, height: { ideal: 240 } },
          audio: false
        });
        setCameraStream(stream);

        // Listen for hardware camera disconnect
        const track = stream.getVideoTracks()[0];
        if (track) {
          track.onended = () => {
            setCameraStream(null);
            handleSecuritySignal('CAMERA_DISCONNECTED', 'CRITICAL', { reason: 'Webcam video track ended' });
          };
        }
      }
    } catch {
      handleSecuritySignal('CAMERA_UNAVAILABLE', 'HIGH', { reason: 'Failed to access camera device' });
    }
  }, [location.state]);

  useEffect(() => {
    initCameraFeed();

    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach((t) => t.stop());
      }
      if (screenStream) {
        screenStream.getTracks().forEach((t) => t.stop());
      }
      if (simCleanupRef.current) {
        simCleanupRef.current();
      }
    };
  }, []);

  // Synchronize pip video ref
  useEffect(() => {
    if (videoPipRef.current && cameraStream) {
      videoPipRef.current.srcObject = cameraStream;
      videoPipRef.current.play().catch(() => {});
    }
  }, [cameraStream]);

  // 3. Centralized Server-Authoritative Security Event Processor
  const handleSecuritySignal = useCallback(async (eventType: string, severity: string, details: any = {}) => {
    const activeAttemptId = attemptIdRef.current;
    if (!activeAttemptId || hasAutoSubmittedRef.current) return;

    try {
      const res = await apiClient.post(`/assessments/attempts/${activeAttemptId}/events/`, {
        event_type: eventType,
        severity,
        details: {
          ...details,
          timestamp: new Date().toISOString()
        }
      });

      const data = res.data;

      // Update current risk tier
      if (data.risk_tier) {
        setCurrentRiskTier(data.risk_tier);
      }

      // 1. TERMINATION CONDITION
      if (data.is_terminated || data.action_taken === 'AUTO_TERMINATE' || data.attempt_status === 'TERMINATED_SECURITY_VIOLATION') {
        hasAutoSubmittedRef.current = true;
        setIsTerminated(true);
        setSaveStatus('locked');
        setActiveWarning(null);
        setTerminationReason(
          data.termination_reason || 'Assessment terminated due to repeated security infractions.'
        );
        return;
      }

      // 2. WARNING CONDITION (Warning 1 or 2)
      if (data.action_taken === 'WARNING_ISSUED') {
        const warningType = data.warning_type || 'General';
        const currentCount = data.current_warning_count || 1;
        const maxWarnings = data.max_warnings || 2;

        // Update violation counters
        setViolationCounts((prev) => ({
          ...prev,
          [warningType]: currentCount
        }));

        let msg = `A security policy violation (${eventType.replace(/_/g, ' ')}) has been detected.`;
        if (eventType.includes('CAMERA') || eventType.includes('BLANK')) {
          msg = 'Webcam feed disconnected, blocked, or blank. Candidate must maintain an unobstructed, illuminated camera view.';
        } else if (eventType.includes('MULTIPLE_FACES')) {
          msg = 'Multiple faces detected in candidate camera frame. Candidates must remain alone throughout the examination. (Note: Assessment will NOT close, but this violation is recorded).';
        } else if (eventType.includes('MOBILE')) {
          msg = 'Unauthorized mobile phone detected in candidate vicinity. Smartphones and handheld electronic devices are strictly prohibited.';
        } else if (eventType.includes('AI')) {
          msg = 'External AI assistance or clipboard operation detected. AI prompt generation and external answer pasting are strictly prohibited.';
        } else if (eventType.includes('FACE_NOT')) {
          msg = 'No candidate face detected in camera viewport. Candidate must remain centered with clear illumination.';
        } else if (eventType.includes('SCREEN')) {
          msg = 'Screen sharing stream was stopped. Examination policies require continuous display sharing.';
        } else if (eventType.includes('FULLSCREEN')) {
          msg = 'Fullscreen mode exited. Please return to fullscreen view immediately.';
        } else if (eventType.includes('TAB') || eventType.includes('BLUR')) {
          msg = 'Tab switch or window blur detected. Do not navigate away from the examination viewport.';
        }

        setActiveWarning({
          eventType,
          warningType,
          currentCount,
          maxWarnings,
          message: msg
        });
      }
    } catch (err: any) {
      // If server returns 403 (already terminated), lock session
      if (err.response?.status === 403 && err.response?.data?.status === 'TERMINATED_SECURITY_VIOLATION') {
        setIsTerminated(true);
        setSaveStatus('locked');
        setTerminationReason(err.response.data.termination_reason || 'Assessment terminated by proctoring engine.');
      }
    }
  }, []);

  // Reconnection / Remediation actions
  const reEnterFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      handleSecuritySignal('FULLSCREEN_RESTORED', 'INFO', { action: 'Manual user restore' });
      setActiveWarning(null);
    } catch (err) {
      console.warn('Fullscreen request rejected', err);
    }
  }, [handleSecuritySignal]);

  const reconnectCamera = useCallback(async () => {
    await initCameraFeed();
    handleSecuritySignal('CAMERA_RECONNECTED', 'INFO', { action: 'Manual camera reconnect' });
    setActiveWarning(null);
    setContinuousAlert((curr) => (curr?.type === 'CAMERA_CLOSED' || curr?.type === 'NO_FACE_BLANK' ? null : curr));
  }, [initCameraFeed, handleSecuritySignal]);

  const enableScreenShare = useCallback(async () => {
    try {
      if (!navigator.mediaDevices?.getDisplayMedia) return;
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      setScreenStream(stream);
      setScreenActive(true);
      stream.getVideoTracks()[0].onended = () => {
        setScreenActive(false);
        setScreenStream(null);
        handleSecuritySignal('SCREEN_SHARE_STOPPED', 'CRITICAL', { reason: 'Screen share ended' });
      };
      handleSecuritySignal('SCREEN_SHARE_RESUMED', 'INFO', { action: 'Manual screen share resume' });
      setActiveWarning(null);
    } catch {
      // Ignored
    }
  }, [handleSecuritySignal]);

  // 4. Multi-layer monitoring loops: Live Face Verification, Camera State, Blank/Mobile Check & Anti-AI
  useEffect(() => {
    if (isTerminated) return;

    // A. Real-time Face Verification, Blank Check & Mobile Detection Loop (Every 1.2s)
    const faceCheckInterval = setInterval(async () => {
      if (isTerminated) return;

      // 1. Camera active check: if stream ended, missing, or tracks disabled
      const isTrackActive = cameraStream && cameraStream.getVideoTracks().some(t => t.readyState === 'live' && t.enabled);
      if (!cameraStream || !isTrackActive) {
        setLiveFaceState('CAMERA_CLOSED');
        setContinuousAlert({
          type: 'CAMERA_CLOSED',
          title: 'CAMERA FEED DISCONNECTED / CLOSED',
          message: 'Your webcam feed is stopped or closed. Examination guidelines mandate continuous camera monitoring.',
          actionLabel: 'Reconnect Camera Feed',
          onAction: reconnectCamera
        });
        return;
      }

      if (!videoPipRef.current) return;

      try {
        const result = await faceDetectorRef.current.detectFaces(videoPipRef.current);

        // 1. Camera Blank, Dark, or Covered by Hand Check (Immediate warning if camera blank)
        if (result.debouncedBlankCamera || result.isCameraBlank) {
          setLiveFaceState('NO_FACE_BLANK');
          setContinuousAlert({
            type: 'NO_FACE_BLANK',
            title: 'CAMERA BLANK / COVERED DETECTED',
            message: 'Your camera feed is BLANK, dark, or covered! Please uncover the camera lens, ensure adequate lighting, and keep your face visible.',
            actionLabel: 'Check Camera',
            onAction: reconnectCamera
          });
          if (result.debouncedBlankCamera) {
            handleSecuritySignal('CAMERA_COVERED_BLANK', 'HIGH', {
              reason: 'Camera feed is blank, dark, or covered by hand/object'
            });
          }
        } 
        // 2. No Candidate Face Detected / Empty Camera View Check
        else if (result.debouncedZeroFaces || result.faceCount === 0 || !result.singleFaceConfirmed) {
          setLiveFaceState('NO_FACE_BLANK');
          setContinuousAlert({
            type: 'NO_FACE_BLANK',
            title: 'NO FACE DETECTED / CAMERA BLANK',
            message: 'No candidate face detected in camera view! Examination guidelines require your face to remain clearly visible at all times.',
            actionLabel: 'Check Camera',
            onAction: reconnectCamera
          });
          if (result.debouncedZeroFaces) {
            handleSecuritySignal('FACE_NOT_DETECTED', 'MEDIUM', {
              reason: 'No candidate face detected in webcam view'
            });
          }
        }
        // 3. Normal Verified State (camera unobstructed and candidate face confirmed)
        else {
          setLiveFaceState('CONFIRMED_SINGLE_FACE');
          // Clear active proctoring visual alerts
          setContinuousAlert((curr) => {
            if (curr && (curr.type === 'NO_FACE_BLANK' || curr.type === 'CAMERA_CLOSED')) {
              return null;
            }
            return curr;
          });
        }
      } catch {
        // Optical CV fallback
      }
    }, 1200);

    // B. Anti-AI and Clipboard Interception (Copying questions to AI tools / pasting AI answers)
    const handleCopy = (e: ClipboardEvent) => {
      if (isTerminated) return;
      e.preventDefault();
      setContinuousAlert({
        type: 'AI_TOOL',
        title: 'AI PROMPT COPYING PROHIBITED',
        message: 'Copying assessment questions to external AI tools (ChatGPT, Claude, Gemini) is strictly forbidden.'
      });
      handleSecuritySignal('AI_ASSISTANCE_DETECTED', 'HIGH', {
        reason: 'Candidate attempted to copy question text to clipboard for AI prompting'
      });
    };

    const handlePaste = (e: ClipboardEvent) => {
      if (isTerminated) return;
      e.preventDefault();
      setContinuousAlert({
        type: 'AI_TOOL',
        title: 'EXTERNAL AI PASTE PROHIBITED',
        message: 'Pasting external content or AI-generated answers into the examination session is blocked.'
      });
      handleSecuritySignal('AI_ASSISTANCE_DETECTED', 'HIGH', {
        reason: 'Candidate attempted to paste external clipboard content'
      });
    };

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
    };

    // C. Tab Visibility Change Listener
    const handleVisibilityChange = () => {
      if (isTerminated) return;
      if (document.hidden) {
        handleSecuritySignal('TAB_SWITCH', 'CRITICAL', {
          reason: 'Document visibility changed to hidden (candidate switched tabs)'
        });
      } else {
        handleSecuritySignal('TAB_RESTORED', 'INFO', {
          reason: 'Document visibility returned to visible'
        });
      }
    };

    // D. Fullscreen Change Listener
    const handleFullscreenChange = () => {
      if (isTerminated) return;
      if (!document.fullscreenElement) {
        handleSecuritySignal('FULLSCREEN_EXIT', 'CRITICAL', {
          reason: 'Document exited fullscreen viewport'
        });
      } else {
        handleSecuritySignal('FULLSCREEN_RESTORED', 'INFO', {
          reason: 'Document restored to fullscreen viewport'
        });
      }
    };

    // E. Window Blur Listener
    const handleWindowBlur = () => {
      if (isTerminated) return;
      handleSecuritySignal('WINDOW_BLUR', 'HIGH', {
        reason: 'Window onblur event fired'
      });
    };

    document.addEventListener('copy', handleCopy);
    document.addEventListener('paste', handlePaste);
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    window.addEventListener('blur', handleWindowBlur);

    return () => {
      clearInterval(faceCheckInterval);
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('paste', handlePaste);
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      window.removeEventListener('blur', handleWindowBlur);
    };
  }, [cameraStream, isTerminated, handleSecuritySignal, reconnectCamera]);

  // 5. Submit handler (manual completion)
  const handleSubmit = useCallback(async () => {
    const activeAttemptId = attemptIdRef.current;
    if (!activeAttemptId || submitting || isTerminated) return;

    setSubmitting(true);
    try {
      const res = await apiClient.post(`/assessments/attempts/${activeAttemptId}/submit/`, {
        answers
      });
      navigate(`/assessments/${activeAttemptId}/result`, {
        state: { result: res.data },
        replace: true
      });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Submission failed. Please contact your faculty mentor.');
      setSubmitting(false);
      setShowSubmitModal(false);
    }
  }, [navigate, submitting, isTerminated, answers]);

  // 6. Server-authoritative timer
  useEffect(() => {
    if (remainingSeconds === null || isTerminated) return;

    if (remainingSeconds <= 0) {
      handleSubmit();
      return;
    }

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer);
          handleSubmit();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [remainingSeconds, handleSubmit, isTerminated]);

  // 7. Option selection and Autosave (Strictly blocked if terminated)
  const handleOptionSelect = async (questionId: number, optionId: number, isMultiple: boolean) => {
    const activeAttemptId = attemptIdRef.current;
    if (!activeAttemptId || isTerminated) return;

    let updatedOptionIds: number[] = [];
    const currentSelected = answers[questionId] || [];

    if (isMultiple) {
      if (currentSelected.includes(optionId)) {
        updatedOptionIds = currentSelected.filter((id) => id !== optionId);
      } else {
        updatedOptionIds = [...currentSelected, optionId];
      }
    } else {
      updatedOptionIds = [optionId];
    }

    setAnswers((prev) => ({
      ...prev,
      [questionId]: updatedOptionIds
    }));

    setSaveStatus('saving');
    try {
      await apiClient.post(`/assessments/attempts/${activeAttemptId}/answers/`, {
        question_id: questionId,
        selected_option_id: updatedOptionIds[0] ?? null,
        option_ids: updatedOptionIds
      });
      setSaveStatus('saved');
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.status === 'TERMINATED_SECURITY_VIOLATION') {
        setIsTerminated(true);
        setSaveStatus('locked');
        setTerminationReason(err.response.data.termination_reason || 'Attempt terminated.');
      } else {
        setSaveStatus('error');
      }
    }
  };



  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-[80vh] flex flex-col items-center justify-center space-y-4">
        <div className="w-10 h-10 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-xs text-slate-500 font-medium">Securing examination environment...</p>
      </div>
    );
  }

  if (error || !attempt) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-red-100 text-red-700 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Session Error</h2>
        <p className="text-xs text-slate-600">{error || 'Assessment attempt could not be loaded.'}</p>
        <button
          onClick={() => navigate('/catalogue')}
          className="px-4 py-2 bg-primary-900 text-white rounded-lg text-xs font-semibold"
        >
          Return to Course Catalogue
        </button>
      </div>
    );
  }

  const questions = attempt.questions || [];
  const currentQuestion: Question | undefined = questions[currentIndex];
  const totalQuestions = questions.length;
  const answeredCount = Object.keys(answers).filter((k) => (answers[Number(k)] || []).length > 0).length;

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 flex flex-col relative select-none">
      {/* Top Authoritative Banner */}
      <header className="bg-primary-950 text-white px-6 py-3 border-b border-primary-900 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`w-2.5 h-2.5 rounded-full ${isTerminated ? 'bg-red-500' : 'bg-emerald-400 animate-pulse'}`}></span>
            <div>
              <h1 className="text-sm font-bold tracking-tight">{attempt.assessment.title}</h1>
              <p className="text-[10px] text-primary-300">
                Francis Xavier Engineering College • Multi-Layer Proctoring Active ({currentRiskTier})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Autosave Status */}
            <div className="hidden sm:flex items-center gap-1.5 text-[11px]">
              {isTerminated ? (
                <span className="text-red-400 font-bold flex items-center gap-1">
                  <Lock className="w-3.5 h-3.5" /> Answers Locked
                </span>
              ) : saveStatus === 'saved' ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Answers saved
                </span>
              ) : saveStatus === 'saving' ? (
                <span className="text-accent-300 animate-pulse flex items-center gap-1">
                  Saving...
                </span>
              ) : (
                <span className="text-red-400 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" /> Save failed
                </span>
              )}
            </div>

            {/* Countdown Clock */}
            <div className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-mono text-sm font-bold border ${
              isTerminated 
                ? 'bg-slate-800 text-slate-400 border-slate-700'
                : (remainingSeconds || 0) < 300 
                  ? 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse' 
                  : 'bg-primary-900/60 text-accent-300 border-primary-800'
            }`}>
              <Clock className="w-4 h-4" />
              <span>{remainingSeconds !== null ? formatTimer(remainingSeconds) : '--:--'}</span>
            </div>

            {/* Fullscreen Lock Icon */}
            <button
              onClick={reEnterFullscreen}
              title="Maintain fullscreen mode"
              className="p-1.5 text-primary-300 hover:text-white rounded hover:bg-primary-900/80 transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
            </button>

            {/* Finish Button */}
            {!isTerminated && (
              <button
                onClick={() => setShowSubmitModal(true)}
                className="px-4 py-1.5 bg-accent-400 hover:bg-accent-300 text-primary-950 text-xs font-bold rounded-lg shadow transition-all flex items-center gap-1.5"
              >
                <span>Submit</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Multi-layer Safeguard Ribbon */}
      <div className={`px-6 py-1.5 text-center text-xs font-bold shadow-inner flex items-center justify-center gap-2 ${
        isTerminated ? 'bg-red-700 text-white' : 'bg-primary-900 text-primary-100'
      }`}>
        <ShieldAlert className="w-4 h-4 shrink-0" />
        <span>
          {isTerminated
            ? 'SESSION TERMINATED: Security violation threshold exceeded. Further actions locked.'
            : 'MULTI-LAYER MONITORING: Camera, Face Verification, Fullscreen & Window Focus Active.'}
        </span>
      </div>

      {/* Main Examination Layout */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 flex-grow grid grid-cols-1 lg:grid-cols-4 gap-6 pb-28">
        {/* Question Content Area (Col 1-3) */}
        <div className="lg:col-span-3 space-y-6">
          {/* CONTINUOUS REAL-TIME PROCTORING ALERT BANNER */}
          {continuousAlert && !isTerminated && (
            <div className={`p-4 sm:p-5 rounded-2xl border-2 shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all animate-pulse-subtle ${
              continuousAlert.type === 'MOBILE_DETECTED' || continuousAlert.type === 'AI_TOOL'
                ? 'bg-purple-50 border-purple-600 text-purple-950 shadow-purple-500/10'
                : 'bg-rose-50 border-rose-500 text-rose-950 shadow-rose-500/10'
            }`}>
              <div className="flex items-start gap-3.5">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  continuousAlert.type === 'CAMERA_CLOSED' || continuousAlert.type === 'NO_FACE_BLANK' ? 'bg-rose-200 text-rose-900' :
                  'bg-purple-200 text-purple-900'
                }`}>
                  {(continuousAlert.type === 'CAMERA_CLOSED' || continuousAlert.type === 'NO_FACE_BLANK') && <EyeOff className="w-5 h-5 animate-pulse" />}
                  {continuousAlert.type === 'MOBILE_DETECTED' && <Smartphone className="w-5 h-5 animate-pulse" />}
                  {continuousAlert.type === 'AI_TOOL' && <Sparkles className="w-5 h-5 animate-pulse" />}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black tracking-wider uppercase px-2 py-0.5 rounded bg-black/10">
                      LIVE PROCTOR WARNING
                    </span>
                    <h4 className="text-sm font-black">{continuousAlert.title}</h4>
                  </div>
                  <p className="text-xs font-medium leading-relaxed opacity-90">
                    {continuousAlert.message}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0 w-full sm:w-auto">
                {continuousAlert.onAction && (
                  <button
                    onClick={continuousAlert.onAction}
                    className="w-full sm:w-auto px-4 py-2 bg-slate-900 hover:bg-black text-white text-xs font-bold rounded-xl transition-all shadow flex items-center justify-center gap-1.5"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>{continuousAlert.actionLabel || 'Reconnect'}</span>
                  </button>
                )}
                <button
                  onClick={() => setContinuousAlert(null)}
                  className="w-full sm:w-auto px-3 py-2 bg-white/70 hover:bg-white text-slate-800 text-xs font-semibold rounded-xl border border-black/10 transition-colors"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {currentQuestion ? (
            <div className={`bg-white rounded-2xl border shadow-sm p-6 sm:p-8 space-y-6 transition-all ${
              isTerminated ? 'border-red-300 opacity-60 pointer-events-none' : 'border-slate-200'
            }`}>
              {/* Question Meta Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold bg-primary-50 text-primary-900 px-3 py-1 rounded-md">
                    Question {currentIndex + 1} of {totalQuestions}
                  </span>
                  <span className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2.5 py-1 rounded-md">
                    Topic: {currentQuestion.topic_tag}
                  </span>
                </div>
                <div className="text-xs font-bold text-slate-500">
                  {currentQuestion.marks} Mark{currentQuestion.marks > 1 ? 's' : ''}
                </div>
              </div>

              {/* Question Text */}
              <div className="text-base sm:text-lg font-medium text-slate-900 leading-relaxed">
                {currentQuestion.text}
              </div>

              {/* Options List */}
              <div className="space-y-3 pt-2">
                {currentQuestion.options.map((option) => {
                  const isSelected = (answers[currentQuestion.id] || []).includes(option.id);
                  const isMultiple = currentQuestion.question_type === 'MULTIPLE_CHOICE';

                  return (
                    <div
                      key={option.id}
                      onClick={() => !isTerminated && handleOptionSelect(currentQuestion.id, option.id, isMultiple)}
                      className={`p-4 rounded-xl border text-sm font-medium transition-all cursor-pointer flex items-center gap-3.5 select-none ${
                        isSelected
                          ? 'border-primary-900 bg-primary-50/50 text-primary-950 ring-1 ring-primary-900'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div
                        className={`w-5 h-5 flex items-center justify-center rounded transition-colors ${
                          isMultiple ? 'rounded-md' : 'rounded-full'
                        } ${
                          isSelected
                            ? 'bg-primary-900 text-white'
                            : 'border border-slate-300 bg-white'
                        }`}
                      >
                        {isSelected && (
                          <div className={isMultiple ? 'text-[10px] font-bold' : 'w-2 h-2 rounded-full bg-white'} />
                        )}
                      </div>
                      <span className="flex-grow">{option.text}</span>
                    </div>
                  );
                })}
              </div>

              {/* Navigation Bar */}
              <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
                  disabled={currentIndex === 0}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Previous
                </button>

                {currentIndex < totalQuestions - 1 ? (
                  <button
                    onClick={() => setCurrentIndex((prev) => Math.min(totalQuestions - 1, prev + 1))}
                    className="px-5 py-2 bg-primary-900 hover:bg-primary-800 text-white rounded-lg text-xs font-bold shadow-sm transition-all flex items-center gap-1.5"
                  >
                    Next <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    onClick={() => setShowSubmitModal(true)}
                    disabled={isTerminated}
                    className="px-6 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg text-xs font-bold shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
                  >
                    Review &amp; Submit <CheckCircle2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 bg-white rounded-2xl border text-center text-slate-500">
              No questions found for this assessment.
            </div>
          )}
        </div>

        {/* Question Palette Sidebar (Col 4) */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Question Navigator
            </h3>

            <div className="grid grid-cols-5 gap-2 pt-2">
              {questions.map((q, idx) => {
                const isAnswered = (answers[q.id] || []).length > 0;
                const isCurrent = idx === currentIndex;

                return (
                  <button
                    key={q.id}
                    onClick={() => setCurrentIndex(idx)}
                    className={`h-9 rounded-lg text-xs font-bold transition-all flex items-center justify-center border ${
                      isCurrent
                        ? 'ring-2 ring-primary-900 border-primary-900'
                        : ''
                    } ${
                      isAnswered
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
                    }`}
                  >
                    {idx + 1}
                  </button>
                );
              })}
            </div>

            <div className="pt-4 border-t border-slate-100 space-y-2 text-[11px] text-slate-500">
              <div className="flex items-center justify-between">
                <span>Total Questions:</span>
                <span className="font-bold text-slate-900">{totalQuestions}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Answered:</span>
                <span className="font-bold text-emerald-600">{answeredCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Unanswered:</span>
                <span className="font-bold text-slate-400">{totalQuestions - answeredCount}</span>
              </div>
            </div>
          </div>

            {/* Security Counters Card */}
          <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200 space-y-3 text-xs text-slate-600">
            <div className="flex items-center gap-1.5 font-bold text-primary-950">
              <HelpCircle className="w-4 h-4 text-primary-800" />
              Proctoring Security Status
            </div>

            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between pb-1 mb-1 border-b border-slate-200/60">
                <span>Screen Stream:</span>
                <span className={`font-bold ${screenActive ? 'text-emerald-600' : 'text-slate-500'}`}>
                  {screenActive ? 'Active' : 'Standby'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Camera Warnings:</span>
                <span className={`font-mono font-bold ${violationCounts.camera > 0 ? 'text-amber-600' : 'text-slate-700'}`}>
                  {violationCounts.camera} / 2
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Multiple Faces:</span>
                <span className={`font-mono font-bold ${violationCounts.multipleFace > 0 ? 'text-amber-600' : 'text-slate-700'}`}>
                  {violationCounts.multipleFace} (Active Warn)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Screen Share Warnings:</span>
                <span className={`font-mono font-bold ${violationCounts.screenShare > 0 ? 'text-amber-600' : 'text-slate-700'}`}>
                  {violationCounts.screenShare} / 2
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Fullscreen Warnings:</span>
                <span className={`font-mono font-bold ${violationCounts.fullscreen > 0 ? 'text-amber-600' : 'text-slate-700'}`}>
                  {violationCounts.fullscreen} / 2
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Tab Switch Warnings:</span>
                <span className={`font-mono font-bold ${violationCounts.tabSwitch > 0 ? 'text-amber-600' : 'text-slate-700'}`}>
                  {violationCounts.tabSwitch} / 2
                </span>
              </div>
            </div>
            <p className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-200">
              *Security guidelines: 3rd critical warning on camera disconnect or tab switch terminates session.
            </p>
          </div>
        </div>
      </div>

      {/* Floating Picture-In-Picture Proctoring Webcam Feed */}
      <div className={`fixed bottom-4 right-4 z-40 bg-slate-950 rounded-2xl p-2.5 shadow-2xl border-2 transition-all flex flex-col items-center gap-1.5 w-52 ${
        liveFaceState === 'CONFIRMED_SINGLE_FACE'
          ? 'border-emerald-500 shadow-emerald-950/40 ring-1 ring-emerald-500/50'
          : 'border-rose-500 shadow-rose-950/50 animate-pulse'
      }`}>
        <div className="w-full flex items-center justify-between px-1 text-[10px] font-mono font-bold">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${
              liveFaceState === 'CONFIRMED_SINGLE_FACE' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500 animate-ping'
            }`}></span>
            <span className="text-slate-200">LIVE PROCTOR</span>
          </span>
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-sans">
            AI Guard
          </span>
        </div>

        <div className="w-full h-28 rounded-xl overflow-hidden bg-black relative flex items-center justify-center">
          <video 
            ref={videoPipRef} 
            autoPlay 
            playsInline 
            muted 
            className={`w-full h-full object-cover ${!cameraStream ? 'opacity-20' : ''}`} 
          />

          {/* Verification Status Overlay Badge */}
          <div className="absolute top-2 left-2 right-2 flex items-center justify-between pointer-events-none">
            {liveFaceState === 'CONFIRMED_SINGLE_FACE' && (
              <span className="px-2 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-500/80 text-emerald-300 text-[10px] font-bold flex items-center gap-1 backdrop-blur-xs">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                Candidate Verified
              </span>
            )}
            {liveFaceState === 'NO_FACE_BLANK' && (
              <span className="px-2 py-0.5 rounded-md bg-rose-950/90 border border-rose-500 text-rose-300 text-[10px] font-bold flex items-center gap-1 backdrop-blur-xs animate-pulse">
                <EyeOff className="w-3 h-3 text-rose-400" />
                ⚠️ Camera Blank / Covered
              </span>
            )}
            {liveFaceState === 'CAMERA_CLOSED' && (
              <span className="px-2 py-0.5 rounded-md bg-rose-950/90 border border-rose-500 text-rose-300 text-[10px] font-bold flex items-center gap-1 backdrop-blur-xs animate-pulse">
                <Camera className="w-3 h-3 text-rose-400" />
                ⚠️ Camera Closed
              </span>
            )}
          </div>

          {/* Quick Reconnect Overlay if camera closed */}
          {!cameraStream && (
            <div className="absolute inset-0 bg-slate-950/80 flex flex-col items-center justify-center p-2 text-center">
              <Camera className="w-6 h-6 text-rose-400 mb-1 animate-pulse" />
              <p className="text-[10px] text-rose-300 font-bold">Camera Feed Inactive</p>
              <button
                onClick={reconnectCamera}
                className="mt-1.5 px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded text-[10px] font-bold transition-all shadow"
              >
                Reconnect
              </button>
            </div>
          )}
        </div>

        <div className="w-full flex items-center justify-between px-1 text-[9px]">
          <span className={`font-semibold tracking-wider uppercase ${
            liveFaceState === 'CONFIRMED_SINGLE_FACE' ? 'text-emerald-400' : 'text-rose-400 font-bold'
          }`}>
            {liveFaceState === 'CONFIRMED_SINGLE_FACE' ? 'Candidate Verified' :
             liveFaceState === 'NO_FACE_BLANK' ? 'Warning: Camera Blank / Covered' :
             'Warning: Camera Inactive'}
          </span>
          <button 
            onClick={reconnectCamera} 
            title="Refresh Camera" 
            className="text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-2.5 h-2.5" />
          </button>
        </div>
      </div>

      {/* NON-DESTRUCTIVE SECURITY WARNING MODAL (Warning 1 of 2 or 2 of 2) */}
      {activeWarning && !isTerminated && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 space-y-5 shadow-2xl border-2 border-amber-400">
            <div className="w-14 h-14 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center mx-auto">
              <ShieldAlert className="w-8 h-8" />
            </div>

            <div className="text-center space-y-1.5">
              <div className="inline-block px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-xs font-black uppercase tracking-wider">
                Warning {activeWarning.currentCount} of {activeWarning.maxWarnings}
              </div>
              <h3 className="text-lg font-extrabold text-slate-900">
                Security Policy Alert
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed pt-1">
                {activeWarning.message}
              </p>
            </div>

            <div className="p-3.5 bg-amber-50 rounded-xl border border-amber-200 text-[11px] text-amber-900 space-y-1">
              <strong>Notice:</strong> Answers submitted prior to this alert remain saved. However, reaching 
              the 3rd violation will permanently terminate your examination.
            </div>

            <div className="space-y-2 pt-2">
              {activeWarning.eventType.includes('CAMERA') && (
                <button
                  onClick={reconnectCamera}
                  className="w-full py-2.5 px-4 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                >
                  <Camera className="w-4 h-4 text-accent-400" />
                  <span>Reconnect Camera Feed</span>
                </button>
              )}

              {activeWarning.eventType.includes('FULLSCREEN') && (
                <button
                  onClick={reEnterFullscreen}
                  className="w-full py-2.5 px-4 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                >
                  <Maximize2 className="w-4 h-4 text-accent-400" />
                  <span>Return to Fullscreen</span>
                </button>
              )}

              {activeWarning.eventType.includes('SCREEN') && (
                <button
                  onClick={enableScreenShare}
                  className="w-full py-2.5 px-4 bg-primary-900 hover:bg-primary-800 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2"
                >
                  <Monitor className="w-4 h-4 text-accent-400" />
                  <span>Resume Screen Sharing</span>
                </button>
              )}

              <button
                onClick={() => setActiveWarning(null)}
                className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors"
              >
                I Understand &amp; Acknowledge Warning
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AUTO-TERMINATION FULLSCREEN OVERLAY (Shown on 3rd violation or server termination) */}
      {isTerminated && (
        <div className="fixed inset-0 z-50 bg-red-950/90 backdrop-blur-md flex items-center justify-center p-6 text-center animate-fade-in">
          <div className="bg-white rounded-3xl max-w-lg w-full p-8 space-y-6 shadow-2xl border-4 border-red-500">
            <div className="w-16 h-16 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto animate-bounce">
              <Lock className="w-9 h-9" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-black text-slate-900 tracking-tight">
                ASSESSMENT TERMINATED: SECURITY LIMIT EXCEEDED
              </h2>
              <p className="text-xs text-red-600 font-bold">
                {terminationReason || 'Security violation limit exceeded.'}
              </p>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              In accordance with Francis Xavier Engineering College autonomous academic integrity guidelines, repeated security infractions automatically terminate candidate examination sessions. Answers submitted up to the termination timestamp have been evaluated and locked.
            </p>

            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-left space-y-2 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Violation Breakdown
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-700">
                <div>Camera Disconnections: <strong>{violationCounts.camera}</strong></div>
                <div>Multiple Face Alerts: <strong>{violationCounts.multipleFace}</strong></div>
                <div>Screen Share Drops: <strong>{violationCounts.screenShare}</strong></div>
                <div>Fullscreen Exits: <strong>{violationCounts.fullscreen}</strong></div>
                <div className="col-span-2">Tab Switches: <strong>{violationCounts.tabSwitch}</strong></div>
              </div>
            </div>

            <button
              onClick={() => {
                const activeId = attemptIdRef.current || attempt.id;
                navigate(`/assessments/${activeId}/result`, { replace: true });
              }}
              className="w-full py-3 px-6 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <span>View Examination Results &amp; Integrity Summary</span>
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Manual Submission Confirmation Modal */}
      {showSubmitModal && !isTerminated && (
        <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl border border-slate-100">
            <h3 className="text-base font-bold text-slate-900">
              Confirm Assessment Submission
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              You have answered <span className="font-bold text-primary-900">{answeredCount}</span> out of{' '}
              <span className="font-bold text-slate-900">{totalQuestions}</span> questions. Once submitted, your answers will be finalized, evaluated, and sent for faculty review.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-5 py-2 bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold rounded-lg shadow transition-all disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Yes, Submit Exam'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
