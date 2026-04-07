/**
 * interviewApi.ts
 *
 * All HTTP calls to the Intervexa backend.
 * Every call is wrapped in safeApiCall / safeFetchJson so:
 *   - Network failures, timeouts, HTML-body (ngrok offline), JSON errors → null
 *   - Mock fallbacks are used transparently
 *   - Every call logs success/failure to the console
 */

import { safeFetchJson, safeApiCall, logApiSkip } from "../utils/apiWrapper";

// ── Base URLs ─────────────────────────────────────────────────────────────────
// Proxy to local backend to avoid NGROK CORS on agent requests
const BASE_URL = "http://localhost:8000";
const APTITUDE_BASE = import.meta.env.VITE_APTITUDE_API_URL ?? "/aptitude-api";
const CONFIDENCE_BASE = import.meta.env.VITE_CONFIDENCE_API_URL ?? "";

export const APTITUDE_QUESTIONS_STORAGE_KEY = "mockmate-aptitude-questions";

const jsonHeaders = (): HeadersInit => ({ "Content-Type": "application/json" });

// ── Mock pools ────────────────────────────────────────────────────────────────

/** 10 interview questions used when /Agent/generate_question is offline */
const MOCK_INTERVIEW_QUESTIONS = [
  "Can you walk me through your background and what motivated you to pursue this role?",
  "Describe a challenging technical problem you faced and how you solved it.",
  "How do you approach debugging a complex bug you have never seen before?",
  "Tell me about a time you disagreed with a teammate and how you resolved it.",
  "What is the difference between REST and GraphQL? When would you choose one?",
  "Explain how you would design a URL shortening service at scale.",
  "What does it mean for code to be 'clean'? How do you ensure your code meets that bar?",
  "Describe your experience with version control and your usual branching strategy.",
  "How do you prioritise tasks when working on multiple projects simultaneously?",
  "Where do you see yourself growing technically in the next two years?",
];

/** Neutral evaluation returned when /Agent/evaluate_interview_conv is offline */
const MOCK_EVALUATION = {
  result: {
    output: {
      technical_accuracy: 7,
      communication: 7,
      problem_solving: 7,
      confidence: 7,
      overall: 7,
      feedback: "[Mock] Server unavailable — evaluation recorded locally for review.",
    },
  },
};

/** Mock coding problem used when /db/fetch_coding_question is offline */
export const MOCK_CODING_QUESTION: DynamicCodingQuestion = {
  question_id: "mock-two-sum",
  question_name: "Two Sum",
  description:
    "Given an array of integers nums and an integer target, return the indices of the two numbers such that they add up to target.\n\nEach input has exactly one solution, and you may not use the same element twice.",
  signature: "def two_sum(nums: List[int], target: int) -> List[int]:",
  examples: {
    examples: [
      { input: { nums: [2, 7, 11, 15], target: 9 }, output: [0, 1], explanation: "nums[0] + nums[1] == 9 → [0, 1]." },
      { input: { nums: [3, 2, 4], target: 6 }, output: [1, 2], explanation: "nums[1] + nums[2] == 6 → [1, 2]." },
    ],
  },
  testcases: {
    cases: [
      { input: { nums: [2, 7, 11, 15], target: 9 }, expected_output: [0, 1] },
      { input: { nums: [3, 2, 4], target: 6 }, expected_output: [1, 2] },
      { input: { nums: [3, 3], target: 6 }, expected_output: [0, 1] },
    ],
  },
  tags: ["Array", "Hash Table"],
  created_at: new Date().toISOString(),
};

// ── Types ─────────────────────────────────────────────────────────────────────

export type ConversationTurn = { AIMessage: string; HumanMessage: string };

type GenerateQuestionOptions = { cadeId?: string; interviewId?: string };

export interface DynamicCodingExample {
  input: Record<string, any>;
  output: any;
  explanation: string;
}
export interface DynamicCodingTestCase {
  input: Record<string, any>;
  expected_output: any;
}
export interface DynamicCodingQuestion {
  question_id: string;
  question_name: string;
  description: string;
  signature: string;
  examples: { examples: DynamicCodingExample[] };
  testcases: { cases: DynamicCodingTestCase[] };
  tags: string[];
  created_at: string;
}

export interface AptitudeApiQuestion {
  id: number | string;
  question: string;
  options: Record<string, string>;
  correctAnswer: string;
  skill?: string;
  difficulty?: string;
}
export interface StartAptitudeInterviewResponse {
  questions: AptitudeApiQuestion[];
}

// ── 1. Resume upload ──────────────────────────────────────────────────────────

export async function uploadResume(
  file: File,
  cadeId: string
): Promise<{ message: string; filename: string; saved_path: string }> {
  console.log(`[API] upload_resume  cadeId=${cadeId}  file=${file.name}`);
  const form = new FormData();
  form.append("file", file);
  form.append("cade_id", cadeId);

  const result = await safeApiCall<{ message: string; filename: string; saved_path: string }>(
    "upload_resume",
    async (signal) => {
      const res = await fetch(`${BASE_URL}/upload_resume`, {
        method: "POST",
        headers: { "ngrok-skip-browser-warning": "true" },
        body: form,
        signal,
      });
      const ct = res.headers.get("content-type") ?? "";
      if (ct.includes("text/html")) throw new Error("HTML_RESPONSE");
      if (!res.ok) throw new Error(`HTTP_${res.status}`);
      return res.json();
    }
  );

  if (!result.ok) throw new Error(`upload_resume failed: ${result}`);
  return result.data;
}

// ── 2. Generate question ──────────────────────────────────────────────────────

export async function generateQuestion(
  history: ConversationTurn[],
  options: GenerateQuestionOptions = {}
): Promise<string> {
  const payload: Record<string, any> = { conversation: history };
  if (options.cadeId) payload.cade_id = options.cadeId;
  if (options.interviewId) payload.interview_id = options.interviewId;

  const data = await safeFetchJson<{ question?: string; text?: string } | string>(
    "generate_question",
    `${BASE_URL}/Agent/generate_question`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload) }
  );

  if (data !== null) {
    const question =
      typeof data === "string" ? data : data.question ?? data.text ?? JSON.stringify(data);
    return question;
  }

  // Mock fallback — avoid repeating questions from this session
  const used = new Set(history.map((t) => t.AIMessage));
  const pool = MOCK_INTERVIEW_QUESTIONS.filter((q) => !used.has(q));
  const chosen = (pool.length > 0 ? pool : MOCK_INTERVIEW_QUESTIONS)[
    Math.floor(Math.random() * (pool.length > 0 ? pool.length : MOCK_INTERVIEW_QUESTIONS.length))
  ];
  return chosen;
}

// ── 3. Evaluate answer ────────────────────────────────────────────────────────

export async function evaluateAnswer(question: string, answer: string): Promise<any> {
  const data = await safeFetchJson<any>(
    "evaluate_interview_conv",
    `${BASE_URL}/Agent/evaluate_interview_conv`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify({ question, answer }) }
  );

  if (data !== null) return data;

  // Mock fallback
  return MOCK_EVALUATION;
}

// ── 4. Fetch coding question ──────────────────────────────────────────────────

export async function fetchCodingQuestion(
  interviewId: string
): Promise<DynamicCodingQuestion | null> {
  if (!interviewId) {
    console.warn("[API] fetch_coding_question → skipped (no interviewId) → using mock");
    return MOCK_CODING_QUESTION;
  }

  const data = await safeFetchJson<any>(
    "fetch_coding_question",
    `${BASE_URL}/db/fetch_coding_question`,
    {
      method: "POST",
      headers: { ...jsonHeaders(), "ngrok-skip-browser-warning": "true" },
      body: JSON.stringify({ interview_id: interviewId }),
    }
  );

  if (data) {
    const question = data?.fetched_question?.question;
    if (question) {
      console.log(`[API] fetch_coding_question → loaded: ${question.question_name}`);
      return question as DynamicCodingQuestion;
    }
    console.warn("[API] fetch_coding_question → unexpected shape", data, "→ using mock");
  }

  return MOCK_CODING_QUESTION;
}

// ── 5. Aptitude: start interview ──────────────────────────────────────────────

export async function startAptitudeInterview(
  interviewId: string
): Promise<StartAptitudeInterviewResponse | null> {
  if (!interviewId) {
    console.warn("[API] start-interview → skipped (no interviewId) → using mock aptitude");
    return null;
  }

  const data = await safeFetchJson<StartAptitudeInterviewResponse>(
    "start-interview (aptitude)",
    `${APTITUDE_BASE}/start-interview`,
    {
      method: "POST",
      headers: { ...jsonHeaders(), "ngrok-skip-browser-warning": "true" },
      body: JSON.stringify({ interview_id: interviewId }),
    }
  );

  if (data && Array.isArray(data.questions)) return data;

  // null → AptitudeTest.jsx falls back to generateMockAptitudeQuestions()
  return null;
}

// ── 6. Insert tech score ──────────────────────────────────────────────────────

export async function insertTechScore(
  cadeId: string,
  interviewId: string,
  evaluation: any
): Promise<void> {
  const payload = { cade_id: cadeId, interview_id: interviewId, evaluation };
  console.log("[API] insert_tech_score  payload:", JSON.stringify(payload).slice(0, 120));

  const data = await safeFetchJson<any>(
    "insert_tech_score",
    `${BASE_URL}/Agent/insert_tech_score`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload) }
  );

  if (data === null) logApiSkip("insert_tech_score", "score will not be persisted this session");
}

// ── 7. Insert coding score ────────────────────────────────────────────────────

export async function insertCodingScore(
  interviewId: string,
  cadeId: string,
  result: { status: string; tests_passed: number; tests_total: number }
): Promise<void> {
  const coding_score = result.tests_total > 0 ? result.tests_passed / result.tests_total : 0;
  const payload = { interview_id: interviewId, candidate_id: cadeId, coding_score };
  console.log("[API] insert_coding_score  payload:", JSON.stringify(payload));

  const data = await safeFetchJson<any>(
    "insert_coding_score",
    `${BASE_URL}/db/insert_coding_score`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload) }
  );

  if (data === null) logApiSkip("insert_coding_score", "coding score not persisted");
}

// ── 8. Insert aptitude score ──────────────────────────────────────────────────

export async function insertAptitudeScore(
  interviewId: string,
  cadeId: string,
  result: { correct: number; total: number; percentage: number }
): Promise<void> {
  const aptitude_score = result.total > 0 ? result.correct / result.total : 0;
  const payload = { interview_id: interviewId, candidate_id: cadeId, aptitude_score };
  console.log("[API] insert_aptitude_score  payload:", JSON.stringify(payload));

  const data = await safeFetchJson<any>(
    "insert_aptitude_score",
    `${BASE_URL}/db/insert_aptitude_score`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload) }
  );

  if (data === null) logApiSkip("insert_aptitude_score", "aptitude score not persisted");
}

// ── 9. Calculate final score ──────────────────────────────────────────────────

export async function calculateFinalScore(
  cadeId: string,
  interviewId: string
): Promise<any> {
  const payload = { cade_id: cadeId, interview_id: interviewId };
  console.log("[API] calculate_final_score  payload:", JSON.stringify(payload));

  const data = await safeFetchJson<any>(
    "calculate_final_score",
    `${BASE_URL}/Agent/calculate_final_score`,
    { method: "POST", headers: jsonHeaders(), body: JSON.stringify(payload) }
  );

  if (data !== null) return data;

  // Local mock score
  console.warn("[API] calculate_final_score → using local mock score");
  return {
    status: "mock",
    result: {
      overall_score: 70,
      breakdown: { interview: 70, aptitude: 70, coding: 70 },
      note: "Score computed locally — backend was unavailable.",
    },
  };
}

// ── 10. TTS (fire-and-forget, used by agent service) ─────────────────────────

export async function textToSpeechUrl(text: string): Promise<string | null> {
  // Nothing to call — browser TTS is used by interviewAgent.ts directly.
  // This export may be used by future REST-TTS integration.
  return null;
}

// ── Aptitude question helpers (local storage + mock generator) ────────────────

export function storeAptitudeQuestions(questions: AptitudeApiQuestion[]): void {
  try {
    localStorage.setItem(APTITUDE_QUESTIONS_STORAGE_KEY, JSON.stringify(questions ?? []));
  } catch { /* ignore */ }
}

export function loadAptitudeQuestions(): AptitudeApiQuestion[] {
  try {
    const raw = localStorage.getItem(APTITUDE_QUESTIONS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function generateMockAptitudeQuestions(): AptitudeApiQuestion[] {
  return [
    { id: 1, question: "What is the capital of France?", options: { A: "London", B: "Berlin", C: "Paris", D: "Madrid" }, correctAnswer: "C", skill: "General Knowledge", difficulty: "Easy" },
    { id: 2, question: "Which is NOT a programming language?", options: { A: "Python", B: "Java", C: "HTML", D: "JavaScript" }, correctAnswer: "C", skill: "Technical", difficulty: "Easy" },
    { id: 3, question: "What does CPU stand for?", options: { A: "Central Processing Unit", B: "Computer Personal Unit", C: "Central Program Utility", D: "Control Processing Unit" }, correctAnswer: "A", skill: "Technical", difficulty: "Easy" },
    { id: 4, question: "Which data structure follows LIFO?", options: { A: "Queue", B: "Stack", C: "Array", D: "Linked List" }, correctAnswer: "B", skill: "Data Structures", difficulty: "Medium" },
    { id: 5, question: "Time complexity of binary search?", options: { A: "O(n)", B: "O(log n)", C: "O(n²)", D: "O(1)" }, correctAnswer: "B", skill: "Algorithms", difficulty: "Medium" },
    { id: 6, question: "SQL command to retrieve data?", options: { A: "INSERT", B: "UPDATE", C: "DELETE", D: "SELECT" }, correctAnswer: "D", skill: "Database", difficulty: "Easy" },
    { id: 7, question: "What does API stand for?", options: { A: "Application Programming Interface", B: "Advanced Programming Interface", C: "Automated Programming Interface", D: "Application Process Integration" }, correctAnswer: "A", skill: "Technical", difficulty: "Easy" },
    { id: 8, question: "Which is a NoSQL database?", options: { A: "MySQL", B: "PostgreSQL", C: "MongoDB", D: "Oracle" }, correctAnswer: "C", skill: "Database", difficulty: "Medium" },
    { id: 9, question: "Output of 2 + 2 * 3?", options: { A: "12", B: "8", C: "10", D: "6" }, correctAnswer: "B", skill: "Mathematics", difficulty: "Easy" },
    { id: 10, question: "HTTP status for 'Not Found'?", options: { A: "200", B: "404", C: "500", D: "301" }, correctAnswer: "B", skill: "Web Development", difficulty: "Easy" },
    { id: 11, question: "Purpose of Git?", options: { A: "Write code", B: "Track changes", C: "Compile code", D: "Debug code" }, correctAnswer: "B", skill: "Dev Tools", difficulty: "Easy" },
    { id: 12, question: "Which is NOT agile?", options: { A: "Scrum", B: "Kanban", C: "Waterfall", D: "XP" }, correctAnswer: "C", skill: "Project Mgmt", difficulty: "Medium" },
    { id: 13, question: "CSS stands for?", options: { A: "Computer Style Sheets", B: "Creative Style Sheets", C: "Cascading Style Sheets", D: "Colorful Style Sheets" }, correctAnswer: "C", skill: "Web Development", difficulty: "Easy" },
    { id: 14, question: "Best average-case sorting algorithm?", options: { A: "Bubble Sort", B: "Quick Sort", C: "Insertion Sort", D: "Selection Sort" }, correctAnswer: "B", skill: "Algorithms", difficulty: "Hard" },
    { id: 15, question: "Purpose of unit testing?", options: { A: "Test entire app", B: "Test individual components", C: "Test UI", D: "Test DB connections" }, correctAnswer: "B", skill: "Testing", difficulty: "Medium" },
  ];
}
