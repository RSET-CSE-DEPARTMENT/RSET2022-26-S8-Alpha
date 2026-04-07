import { useEffect, useMemo, useState } from "react";
import { m } from "framer-motion";
import {
  Clock,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
} from "lucide-react";
import toast from "react-hot-toast";
import { loadAptitudeQuestions, generateMockAptitudeQuestions } from "../services/interviewApi";

function normalizeQuestions(rawQuestions) {
  if (!Array.isArray(rawQuestions)) return [];

  return rawQuestions
    .filter((q) => q && q.question && q.options)
    .map((q, index) => {
      const optionEntries = Object.entries(q.options || {}).sort(([a], [b]) =>
        a.localeCompare(b)
      );
      const options = optionEntries.map(([key, value]) => ({
        key,
        text: String(value ?? ""),
      }));

      return {
        id: q.id ?? index + 1,
        text: q.question,
        options,
        correctAnswer: String(q.correctAnswer ?? ""),
        skill: q.skill || "General",
        difficulty: q.difficulty || "Medium",
      };
    });
}

function getDifficultyStyles(difficulty) {
  const value = String(difficulty || "").toLowerCase();
  if (value === "easy") return "bg-green-500/20 text-green-400";
  if (value === "hard") return "bg-red-500/20 text-red-400";
  return "bg-yellow-500/20 text-yellow-400";
}

export default function AptitudeTest({ embedded = false, onComplete } = {}) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState({});
  const [timeRemaining, setTimeRemaining] = useState(15 * 60);
  const [showSummary, setShowSummary] = useState(false);
  const [reportedSummary, setReportedSummary] = useState(false);

  const questions = useMemo(() => {
    const loadedQuestions = loadAptitudeQuestions();
    if (loadedQuestions.length > 0) {
      return normalizeQuestions(loadedQuestions);
    } else {
      // Fallback to mock questions if no questions are loaded
      console.log("[AptitudeTest] No questions loaded, using mock questions");
      return normalizeQuestions(generateMockAptitudeQuestions());
    }
  }, []);

  const totalQuestions = questions.length;
  const question = questions[currentQuestion];

  useEffect(() => {
    if (showSummary || totalQuestions === 0) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setShowSummary(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [showSummary, totalQuestions]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSelectAnswer = (questionId, answerKey) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answerKey }));
  };

  const handleNextQuestion = () => {
    if (!question) return;
    if (answers[question.id] === undefined) {
      toast.error("Choose any one of the options");
      return;
    }
    if (currentQuestion < totalQuestions - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      setShowSummary(true);
      setReportedSummary(false);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestion > 0) setCurrentQuestion(currentQuestion - 1);
  };

  const handleSkipQuestion = () => {
    if (currentQuestion < totalQuestions - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      setShowSummary(true);
      setReportedSummary(false);
    }
  };

  const correctCount = questions.reduce((count, q) => {
    if (answers[q.id] === q.correctAnswer) return count + 1;
    return count;
  }, 0);
  const skippedCount = totalQuestions - Object.keys(answers).length;
  const percentage =
    totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;

  useEffect(() => {
    if (showSummary && !reportedSummary && typeof onComplete === "function") {
      onComplete({ correctCount, totalQuestions, percentage });
      setReportedSummary(true);
    }
  }, [showSummary, reportedSummary, onComplete, correctCount, totalQuestions, percentage]);

  if (totalQuestions === 0) {
    return (
      <div className={`${embedded ? "h-full overflow-y-auto" : "min-h-screen"} bg-[#0a0e1a] text-white flex flex-col`}>
        <div className="flex items-center justify-center flex-1 px-6">
          <div className="max-w-xl p-6 text-center border rounded-xl border-slate-700 bg-slate-900/40">
            <h2 className="text-xl font-bold">No aptitude questions available</h2>
            <p className="mt-3 text-sm text-slate-400">
              Questions are loaded when the candidate uploads the resume.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!showSummary) {
    return (
      <div className={`${embedded ? "h-full overflow-y-auto" : "min-h-screen"} bg-[#0a0e1a] text-white flex flex-col`}>
        <header className="border-b border-slate-700/50 px-6 py-4 bg-[#0f1424]/50 backdrop-blur">
          <div className="flex items-center justify-between max-w-6xl mx-auto">
            <div className="flex items-center gap-2">
              {[...Array(totalQuestions)].map((_, i) => (
                <m.button
                  key={i}
                  onClick={() => setCurrentQuestion(i)}
                  className={`w-10 h-10 rounded-lg font-semibold text-sm transition ${
                    i === currentQuestion
                      ? "bg-blue-600 text-white"
                      : answers[questions[i].id] !== undefined
                      ? "bg-green-600/30 text-green-400 border border-green-500/50"
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {i + 1}
                </m.button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-orange-400" />
              <span className="font-mono text-lg font-bold text-orange-400">
                {formatTime(timeRemaining)}
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 w-full max-w-4xl min-h-0 px-6 py-6 mx-auto overflow-y-auto">
          <m.div
            key={currentQuestion}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-5"
          >
            <div>
              <div className="flex items-center gap-3 mb-3">
                <span className="text-sm font-semibold text-blue-400">
                  Question {currentQuestion + 1}
                </span>
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${getDifficultyStyles(question.difficulty)}`}>
                  {question.difficulty}
                </span>
                <span className="text-xs font-semibold px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300">
                  {question.skill}
                </span>
              </div>
              <h2 className="text-lg font-bold leading-snug text-white">{question.text}</h2>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-wider uppercase text-slate-400">Answer</p>
              <div className="space-y-2">
                {question.options.map((option) => (
                  <m.button
                    key={option.key}
                    onClick={() => handleSelectAnswer(question.id, option.key)}
                    whileHover={{ scale: 1.01 }}
                    className={`w-full p-3 rounded-lg border text-left transition ${
                      answers[question.id] === option.key
                        ? "border-blue-500 bg-blue-500/20"
                        : "border-slate-700 bg-slate-900/30 hover:border-slate-600"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg border border-slate-600 bg-slate-800 text-slate-300 text-xs font-bold flex items-center justify-center">
                        {option.key}
                      </div>
                      <div
                        className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center ${
                          answers[question.id] === option.key
                            ? "border-blue-500 bg-blue-500"
                            : "border-slate-600"
                        }`}
                      >
                        {answers[question.id] === option.key && (
                          <CheckCircle className="w-4 h-4 text-white" />
                        )}
                      </div>
                      <span className="text-white">{option.text}</span>
                    </div>
                  </m.button>
                ))}
              </div>
            </div>
          </m.div>
        </main>

        <footer className="border-t border-slate-700/50 px-6 py-4 bg-[#0f1424]/50 backdrop-blur shrink-0">
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <button
              onClick={handlePreviousQuestion}
              disabled={currentQuestion === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold transition rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
              Previous
            </button>
            <span className="text-slate-400">
              Question {currentQuestion + 1} of {totalQuestions}
            </span>
            <div className="flex items-center gap-3">
              <button
                onClick={handleSkipQuestion}
                className="px-4 py-2 text-sm font-semibold transition rounded-lg bg-slate-800 hover:bg-slate-700"
              >
                Skip
              </button>
              {currentQuestion === totalQuestions - 1 ? (
                <button
                  onClick={handleNextQuestion}
                  className="px-6 py-2 text-sm font-semibold transition bg-green-600 rounded-lg hover:bg-green-700"
                >
                  Finish Test
                </button>
              ) : (
                <button
                  onClick={handleNextQuestion}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-semibold transition bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Next
                  <ChevronRight className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <div className={`${embedded ? "h-full overflow-y-auto" : "min-h-screen"} bg-[#0a0e1a] text-white flex flex-col`}>
      <header className="border-b border-slate-700/50 px-6 py-4 bg-[#0f1424]/50 backdrop-blur">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <h1 className="text-2xl font-bold">Aptitude Test</h1>
          <div />
        </div>
      </header>

      <main className="flex-1 w-full max-w-6xl px-6 py-12 mx-auto overflow-y-auto">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <div className="space-y-8">
              <div className="p-8 text-center bg-linear-to-br from-blue-600 to-blue-800 rounded-2xl">
                <p className="mb-2 text-slate-300">Total Score</p>
                <div className="mb-2 text-6xl font-bold text-white">{correctCount}/{totalQuestions}</div>
                <p className="text-slate-200">{percentage}%</p>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <p className="mb-1 text-sm text-slate-400">Questions Attempted</p>
                  <p className="text-2xl font-bold text-white">{totalQuestions - skippedCount}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <p className="mb-1 text-sm text-slate-400">Questions Skipped</p>
                  <p className="text-2xl font-bold text-slate-300">{skippedCount}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <p className="mb-1 text-sm text-slate-400">Correct</p>
                  <p className="text-2xl font-bold text-green-400">{correctCount}</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <p className="mb-1 text-sm text-slate-400">Incorrect</p>
                  <p className="text-2xl font-bold text-red-400">{totalQuestions - correctCount}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <h2 className="mb-6 text-2xl font-bold">Question Review</h2>
            <div className="space-y-4 overflow-y-auto max-h-96">
              {questions.map((q, idx) => {
                const isCorrect = answers[q.id] === q.correctAnswer;
                const isAnswered = answers[q.id] !== undefined;
                return (
                  <m.div
                    key={q.id}
                    whileHover={{ scale: 1.01 }}
                    className="p-4 transition border rounded-lg bg-slate-800/50 border-slate-700"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-semibold text-white">Question {idx + 1}</p>
                        <p className="mt-1 text-sm text-slate-400 line-clamp-2">{q.text}</p>
                      </div>
                      <div className="shrink-0">
                        {!isAnswered ? (
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-slate-700">
                            <span className="text-xs text-slate-400">-</span>
                          </div>
                        ) : isCorrect ? (
                          <div className="flex items-center justify-center w-8 h-8 border border-green-500 rounded-full bg-green-600/20">
                            <span className="text-green-400">+</span>
                          </div>
                        ) : (
                          <div className="flex items-center justify-center w-8 h-8 border border-red-500 rounded-full bg-red-600/20">
                            <span className="text-red-400">x</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </m.div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
