import { useState, useEffect, useRef, useCallback } from "react";
import { m, AnimatePresence } from "framer-motion";
import CodeDemo from "../CodeDemo";
import AptitudeTest from "../AptitudeTest";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";
import { InterviewAgentService } from "../../services/interviewAgent";
import { saveLog } from "../../services/conversationLog";
import { fetchCodingQuestion, MOCK_CODING_QUESTION, insertCodingScore, insertAptitudeScore, type DynamicCodingQuestion } from "../../services/interviewApi";
import { VideoConfidenceRecorder } from "../../services/videoConfidenceService";
import type { ExamGuardState } from "../../hooks/useExamGuard";
import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  Phone,
  Sparkles,
  User,
  Lightbulb,
  Clock,
  MessageSquare,
  Code,
  Brain,
  X,
  Camera,
  Loader,
  AlertTriangle,
  Wifi,
  Send,
  Captions,
  Shield,
  Eye,
} from "lucide-react";


export default function InterviewRoom({ config, sessionId, onEnd, examGuard }: { config: any; sessionId: string; onEnd: () => void; examGuard: ExamGuardState }) {
  const [isMicOn, setIsMicOn] = useState(config.useAudio);
  const [isCameraOn, setIsCameraOn] = useState(config.useVideo);
  const [showCodeCompiler, setShowCodeCompiler] = useState(false);
  const [showAptitude, setShowAptitude] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(config.duration * 60);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [showSubtitles, setShowSubtitles] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [typedMessage, setTypedMessage] = useState("");
  const [proctorStatus, setProctorStatus] = useState<string | null>(null);
  const [proctorViolations, setProctorvViolations] = useState<Array<{ time: Date; violation: string }>>([]);
  const [showProctorHistory, setShowProctorHistory] = useState(false);
  const [dynamicCodingQuestion, setDynamicCodingQuestion] = useState<DynamicCodingQuestion | null>(null);

  /* ----------- Sync tab-switch violations into proctoring log ----------- */
  const lastSyncedCount = useRef(0);
  useEffect(() => {
    if (examGuard.violations.length > lastSyncedCount.current) {
      const newViolations = examGuard.violations.slice(lastSyncedCount.current);
      lastSyncedCount.current = examGuard.violations.length;
      setProctorvViolations((prev) => [
        ...prev,
        ...newViolations.map((v) => ({ time: v.time, violation: v.violation })),
      ]);
    }
  }, [examGuard.violations]);

  /* ----------- End handler: save log then notify parent ----------- */
  const handleEndInterview = useCallback(async () => {
    // Stop video confidence recording
    videoConfidenceRef.current?.stop();
    videoConfidenceRef.current = null;

    try {
      await saveLog(
        sessionId ?? `session-${Date.now()}`,
        {
          role: config.role ?? "Unknown",
          interviewType: config.interviewType ?? "mixed",
          difficulty: config.difficulty ?? "medium",
        },
        chatMessages
      );
    } catch (err) {
      console.warn("[InterviewRoom] Failed to save log:", err);
    }
    onEnd();
  }, [sessionId, config, chatMessages, onEnd]);

  /* ----------- Agent (WebSocket + TTS) ----------- */
  const agentRef = useRef<InterviewAgentService | null>(null);
  const [agentConnected, setAgentConnected] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<string | null>(null);

  /* ----------- Silence-detection buffer ----------- */
  // Accumulates speech segments; fires sendSpeech after SILENCE_MS of no new words.
  const SILENCE_MS = 3000; // ms of silence before sending to agent
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const speechBufferRef = useRef<string>("");

  /* ----------- Audio capture (MediaRecorder) ----------- */
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  /* ----------- Video Confidence Recorder ----------- */
  const videoConfidenceRef = useRef<VideoConfidenceRecorder | null>(null);

  const startRecording = useCallback((stream: MediaStream) => {
    try {
      // Guard: only record if the stream has at least one live audio track
      const audioTracks = stream.getAudioTracks().filter(t => t.readyState === "live" && t.enabled);
      if (audioTracks.length === 0) {
        console.warn("[MediaRecorder] No live audio tracks — skipping recording.");
        return;
      }

      // If already recording, don't start another
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        return;
      }

      // Create a stream with only the audio tracks for recording
      const audioOnlyStream = new MediaStream(audioTracks);

      // Prefer opus codec; fall back to browser default
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const mr = new MediaRecorder(audioOnlyStream, mimeType ? { mimeType } : undefined);
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mr.start(200); // collect every 200 ms
      mediaRecorderRef.current = mr;
    } catch (err) {
      console.warn("[MediaRecorder] Could not start recording:", err);
    }
  }, []);

  const stopRecordingAsBlob = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const mr = mediaRecorderRef.current;
      if (!mr || mr.state === "inactive") { resolve(null); return; }
      mr.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mr.mimeType || "audio/webm" });
        audioChunksRef.current = [];
        mediaRecorderRef.current = null;
        resolve(blob.size > 500 ? blob : null); // ignore near-empty recordings
      };
      mr.stop();
    });
  }, []);

  /* ----------- Speech-to-Text ----------- */

  // Called while the user is actively mid-sentence (interim results).
  // Cancel the silence timer so we don't trigger while they're still talking.
  const handleInterimTranscript = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const handleFinalTranscript = useCallback((text: string) => {
    // Always show the segment in the transcript immediately
    setChatMessages((prev) => [
      ...prev,
      { text, sender: "user", time: new Date(), fromSpeech: true },
    ]);

    // Append to buffer
    speechBufferRef.current = (speechBufferRef.current + " " + text).trim();

    // (Re)start the silence countdown — only fires if user stays quiet
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = setTimeout(async () => {
      const fullAnswer = speechBufferRef.current.trim();
      // —— Clear buffer immediately so any late STT chunks go to the NEXT answer ——
      speechBufferRef.current = "";
      silenceTimerRef.current = null;
      if (!fullAnswer) return;

      // Stop recording and grab the blob, then send both to the agent
      const audioBlob = await stopRecordingAsBlob();
      agentRef.current?.sendSpeechWithAudio(fullAnswer, audioBlob);
    }, SILENCE_MS);
  }, [stopRecordingAsBlob]);

  const {
    status: sttStatus,
    interimText,
    finalText: _sttFinalText,
    start: startStt,
    stop: stopStt,
    isSupported: isSttSupported,
  } = useSpeechRecognition({
    onInterim: handleInterimTranscript,
    onFinal: handleFinalTranscript,
    continuous: true,
    lang: "en-US",
  });

  // Media states
  const hasGrantedBefore = localStorage.getItem("mockmate-media-granted") === "true";
  const [showPermissionPrompt, setShowPermissionPrompt] = useState(!hasGrantedBefore);
  const [permissionsGranted, setPermissionsGranted] = useState(false);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [isLoadingMedia, setIsLoadingMedia] = useState(false);

  // Device settings
  const [selectedMicrophone, setSelectedMicrophone] = useState<string>("");
  const [selectedCamera, setSelectedCamera] = useState<string>("");
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);

  /* ---------------- Devices ---------------- */

  const enumerateDevices = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices.filter((d) => d.kind === "audioinput");
      const videoInputs = devices.filter((d) => d.kind === "videoinput");
      setAudioDevices(audioInputs);
      setVideoDevices(videoInputs);
      if (audioInputs.length > 0 && !selectedMicrophone) setSelectedMicrophone(audioInputs[0].deviceId);
      if (videoInputs.length > 0 && !selectedCamera) setSelectedCamera(videoInputs[0].deviceId);
    } catch (err) {
      console.error("Failed to enumerate devices:", err);
    }
  };

  /* ---------------- Permissions ---------------- */

  const requestPermissions = async () => {
    setIsLoadingMedia(true);
    setMediaError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: config.useVideo
          ? {
            width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user",
            deviceId: selectedCamera ? { exact: selectedCamera } : undefined
          }
          : false,
        audio: config.useAudio
          ? {
            echoCancellation: true, noiseSuppression: true, autoGainControl: true,
            deviceId: selectedMicrophone ? { exact: selectedMicrophone } : undefined
          }
          : false,
      });
      setMediaStream(stream);
      setPermissionsGranted(true);
      setShowPermissionPrompt(false);
      setIsLoadingMedia(false);
      localStorage.setItem("mockmate-media-granted", "true");
      await enumerateDevices();
    } catch (err: any) {
      setIsLoadingMedia(false);
      let errorMessage = "Failed to access camera/microphone";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError")
        errorMessage = "Permission denied. Please allow camera and microphone access in your browser settings.";
      else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError")
        errorMessage = "No camera or microphone found. Please connect a device and try again.";
      else if (err.name === "NotReadableError" || err.name === "TrackStartError")
        errorMessage = "Camera/microphone is already in use by another application.";
      setMediaError(errorMessage);
    }
  };

  /* ---------------- Effects ---------------- */

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
      // Stop video confidence recording on unmount
      videoConfidenceRef.current?.stop();
      videoConfidenceRef.current = null;
    };
  }, [mediaStream]);

  // Auto-request if previously granted
  useEffect(() => {
    if (localStorage.getItem("mockmate-media-granted") === "true") requestPermissions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Camera track toggle
  useEffect(() => {
    if (!mediaStream) return;
    const track = mediaStream.getVideoTracks()[0];
    if (track) track.enabled = isCameraOn;
  }, [isCameraOn, mediaStream]);

  // Mic track toggle — also control STT
  useEffect(() => {
    if (!mediaStream) return;
    mediaStream.getAudioTracks().forEach(track => { track.enabled = isMicOn; });

    if (isMicOn && isSttSupported) {
      startStt();
    } else {
      stopStt();
    }
  }, [isMicOn, mediaStream, isSttSupported, startStt, stopStt]);

  // —— Echo cancellation & Task Isolation: pause STT while agent is speaking or in task ——
  const isPauseStt = isAgentSpeaking || showAptitude || showCodeCompiler;

  useEffect(() => {
    if (!isMicOn || !isSttSupported) return;

    if (isPauseStt) {
      // Agent started speaking or task opened → mute STT + cancel any pending silence trigger
      stopStt();
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      speechBufferRef.current = "";
      // Also stop any ongoing recording (discard — this was TTS echo, not the user)
      const mr = mediaRecorderRef.current;
      if (mr && mr.state !== "inactive") {
        mr.onstop = null; // discard chunks
        mr.stop();
        audioChunksRef.current = [];
        mediaRecorderRef.current = null;
      }
    } else {
      // Agent/task stopped → wait 600 ms for audio to decay, then re-open mic + start recording
      const resume = setTimeout(() => {
        if (isMicOn && mediaStream) {
          startStt();
          startRecording(mediaStream); // begin capturing the user's answer
        }
      }, 600);
      return () => clearTimeout(resume);
    }
  }, [isPauseStt, isMicOn, isSttSupported, startStt, stopStt, mediaStream, startRecording]);

  // STT recovery watchdog — if STT dies while the user expects it to be on, restart it
  useEffect(() => {
    if (!isMicOn || !isSttSupported || isPauseStt) return;

    const watchdog = setInterval(() => {
      if (sttStatus === "stopped" && isMicOn && !isPauseStt) {
        console.warn("[STT Watchdog] STT died unexpectedly — restarting");
        startStt();
      }
    }, 4000);

    return () => clearInterval(watchdog);
  }, [isMicOn, isSttSupported, isPauseStt, sttStatus, startStt]);

  // Attach stream to video element
  useEffect(() => {
    if (!videoRef.current) return;
    if (!mediaStream || !isCameraOn) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
      return;
    }
    videoRef.current.srcObject = mediaStream;
    videoRef.current.play().catch((err) => console.error("Video play error:", err));
  }, [mediaStream, isCameraOn]);

  // Timer (only after permissions granted)
  useEffect(() => {
    if (!permissionsGranted) return;
    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) { clearInterval(timer); handleEndInterview(); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [handleEndInterview, permissionsGranted]);

  // Connect to backend agent + start STT when permissions granted
  useEffect(() => {
    if (!permissionsGranted) return;

    // Auto-start STT
    if (isMicOn && isSttSupported) startStt();

    // Create and connect the agent WebSocket service
    const sid = sessionId ?? `session-${Date.now()}`;
    const interviewId = config?.interviewId ?? localStorage.getItem("interviewId") ?? "";
    const resolvedCadeId = config?.cadeId ?? localStorage.getItem("intervexa-cade-id") ?? "";
    const agent = new InterviewAgentService(sid, {
      onAgentText: (text) => {
        setChatMessages((prev) => [...prev, { text, sender: "ai", time: new Date() }]);
        setCurrentQuestion(text);
      },
      onSpeakingChange: (speaking) => setIsAgentSpeaking(speaking),
      onEvaluation: (_result) => {
        console.debug("[Agent] Evaluation received", _result);
      },
      onConnectionChange: (connected) => setAgentConnected(connected),
      onError: (msg) => {
        setChatMessages((prev) => [
          ...prev,
          { text: `⚠️ ${msg}`, sender: "ai", time: new Date() },
        ]);
      },
      onAptitudeTask: () => setShowAptitude(true),
      onCodingTask: async () => {
        const codingQuestionId = interviewId || localStorage.getItem("interviewId");
        let question: DynamicCodingQuestion | null = null;
        if (codingQuestionId) {
          question = await fetchCodingQuestion(codingQuestionId);
        }
        // Fallback: if API returned nothing, use the mock question so CodeDemo always renders
        setDynamicCodingQuestion(question ?? MOCK_CODING_QUESTION);
        setShowCodeCompiler(true);
      },
      onInterviewEnd: () => {
        pushAiMessage("The interview session has concluded. Thank you for your time.");
        setTimeout(() => handleEndInterview(), 3000);
      },
      onProctoringAlert: (status) => {
        setProctorStatus(status === "Candidate OK" ? null : status);
        if (status && status !== "Candidate OK") {
          setProctorvViolations((prev) => [...prev, { time: new Date(), violation: status }]);
        }
      },
    }, resolvedCadeId, interviewId);

    agentRef.current = agent;
    agent.connect();

    // Start video confidence recording if camera is on and we have interview credentials
    const cadeId = config?.cadeId ?? localStorage.getItem("intervexa-cade-id");
    if (mediaStream && interviewId && cadeId) {
      const recorder = new VideoConfidenceRecorder();
      videoConfidenceRef.current = recorder;
      recorder.start(mediaStream, interviewId, cadeId);
    }

    return () => {
      agent.disconnect();
      agentRef.current = null;
      // Stop video confidence recording on disconnect
      videoConfidenceRef.current?.stop();
      videoConfidenceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [permissionsGranted]);

  // Proctoring frame capture
  useEffect(() => {
    console.log("[Proctoring] Setup effect triggered. agentConnected:", agentConnected, "isCameraOn:", isCameraOn);
    // Don't check videoRef.current here because it doesn't trigger re-renders
    if (!agentConnected || !isCameraOn) return;

    console.log("[Proctoring] Starting 1FPS frame capture interval");
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = 320;
    canvas.height = 240;

    const interval = setInterval(() => {
      // Check for videoRef inside the interval
      if (videoRef.current && ctx && videoRef.current.readyState >= 2) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.3); // compression to save bandwidth
        agentRef.current?.sendVideoFrame(dataUrl);
      } else {
        console.warn("[Proctoring] Skipping frame — video not ready yet");
      }
    }, 1000); // 1 FPS for proctoring

    return () => {
      console.log("[Proctoring] Stopping frame capture interval");
      clearInterval(interval);
    };
  }, [agentConnected, isCameraOn]);

  /* ---------------- Helpers ---------------- */

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const pushAiMessage = (text: string) => {
    setChatMessages((prev) => [...prev, { text, sender: "ai", time: new Date() }]);
  };

  const handleCodeComplete = (result: any) => {
    if (!result) return;
    const testsInfo = typeof result.tests_total === "number" && typeof result.tests_passed === "number"
      ? `Tests: ${result.tests_passed}/${result.tests_total}.` : "Tests: Completed.";
    const clarityInfo = result.clarity ? `Clarity: ${result.clarity.label} (${result.clarity.score}/100).` : "Clarity: Pending.";
    const statusInfo = result.status ? `Result: ${result.status}.` : "Result: Completed.";
    pushAiMessage(`Great work completing the coding task. ${statusInfo} ${testsInfo} ${clarityInfo}`);

    // Submit coding score to backend
    const interviewId = config?.interviewId ?? localStorage.getItem("interviewId") ?? "";
    const cadeId = config?.cadeId ?? localStorage.getItem("intervexa-cade-id") ?? "";
    if (interviewId && cadeId) {
      insertCodingScore(interviewId, cadeId, {
        status: result.status ?? "completed",
        tests_passed: result.tests_passed ?? 0,
        tests_total: result.tests_total ?? 1,
      }).catch(() => console.warn("[InterviewRoom] insertCodingScore failed"));
    }
  };

  const handleAptitudeComplete = (result: any) => {
    if (!result) return;
    const score = `${result.correctCount}/${result.totalQuestions}`;
    const percent = result.percentage ?? Math.round((result.correctCount / result.totalQuestions) * 100);
    const evaluation = percent >= 85 ? "Excellent performance with strong accuracy."
      : percent >= 70 ? "Solid performance with good fundamentals."
        : percent >= 50 ? "Decent effort — keep practicing."
          : "Keep going — practice will sharpen your aptitude.";
    pushAiMessage(`Aptitude test completed. Score: ${score} (${percent}%). ${evaluation}`);

    // Submit aptitude score to backend
    const interviewId = config?.interviewId ?? localStorage.getItem("interviewId") ?? "";
    const cadeId = config?.cadeId ?? localStorage.getItem("intervexa-cade-id") ?? "";
    if (interviewId && cadeId) {
      insertAptitudeScore(interviewId, cadeId, {
        correct: result.correctCount,
        total: result.totalQuestions,
        percentage: percent,
      }).catch(() => console.warn("[InterviewRoom] insertAptitudeScore failed"));
    }

    try {
      localStorage.setItem("mockmate-aptitude-result", JSON.stringify({
        correctCount: result.correctCount, totalQuestions: result.totalQuestions,
        percentage: percent, completedAt: new Date().toISOString(),
      }));
    } catch { /* ignore */ }
  };

  const handleSend = () => {
    const text = typedMessage.trim();
    if (!text) return;
    setChatMessages((prev) => [...prev, { text, sender: "user", time: new Date() }]);
    setTypedMessage("");
  };

  // Auto-scroll to latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  /* ---------------- Render ---------------- */

  return (
    <div className="flex flex-col w-full h-screen bg-[#020617] text-white overflow-hidden">

      {/* ================= PERMISSION PROMPT ================= */}

      <AnimatePresence>
        {showPermissionPrompt && (
          <m.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm"
          >
            <m.div
              initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
              className="w-full max-w-md p-8 border shadow-2xl bg-slate-900 rounded-2xl border-slate-800"
            >
              <div className="text-center">
                <div className="flex items-center justify-center w-20 h-20 mx-auto mb-6 rounded-full bg-linear-to-br from-blue-500 to-indigo-600">
                  {isLoadingMedia ? <Loader className="w-10 h-10 text-white animate-spin" /> : <Camera className="w-10 h-10 text-white" />}
                </div>
                <h2 className="mb-3 text-2xl font-bold text-white">
                  {isLoadingMedia ? "Requesting Access..." : "Camera & Microphone"}
                </h2>
                {!mediaError ? (
                  <>
                    <p className="mb-6 text-slate-400">
                      Intervexa needs access to your camera and microphone to conduct the interview.
                    </p>
                    <div className="p-4 mb-6 text-left border bg-blue-500/10 border-blue-500/20 rounded-xl">
                      <div className="flex items-start gap-3">
                        <Sparkles className="shrink-0 w-5 h-5 text-blue-400 mt-0.5" />
                        <ul className="space-y-1 text-xs text-slate-400">
                          <li>• Your camera helps analyze body language</li>
                          <li>• Your microphone records your answers</li>
                          <li>• All data is processed securely</li>
                        </ul>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-4 mb-6 border bg-rose-500/10 border-rose-500/20 rounded-xl">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="shrink-0 w-5 h-5 text-rose-400 mt-0.5" />
                      <div className="text-left">
                        <p className="mb-1 text-sm font-medium text-rose-300">Access Denied</p>
                        <p className="text-xs text-slate-400">{mediaError}</p>
                      </div>
                    </div>
                  </div>
                )}
                <div className="flex gap-3">
                  <button
                    onClick={() => { setShowPermissionPrompt(false); handleEndInterview(); }}
                    disabled={isLoadingMedia}
                    className="flex-1 px-4 py-3 font-medium text-white transition-colors rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50"
                  >Cancel</button>
                  <button
                    onClick={requestPermissions}
                    disabled={isLoadingMedia}
                    className="flex-1 px-4 py-3 font-medium text-white transition-colors bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50"
                  >
                    {isLoadingMedia ? "Requesting..." : mediaError ? "Try Again" : "Allow Access"}
                  </button>
                </div>
              </div>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ================= MAIN UI ================= */}

      {permissionsGranted && (
        <>
          {/* ================= HEADER ================= */}

          <header className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#020617]/60 backdrop-blur-md shrink-0">
            <div className="flex items-center gap-2 px-3 py-1 border rounded-full bg-purple-500/10 border-purple-500/20">
              <m.div
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                className="bg-purple-500 rounded-full size-2"
              />
              <span className="text-xs font-medium text-purple-400">Proctoring</span>
            </div>

            <div className="flex items-center gap-6 px-6 py-2 border rounded-full bg-white/5 border-white/10">
              <div className="text-sm font-semibold tracking-wide">
                {({
                  behavioral: "🧠 Behavioral",
                  technical: "⚙️ Technical",
                  mixed: "🔀 Mixed",
                  intro: "👋 Intro",
                  hr: "🤝 HR",
                  coding: "💻 Coding",
                } as Record<string, string>)[config?.interviewType] ?? "📋 Interview"}
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" />
                <span className="font-bold tabular-nums">{formatTime(timeRemaining)}</span>
              </div>
            </div>

            <div className={`flex items-center gap-2 px-3 py-1 border rounded-full transition-colors ${agentConnected
              ? "bg-green-500/10 border-green-500/20"
              : "bg-amber-500/10 border-amber-500/20"
              }`}>
              <div className={`rounded-full size-2 animate-pulse ${agentConnected ? "bg-green-500" : "bg-amber-400"
                }`} />
              <span className={`text-xs font-medium ${agentConnected ? "text-green-400" : "text-amber-400"
                }`}>
                {agentConnected ? "Agent Connected" : "Connecting..."}
              </span>
            </div>
          </header>

          {/* ================= MAIN ================= */}

          <main className="flex flex-1 min-h-0 gap-4 p-4 overflow-hidden">

            {/* LEFT PANEL */}
            <div className="flex flex-col w-[300px] shrink-0 min-h-0 gap-4">

              {/* AI Interviewer */}
              <div className="relative flex flex-col items-center justify-center flex-1 min-h-0 border bg-[#0a0e14] border-white/10 rounded-2xl overflow-hidden">
                <div className="absolute inset-0 pointer-events-none bg-blue-500/5 blur-2xl" />
                <div className={`relative flex items-center justify-center w-16 h-16 mb-3 rounded-full shadow-lg bg-linear-to-br from-blue-500 to-indigo-600 ${isAgentSpeaking ? "animate-pulse" : ""
                  }`}>
                  <Sparkles className="w-8 h-8" />
                </div>
                <div className="flex items-center h-5 gap-1 mb-2">
                  {[0.1, 0.3, 0.2, 0.4, 0.1, 0.3, 0.2].map((delay, i) => (
                    <m.div key={i}
                      animate={isAgentSpeaking ? { height: ["4px", "18px", "4px"] } : { height: "4px" }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut", delay }}
                      className="w-0.5 bg-blue-400 rounded-full" />
                  ))}
                </div>
                <p className="text-xs tracking-widest uppercase text-slate-400">Interviewer</p>
                <p className="text-sm text-white/70">
                  {isAgentSpeaking ? "AI is speaking..." : agentConnected ? "Listening..." : "Connecting..."}
                </p>
              </div>

              {/* Candidate Camera */}
              <div className="relative flex items-center justify-center flex-1 min-h-0 overflow-hidden bg-black border border-white/10 rounded-2xl">
                {isCameraOn && mediaStream ? (
                  <video ref={videoRef} autoPlay playsInline muted
                    className="object-cover w-full h-full" style={{ transform: "scaleX(-1)" }} />
                ) : (
                  <div className="flex flex-col items-center justify-center">
                    <User className="w-14 h-14 text-slate-600" />
                    <p className="text-xs text-slate-400">Camera Off</p>
                  </div>
                )}
                <div className="absolute px-2 py-1 text-xs font-bold rounded-md top-2 left-2 bg-black/60">YOU</div>

                {/* Proctoring Alert Badge */}
                <AnimatePresence>
                  {proctorStatus && (
                    <m.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      className="absolute px-3 py-2 text-xs font-bold rounded-lg top-2 right-2 bg-rose-600/95 text-white backdrop-blur-md border-2 border-rose-300 flex items-center gap-2 shadow-2xl animate-pulse z-20"
                    >
                      <AlertTriangle className="w-4 h-4 animate-bounce" />
                      <div className="flex flex-col">
                        <span className="font-extrabold tracking-wide">⚠️ ALERT</span>
                        <span className="text-[10px] font-semibold">{proctorStatus}</span>
                      </div>
                    </m.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Controls */}
              <div className="flex items-center justify-center gap-2 py-2">
                {/* Mic button with live STT pulse ring */}
                <div className="relative">
                  <button
                    onClick={() => setIsMicOn(!isMicOn)}
                    className="p-2.5 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors relative z-10"
                  >
                    {isMicOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5 text-rose-400" />}
                  </button>
                  {/* Pulse ring while listening */}
                  {sttStatus === "listening" && (
                    <m.span
                      className="absolute inset-0 rounded-full border-2 border-blue-400 pointer-events-none"
                      animate={{ scale: [1, 1.6], opacity: [0.7, 0] }}
                      transition={{ duration: 1.2, repeat: Infinity, ease: "easeOut" }}
                    />
                  )}
                </div>

                <button onClick={() => setIsCameraOn(!isCameraOn)}
                  className="p-2.5 rounded-full bg-slate-800 hover:bg-slate-700 transition-colors">
                  {isCameraOn ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5 text-rose-400" />}
                </button>

                {/* Subtitles toggle */}
                <button
                  onClick={() => setShowSubtitles((v) => !v)}
                  title="Toggle subtitles"
                  className={`p-2.5 rounded-full transition-colors ${showSubtitles ? "bg-blue-600 hover:bg-blue-500" : "bg-slate-800 hover:bg-slate-700"
                    }`}
                >
                  <Captions className="w-5 h-5" />
                </button>

                <button onClick={handleEndInterview}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-bold transition-colors rounded-full bg-rose-600 hover:bg-rose-500">
                  <Phone className="w-4 h-6 rotate-135" />
                  End Interview
                </button>
              </div>

              {/* STT unsupported notice */}
              {!isSttSupported && isMicOn && (
                <p className="text-center text-[10px] text-amber-400/70 pb-1">
                  Live captions unavailable in this browser. Use Chrome or Edge.
                </p>
              )}
            </div>

            {/* RIGHT PANEL */}
            <div className="flex flex-col flex-1 min-w-0 min-h-0 overflow-hidden border bg-slate-900 border-white/10 rounded-2xl">

              {/* Question + Tool Buttons */}
              <div className="flex items-start justify-between gap-4 p-6 border-b border-white/10">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2 text-xs tracking-widest text-blue-400 uppercase">
                    <Lightbulb className="w-4 h-4" />
                    Current Question
                  </div>
                  <p className="text-base font-semibold leading-relaxed">
                    {currentQuestion
                      ? `"${currentQuestion}"`
                      : <span className="text-slate-500 italic text-sm">Waiting for the interviewer to ask a question…</span>}
                  </p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button onClick={() => setShowCodeCompiler(true)}
                    className="flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded-full border bg-slate-800/60 border-slate-700 hover:bg-slate-700 transition-colors whitespace-nowrap">
                    <Code className="w-3.5 h-3.5 text-blue-400" /> Code
                  </button>
                  <button onClick={() => setShowAptitude(true)}
                    className="flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded-full border bg-slate-800/60 border-slate-700 hover:bg-slate-700 transition-colors whitespace-nowrap">
                    <Brain className="w-3.5 h-3.5 text-purple-400" /> Aptitude
                  </button>
                </div>
              </div>

              {/* Transcript */}
              <div className="flex-1 min-h-0 p-6 space-y-4 overflow-y-auto">
                {chatMessages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <MessageSquare className="w-10 h-10 mx-auto mb-3 text-slate-700" />
                      <p className="text-sm text-slate-500">Transcript will appear here</p>
                    </div>
                  </div>
                ) : (
                  chatMessages.map((msg, i) => {
                    const isBot = msg.sender === "ai";
                    return (
                      <div key={i} className={`flex ${isBot ? "justify-start" : "justify-end"}`}>
                        <div className={`max-w-[85%] px-4 py-3 rounded-2xl ${isBot ? "bg-slate-800 border border-white/5" : "bg-blue-600"}`}>
                          <div className="text-[10px] uppercase tracking-widest text-white/50 mb-1">
                            {isBot ? "Interviewer" : "Candidate"}
                          </div>
                          <p className="text-sm leading-relaxed">{msg.text}</p>
                          <span className="mt-1 block text-[11px] text-white/40">
                            {new Date(msg.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Subtitle / Status Bar */}
              <AnimatePresence>
                {/* Mic paused while agent speaks or task is active */}
                {isPauseStt && (
                  <m.div
                    key="agent-speaking"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 6 }}
                    transition={{ duration: 0.2 }}
                    className="mx-4 mb-2 px-4 py-2.5 rounded-xl bg-black/70 border border-amber-500/30 backdrop-blur-sm flex items-center gap-2 shrink-0"
                  >
                    <m.span
                      className="shrink-0 w-2 h-2 rounded-full bg-amber-400"
                      animate={{ opacity: [1, 0.2, 1] }}
                      transition={{ duration: 0.8, repeat: Infinity }}
                    />
                    <p className="text-sm text-amber-300/80 italic">
                      {isAgentSpeaking ? "Agent speaking — mic paused" : "Task active — mic paused"}
                    </p>
                  </m.div>
                )}

                {/* Live candidate subtitles */}
                {!isPauseStt && showSubtitles && (interimText || sttStatus === "listening") && (
                  <m.div
                    key="subtitles"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 6 }}
                    transition={{ duration: 0.2 }}
                    className="mx-4 mb-2 px-4 py-2.5 rounded-xl bg-black/70 border border-blue-500/30 backdrop-blur-sm flex items-start gap-2 shrink-0"
                  >
                    <m.span
                      className="mt-1 shrink-0 w-2 h-2 rounded-full bg-blue-400"
                      animate={{ opacity: [1, 0.2, 1] }}
                      transition={{ duration: 1, repeat: Infinity }}
                    />
                    <p className="text-sm leading-relaxed text-white/90">
                      {interimText || (
                        <span className="italic text-white/40">Listening...</span>
                      )}
                    </p>
                  </m.div>
                )}
              </AnimatePresence>

              {/* Typing Bar */}
              <div className="px-4 py-3 border-t border-white/10 bg-slate-900/60 shrink-0">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={typedMessage}
                    onChange={(e) => setTypedMessage(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder={isMicOn && isSttSupported ? "Speaking... or type here" : "Type a message..."}
                    className="flex-1 bg-slate-800 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!typedMessage.trim()}
                    className="flex items-center justify-center w-10 h-10 transition-colors bg-blue-600 rounded-xl hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </main>
        </>
      )}

      {/* ================= CODE MODAL ================= */}

      <AnimatePresence>
        {showCodeCompiler && (
          <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
            <m.div initial={{ scale: 0.96, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 20 }}
              className="flex flex-col w-[94vw] h-[94vh] max-w-[1400px] bg-[#020617] border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/60 shrink-0">
                <span className="text-sm font-semibold">Code Compiler</span>
                <button onClick={() => { setShowCodeCompiler(false); agentRef.current?.taskCompleted(); }}
                  className="px-3 py-1.5 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-slate-300">
                  Close
                </button>
              </div>
              <div className="flex-1 min-h-0">
                <CodeDemo
                  embedded
                  dynamicQuestion={dynamicCodingQuestion}
                  onReturnToInterview={() => { setShowCodeCompiler(false); agentRef.current?.taskCompleted(); }}
                  onSubmissionComplete={handleCodeComplete}
                />
              </div>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>

      {/* Proctoring Violations History Modal */}
      <AnimatePresence>
        {showProctorHistory && proctorViolations.length > 0 && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowProctorHistory(false)}
            className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          >
            <m.div
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-lg shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="px-6 py-4 bg-gradient-to-r from-rose-600/20 to-rose-600/10 border-b border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-rose-400" />
                  <h3 className="text-lg font-bold text-white">Proctoring Violations</h3>
                </div>
                <button
                  onClick={() => setShowProctorHistory(false)}
                  className="text-slate-400 hover:text-white transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Violations List */}
              <div className="max-h-96 overflow-y-auto space-y-2 p-4">
                {proctorViolations.map((v, idx) => (
                  <m.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-2 flex-1">
                        <span className="text-rose-400 font-bold mt-0.5">⚠️</span>
                        <div>
                          <p className="font-semibold text-white">{v.violation}</p>
                          <p className="text-xs text-slate-400 mt-1">
                            {v.time.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </m.div>
                ))}
              </div>

              {/* Summary */}
              <div className="px-6 py-3 bg-slate-800/50 border-t border-slate-700">
                <p className="text-sm text-slate-300">
                  Total violations: <span className="font-bold text-rose-400">{proctorViolations.length}</span>
                </p>
              </div>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ================= APTITUDE MODAL ================= */}

      <AnimatePresence>
        {showAptitude && (
          <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
            <m.div initial={{ scale: 0.96, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 20 }}
              className="flex flex-col w-[94vw] h-[94vh] max-w-[1400px] bg-[#020617] border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/60 shrink-0">
                <span className="text-sm font-semibold">Aptitude Test</span>
                <button onClick={() => { setShowAptitude(false); agentRef.current?.taskCompleted(); }}
                  className="px-3 py-1.5 text-xs font-semibold rounded bg-slate-800 hover:bg-slate-700 text-slate-300">
                  Close
                </button>
              </div>
              <div className="flex-1 min-h-0">
                <AptitudeTest embedded onComplete={handleAptitudeComplete} />
              </div>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ================= TAB-SWITCH WARNING OVERLAY ================= */}

      <AnimatePresence>
        {examGuard.showWarning && (
          <m.div
            key="tab-switch-warning"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md"
          >
            <m.div
              initial={{ scale: 0.8, y: 40 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.8, y: 40 }}
              transition={{ type: "spring", damping: 20, stiffness: 300 }}
              className="relative w-full max-w-lg mx-4 overflow-hidden border shadow-2xl rounded-2xl border-rose-500/40 bg-gradient-to-b from-slate-900 to-slate-950"
            >
              {/* Animated danger stripe */}
              <m.div
                className="h-1.5 bg-gradient-to-r from-rose-600 via-amber-500 to-rose-600"
                animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                style={{ backgroundSize: "200% 200%" }}
              />

              <div className="p-8 text-center">
                {/* Pulsing shield icon */}
                <m.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  className="flex items-center justify-center w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-rose-600 to-rose-800 shadow-lg shadow-rose-500/30"
                >
                  <Shield className="w-10 h-10 text-white" />
                </m.div>

                <h2 className="mb-2 text-2xl font-extrabold text-white">
                  ⚠️ Tab Switch Detected
                </h2>
                <p className="mb-5 text-sm leading-relaxed text-slate-400">
                  Switching tabs, windows, or applications during the interview is
                  <strong className="text-rose-300"> not allowed</strong>. This
                  activity has been recorded and flagged by the proctoring system.
                </p>

                {/* Violation count badge */}
                <div className="inline-flex items-center gap-2 px-4 py-2 mb-6 text-sm font-semibold border rounded-full bg-rose-500/15 border-rose-500/30 text-rose-300">
                  <Eye className="w-4 h-4" />
                  <span>
                    Violation #{examGuard.violationCount} recorded
                  </span>
                </div>

                <div className="p-4 mb-6 text-left border rounded-xl bg-amber-500/10 border-amber-500/20">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="shrink-0 w-5 h-5 text-amber-400 mt-0.5" />
                    <div className="text-xs leading-relaxed text-slate-400">
                      <p className="mb-1 font-semibold text-amber-300">Please note:</p>
                      <ul className="space-y-1">
                        <li>• All tab switches are logged and reported</li>
                        <li>• Repeated violations may affect your evaluation</li>
                        <li>• Please stay focused on the interview window</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => {
                    examGuard.dismissWarning();
                    // Re-request fullscreen if they exited it
                    if (!examGuard.isFullscreen) {
                      examGuard.requestFullscreen();
                    }
                  }}
                  className="w-full px-6 py-3.5 text-sm font-bold text-white transition-all rounded-xl bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 shadow-lg shadow-rose-500/20 hover:shadow-rose-500/40"
                >
                  Return to Interview
                </button>
              </div>
            </m.div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

