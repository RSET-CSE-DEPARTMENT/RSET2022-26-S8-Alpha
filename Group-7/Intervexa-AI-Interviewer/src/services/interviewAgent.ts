import {
  generateQuestion as apiGenerateQuestion,
  evaluateAnswer as apiEvaluateAnswer,
  insertTechScore as apiInsertTechScore,
  calculateFinalScore as apiCalculateFinalScore,
  type ConversationTurn,
} from "./interviewApi";
import { logApiSkip } from "../utils/apiWrapper";

const AGENT_API_URL = import.meta.env.VITE_AGENT_API_URL ?? "";
const INTRO_QUESTION =
  "Welcome to the interview! Before we begin with technical questions, could you please introduce yourself? Tell me about your background, your experience, and what interests you about this role.";

export type AgentCallbacks = {
  onAgentText: (text: string) => void;
  onEvaluation: (result: any) => void;
  onConnectionChange: (connected: boolean) => void;
  onError: (msg: string) => void;
  onSpeakingChange?: (speaking: boolean) => void;
  onAptitudeTask?: () => void;
  onCodingTask?: () => void;
  onInterviewEnd?: () => void;
  onProctoringAlert?: (status: string) => void;
};

const EVAL_LS_KEY = "intervexa-eval-log";
const AUDIO_LS_KEY = "intervexa-audio-scores";

function appendEvalLog(entry: { timestamp: string; question: string; answer: string; evaluation: any }) {
  try {
    const raw = localStorage.getItem(EVAL_LS_KEY);
    const existing: any[] = raw ? JSON.parse(raw) : [];
    existing.push(entry);
    localStorage.setItem(EVAL_LS_KEY, JSON.stringify(existing));
  } catch {
    // ignore localStorage errors
  }
}

function appendAudioLog(entry: any) {
  try {
    const raw = localStorage.getItem(AUDIO_LS_KEY);
    const existing: any[] = raw ? JSON.parse(raw) : [];
    existing.push(entry);
    localStorage.setItem(AUDIO_LS_KEY, JSON.stringify(existing));
  } catch {
    // ignore localStorage errors
  }
}

class BrowserTTS {
  private voice: SpeechSynthesisVoice | null = null;
  readonly isSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  constructor() {
    if (!this.isSupported) return;
    const load = () => {
      const voices = window.speechSynthesis.getVoices();
      this.voice =
        voices.find((v) => v.name === "Google US English") ||
        voices.find((v) => v.lang === "en-US" && v.localService) ||
        voices.find((v) => v.lang.startsWith("en")) ||
        null;
    };
    load();
    window.speechSynthesis.onvoiceschanged = load;
  }

  speak(text: string, onStart?: () => void, onEnd?: () => void) {
    if (!this.isSupported) {
      onEnd?.();
      return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = 0.92;
    u.pitch = 1.0;
    u.volume = 1.0;
    if (this.voice) u.voice = this.voice;
    u.onstart = () => onStart?.();
    u.onend = () => onEnd?.();
    u.onerror = () => onEnd?.();
    window.speechSynthesis.speak(u);
  }

  stop() {
    if (this.isSupported) window.speechSynthesis.cancel();
  }
}

export class InterviewAgentService {
  private callbacks: AgentCallbacks;
  private tts = new BrowserTTS();
  private history: ConversationTurn[] = [];
  private currentQuestion = "";
  private alive = false;
  private cadeId: string;
  private interviewId: string;
  private taskList: string[] = ["interview", "interview", "interview", "aptitude", "coding"];
  private isFirstQuestion = true;
  private isBusy = false;
  private ws: WebSocket | null = null;
  private sessionId: string;

  constructor(_sessionId: string, callbacks: AgentCallbacks, cadeId = "", interviewId = "") {
    this.sessionId = _sessionId;
    this.callbacks = callbacks;
    this.cadeId = cadeId;
    this.interviewId = interviewId;
  }

  connect() {
    this.alive = true;
    this.callbacks.onConnectionChange(true);

    // ── WebSocket (proctoring only) — always local, never ngrok ─────────────
    const LOCAL_WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
    const wsUrl = `${LOCAL_WS_URL.replace(/\/$/, "")}/ws/interview/${this.sessionId}`;

    console.log(`[WS] Connecting to ${wsUrl}`);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[WS] Connected — proctoring active");
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "proctoring_alert") {
            this.callbacks.onProctoringAlert?.(msg.status);
          }
        } catch {
          // ignore parse errors
        }
      };

      this.ws.onerror = (ev) => {
        console.warn("[WS] WebSocket error — proctoring may be unavailable, interview continues", ev);
      };

      this.ws.onclose = (ev) => {
        console.warn(`[WS] WebSocket closed (code=${ev.code}) — interview continues without proctoring`);
        this.ws = null;
      };
    } catch (err) {
      console.warn("[WS] Failed to create WebSocket — interview continues without proctoring", err);
      this.ws = null;
    }

    setTimeout(() => {
      this.isBusy = false;
      this.askIntroQuestion();
    }, 600);
  }

  sendSpeech(answer: string) {
    this.sendSpeechWithAudio(answer, null);
  }

  sendSpeechWithAudio(answer: string, audioBlob: Blob | null) {
    if (!this.alive || !this.currentQuestion || this.isBusy) return;

    this.isBusy = true;
    const question = this.currentQuestion;

    const textEval = this.evaluate(question, answer);
    const audioEval = audioBlob ? this.analyzeAudio(audioBlob, question) : Promise.resolve(null);

    Promise.all([textEval, audioEval])
      .then(([result]) => {
        if (result?.result?.output && !this.isFirstQuestion) {
          apiInsertTechScore(this.cadeId, this.interviewId, result).catch(() => {
            logApiSkip("insert_tech_score", "non-fatal");
          });
        }

        this.callbacks.onEvaluation(result);
        this.history.push({ AIMessage: question, HumanMessage: answer });

        if (this.isFirstQuestion) this.isFirstQuestion = false;
        this.executeNextTask();
      })
      .catch((err) => {
        console.error("[Agent] Evaluation pipeline failed:", err);
        // Don't crash — still advance the interview
        this.callbacks.onEvaluation(null);
        this.history.push({ AIMessage: question, HumanMessage: answer });
        if (this.isFirstQuestion) this.isFirstQuestion = false;
        this.isBusy = false;
        this.executeNextTask();
      });
  }

  disconnect() {
    this.alive = false;
    this.isBusy = false;
    this.tts.stop();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendVideoFrame(base64Image: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "video_frame", image: base64Image }));
    }
  }

  public taskCompleted() {
    if (!this.alive || !this.isBusy) return;
    this.isBusy = false;
    setTimeout(() => this.executeNextTask(), 1500);
  }

  private async executeNextTask() {
    if (!this.alive) return;

    if (this.taskList.length === 0) {
      console.log("[Agent] All tasks complete — calculating final score");
      await apiCalculateFinalScore(this.cadeId, this.interviewId).catch(() => {
        logApiSkip("calculate_final_score", "non-fatal");
      });
      this.callbacks.onInterviewEnd?.();
      return;
    }

    const randomIndex = Math.floor(Math.random() * this.taskList.length);
    const task = this.taskList.splice(randomIndex, 1)[0];
    console.log(`[Agent] Next task: "${task}" (${this.taskList.length} remaining)`);

    if (task === "interview") {
      try {
        const question = await this.generateQuestion();
        this.currentQuestion = question;
        this.callbacks.onAgentText(question);
        this.callbacks.onSpeakingChange?.(true);
        this.tts.speak(
          question,
          () => this.callbacks.onSpeakingChange?.(true),
          () => {
            this.isBusy = false;
            this.callbacks.onSpeakingChange?.(false);
          }
        );
      } catch {
        // Defense-in-depth: generateQuestion already has a mock fallback,
        // but if something truly unexpected happens, use a hardcoded fallback.
        console.warn("[Agent] generateQuestion threw unexpectedly — using hardcoded fallback");
        const fallback =
          "Could you walk me through how you approach solving a problem you've never seen before?";
        this.currentQuestion = fallback;
        this.callbacks.onAgentText(fallback);
        this.callbacks.onSpeakingChange?.(true);
        this.tts.speak(
          fallback,
          () => this.callbacks.onSpeakingChange?.(true),
          () => {
            this.isBusy = false;
            this.callbacks.onSpeakingChange?.(false);
          }
        );
      }
      return;
    }

    if (task === "aptitude") {
      this.currentQuestion = "";
      const msg = "Excellent work so far! Now let's pivot to testing your logical reasoning and problem-solving abilities. I'll present you with an aptitude assessment that will evaluate your analytical thinking and quick decision-making. Take your time and approach each problem methodically. Ready?";
      this.callbacks.onAgentText(msg);
      this.callbacks.onSpeakingChange?.(true);
      this.isBusy = true;
      this.tts.speak(
        msg,
        () => this.callbacks.onSpeakingChange?.(true),
        () => {
          this.callbacks.onSpeakingChange?.(false);
          setTimeout(() => this.callbacks.onAptitudeTask?.(), 2000);
        }
      );
      return;
    }

    this.currentQuestion = "";
    const msg = "Great job with the assessments so far! Now it's time to showcase your technical skills and demonstrate your coding expertise. You'll be given a coding challenge where you can prove your programming knowledge, problem-solving approach, and code quality. Write clean and efficient code. Let's begin!";
    this.callbacks.onAgentText(msg);
    this.callbacks.onSpeakingChange?.(true);
    this.isBusy = true;
    this.tts.speak(
      msg,
      () => this.callbacks.onSpeakingChange?.(true),
      () => {
        this.callbacks.onSpeakingChange?.(false);
        setTimeout(() => this.callbacks.onCodingTask?.(), 2000);
      }
    );
  }

  private askIntroQuestion() {
    if (!this.alive) return;
    console.log("[Agent] Asking intro question");
    this.currentQuestion = INTRO_QUESTION;
    this.callbacks.onAgentText(INTRO_QUESTION);
    this.callbacks.onSpeakingChange?.(true);
    this.isBusy = true;
    this.tts.speak(
      INTRO_QUESTION,
      () => this.callbacks.onSpeakingChange?.(true),
      () => {
        this.isBusy = false;
        this.callbacks.onSpeakingChange?.(false);
      }
    );
  }

  private async generateQuestion(): Promise<string> {
    return await apiGenerateQuestion(this.history, {
      cadeId: this.cadeId,
      interviewId: this.interviewId,
    });
  }

  private async evaluate(question: string, answer: string): Promise<any> {
    const result = await apiEvaluateAnswer(question, answer);
    appendEvalLog({ timestamp: new Date().toISOString(), question, answer, evaluation: result });
    return result;
  }

  private async analyzeAudio(audioBlob: Blob, question: string): Promise<any> {
    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "answer.wav");
      formData.append("question", question);

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 10_000);

      const response = await fetch(`${AGENT_API_URL}/Agent/analyze_audio`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      console.log("[Agent] analyze_audio → SUCCESS");
      appendAudioLog(result);
      return result;
    } catch (err: any) {
      console.warn(`[Agent] analyze_audio → FAILED (${err.message}) → skipped`);
      return null;
    }
  }
}
