/**
 * conversationLog.ts
 *
 * Saves the completed interview conversation:
 *  1. localStorage  → always works, key "intervexa-logs"
 *  2. Backend POST /Agent/save_log  → prints to uvicorn terminal
 *                                     + writes conversation_log.json
 *                                     + writes conversation_log.txt
 *
 * No Supabase. Log files are written by the backend at:
 *   backend/conversation_log.json   (full JSON array)
 *   backend/conversation_log.txt    (human-readable transcript)
 *   backend/evaluation_log.json     (per-answer scores, written by agent)
 *
 * Even when the backend is offline, you can call downloadLogAsText()
 * to download a .txt transcript from localStorage directly in the browser.
 */

const LS_KEY = "intervexa-logs";
const EVAL_LS_KEY = "intervexa-eval-log";

export interface ChatMessage {
    text: string;
    sender: "ai" | "user";
    time: string;
    fromSpeech?: boolean;
}

export interface ConversationLog {
    sessionId: string;
    role: string;
    interviewType: string;
    difficulty: string;
    messages: ChatMessage[];
    savedAt: string;
}

/**
 * Save a completed interview session to localStorage + backend text files.
 */
export async function saveLog(
    sessionId: string,
    config: { role: string; interviewType: string; difficulty: string },
    messages: { text: string; sender: string; time: Date; fromSpeech?: boolean }[]
): Promise<void> {
    const log: ConversationLog = {
        sessionId,
        role: config.role,
        interviewType: config.interviewType,
        difficulty: config.difficulty,
        messages: messages.map((m) => ({
            text: m.text,
            sender: m.sender as "ai" | "user",
            time: new Date(m.time).toISOString(),
            fromSpeech: m.fromSpeech,
        })),
        savedAt: new Date().toISOString(),
    };

    // ── 1. localStorage (always works, no backend needed) ──────────────────────
    try {
        const raw = localStorage.getItem(LS_KEY);
        const existing: ConversationLog[] = raw ? JSON.parse(raw) : [];
        const updated = [log, ...existing.filter((l) => l.sessionId !== sessionId)].slice(0, 20);
        localStorage.setItem(LS_KEY, JSON.stringify(updated));
        console.log(`[ConversationLog] ✓ Saved to localStorage (${messages.length} messages)`);
        console.log(`[ConversationLog]   Key: "${LS_KEY}" — call downloadLogAsText() to get a .txt file`);
    } catch { /* ignore */ }

    // ── 2. Backend via Vite proxy (prints + saves .json and .txt) ──────────────
    // Uses relative URL — Vite proxies /Agent/* to localhost:8000
    console.log(`[ConversationLog] Sending to backend → /Agent/save_log`);
    try {
        const res = await fetch(`/Agent/save_log`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(log),
        });
        if (res.ok) {
            console.log("[ConversationLog] ✓ Backend saved → backend/conversation_log.txt & .json");
        } else {
            console.warn("[ConversationLog] Backend error:", res.status);
            console.log("[ConversationLog] ℹ️  Tip: use downloadLogAsText() to get a .txt from localStorage");
        }
    } catch (err) {
        console.warn("[ConversationLog] Backend unreachable:", err);
        console.log("[ConversationLog] ℹ️  Tip: use downloadLogAsText() to download the log as a .txt file");
    }
}

// ── Helpers to read back from localStorage ─────────────────────────────────────

export function getLogs(): ConversationLog[] {
    try {
        const raw = localStorage.getItem(LS_KEY);
        return raw ? (JSON.parse(raw) as ConversationLog[]) : [];
    } catch { return []; }
}

export function getLatestLog(): ConversationLog | null {
    const logs = getLogs();
    return logs.length > 0 ? logs[0] : null;
}

// ── Download helpers ────────────────────────────────────────────────────────────

/**
 * Format a single ConversationLog as a plain-text transcript string.
 */
function formatLogAsText(log: ConversationLog): string {
    const sep = "=".repeat(60);
    const lines: string[] = [
        sep,
        `INTERVIEW SESSION  |  ${log.savedAt}`,
        `Session  : ${log.sessionId}`,
        `Role     : ${log.role}`,
        `Type     : ${log.interviewType}  |  Difficulty: ${log.difficulty}`,
        "-".repeat(60),
    ];
    for (const msg of log.messages) {
        const speaker = msg.sender === "ai" ? "AI  " : "USER";
        lines.push(`[${speaker}] ${msg.text}`);
    }
    lines.push(sep);
    return lines.join("\n");
}

/**
 * Download the latest (or all) conversation logs from localStorage as a .txt file.
 * Works entirely in the browser — no backend needed.
 */
export function downloadLogAsText(mode: "latest" | "all" = "latest") {
    const logs = getLogs();
    if (logs.length === 0) {
        console.warn("[ConversationLog] No logs in localStorage to download.");
        return;
    }

    const toDownload = mode === "latest" ? [logs[0]] : logs;
    const content = toDownload.map(formatLogAsText).join("\n\n");
    const filename = mode === "latest"
        ? `interview_log_${logs[0].sessionId}.txt`
        : `interview_logs_all.txt`;

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    console.log(`[ConversationLog] ✓ Downloaded: ${filename}`);
}

/**
 * Download the evaluation log from localStorage as a .txt file.
 */
export function downloadEvalLogAsText() {
    try {
        const raw = localStorage.getItem(EVAL_LS_KEY);
        const evals: any[] = raw ? JSON.parse(raw) : [];
        if (evals.length === 0) {
            console.warn("[EvalLog] No evaluation entries in localStorage.");
            return;
        }

        const lines: string[] = ["EVALUATION LOG", "=".repeat(60)];
        evals.forEach((e, i) => {
            lines.push(`\n[Entry ${i + 1}]  ${e.timestamp}`);
            lines.push(`Q: ${e.question}`);
            lines.push(`A: ${e.answer}`);
            lines.push(`Scores: ${JSON.stringify(e.evaluation?.result?.output ?? e.evaluation, null, 2)}`);
            lines.push("-".repeat(40));
        });

        const blob = new Blob([lines.join("\n")], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "evaluation_log.txt";
        a.click();
        URL.revokeObjectURL(url);
        console.log(`[EvalLog] ✓ Downloaded evaluation_log.txt (${evals.length} entries)`);
    } catch (e) {
        console.error("[EvalLog] Failed to download:", e);
    }
}
