import { useEffect, useState } from "react";
import { m, AnimatePresence } from "framer-motion";
import InterviewRoom from "./interview/InterviewRoom";
import CandidateSummary from "./interview/CandidateSummary";
import ResumeUploadDialog from "@/components/ResumeUploadDialog";
import { useExamGuard } from "@/hooks/useExamGuard";

type InterviewStage = "setup" | "resume" | "active" | "summary";

interface InterviewConfig {
  role: string;
  difficulty: "easy" | "medium" | "hard";
  duration: number;
  interviewType: "behavioral" | "technical" | "mixed";
  useVideo: boolean;
  useAudio: boolean;
  cadeId?: string;
  interviewId?: string;
}

export default function Interview() {
  /* ── Check if candidate came from login with interview credentials ── */
  const storedInterviewId = localStorage.getItem("interviewId");
  const storedCadeId = localStorage.getItem("intervexa-cade-id");
  const hasCredentials = !!(storedInterviewId && storedCadeId);

  const [stage, setStage] = useState<InterviewStage>(
    hasCredentials ? "resume" : "setup"
  );
  const [config, setConfig] = useState<InterviewConfig | null>(
    hasCredentials
      ? {
        role: "Interview",
        difficulty: "medium",
        duration: 45,
        interviewType: "mixed",
        useVideo: true,
        useAudio: true,
        cadeId: storedCadeId!,
        interviewId: storedInterviewId!,
      }
      : null
  );
  const [sessionId, setSessionId] = useState<string | null>(
    hasCredentials ? storedCadeId : null
  );

  /* ── Exam Guard: fullscreen + tab-switch detection ── */
  const examGuard = useExamGuard(stage === "active");

  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("navbar-visibility", {
        detail: { hidden: stage === "active", hideFooter: stage === "active" },
      })
    );

    return () => {
      window.dispatchEvent(
        new CustomEvent("navbar-visibility", {
          detail: { hidden: false, hideFooter: false },
        })
      );
    };
  }, [stage]);

  /* ── Enter fullscreen when interview goes active ── */
  useEffect(() => {
    if (stage === "active") {
      examGuard.requestFullscreen();
    }
    if (stage === "summary") {
      examGuard.exitFullscreen();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  const handleStartInterview = (interviewConfig: InterviewConfig) => {
    setConfig(interviewConfig);
    setSessionId(`session-${Date.now()}`);
    setStage("active");
  };

  const handleEndInterview = () => {
    setStage("summary");
  };

  /* ── Resume upload handler for credential-based flow ── */
  const handleResumeUploaded = (_file: File, uploadedCadeId?: string) => {
    // Resume uploaded — go straight to interview room
    if (uploadedCadeId && config) {
      setConfig({ ...config, cadeId: uploadedCadeId });
    }
    setSessionId(storedCadeId ?? `session-${Date.now()}`);
    setStage("active");
  };

  return (
    <main className={`min-h-screen bg-[#0b1120] text-slate-100 ${stage === "active" ? "" : "pt-20"}`}>
      <AnimatePresence mode="wait">
        {/* Resume upload step — when candidate logged in with interview_id + cade_id */}
        {stage === "resume" && (
          <m.div
            key="resume"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <ResumeUploadDialog
              isOpen={true}
              onClose={(wasSubmitted?: boolean) => {
                if (!wasSubmitted) {
                  // Only go back to setup if they cancelled.
                  // If they submitted, handleResumeUploaded already advances the stage.
                  setStage("setup");
                }
              }}
              onSubmit={handleResumeUploaded}
            />
          </m.div>
        )}

        {stage === "active" && config && sessionId && (
          <m.div
            key="active"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
          >
            <InterviewRoom
              config={config}
              sessionId={sessionId}
              onEnd={handleEndInterview}
              examGuard={examGuard}
            />
          </m.div>
        )}

        {stage === "summary" && sessionId && (
          <m.div
            key="summary"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <CandidateSummary
              onRestart={() => setStage("setup")}
            />
          </m.div>
        )}
      </AnimatePresence>
    </main>
  );
}
