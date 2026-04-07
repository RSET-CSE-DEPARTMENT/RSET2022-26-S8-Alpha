import { useState, useEffect, useCallback, useRef } from "react";

export interface TabSwitchViolation {
  time: Date;
  type: "visibility" | "blur";
  violation: string;
}

export interface ExamGuardState {
  /** Whether the browser is currently in fullscreen */
  isFullscreen: boolean;
  /** Whether a tab-switch warning is currently showing */
  showWarning: boolean;
  /** How many tab-switch violations have occurred */
  violationCount: number;
  /** List of all recorded violations */
  violations: TabSwitchViolation[];
  /** Dismiss the current warning */
  dismissWarning: () => void;
  /** Request fullscreen on the document element */
  requestFullscreen: () => Promise<void>;
  /** Exit fullscreen */
  exitFullscreen: () => Promise<void>;
}

/**
 * useExamGuard — fullscreen + tab-switch detection for proctored interviews.
 *
 * @param enabled  Whether monitoring is active (set to true once interview starts)
 */
export function useExamGuard(enabled: boolean): ExamGuardState {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [violations, setViolations] = useState<TabSwitchViolation[]>([]);
  const warningTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Fullscreen helpers ───────────────────────────────────────────── */

  const requestFullscreen = useCallback(async () => {
    try {
      const el = document.documentElement;
      if (el.requestFullscreen) {
        await el.requestFullscreen();
      } else if ((el as any).webkitRequestFullscreen) {
        await (el as any).webkitRequestFullscreen();
      } else if ((el as any).msRequestFullscreen) {
        await (el as any).msRequestFullscreen();
      }
    } catch (err) {
      console.warn("[ExamGuard] Fullscreen request failed:", err);
    }
  }, []);

  const exitFullscreen = useCallback(async () => {
    try {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      } else if ((document as any).webkitExitFullscreen) {
        await (document as any).webkitExitFullscreen();
      } else if ((document as any).msExitFullscreen) {
        await (document as any).msExitFullscreen();
      }
    } catch (err) {
      console.warn("[ExamGuard] Exit fullscreen failed:", err);
    }
  }, []);

  /* ── Track fullscreen state ───────────────────────────────────────── */

  useEffect(() => {
    const handleFullscreenChange = () => {
      const fsEl =
        document.fullscreenElement ??
        (document as any).webkitFullscreenElement ??
        (document as any).msFullscreenElement;
      setIsFullscreen(!!fsEl);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    document.addEventListener("msfullscreenchange", handleFullscreenChange);

    // Set initially
    handleFullscreenChange();

    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
      document.removeEventListener("msfullscreenchange", handleFullscreenChange);
    };
  }, []);

  /* ── Tab-switch / visibility detection ────────────────────────────── */

  useEffect(() => {
    if (!enabled) return;

    const addViolation = (type: "visibility" | "blur", message: string) => {
      const v: TabSwitchViolation = {
        time: new Date(),
        type,
        violation: message,
      };
      setViolations((prev) => [...prev, v]);
      setShowWarning(true);

      // Auto-dismiss warning after 6 seconds
      if (warningTimeoutRef.current) clearTimeout(warningTimeoutRef.current);
      warningTimeoutRef.current = setTimeout(() => {
        setShowWarning(false);
        warningTimeoutRef.current = null;
      }, 6000);

      console.warn(`[ExamGuard] Tab switch detected (${type}): ${message}`);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        addViolation("visibility", "Tab switch or window minimized detected");
      }
    };

    const handleWindowBlur = () => {
      // Fires when the window itself loses focus (e.g. Alt+Tab, clicking another app)
      // Small delay to avoid false positives from browser dialogs / fullscreen prompt
      setTimeout(() => {
        if (document.hidden || !document.hasFocus()) {
          addViolation("blur", "Window lost focus — possible app switch");
        }
      }, 200);
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleWindowBlur);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleWindowBlur);
      if (warningTimeoutRef.current) {
        clearTimeout(warningTimeoutRef.current);
        warningTimeoutRef.current = null;
      }
    };
  }, [enabled]);

  /* ── Dismiss ──────────────────────────────────────────────────────── */

  const dismissWarning = useCallback(() => {
    setShowWarning(false);
    if (warningTimeoutRef.current) {
      clearTimeout(warningTimeoutRef.current);
      warningTimeoutRef.current = null;
    }
  }, []);

  return {
    isFullscreen,
    showWarning,
    violationCount: violations.length,
    violations,
    dismissWarning,
    requestFullscreen,
    exitFullscreen,
  };
}
