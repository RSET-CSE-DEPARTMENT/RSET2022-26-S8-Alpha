import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { m } from "framer-motion";
import { User, Hash, Lock, Loader, Building2 } from "lucide-react";
import { candidateLogin, saveCandidateSession } from "../services/candidateAuthService";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ candidateId: "", interviewId: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleFormChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError("");
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    
    if (!form.candidateId.trim()) {
      setError("Candidate ID is required");
      return;
    }
    if (!form.interviewId.trim()) {
      setError("Interview ID is required");
      return;
    }

    setLoading(true);
    setError("");

    // Test login functionality for developers
    if (form.candidateId === "test" && form.interviewId === "test") {
      // Save session
      saveCandidateSession(form.candidateId, form.interviewId);
      setSuccess("Test login successful! Redirecting to interview...");
      setTimeout(() => {
        navigate("/interview", {
          state: {
            candidateId: form.candidateId,
            interviewId: form.interviewId,
          },
        });
      }, 1500);
      return;
    }

    const result = await candidateLogin({
      candidate_id: form.candidateId,
      interview_id: form.interviewId,
    });

    if (result.status) {
      // Save session
      saveCandidateSession(form.candidateId, form.interviewId);
      setSuccess("Login successful! Redirecting to interview...");
      setTimeout(() => {
        navigate("/interview", {
          state: {
            candidateId: form.candidateId,
            interviewId: form.interviewId,
          },
        });
      }, 1500);
    } else {
      setError(result.message || "Login failed. Please check your credentials.");
    }

    setLoading(false);
  };

  return (
    <>
      <div className="flex w-full min-h-screen pt-16 bg-slate-950 md:pt-20">
        {/* Left Section: Authentication Form */}
        <div className="flex flex-col justify-center w-full h-full px-6 py-8 overflow-y-auto lg:w-1/2 md:px-12 lg:px-20">
          <m.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-[440px] mx-auto w-full"
          >
            {/* Header */}
            <div className="mb-5">
              <h1 className="text-3xl font-black tracking-tight text-white">
                Join Interview
              </h1>
              <p className="mt-2 text-sm text-slate-400">
                Enter the Interview ID and Candidate ID provided by your company
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <m.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="px-4 py-3 mb-5 text-sm border rounded-lg bg-rose-500/10 border-rose-500/20 text-rose-400"
              >
                {error}
              </m.div>
            )}

            {/* Success Message */}
            {success && (
              <m.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="px-4 py-3 mb-5 text-sm border rounded-lg bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              >
                {success}
              </m.div>
            )}

            {/* Form */}
            <form onSubmit={handleLogin} className="space-y-4" noValidate>
              {/* Interview ID Field */}
              <div className="flex flex-col gap-2">
                <label
                  htmlFor="interviewId"
                  className="ml-1 text-sm font-medium text-slate-300"
                >
                  Interview ID <span className="text-xs text-slate-500">(provided by company)</span>
                </label>
                <div className="relative">
                  <Hash className="absolute w-5 h-5 -translate-y-1/2 text-slate-500 left-4 top-1/2" />
                  <input
                    id="interviewId"
                    name="interviewId"
                    type="text"
                    value={form.interviewId}
                    onChange={handleFormChange}
                    className="w-full p-3 pl-12 text-white transition-all border outline-none bg-slate-900 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder:text-slate-500 border-slate-700"
                    placeholder="e.g. 1db56462-154a-11f1-b948-c9692e84c1a5"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Candidate ID Field */}
              <div className="flex flex-col gap-2">
                <label
                  htmlFor="candidateId"
                  className="ml-1 text-sm font-medium text-slate-300"
                >
                  Candidate ID <span className="text-xs text-slate-500">(provided by company)</span>
                </label>
                <div className="relative">
                  <User className="absolute w-5 h-5 -translate-y-1/2 text-slate-500 left-4 top-1/2" />
                  <input
                    id="candidateId"
                    name="candidateId"
                    type="text"
                    value={form.candidateId}
                    onChange={handleFormChange}
                    className="w-full p-3 pl-12 text-white transition-all border outline-none bg-slate-900 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder:text-slate-500 border-slate-700"
                    placeholder="e.g. matt_652354331"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Submit Button */}
              <div className="w-full">
                <m.button
                  type="submit"
                  disabled={loading}
                  aria-busy={loading}
                  whileTap={{ scale: 0.97 }}
                  className="w-full push-button-scale"
                >
                  <div className="push-button">
                    <div className="button-outer">
                      <div className="button-inner">
                        <span>{loading ? "Joining..." : "Join Interview"}</span>
                      </div>
                    </div>
                  </div>
                </m.button>
              </div>
            </form>

            {/* Test Login Note */}
            <p className="text-center text-xs text-slate-500 mt-4">
              For testing: use 'test' for both Candidate ID and Interview ID
            </p>

            {/* Interviewer Button */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-700/60"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="px-4 tracking-widest bg-slate-950 text-slate-500">or</span>
              </div>
            </div>
            <m.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate("/interviewer/login")}
              className="interviewer-btn-scale"
            >
              <div className="interviewer-button-wrap">
                <button type="button" className="interviewer-button">
                  <span className="flex items-center gap-3">
                    <Building2 className="w-5 h-5" />
                    Continue as an Interviewer
                  </span>
                </button>
                <div className="interviewer-button-shadow"></div>
              </div>
            </m.button>
          </m.div>
        </div>

        {/* Right Section: Visual Content with Overlay */}
        <div className="relative hidden min-h-screen lg:block lg:w-1/2">
          {/* Background Image */}
          <img
            src="https://images.unsplash.com/photo-1517694712202-14dd9538aa97?q=80&w=2070"
            alt="Developer workspace"
            className="absolute inset-0 object-cover w-full h-full"
          />
          {/* Overlay */}
          <div className="absolute inset-0 bg-linear-to-t from-slate-950 via-slate-950/60 to-transparent"></div>
          <div className="absolute inset-0 bg-blue-600/20 mix-blend-multiply"></div>
        </div>
      </div>

      {/* Success Toast */}
      {success && (
        <m.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.9 }}
          className="fixed z-50 flex items-center gap-3 px-6 py-4 text-white border rounded-full shadow-2xl bottom-10 right-10 bg-emerald-500/90 backdrop-blur-md border-emerald-400/50"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          <span className="text-sm font-bold">Signed in successfully!</span>
        </m.div>
      )}
    </>
  );
}
