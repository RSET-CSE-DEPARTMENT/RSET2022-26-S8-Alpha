/**
 * apiWrapper.ts
 *
 * A shared "safe fetch" layer used by every API call in the frontend.
 *
 * Features:
 *  - AbortController timeout (default 30s, configurable per-call)
 *  - Detects ngrok / HTML error pages (catches "backend offline" pages)
 *  - Detects JSON parse failures
 *  - NEVER throws — always returns null on failure
 *  - Structured console logging:
 *      [API] <name> → SUCCESS (Xms)
 *      [API] <name> → FAILED (<reason>) → using mock
 */

const DEFAULT_TIMEOUT_MS = 30_000;

export type SafeApiResult<T> =
    | { ok: true; data: T; durationMs: number }
    | { ok: false; reason: string; durationMs: number };

/**
 * Wrap any async API call with timeout + error handling.
 *
 * @param name     Human-readable endpoint name for logging  (e.g. "generate_question")
 * @param fn       Async factory that receives an AbortSignal and returns the parsed response
 * @returns        { ok, data, durationMs } | { ok: false, reason, durationMs }
 */
export async function safeApiCall<T>(
    name: string,
    fn: (signal: AbortSignal) => Promise<T>,
    timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<SafeApiResult<T>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const t0 = performance.now();

    try {
        const data = await fn(controller.signal);
        const durationMs = Math.round(performance.now() - t0);
        console.log(`[API] ${name} → SUCCESS (${durationMs}ms)`);
        return { ok: true, data, durationMs };
    } catch (err: any) {
        const durationMs = Math.round(performance.now() - t0);
        const reason = classifyError(err);
        console.warn(`[API] ${name} → FAILED (${reason}) → using mock`);
        return { ok: false, reason, durationMs };
    } finally {
        clearTimeout(timer);
    }
}

/**
 * Convenience: fetch JSON via safeApiCall using global fetch.
 * Handles HTML-body detection (ngrok offline pages).
 */
export async function safeFetchJson<T>(
    name: string,
    url: string,
    init: RequestInit = {},
    timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<T | null> {
    const result = await safeApiCall<T>(name, async (signal) => {
        const res = await fetch(url, { ...init, signal });

        // ngrok / tunnel offline pages return 200 with HTML body
        const contentType = res.headers.get("content-type") ?? "";
        if (contentType.includes("text/html")) {
            throw new Error("HTML_RESPONSE — backend/tunnel offline");
        }

        if (!res.ok) {
            throw new Error(`HTTP_${res.status}`);
        }

        // Guard JSON parse
        const text = await res.text();
        try {
            return JSON.parse(text) as T;
        } catch {
            throw new Error("JSON_PARSE_FAILURE");
        }
    }, timeoutMs);

    return result.ok ? result.data : null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function classifyError(err: any): string {
    if (!err) return "unknown";
    const msg = String(err.message ?? err);
    if (err.name === "AbortError") return "timeout";
    if (msg.includes("HTML_RESPONSE")) return "tunnel/ngrok offline";
    if (msg.includes("JSON_PARSE")) return "JSON parse failure";
    if (msg.includes("HTTP_")) return msg;
    if (msg.includes("ECONNRESET") || msg.includes("Failed to fetch") || msg.includes("NetworkError"))
        return "network unreachable";
    return msg.slice(0, 80);
}

/** Log a skipped/fire-and-forget call that failed (for non-critical paths) */
export function logApiSkip(name: string, reason: string) {
    console.warn(`[API] ${name} → SKIPPED (${reason}) — non-fatal`);
}
