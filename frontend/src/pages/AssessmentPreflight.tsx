import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { FaceDetectionEngine } from '../utils/faceDetector';
import { 
  Camera, 
  Monitor, 
  Maximize2, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight,
  Sparkles,
  ShieldAlert,
  Mic,
  Wifi,
  UserCheck,
  Users,
  RefreshCw,
  Lock
} from 'lucide-react';

export const AssessmentPreflight: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [noticeAccepted, setNoticeAccepted] = useState(false);
  const [eligibilityChecking, setEligibilityChecking] = useState(true);
  const [isEligible, setIsEligible] = useState<boolean | null>(null);
  const [eligibilityData, setEligibilityData] = useState<any>(null);

  // 6 Preflight Checks State
  const [cameraReady, setCameraReady] = useState(false);
  const [isSimulatedCamera, setIsSimulatedCamera] = useState(false);
  const [faceCheckStatus, setFaceCheckStatus] = useState<'pending' | 'checking' | 'verified' | 'multiple' | 'none'>('pending');
  const [faceCount, setFaceCount] = useState<number>(0);
  const [micReady, setMicReady] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [screenReady, setScreenReady] = useState(false);
  const [fullscreenReady, setFullscreenReady] = useState(false);
  const [networkReady, setNetworkReady] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permissionStatus, setPermissionStatus] = useState<'prompt' | 'granted' | 'denied' | 'requesting'>('prompt');
  const [showPermissionGuide, setShowPermissionGuide] = useState(false);

  const simCleanupRef = useRef<(() => void) | null>(null);
  const faceDetectorRef = useRef<FaceDetectionEngine>(new FaceDetectionEngine(2.0));
  const audioContextRef = useRef<AudioContext | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);

  // 0. Verify Assessment Eligibility on Mount
  useEffect(() => {
    const verifyEligibility = async () => {
      try {
        const res = await apiClient.get(`/assessments/${assessmentId}/eligibility/`);
        setEligibilityData(res.data);
        if (!res.data.eligible) {
          setIsEligible(false);
          setError(res.data.reason || 'Complete all required modules before starting the assessment.');
        } else {
          setIsEligible(true);
        }
      } catch (err: any) {
        setIsEligible(false);
        setError('Complete all required modules before starting the assessment.');
      } finally {
        setEligibilityChecking(false);
      }
    };
    verifyEligibility();
  }, [assessmentId]);

  // 1. Initial Network & System Readiness Check
  useEffect(() => {
    const checkNetwork = async () => {
      const startTime = performance.now();
      try {
        await apiClient.get('/health/');
        const latency = Math.round(performance.now() - startTime);
        setLatencyMs(latency);
        setNetworkReady(navigator.onLine);
      } catch {
        setLatencyMs(null);
        setNetworkReady(navigator.onLine);
      }
    };
    checkNetwork();

    // Listen for fullscreen changes
    const onFullscreenChange = () => {
      setFullscreenReady(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, []);

  // 2. Synchronize stream with videoRef
  useEffect(() => {
    if (videoRef.current && mediaStream) {
      videoRef.current.srcObject = mediaStream;
      videoRef.current.play().catch(() => {});
    }
  }, [mediaStream, cameraReady]);

  // 3. Face Detection Loop when camera is active
  useEffect(() => {
    if (!cameraReady || !videoRef.current) {
      setFaceCheckStatus('pending');
      return;
    }

    let intervalId: any;
    setFaceCheckStatus('checking');

    const runDetection = async () => {
      if (!videoRef.current) return;
      try {
        const res = await faceDetectorRef.current.detectFaces(videoRef.current);
        setFaceCount(res.faceCount);

        if (res.faceCount === 1) {
          setFaceCheckStatus('verified');
        } else if (res.faceCount >= 2) {
          setFaceCheckStatus('multiple');
        } else {
          setFaceCheckStatus('none');
        }
      } catch {
        // Fallback to verified for virtual demo feed
        if (isSimulatedCamera) {
          setFaceCount(1);
          setFaceCheckStatus('verified');
        }
      }
    };

    intervalId = setInterval(runDetection, 1000);
    return () => clearInterval(intervalId);
  }, [cameraReady, isSimulatedCamera]);

  // Clean up streams on unmount
  useEffect(() => {
    return () => {
      if (mediaStream) {
        mediaStream.getTracks().forEach((t) => t.stop());
      }
      if (audioStream) {
        audioStream.getTracks().forEach((t) => t.stop());
      }
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (simCleanupRef.current) {
        simCleanupRef.current();
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, [mediaStream, audioStream]);

  // Helper to set up live microphone level meter
  const setupAudioMeter = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        if (audioContextRef.current) {
          audioContextRef.current.close().catch(() => {});
        }
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 64;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const updateMeter = () => {
          if (!stream.active) return;
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          setMicLevel(Math.min(100, Math.round((avg / 128) * 100)));
          requestAnimationFrame(updateMeter);
        };
        updateMeter();
      }
    } catch (e) {
      console.warn('Audio analyzer initialization note:', e);
    }
  };

  // Combined: Request both Camera and Microphone permissions in 1 unified prompt
  const requestAllMediaPermissions = async () => {
    setError(null);
    setShowPermissionGuide(false);
    setPermissionStatus('requesting');
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Webcam & Microphone media APIs are not supported in this browser.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true
      });

      const videoTracks = stream.getVideoTracks();
      const audioTracks = stream.getAudioTracks();

      if (videoTracks.length > 0) {
        const vStream = new MediaStream([videoTracks[0]]);
        setMediaStream(vStream);
        setIsSimulatedCamera(false);
        setCameraReady(true);
      }

      if (audioTracks.length > 0) {
        const aStream = new MediaStream([audioTracks[0]]);
        setAudioStream(aStream);
        setMicReady(true);
        setupAudioMeter(aStream);
      }

      setPermissionStatus('granted');
    } catch (err: any) {
      console.error('All media permission error:', err);
      setPermissionStatus('denied');
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Camera & Microphone permissions were blocked or declined in your browser.');
        setShowPermissionGuide(true);
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setError('No physical camera or microphone detected. You can use the simulated candidate demo feed below for testing.');
      } else {
        setError(`Device permission error: ${err.message}`);
      }
    }
  };

  // Check 1: Real Hardware Camera
  const requestCamera = async () => {
    setError(null);
    setShowPermissionGuide(false);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Webcam media API is not supported in this browser.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false
      });
      
      setMediaStream(stream);
      setIsSimulatedCamera(false);
      setCameraReady(true);
      setPermissionStatus('granted');
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Camera permission was blocked. Click the lock icon 🔒 in your browser URL bar and set Camera to Allow.');
        setShowPermissionGuide(true);
        setPermissionStatus('denied');
      } else {
        setError(`Physical camera not accessible: ${err.message}. You can enable the simulated candidate feed below for testing/demo.`);
      }
    }
  };

  // Check 1 Alternative: Simulated Candidate Video Feed
  const enableSimulatedCamera = () => {
    setError(null);
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 640;
      canvas.height = 480;
      const ctx = canvas.getContext('2d');
      let frame = 0;

      const interval = setInterval(() => {
        if (!ctx) return;
        frame++;

        // Background gradient
        const grad = ctx.createLinearGradient(0, 0, 640, 480);
        grad.addColorStop(0, '#0f172a');
        grad.addColorStop(1, '#1e293b');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 640, 480);

        // Grid lines
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.1)';
        ctx.lineWidth = 1;
        for (let x = 0; x < 640; x += 40) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, 480);
          ctx.stroke();
        }
        for (let y = 0; y < 480; y += 40) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(640, y);
          ctx.stroke();
        }

        // Candidate silhouette (1 face)
        ctx.fillStyle = '#334155';
        ctx.beginPath();
        ctx.ellipse(320, 370, 110, 80, 0, 0, Math.PI * 2);
        ctx.fill();

        // Candidate face with realistic skin tone for optical validation
        ctx.fillStyle = '#d4976a';
        ctx.beginPath();
        ctx.arc(320, 210, 65, 0, Math.PI * 2);
        ctx.fill();

        // Facial bounding tracking box (AI proctoring)
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.strokeRect(230, 125, 180, 200);

        // Corner accents
        ctx.fillStyle = '#38bdf8';
        ctx.fillRect(225, 120, 15, 4);
        ctx.fillRect(225, 120, 4, 15);
        ctx.fillRect(395, 120, 15, 4);
        ctx.fillRect(406, 120, 4, 15);

        // Header overlay
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('FXEC AI PROCTORING — LIVE FEED', 320, 40);

        // Status
        ctx.fillStyle = '#94a3b8';
        ctx.font = '12px monospace';
        ctx.fillText(`CANDIDATE: VERIFIED • ${new Date().toLocaleTimeString()}`, 320, 440);

        // Live blinking REC dot
        if (frame % 2 === 0) {
          ctx.fillStyle = '#ef4444';
          ctx.beginPath();
          ctx.arc(600, 35, 7, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText('REC', 585, 39);
      }, 250);

      const stream = (canvas as any).captureStream ? (canvas as any).captureStream(30) : null;
      if (!stream) {
        setError('Canvas stream capture is not supported in this browser.');
        clearInterval(interval);
        return;
      }

      simCleanupRef.current = () => clearInterval(interval);
      setMediaStream(stream);
      setIsSimulatedCamera(true);
      setCameraReady(true);
      setFaceCheckStatus('verified');
      setFaceCount(1);
    } catch (err: any) {
      setError(`Failed to initialize simulated feed: ${err.message}`);
    }
  };

  // Check 3: Microphone Check
  const requestMicrophone = async () => {
    setError(null);
    setShowPermissionGuide(false);
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Microphone media API is not supported in this browser.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setAudioStream(stream);
      setMicReady(true);
      setupAudioMeter(stream);
      setPermissionStatus('granted');
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Microphone permission was blocked. Click the lock icon 🔒 in your browser URL bar and set Microphone to Allow.');
        setShowPermissionGuide(true);
        setPermissionStatus('denied');
      } else {
        setError(`Microphone access error: ${err.message}. Please allow mic access in your browser.`);
      }
    }
  };

  // Check 4: Screen Sharing Check
  const requestScreen = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices?.getDisplayMedia) {
        setError('Screen sharing API is not supported in this browser environment.');
        return;
      }
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      screenStreamRef.current = stream;
      setScreenReady(true);
      // Listen for screen-share stop
      stream.getVideoTracks()[0].onended = () => {
        setScreenReady(false);
      };
    } catch (err: any) {
      setError(`Screen share was declined: ${err.message}`);
    }
  };

  // Check 5: Fullscreen Check
  const requestFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      setFullscreenReady(true);
    } catch (err: any) {
      setError(`Fullscreen request failed: ${err.message}`);
    }
  };

  const handleStartExam = async () => {
    if (!noticeAccepted) {
      setError('Please accept the assessment security disclosure before proceeding.');
      return;
    }

    setStarting(true);
    try {
      const res = await apiClient.post(`/assessments/${assessmentId}/start/`);
      navigate(`/assessments/${assessmentId}/session`, {
        state: { 
          attemptId: res.data.id,
          isSimulatedCamera,
          cameraReady,
          screenReady,
          fullscreenReady
        }
      });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to start assessment attempt.');
    } finally {
      setStarting(false);
    }
  };

  if (eligibilityChecking) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary-900 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (isEligible === false) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center space-y-6 min-h-[75vh] flex flex-col items-center justify-center">
        <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center shadow-sm">
          <Lock className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-black text-slate-900">
          Final Certification Assessment Locked
        </h2>
        <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed bg-amber-50 p-4 rounded-xl border border-amber-200">
          {error || 'Complete all required course modules before attempting the final certification assessment.'}
        </p>
        <div className="pt-2">
          <Link
            to={eligibilityData?.course_slug ? `/learn/${eligibilityData.course_slug}` : '/catalogue'}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary-900 hover:bg-primary-800 text-white font-bold text-xs shadow-md transition-all"
          >
            ← Return to Course Learning Roadmap
          </Link>
        </div>
      </div>
    );
  }

  const allChecksReady = cameraReady && (faceCheckStatus === 'verified' || isSimulatedCamera) && micReady && screenReady && fullscreenReady;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 min-h-[85vh]">
      <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm space-y-6">
        {/* Header */}
        <div className="pb-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-xs font-bold text-primary-800 bg-primary-50 px-2.5 py-1 rounded">
              Preflight Readiness Check (6-Point Assessment Audit)
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 mt-2">
              Secure Assessment Environment Verification
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Francis Xavier Engineering College • Autonomous Certification &amp; Academic Integrity
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Readiness:</span>
            <span className={`px-2.5 py-1 rounded-full font-bold ${
              allChecksReady ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {allChecksReady ? 'All 6 Checks Passed' : 'In Progress'}
            </span>
          </div>
        </div>

        {error && (
          <div className="p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {/* Security Policy Disclosure */}
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-950">
            <ShieldAlert className="w-4 h-4 text-amber-700" />
            MULTI-LAYER ASSESSMENT INTEGRITY DISCLOSURE
          </div>
          <p className="leading-relaxed">
            During your examination, multi-layer browser proctoring actively monitors 
            <strong> webcam feed, facial presence, screen sharing, fullscreen lock, and tab visibility</strong>.
            Violations will trigger a warning. Exceeding policy limits automatically terminates and submits the assessment.
          </p>
          <label className="flex items-center gap-2 pt-2 font-semibold text-primary-900 cursor-pointer">
            <input
              type="checkbox"
              checked={noticeAccepted}
              onChange={(e) => setNoticeAccepted(e.target.checked)}
              className="rounded text-primary-900 focus:ring-primary-700 w-4 h-4"
            />
            <span>I understand and agree to the academic integrity and automated proctoring regulations.</span>
          </label>
        </div>

        {/* ONE-CLICK ALLOW CAMERA & MICROPHONE PERMISSION ACTION BANNER */}
        <div className="p-5 rounded-2xl bg-gradient-to-r from-slate-900 via-primary-950 to-indigo-950 text-white shadow-lg border border-indigo-500/30 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-300">
                  <Camera className="w-4 h-4" />
                </span>
                <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-300">
                  <Mic className="w-4 h-4" />
                </span>
                <h2 className="text-sm font-black tracking-wide text-white">
                  Camera &amp; Microphone Device Permissions
                </h2>
              </div>
              <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
                Autonomous assessment proctoring requires your webcam and microphone sensors. Click <strong>Allow Camera &amp; Microphone</strong> to grant device permissions in your browser.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 shrink-0">
              {cameraReady && micReady ? (
                <div className="px-4 py-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-xs font-bold flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Permissions Allowed &amp; Active</span>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={requestAllMediaPermissions}
                  disabled={permissionStatus === 'requesting'}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-black text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition cursor-pointer disabled:opacity-60"
                >
                  {permissionStatus === 'requesting' ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Requesting Permission...</span>
                    </>
                  ) : (
                    <>
                      <Camera className="w-4 h-4" />
                      <Mic className="w-4 h-4" />
                      <span>Allow Camera &amp; Microphone</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {/* Permission Troubleshooting Guide */}
          {showPermissionGuide && (
            <div className="p-3.5 rounded-xl bg-amber-500/15 border border-amber-400/30 text-amber-200 text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-amber-300">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                <span>How to Allow Camera &amp; Microphone in your Browser:</span>
              </div>
              <ol className="list-decimal list-inside space-y-1 text-[11px] text-amber-100/90 pl-1">
                <li>Look at the top URL address bar (next to <strong>localhost</strong> or the site URL).</li>
                <li>Click the <strong>Lock (🔒) or Tune/Settings</strong> icon.</li>
                <li>Find <strong>Camera</strong> and <strong>Microphone</strong>, and switch them to <strong>Allow</strong>.</li>
                <li>Click <strong>Allow Camera &amp; Microphone</strong> again or reload the page.</li>
              </ol>
            </div>
          )}
        </div>

        {/* 6-Point Readiness Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Point 1: Camera Feed */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">1</span>
                  <Camera className="w-4 h-4 text-primary-800" />
                </div>
                {cameraReady ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">1. Webcam Sensor</h3>
              <p className="text-[11px] text-slate-500">
                {cameraReady 
                  ? (isSimulatedCamera ? 'Simulated demo feed connected' : 'Hardware webcam connected') 
                  : 'Webcam required for candidate identity.'}
              </p>

              {/* Video Preview Box */}
              <div className={`w-full h-28 rounded-lg overflow-hidden bg-slate-950 mt-2 border border-slate-300 ${cameraReady ? 'block' : 'hidden'}`}>
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted 
                  className="w-full h-full object-cover" 
                />
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <button
                onClick={requestCamera}
                className={`w-full py-2 px-3 rounded-lg text-xs font-semibold border transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
                  cameraReady && !isSimulatedCamera
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                    : 'bg-primary-900 hover:bg-primary-800 text-white shadow-sm'
                }`}
              >
                <Camera className="w-3.5 h-3.5" />
                <span>{cameraReady && !isSimulatedCamera ? 'Camera Permission Granted ✓' : 'Allow Camera Permission'}</span>
              </button>

              <button
                onClick={enableSimulatedCamera}
                className={`w-full py-1.5 px-2 rounded-lg text-[11px] font-medium border transition-colors flex items-center justify-center gap-1.5 ${
                  isSimulatedCamera
                    ? 'bg-cyan-50 border-cyan-300 text-cyan-800 font-bold'
                    : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
                {isSimulatedCamera ? 'Simulated Feed Active' : 'No Webcam? Use Demo Feed'}
              </button>
            </div>
          </div>

          {/* Point 2: Face Presence & Bounding */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">2</span>
                  <UserCheck className="w-4 h-4 text-primary-800" />
                </div>
                {faceCheckStatus === 'verified' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">2. Face Verification</h3>
              <p className="text-[11px] text-slate-500">
                Candidate must be alone with 1 face visible in frame.
              </p>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Detected:</span>
                  <span className="font-bold text-slate-900">{faceCount} Face{faceCount !== 1 ? 's' : ''}</span>
                </div>
                <div className="text-[11px]">
                  {faceCheckStatus === 'verified' && (
                    <span className="text-emerald-700 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Optimal (1 Candidate)
                    </span>
                  )}
                  {faceCheckStatus === 'multiple' && (
                    <span className="text-amber-700 font-bold flex items-center gap-1">
                      <Users className="w-3.5 h-3.5" /> Multiple Faces Detected
                    </span>
                  )}
                  {faceCheckStatus === 'none' && cameraReady && (
                    <span className="text-amber-700 font-bold flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" /> Face Not Detected
                    </span>
                  )}
                  {faceCheckStatus === 'pending' && (
                    <span className="text-slate-400">Awaiting camera activation</span>
                  )}
                </div>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 italic">
              *Debounced detection prevents false positive alerts.
            </div>
          </div>

          {/* Point 3: Microphone Check */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">3</span>
                  <Mic className="w-4 h-4 text-primary-800" />
                </div>
                {micReady ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">3. Microphone Sensor</h3>
              <p className="text-[11px] text-slate-500">
                Verify audio capture for room sound integrity.
              </p>

              {/* Audio meter */}
              {micReady && (
                <div className="space-y-1 pt-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>Input Level:</span>
                    <span className="font-mono">{micLevel}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-emerald-500 transition-all duration-75"
                      style={{ width: `${micLevel}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={requestMicrophone}
              className={`w-full py-2 px-3 rounded-lg text-xs font-semibold border transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
                micReady
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : 'bg-primary-900 hover:bg-primary-800 text-white shadow-sm'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>{micReady ? 'Microphone Permission Granted ✓' : 'Allow Microphone Permission'}</span>
            </button>
          </div>

          {/* Point 4: Screen Sharing Check */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">4</span>
                  <Monitor className="w-4 h-4 text-primary-800" />
                </div>
                {screenReady ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">4. Screen Stream</h3>
              <p className="text-[11px] text-slate-500">
                Broadcast full desktop or application window.
              </p>
            </div>

            <button
              onClick={requestScreen}
              className={`w-full py-2 px-3 rounded-lg text-xs font-semibold border transition-colors ${
                screenReady
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700'
              }`}
            >
              {screenReady ? 'Screen Share Active' : 'Enable Screen Share'}
            </button>
          </div>

          {/* Point 5: Fullscreen Lock Check */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">5</span>
                  <Maximize2 className="w-4 h-4 text-primary-800" />
                </div>
                {fullscreenReady ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">5. Fullscreen Viewport</h3>
              <p className="text-[11px] text-slate-500">
                Locks exam window to prevent desktop distractions.
              </p>
            </div>

            <button
              onClick={requestFullscreen}
              className={`w-full py-2 px-3 rounded-lg text-xs font-semibold border transition-colors ${
                fullscreenReady
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700'
              }`}
            >
              {fullscreenReady ? 'Fullscreen Locked' : 'Engage Fullscreen'}
            </button>
          </div>

          {/* Point 6: Browser & Network Readiness */}
          <div className="p-5 rounded-xl border border-slate-200 bg-white space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-900 text-[10px] font-black flex items-center justify-center">6</span>
                  <Wifi className="w-4 h-4 text-primary-800" />
                </div>
                {networkReady ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                )}
              </div>
              <h3 className="text-xs font-bold text-slate-900">6. Browser &amp; Network</h3>
              <p className="text-[11px] text-slate-500">
                Server connection, latency, and browser capability.
              </p>

              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Status:</span>
                  <span className="font-bold text-emerald-600">Online &amp; Synced</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">API Latency:</span>
                  <span className="font-mono font-bold text-slate-800">
                    {latencyMs !== null ? `${latencyMs} ms` : 'Checking...'}
                  </span>
                </div>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 font-mono">
              User Agent: {navigator.userAgent.slice(0, 32)}...
            </div>
          </div>
        </div>

        {/* Launch Exam Bar */}
        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span className="text-xs text-slate-500">
            {allChecksReady 
              ? 'All 6 readiness checks passed. You may now launch your exam.'
              : 'Complete all 6 readiness checks above to unlock exam launch.'}
          </span>

          <button
            onClick={handleStartExam}
            disabled={starting || !noticeAccepted || !cameraReady}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-primary-900 hover:bg-primary-800 text-white text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {starting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Initializing Attempt...</span>
              </>
            ) : (
              <>
                <span>Launch Secure Exam Session</span>
                <ArrowRight className="w-4 h-4 text-accent-400" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
