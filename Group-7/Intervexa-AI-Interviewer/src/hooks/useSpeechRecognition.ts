import { useRef, useState, useCallback, useEffect } from "react";

export type SpeechRecognitionStatus = "idle" | "listening" | "stopped" | "unsupported";

export interface UseSpeechRecognitionOptions {
    /** Called every time an interim (in-progress) transcript changes */
    onInterim?: (text: string) => void;
    /** Called when a final transcript segment is committed */
    onFinal?: (text: string) => void;
    /** Language for recognition; defaults to "en-US" */
    lang?: string;
    /** Continuous mode — keep listening after each pause. Default: true */
    continuous?: boolean;
}

export interface UseSpeechRecognitionReturn {
    status: SpeechRecognitionStatus;
    interimText: string;   // live, in-progress words
    finalText: string;     // accumulated confirmed transcript
    start: () => void;
    stop: () => void;
    clear: () => void;     // wipe accumulated finalText
    isSupported: boolean;
}

// ─── Minimal Web Speech API type declarations ───────────────────────────────
// TypeScript's lib.dom.d.ts does not include SpeechRecognition in all versions.
// We declare just what we need here so the hook is self-contained.

interface ISpeechRecognitionResult {
    readonly isFinal: boolean;
    readonly length: number;
    item(index: number): { transcript: string };
    [index: number]: { transcript: string };
}

interface ISpeechRecognitionResultList {
    readonly length: number;
    item(index: number): ISpeechRecognitionResult;
    [index: number]: ISpeechRecognitionResult;
}

interface ISpeechRecognitionEvent extends Event {
    readonly resultIndex: number;
    readonly results: ISpeechRecognitionResultList;
}

interface ISpeechRecognitionErrorEvent extends Event {
    readonly error: string;
}

interface ISpeechRecognition extends EventTarget {
    lang: string;
    continuous: boolean;
    interimResults: boolean;
    maxAlternatives: number;
    onstart: (() => void) | null;
    onresult: ((event: ISpeechRecognitionEvent) => void) | null;
    onerror: ((event: ISpeechRecognitionErrorEvent) => void) | null;
    onend: (() => void) | null;
    start(): void;
    stop(): void;
}

type ISpeechRecognitionConstructor = new () => ISpeechRecognition;

// ─── Resolve the constructor (Chrome/Edge prefix) ───────────────────────────
function getRecognitionClass(): ISpeechRecognitionConstructor | null {
    if (typeof window === "undefined") return null;
    return (
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition ||
        null
    );
}

// ─── Hook ────────────────────────────────────────────────────────────────────
export function useSpeechRecognition(
    options: UseSpeechRecognitionOptions = {}
): UseSpeechRecognitionReturn {
    const { onInterim, onFinal, lang = "en-US", continuous = true } = options;

    const RecognitionClass = getRecognitionClass();

    const recognitionRef = useRef<ISpeechRecognition | null>(null);
    const isListeningRef = useRef(false); // track intent separately from state

    const [status, setStatus] = useState<SpeechRecognitionStatus>(
        RecognitionClass ? "idle" : "unsupported"
    );
    const [interimText, setInterimText] = useState("");
    const [finalText, setFinalText] = useState("");

    // Keep latest callbacks in refs to avoid re-creating the recognition instance
    const onInterimRef = useRef(onInterim);
    const onFinalRef = useRef(onFinal);
    useEffect(() => { onInterimRef.current = onInterim; }, [onInterim]);
    useEffect(() => { onFinalRef.current = onFinal; }, [onFinal]);

    const start = useCallback(() => {
        if (!RecognitionClass) return;

        // If already running with a live instance, skip
        if (isListeningRef.current && recognitionRef.current) return;

        // Clean up any stale/dead instance before creating a new one
        if (recognitionRef.current) {
            recognitionRef.current.onend = null;
            try { recognitionRef.current.stop(); } catch { /* ignore */ }
            recognitionRef.current = null;
        }

        isListeningRef.current = true;

        const recognition = new RecognitionClass();
        recognition.lang = lang;
        recognition.continuous = continuous;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => setStatus("listening");

        recognition.onresult = (event: ISpeechRecognitionEvent) => {
            let interim = "";
            let newFinal = "";

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    newFinal += transcript + " ";
                } else {
                    interim += transcript;
                }
            }

            if (interim) {
                setInterimText(interim);
                onInterimRef.current?.(interim);
            }

            if (newFinal) {
                setInterimText("");
                setFinalText((prev) => prev + newFinal);
                onFinalRef.current?.(newFinal.trim());
            }
        };

        recognition.onerror = (event: ISpeechRecognitionErrorEvent) => {
            // "no-speech" is benign — keep listening
            if (event.error === "no-speech") return;

            console.warn("[STT] Recognition error:", event.error);

            // "network" errors are often transient — let onend auto-restart
            if (event.error === "network" || event.error === "aborted") {
                return;
            }

            isListeningRef.current = false;
            setStatus("stopped");
        };

        recognition.onend = () => {
            setInterimText("");
            // Auto-restart while intent is still "listening" (browser cuts stream after pause)
            if (isListeningRef.current) {
                // Small delay to avoid rapid-fire restarts on persistent errors
                setTimeout(() => {
                    if (!isListeningRef.current) {
                        setStatus("stopped");
                        return;
                    }
                    // Create a fresh recognition instance for the restart
                    try {
                        const fresh = new RecognitionClass();
                        fresh.lang = lang;
                        fresh.continuous = continuous;
                        fresh.interimResults = true;
                        fresh.maxAlternatives = 1;
                        fresh.onstart = recognition.onstart;
                        fresh.onresult = recognition.onresult;
                        fresh.onerror = recognition.onerror;
                        fresh.onend = recognition.onend; // reuse the same restart logic
                        recognitionRef.current = fresh;
                        fresh.start();
                    } catch {
                        console.warn("[STT] Auto-restart failed — resetting for next start() call");
                        isListeningRef.current = false;
                        recognitionRef.current = null;
                        setStatus("stopped");
                    }
                }, 500);
            } else {
                setStatus("stopped");
            }
        };

        recognitionRef.current = recognition;
        try {
            recognition.start();
        } catch (e) {
            console.error("[STT] Could not start recognition:", e);
            isListeningRef.current = false;
        }
    }, [RecognitionClass, lang, continuous]);

    const stop = useCallback(() => {
        isListeningRef.current = false;
        if (!recognitionRef.current) return;
        recognitionRef.current.onend = null; // prevent auto-restart
        recognitionRef.current.stop();
        recognitionRef.current = null;
        setInterimText("");
        setStatus("stopped");
    }, []);

    const clear = useCallback(() => {
        setFinalText("");
        setInterimText("");
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            isListeningRef.current = false;
            if (recognitionRef.current) {
                recognitionRef.current.onend = null;
                recognitionRef.current.stop();
            }
        };
    }, []);

    return {
        status,
        interimText,
        finalText,
        start,
        stop,
        clear,
        isSupported: !!RecognitionClass,
    };
}
