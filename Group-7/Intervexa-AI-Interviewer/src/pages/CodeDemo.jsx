import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import Editor from "@monaco-editor/react";
import { loadPyodide } from "pyodide";
import {
  Play,
  Upload,
  History,
  RotateCcw,
  ChevronDown,
  CheckCircle,
  XCircle,
  Terminal,
} from "lucide-react";
import { m } from "framer-motion";

const AGENT_API_BASE = import.meta.env.VITE_AGENT_API_URL || "";
const EXECUTOR_API_BASE = import.meta.env.VITE_EXECUTOR_API_URL || "";

const LANGUAGES = [{ id: 71, label: "Python 3", key: "python3" }];


function getStatusClasses(status) {
  if (!status) return "text-slate-200";
  const s = status.toLowerCase();
  if (s.includes("accepted")) return "text-emerald-400";
  if (s.includes("wrong answer")) return "text-rose-400";
  if (s.includes("time limit")) return "text-amber-400";
  if (s.includes("compilation")) return "text-orange-400";
  if (s.includes("runtime")) return "text-red-400";
  return "text-slate-200";
}

function buildPythonStarterCode(question) {
  const raw = (question?.signature || "def solve() -> int").trim();
  const signature = raw.endsWith(":") ? raw : `${raw}:`;
  const needsListImport = /\bList\s*\[/.test(signature);
  const importLine = needsListImport ? "from typing import List\n\n" : "";
  return `${importLine}${signature}\n    pass\n`;
}

function formatInput(inputObj) {
  return Object.entries(inputObj || {})
    .map(([k, v]) => `${k} = ${JSON.stringify(v)}`)
    .join(", ");
}

function evaluateClarity(code) {
  const lines = code.split("\n");
  const nonEmpty = lines.filter((l) => l.trim().length > 0);
  const commentLines = lines.filter((l) => /^\s*#/.test(l)).length;
  const avgLength = nonEmpty.length
    ? Math.round(nonEmpty.reduce((s, l) => s + l.length, 0) / nonEmpty.length)
    : 0;

  let score = 70;
  if (nonEmpty.length > 0 && commentLines / nonEmpty.length >= 0.05) score += 10;
  if (avgLength <= 100) score += 5;
  score = Math.max(0, Math.min(100, score));

  const label = score >= 85 ? "Excellent" : score >= 70 ? "Good" : score >= 50 ? "Needs improvement" : "Poor";
  return {
    score,
    label,
    notes: [
      `Average line length: ${avgLength}`,
      `Comment coverage: ${Math.round((nonEmpty.length ? commentLines / nonEmpty.length : 0) * 100)}%`,
    ],
  };
}

export default function CodeDemo({
  embedded = false,
  onReturnToInterview,
  onSubmissionComplete,
  dynamicQuestion = null,
} = {}) {
  const [searchParams] = useSearchParams();
  const [fetchedQuestion, setFetchedQuestion] = useState(null);

  const activeQuestion = dynamicQuestion || fetchedQuestion;
  const problemId = activeQuestion?.question_id || "api-question";

  const currentProblem = useMemo(() => {
    return {
      id: activeQuestion?.question_id || "",
      title: activeQuestion?.question_name || "Coding Question",
      difficulty: "Medium",
      description: activeQuestion?.description || "",
      signature: activeQuestion?.signature || "",
      tags: activeQuestion?.tags || [],
      samples: (activeQuestion?.examples?.examples || []).map((ex) => ({
        input: formatInput(ex.input),
        output: JSON.stringify(ex.output),
        explanation: ex.explanation || "",
      })),
      testcases: activeQuestion?.testcases?.cases || [],
    };
  }, [activeQuestion]);

  const starterCode = useMemo(() => buildPythonStarterCode(activeQuestion), [activeQuestion]);

  const [languageId, setLanguageId] = useState(71);
  const [languageKey, setLanguageKey] = useState("python3");
  const [code, setCode] = useState(starterCode);
  const [output, setOutput] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [statusText, setStatusText] = useState("");

  const [failedRuns, setFailedRuns] = useState(0);
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const [clarityLoading, setClarityLoading] = useState(false);
  const [clarityResult, setClarityResult] = useState(null);
  const [submissionComplete, setSubmissionComplete] = useState(false);

  const [testResults, setTestResults] = useState(null);
  const [activeProblemTab, setActiveProblemTab] = useState("description");

  // Pyodide state
  const [pyodide, setPyodide] = useState(null);
  const [pyodideLoading, setPyodideLoading] = useState(true);
  const [pyodideError, setPyodideError] = useState(null);

  const [editorFontSize, setEditorFontSize] = useState(
    Number(localStorage.getItem("mockmate-editor-font-size") || 14)
  );
  const [editorTheme, setEditorTheme] = useState(
    localStorage.getItem("mockmate-editor-theme") || "vs-dark"
  );

  const languageSelectRef = useRef(null);

  useEffect(() => {
    if (dynamicQuestion) return;

    let cancelled = false;
    async function fetchQuestion() {
      const interviewId = searchParams.get("interview_id") || localStorage.getItem("interviewId");
      if (!interviewId) return;

      try {
        const res = await axios.post(`${AGENT_API_BASE}/db/fetch_coding_question`, {
          interview_id: interviewId,
        });
        const q = res?.data?.fetched_question?.question;
        if (!cancelled && q) setFetchedQuestion(q);
      } catch {
        if (!cancelled) setFetchedQuestion(null);
      }
    }

    fetchQuestion();
    return () => {
      cancelled = true;
    };
  }, [dynamicQuestion, searchParams]);

  // Initialize Pyodide for local Python execution
  useEffect(() => {
    let cancelled = false;

    async function initPyodide() {
      try {
        setPyodideLoading(true);
        setPyodideError(null);
        console.log("[Pyodide] Loading Python runtime from CDN...");
        const pyodideInstance = await loadPyodide({
          indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/",
        });
        if (!cancelled) {
          setPyodide(pyodideInstance);
          setPyodideLoading(false);
          console.log("[Pyodide] ✓ Python runtime loaded successfully");
        }
      } catch (error) {
        if (!cancelled) {
          console.error("[Pyodide] Failed to load Python runtime:", error);
          setPyodideError("Failed to load Python runtime — code will run via server if available");
          setPyodideLoading(false);
        }
      }
    }

    initPyodide();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem("mockmate-editor-font-size", String(editorFontSize));
  }, [editorFontSize]);

  useEffect(() => {
    localStorage.setItem("mockmate-editor-theme", editorTheme);
  }, [editorTheme]);

  useEffect(() => {
    const saved = localStorage.getItem(`mockmate-code-${languageKey}-${problemId}`);
    setCode(saved != null ? saved : starterCode);
  }, [languageKey, problemId, starterCode]);

  useEffect(() => {
    const savedHistory = localStorage.getItem(`mockmate-history-${problemId}`);
    setHistory(savedHistory ? JSON.parse(savedHistory) : []);
    setFailedRuns(0);
    setSubmissionComplete(false);
    setClarityResult(null);
    setOutput("");
    setStatusText("");
    setTestResults(null);
  }, [problemId]);

  useEffect(() => {
    localStorage.setItem(`mockmate-code-${languageKey}-${problemId}`, code);
  }, [code, languageKey, problemId]);

  useEffect(() => {
    localStorage.setItem(`mockmate-history-${problemId}`, JSON.stringify(history));
  }, [history, problemId]);

  useEffect(() => {
    const handler = (e) => {
      const key = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && key === "enter") {
        e.preventDefault();
        if (!isRunning) handleRun();
      }
      if ((e.ctrlKey || e.metaKey) && key === "s") {
        e.preventDefault();
        localStorage.setItem(`mockmate-code-${languageKey}-${problemId}`, code);
        setStatusText("Snippet saved locally.");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isRunning, code, languageKey, problemId]);

  // FIX 1: Extract function name from signature so we call the right function, not always "solve"
  function getFuncName(question) {
    const sig = question?.signature || "def solve()";
    const match = sig.match(/def\s+(\w+)\s*\(/);
    return match ? match[1] : "solve";
  }

  async function executeWithPyodide(sourceCode, testCases) {
    if (!pyodide) {
      throw new Error("Python runtime not loaded");
    }

    // Reset Pyodide stdout/stderr each run
    pyodide.runPython(`
import sys
from io import StringIO
sys.stdout = StringIO()
sys.stderr = StringIO()
`);

    const funcName = getFuncName(activeQuestion);
    let testsPassed = 0;
    const testsTotal = testCases.length;
    const results = [];
    let stdout = "";
    let stderr = "";

    try {
      // FIX 2: Wrap user code load in try/catch to catch syntax errors gracefully
      try {
        pyodide.runPython(sourceCode);
      } catch (loadError) {
        stderr = loadError.message;
        // Return early with all tests failed due to syntax/load error
        return {
          status: "Runtime Error",
          tests_total: testsTotal,
          tests_passed: 0,
          results: testCases.map((tc, i) => ({
            test_case: i + 1,
            input: tc.input,
            expected: tc.expected_output,
            actual: `Load Error: ${loadError.message}`,
            passed: false,
          })),
          stdout: "",
          stderr,
        };
      }

      // Run each test case
      for (let i = 0; i < testCases.length; i++) {
        const testCase = testCases[i];
        const input = testCase.input;
        const expectedOutput = testCase.expected_output;

        try {
          // FIX 3: Inject input variables then call the real function with unpacked arg names
          let inputCode = "";
          const argNames = [];
          if (typeof input === "object" && input !== null) {
            for (const [key, value] of Object.entries(input)) {
              inputCode += `${key} = ${JSON.stringify(value)}\n`;
              argNames.push(key);
            }
          }
          // Call the function with the injected variable names as positional args
          inputCode += `_result = ${funcName}(${argNames.join(", ")})`;

          pyodide.runPython(inputCode);
          // FIX 4: Use _result (prefixed to avoid collisions) and convert to JS
          const actualOutput = pyodide.globals.get("_result");
          const actualJS = actualOutput?.toJs ? actualOutput.toJs() : actualOutput;

          // FIX 5: Robust comparison — compare JSON strings
          const passed =
            JSON.stringify(actualJS) === JSON.stringify(expectedOutput);

          results.push({
            test_case: i + 1,
            input,
            expected: expectedOutput,
            actual: actualJS,
            passed,
          });

          if (passed) testsPassed++;
        } catch (testError) {
          results.push({
            test_case: i + 1,
            input,
            expected: expectedOutput,
            actual: `Error: ${testError.message}`,
            passed: false,
          });
        }
      }

      stdout = pyodide.runPython("sys.stdout.getvalue()");
      stderr = pyodide.runPython("sys.stderr.getvalue()");
    } catch (error) {
      stderr = error.message;
    }

    const status = testsPassed === testsTotal && testsTotal > 0 ? "Accepted" : "Wrong Answer";

    // FIX 6: Actually return the result object — original code was missing this entirely
    return {
      status,
      tests_total: testsTotal,
      tests_passed: testsPassed,
      results,
      stdout,
      stderr,
    };
  }

  async function handleRun() {
    const trimmed = code.trim();
    const defaultSnippet = starterCode.trim();

    if (
      trimmed === "" ||
      trimmed === defaultSnippet ||
      trimmed === "# write your solution here" ||
      trimmed === "pass"
    ) {
      setStatusText("Please write a solution before running.");
      setOutput("Type your code in the editor before running.");
      return null;
    }

    if (pyodideLoading) {
      setStatusText("Loading Python runtime...");
      setOutput("Please wait while Python runtime loads.");
      return null;
    }

    if (pyodideError) {
      setStatusText("Python runtime error");
      setOutput(`Failed to load Python runtime: ${pyodideError}`);
      return null;
    }

    setIsRunning(true);
    setOutput("");
    setStatusText("Running...");
    setClarityResult(null);
    setSubmissionComplete(false);
    setTestResults(null);

    const cases = activeQuestion?.testcases?.cases || [];
    let runSnapshot = null;

    try {
      const result = await executeWithPyodide(code, cases);

      const {
        status,
        tests_total,
        tests_passed,
        failing_tests = [],
        stdout = "",
        stderr = "",
        results = [],
      } = result;

      const isAccepted = status === "Accepted";
      const scoreText = tests_total > 0 ? `${tests_passed}/${tests_total}` : "0/0";

      if (stderr && !isAccepted) {
        setOutput(`Score: ${scoreText}\n\n${stderr}`);
      } else {
        setOutput(`Score: ${scoreText}${stdout ? `\n\n${stdout}` : ""}`);
      }

      setStatusText(`${status}  •  score: ${scoreText}`);

      if (!isAccepted) setFailedRuns((c) => c + 1);
      if (results.length > 0) setTestResults(results);

      runSnapshot = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        languageKey,
        languageId,
        code,
        status,
        status_id: isAccepted ? 3 : 4,
        tests_total,
        tests_passed,
        failing_tests,
      };

      setHistory((prev) => [runSnapshot, ...prev.slice(0, 19)]);
    } catch (err) {
      console.error("[executeWithPyodide]", err);
      setOutput(`Failed to execute code locally.\nError: ${err.message}`);
      setStatusText("Execution Failed");
      setFailedRuns((c) => c + 1);
      runSnapshot = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        languageKey,
        languageId,
        code,
        status: "Execution Failed",
        tests_total: null,
        tests_passed: null,
      };
      setHistory((prev) => [runSnapshot, ...prev.slice(0, 19)]);
    } finally {
      setIsRunning(false);
    }

    return runSnapshot;
  }

  async function handleSubmit() {
    const runSnapshot = await handleRun();
    if (!runSnapshot || runSnapshot.status === "Request Failed") return;

    setSubmissionComplete(true);
    setClarityLoading(true);
    const clarity = evaluateClarity(code);
    setClarityResult(clarity);
    setClarityLoading(false);

    try {
      localStorage.setItem(
        "mockmate-coding-result",
        JSON.stringify({
          status: runSnapshot.status,
          tests_total: runSnapshot.tests_total,
          tests_passed: runSnapshot.tests_passed,
          clarity,
          completedAt: new Date().toISOString(),
        })
      );
    } catch {
      // ignore localStorage errors
    }

    if (embedded && typeof onSubmissionComplete === "function") {
      onSubmissionComplete({
        status: runSnapshot.status,
        tests_total: runSnapshot.tests_total,
        tests_passed: runSnapshot.tests_passed,
        clarity,
      });
    }
  }

  function handleLanguageChange(e) {
    const id = Number(e.target.value);
    const lang = LANGUAGES.find((l) => l.id === id) || LANGUAGES[0];
    setLanguageId(id);
    setLanguageKey(lang.key);
  }

  function handleReset() {
    setCode(starterCode);
    setOutput("");
    setStatusText("");
    setClarityResult(null);
    setSubmissionComplete(false);
    setTestResults(null);
  }

  function restoreRun(run) {
    setLanguageId(run.languageId || 71);
    setLanguageKey(run.languageKey || "python3");
    setCode(run.code || starterCode);
    setStatusText(`Restored run from ${new Date(run.timestamp).toLocaleTimeString()}`);
    setIsHistoryOpen(false);
  }

  const showHint1 = failedRuns >= 2;
  const lastRun = history[0];

  return (
    <div className={`${embedded ? "h-full" : "h-screen"} flex flex-col overflow-hidden bg-[#020617] text-slate-100`}>
      <header className="flex items-center justify-between h-14 border-b border-slate-800 px-4 bg-[#020617] z-50 relative shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-emerald-500">
            <Terminal className="w-7 h-7" />
            {!embedded && (
              <Link
                to="/dashboard"
                className="text-xs font-semibold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-md hover:bg-emerald-500/20 transition"
              >
                Dashboard
              </Link>
            )}
          </div>
          <div className="h-6 w-[1px] bg-slate-800" />
          <div className="flex items-center gap-4">
            <h3 className="text-sm font-medium text-white">{currentProblem.title}</h3>
            <div className="flex h-6 items-center justify-center rounded border px-2 text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border-amber-500/20">
              Medium
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {embedded && onReturnToInterview && (
            <button
              onClick={onReturnToInterview}
              className="px-3 py-1.5 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Back
            </button>
          )}

          <div className="relative">
            <m.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setIsHistoryOpen((p) => !p)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium transition-colors rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700"
            >
              <History className="w-4 h-4" />
              <span>Run History</span>
              <ChevronDown className="w-4 h-4" />
            </m.button>
            {isHistoryOpen && (
              <div className="absolute right-0 z-50 w-72 max-h-96 overflow-auto mt-2 border rounded-lg shadow-lg top-full border-slate-700 bg-[#020617]">
                <div className="px-3 py-2 text-xs font-semibold border-b border-slate-800 text-slate-300">
                  Run History
                </div>
                <div className="p-2 space-y-2 text-[11px] text-slate-300">
                  {history.length === 0 ? (
                    <p className="px-1 py-2 text-slate-500">No runs yet.</p>
                  ) : (
                    history.map((run) => (
                      <button
                        key={run.id}
                        onClick={() => restoreRun(run)}
                        className="w-full text-left rounded border border-slate-700 bg-slate-900/60 px-2 py-1.5 transition hover:bg-slate-800"
                      >
                        <div className="flex justify-between">
                          <span className={`font-semibold ${getStatusClasses(run.status)}`}>{run.status}</span>
                          <span className="text-[10px] text-slate-400">
                            {new Date(run.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="mt-0.5 flex justify-between text-[10px] text-slate-400">
                          <span>{run.languageKey}</span>
                          <span>
                            {typeof run.tests_total === "number"
                              ? `${run.tests_passed}/${run.tests_total} tests`
                              : "Run"}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        <section className="w-[400px] border-r border-slate-800 flex flex-col bg-slate-900/30 overflow-y-auto custom-scrollbar">
          <div className="sticky top-0 bg-[#020617] z-30 border-b border-slate-800">
            <div className="flex px-4">
              <button
                onClick={() => setActiveProblemTab("description")}
                className={`py-3 px-4 text-sm font-medium capitalize transition-colors ${
                  activeProblemTab === "description"
                    ? "border-b-2 border-emerald-500 text-white font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                description
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            <h1 className="mb-2 text-2xl font-bold text-white">{currentProblem.title}</h1>
            <pre className="rounded-lg border border-slate-800 bg-black/40 p-3 font-mono text-xs text-emerald-300 whitespace-pre-wrap">
              {currentProblem.signature}
            </pre>
            <div className="flex flex-wrap gap-2">
              {currentProblem.tags.map((tag) => (
                <span key={tag} className="px-2 py-1 text-xs font-medium rounded bg-slate-800 text-slate-300">
                  {tag}
                </span>
              ))}
            </div>

            <p className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">{currentProblem.description}</p>

            <div className="space-y-4">
              <h4 className="text-sm font-bold tracking-wider text-white uppercase">Examples:</h4>
              {currentProblem.samples.map((sample, idx) => (
                <div key={idx} className="p-4 border rounded-lg bg-black/40 border-slate-800">
                  <div className="space-y-2 font-mono text-xs">
                    <p>
                      <span className="text-slate-500">Input:</span> <span className="text-slate-200">{sample.input}</span>
                    </p>
                    <p>
                      <span className="text-slate-500">Output:</span> <span className="text-slate-200">{sample.output}</span>
                    </p>
                    {sample.explanation && (
                      <p>
                        <span className="text-slate-500">Explanation:</span> <span className="text-slate-400">{sample.explanation}</span>
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {showHint1 && (
              <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 text-sm text-indigo-200">
                Hint: Double-check edge cases and return value types for all inputs.
              </div>
            )}
          </div>
        </section>

        <section className="flex flex-col flex-1 min-w-0 border-r border-slate-800">
          <div className="relative z-20 flex items-center justify-between h-10 px-3 border-b border-slate-800 bg-slate-900/20 shrink-0">
            <div className="flex items-center gap-2">
              <div
                className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded bg-slate-800 text-slate-300"
                onClick={() => {
                  if (languageSelectRef.current) {
                    languageSelectRef.current.focus();
                    languageSelectRef.current.click?.();
                  }
                }}
              >
                <select
                  ref={languageSelectRef}
                  value={languageId}
                  onChange={handleLanguageChange}
                  disabled
                  className="pr-5 text-xs bg-transparent border-none outline-none appearance-none cursor-pointer disabled:cursor-not-allowed"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.id} value={lang.id} className="bg-slate-800">
                      {lang.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 pointer-events-none" />
              </div>
              <m.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleReset}
                className="p-1 rounded hover:bg-slate-800 text-slate-400"
              >
                <RotateCcw className="w-4 h-4" />
              </m.button>
            </div>

            <div className="items-center hidden gap-3 lg:flex">
              <m.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleRun}
                disabled={isRunning || pyodideLoading}
                className="flex items-center gap-2 px-3 py-1 text-sm font-medium transition-all rounded-md text-slate-300 hover:bg-slate-800 disabled:opacity-60"
              >
                <Play className="w-4 h-4" />
                <span>
                  {pyodideLoading ? "Loading Python..." : isRunning ? "Running..." : "Run"}
                </span>
              </m.button>
              <m.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSubmit}
                disabled={isRunning}
                className="flex items-center gap-2 px-4 py-1 text-sm font-bold text-white transition-all rounded-md bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60"
              >
                <Upload className="w-4 h-4" />
                <span>Submit</span>
              </m.button>
            </div>
          </div>

          <div className="flex-1 min-h-0 bg-[#010409]">
            <Editor
              height="100%"
              language="python"
              theme={editorTheme}
              value={code}
              onChange={(value) => setCode(value ?? "")}
              options={{
                fontSize: editorFontSize,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                wordWrap: "on",
                fontFamily: "'Fira Code', 'Courier New', monospace",
                lineNumbers: "on",
                renderLineHighlight: "all",
                padding: { top: 8, bottom: 8 },
              }}
            />
          </div>
        </section>

        <section className="w-[420px] flex flex-col bg-slate-900/10 min-h-0">
          <div className="flex flex-col min-h-0 border-b h-1/3 border-slate-800">
            <div className="relative z-20 flex items-center justify-between h-10 px-4 border-b bg-slate-800/30 border-slate-800/50 shrink-0">
              <span className="text-xs font-bold tracking-widest uppercase text-slate-400">Testcase Input</span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-bold">
                {currentProblem.testcases.length} CASES
              </span>
            </div>
            <div className="flex-1 min-h-0 p-4">
              <textarea
                value={currentProblem.testcases
                  .map((testCase, idx) => `Case ${idx + 1}: ${JSON.stringify(testCase.input)}`)
                  .join("\n")}
                readOnly
                spellCheck={false}
                className="w-full h-full bg-[#0d1117] border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 outline-none resize-none"
              />
            </div>
          </div>

          <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
            <div className="relative z-20 flex items-center h-10 px-4 border-b bg-slate-800/30 border-slate-800/50 shrink-0">
              <span className="text-xs font-bold tracking-widest uppercase text-slate-400">Output & Results</span>
            </div>
            <div className="flex-1 min-h-0 p-4 space-y-4 overflow-y-auto custom-scrollbar">
              <div className="text-xs text-slate-400">{statusText || "Ready"}</div>

              {lastRun && lastRun.status.toLowerCase().includes("accepted") && (
                <m.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex items-center gap-3 p-3 border rounded-lg bg-emerald-500/10 border-emerald-500/20"
                >
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                  <div>
                    <p className="text-sm font-bold leading-none text-white">Accepted</p>
                    <p className="mt-1 text-xs text-emerald-500/70">
                      Score: {lastRun.tests_passed}/{lastRun.tests_total}
                    </p>
                  </div>
                </m.div>
              )}

              <pre className="p-3 font-mono text-xs whitespace-pre-wrap rounded bg-slate-950/60 text-slate-100">
                {output || "Type your code and run to see output here."}
              </pre>

              {testResults && testResults.length > 0 && (
                <m.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
                  <h5 className="text-[10px] font-bold tracking-widest uppercase text-slate-400 px-1">
                    Test Cases - {testResults.filter((r) => r.passed).length}/{testResults.length} passed
                  </h5>
                  {testResults.map((r, i) => (
                    <div
                      key={i}
                      className={`rounded-lg border px-3 py-2 text-xs font-mono ${
                        r.passed ? "bg-emerald-500/5 border-emerald-500/20" : "bg-rose-500/5 border-rose-500/20"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-slate-300">Case {i + 1}</span>
                        {r.passed ? (
                          <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <XCircle className="w-3.5 h-3.5 text-rose-400" />
                        )}
                      </div>
                      <div className="text-slate-400 space-y-0.5">
                        <p>
                          <span className="text-slate-500">Input: </span>
                          {formatInput(r.input || {})}
                        </p>
                        <p>
                          <span className="text-slate-500">Expected: </span>
                          <span className="text-emerald-400/80">{JSON.stringify(r.expected)}</span>
                        </p>
                        {!r.passed && (
                          <p>
                            <span className="text-slate-500">Got: </span>
                            <span className="text-rose-400/80">{JSON.stringify(r.actual)}</span>
                          </p>
                        )}
                        {r.error && (
                          <p className="text-rose-400/70 whitespace-pre-wrap mt-1">
                            {r.error.split("\n").slice(-3).join("\n")}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </m.div>
              )}

              {clarityResult && embedded && submissionComplete && (
                <m.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 border rounded-xl bg-slate-900/60 border-slate-800"
                >
                  <h5 className="mb-2 text-xs font-bold text-indigo-400">CLARITY CHECK</h5>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-white">{clarityResult.label}</p>
                      <p className="text-xs text-slate-400">Score: {clarityResult.score}/100</p>
                    </div>
                    <div className="text-xs text-slate-400">{clarityLoading ? "Analyzing..." : "Complete"}</div>
                  </div>
                </m.div>
              )}
            </div>
          </div>
        </section>
      </div>

      <footer className="relative z-10 h-6 bg-slate-900 border-t border-slate-800 px-4 flex items-center justify-between text-[10px] font-medium text-slate-500 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Online</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span>UTF-8</span>
          <span>{LANGUAGES.find((l) => l.id === languageId)?.label}</span>
        </div>
      </footer>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
      `}</style>
    </div>
  );
}