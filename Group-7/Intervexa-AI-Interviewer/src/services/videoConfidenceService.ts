/**
 * Records 5-second video chunks from the candidate's camera stream
 * and sends each chunk to /confidence/evaluate.
 * All errors are non-fatal and only logged — interview never stops.
 */

const CONFIDENCE_LS_KEY = "intervexa-video-confidence-log";
const CONFIDENCE_TIMEOUT_MS = 10_000;

/** Set VITE_SKIP_CONFIDENCE=true in .env to disable confidence API calls */
const SKIP_CONFIDENCE = (import.meta.env.VITE_SKIP_CONFIDENCE ?? "").toString().toLowerCase() === "true";

function appendConfidenceLog(entry: any) {
  try {
    const raw = localStorage.getItem(CONFIDENCE_LS_KEY);
    const existing: any[] = raw ? JSON.parse(raw) : [];
    existing.push(entry);
    localStorage.setItem(CONFIDENCE_LS_KEY, JSON.stringify(existing));
  } catch (e) {
    console.warn("[Confidence] Could not write to localStorage:", e);
  }
}

export class VideoConfidenceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private interviewId = "";
  private cadeId = "";
  private chunkCount = 0;
  private alive = false;
  private apiBase: string;

  constructor() {
    this.apiBase = import.meta.env.VITE_CONFIDENCE_API_URL ?? "";
  }

  start(stream: MediaStream, interviewId: string, cadeId: string) {
    if (this.alive) return;

    if (SKIP_CONFIDENCE) {
      console.log("[Confidence] Disabled via VITE_SKIP_CONFIDENCE=true — skipping all API calls");
      return;
    }

    const videoTracks = stream.getVideoTracks().filter((t) => t.readyState === "live" && t.enabled);
    if (videoTracks.length === 0) {
      console.warn("[Confidence] No live video tracks; skipping confidence recording.");
      return;
    }

    this.interviewId = interviewId;
    this.cadeId = cadeId;
    this.chunkCount = 0;
    this.alive = true;

    console.log("[Confidence] Started recording 5s chunks");

    this.startSegment(stream);
    this.intervalId = setInterval(() => {
      if (!this.alive) return;
      this.stopAndSendSegment();
      this.startSegment(stream);
    }, 5000);
  }

  stop() {
    this.alive = false;

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.stopAndSendSegment();
    console.log("[Confidence] Stopped recording");
  }

  private startSegment(stream: MediaStream) {
    try {
      const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp8,opus")
        ? "video/webm;codecs=vp8,opus"
        : MediaRecorder.isTypeSupported("video/webm")
          ? "video/webm"
          : "";

      const mr = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      this.chunks = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) this.chunks.push(e.data);
      };

      mr.start(500);
      this.mediaRecorder = mr;
    } catch (err) {
      console.warn("[Confidence] Could not start segment:", err);
    }
  }

  private stopAndSendSegment() {
    const mr = this.mediaRecorder;
    if (!mr || mr.state === "inactive") return;

    const currentChunks = this.chunks;
    const mimeType = mr.mimeType || "video/webm";
    this.chunks = [];
    this.mediaRecorder = null;

    mr.onstop = () => {
      const blob = new Blob(currentChunks, { type: mimeType });
      if (blob.size > 500) {
        this.chunkCount++;
        this.sendToApi(blob, this.chunkCount);
      }
    };

    try {
      mr.stop();
    } catch (err) {
      console.warn("[Confidence] Error stopping segment:", err);
    }
  }

  private async sendToApi(videoBlob: Blob, chunkNumber: number) {
    const t0 = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), CONFIDENCE_TIMEOUT_MS);

    try {
      const formData = new FormData();
      formData.append("interview_id", this.interviewId);
      formData.append("cade_id", this.cadeId);
      formData.append("video", videoBlob, `chunk_${chunkNumber}.webm`);

      const response = await fetch(`${this.apiBase}/confidence/evaluate`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      const ms = Math.round(performance.now() - t0);
      console.log(`[Confidence] chunk #${chunkNumber} → SUCCESS (${ms}ms)`);
      appendConfidenceLog({
        timestamp: new Date().toISOString(),
        chunkNumber,
        ...result,
      });
    } catch (err: any) {
      clearTimeout(timer);
      const ms = Math.round(performance.now() - t0);
      const reason = err.name === "AbortError" ? "timeout (10s)" : err.message;
      console.warn(`[Confidence] chunk #${chunkNumber} → FAILED (${reason}, ${ms}ms) → skipped silently`);
      appendConfidenceLog({
        timestamp: new Date().toISOString(),
        chunkNumber,
        status: false,
        error: reason,
      });
    }
  }
}
