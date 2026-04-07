// src/pages/InterviewerSignup.tsx — Company Registration
import { useState } from "react";
import { m } from "framer-motion";
import { Building2, Lock, Eye, EyeOff, FileText, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { insertCompanyDetails } from "../services/companyAuthService";
import toast from "react-hot-toast";

const INDUSTRY_TYPES = [
  "IT", "Finance", "Healthcare", "Education", "E-Commerce",
  "Manufacturing", "Retail", "Consulting", "Legal", "Media & Entertainment", "Other"
];

const COMPANY_SIZES = [
  { label: "1–50", value: "50" },
  { label: "51–200", value: "200" },
  { label: "201–500", value: "500" },
  { label: "501–1000", value: "1K" },
  { label: "1001–5000", value: "2K" },
  { label: "5000+", value: "5K+" },
];

export default function InterviewerSignup() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({
    companyName: "",
    password: "",       // used as suffix in cmpy_id and as sign-in password
    industryType: "IT",
    companySize: "2K",
    companyDescription: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = (key: string, value: string) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setErrors(prev => ({ ...prev, [key]: "" }));
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.companyName.trim()) e.companyName = "Company name is required";
    if (form.password.length < 6) e.password = "Password must be at least 6 characters";
    if (!form.companyDescription.trim()) e.companyDescription = "Description is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);

    // cmpy_id = slug_password (e.g. "infotech_546738")
    // This becomes the sign-in password too
    // const slug = form.companyName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    const cmpy_id = `${form.password}`;

    const result = await insertCompanyDetails({
      cmpy_id,
      company_name: form.companyName,
      industry_type: form.industryType,
      company_size: form.companySize,
      company_description: form.companyDescription,
    });

    setLoading(false);

    if (result.success) {
      localStorage.setItem("cmpy_id", cmpy_id);
      localStorage.setItem("company_name", form.companyName);
      localStorage.setItem("userType", "company");
      toast.success("Company registered! Sign in to continue.");
      navigate("/interviewer/login");
    } else if (result.message?.toLowerCase().includes("already exists")) {
      toast("Company already registered — sign in below.", { icon: "ℹ️" });
      navigate("/interviewer/login");
    } else {
      toast.error(result.message || "Registration failed. Please try again.");
    }
  };

  return (
    <div className="relative min-h-screen bg-[#0a0e1a] flex flex-col overflow-x-hidden">
      <main className="flex flex-col items-center justify-start flex-1 px-4 py-12">

        <div className="mb-10 text-center">
          <br /><br /><br />
          <h1 className="mb-3 text-4xl font-bold text-white">Company Registration</h1>
          <p className="text-lg text-slate-400">Register your company to start AI-powered interviews.</p>
        </div>

        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-xl backdrop-blur-md bg-white/3 border border-white/10 rounded-xl shadow-2xl"
        >
          <form onSubmit={handleSubmit} className="p-8 space-y-5">

            {/* Company Name */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">Company Name</label>
              <div className="relative">
                <Building2 className="absolute w-5 h-5 -translate-y-1/2 text-slate-500 left-4 top-1/2" />
                <input
                  type="text"
                  value={form.companyName}
                  onChange={e => set("companyName", e.target.value)}
                  className={`w-full bg-white/5 border ${errors.companyName ? "border-rose-500" : "border-white/10"} rounded-lg pl-12 pr-4 py-3 focus:border-[#0d59f2] focus:ring-1 focus:ring-[#0d59f2] outline-none transition-all placeholder:text-white/20 text-white`}
                  placeholder="e.g. Doctech"
                />
              </div>
              {errors.companyName && <p className="text-xs text-rose-400">{errors.companyName}</p>}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">Password</label>
              <p className="text-xs text-slate-500">This will be your sign-in password</p>
              <div className="relative">
                <Lock className="absolute w-5 h-5 -translate-y-1/2 text-slate-500 left-4 top-1/2" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={e => set("password", e.target.value)}
                  className={`w-full bg-white/5 border ${errors.password ? "border-rose-500" : "border-white/10"} rounded-lg pl-12 pr-12 py-3 focus:border-[#0d59f2] focus:ring-1 focus:ring-[#0d59f2] outline-none transition-all placeholder:text-white/20 text-white`}
                  placeholder="e.g. 546738"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute -translate-y-1/2 text-slate-500 hover:text-slate-300 right-4 top-1/2"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-rose-400">{errors.password}</p>}
            </div>

            {/* Industry Type */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">Industry Type</label>
              <select
                value={form.industryType}
                onChange={e => set("industryType", e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 focus:border-[#0d59f2] outline-none transition-all appearance-none text-white"
              >
                {INDUSTRY_TYPES.map(t => <option key={t} value={t} className="bg-[#0a0e1a]">{t}</option>)}
              </select>
            </div>

            {/* Company Size */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">Company Size</label>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
                {COMPANY_SIZES.map(s => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => set("companySize", s.value)}
                    className={`py-2 px-3 rounded-lg border text-sm font-medium transition-all ${form.companySize === s.value
                      ? "border-[#0d59f2] bg-[#0d59f2]/20 text-white"
                      : "border-white/10 bg-white/5 text-slate-400 hover:border-white/30"
                      }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Company Description */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-300">Company Description</label>
              <div className="relative">
                <FileText className="absolute w-5 h-5 text-slate-500 left-4 top-4" />
                <textarea
                  value={form.companyDescription}
                  onChange={e => set("companyDescription", e.target.value)}
                  className={`w-full bg-white/5 border ${errors.companyDescription ? "border-rose-500" : "border-white/10"} rounded-lg pl-12 pr-4 py-3 focus:border-[#0d59f2] outline-none transition-all placeholder:text-white/20 text-white resize-none`}
                  placeholder="e.g. Best for medical software development."
                  rows={3}
                />
              </div>
              {errors.companyDescription && <p className="text-xs text-rose-400">{errors.companyDescription}</p>}
            </div>

            {/* Submit */}
            <m.button
              type="submit"
              disabled={loading}
              whileTap={{ scale: 0.97 }}
              className="w-full py-3 bg-[#0d59f2] hover:bg-blue-600 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-[#0d59f2]/20 disabled:opacity-50 mt-2"
            >
              {loading ? "Registering..." : "Register Company"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </m.button>

            <p className="text-sm text-center text-slate-500">
              Already registered?{" "}
              <button type="button" onClick={() => navigate("/interviewer/login")} className="font-semibold text-blue-500 hover:underline">
                Sign In
              </button>
            </p>
          </form>
        </m.div>
      </main>

      <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#0d59f2]/5 blur-[120px] rounded-full -z-10" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-blue-500/5 blur-[120px] rounded-full -z-10" />
    </div>
  );
}
