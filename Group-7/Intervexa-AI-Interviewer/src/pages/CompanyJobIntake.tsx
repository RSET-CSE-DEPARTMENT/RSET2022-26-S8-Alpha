import { useState } from "react";
import { m } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Briefcase, Target, Code2, Users, TrendingUp,
  Brain, AlertCircle, CheckCircle2, ChevronDown, ChevronUp, ArrowRight,
  Calendar, Clock
} from "lucide-react";
import { submitObjectiveDatabase, createInterviewDetails } from "../services/companyAuthService";
import toast from "react-hot-toast";

// ─── Types ───────────────────────────────────────────────────────────────────

type WeightsData = {
  date: string;
  time: string;
  aptitude_weightage: number;
  coding_weightage: number;
  technical_interview_weightage: number;
};

type FormData = {
  interview_name: string;
  role_title: string;
  department: string;
  experience_level_required: string;
  employment_level: string;
  core_skills_required: string;
  secondary_skills_required: string;
  tools_and_technologies: string;
  expected_proficiency_level: string;
  objective_role: string;
  key_performance_indicator: string;
  expected_output: string;
  business_impact_role: string;
  communication_level: string;
  team_collaboration_expectation: string;
  leadership_requirements: string;
  learning_and_adaptability: string;
  decision_making_capability: string;
};

const EMPTY_WEIGHTS: WeightsData = {
  date: "",
  time: "",
  aptitude_weightage: 33,
  coding_weightage: 33,
  technical_interview_weightage: 34,
};

const EMPTY: FormData = {
  interview_name: "",
  role_title: "",
  department: "",
  experience_level_required: "",
  employment_level: "",
  core_skills_required: "",
  secondary_skills_required: "",
  tools_and_technologies: "",
  expected_proficiency_level: "",
  objective_role: "",
  key_performance_indicator: "",
  expected_output: "",
  business_impact_role: "",
  communication_level: "",
  team_collaboration_expectation: "",
  leadership_requirements: "",
  learning_and_adaptability: "",
  decision_making_capability: "",
};

// ─── Field metadata for layout ────────────────────────────────────────────────

type FieldDef = {
  key: keyof FormData;
  label: string;
  placeholder: string;
  rows?: number;
};

type SectionDef = {
  title: string;
  subtitle: string;
  icon: any;
  color: string;
  fields: FieldDef[];
};

const SECTIONS: SectionDef[] = [
  {
    title: "Interview Overview",
    subtitle: "Basic role and interview identification",
    icon: Briefcase,
    color: "text-blue-400",
    fields: [
      {
        key: "interview_name",
        label: "Interview Name",
        placeholder: "e.g. Backend Developer - Technical Evaluation Round 1",
        rows: 1,
      },
      {
        key: "role_title",
        label: "Role Title",
        placeholder: "e.g. Backend Software Engineer",
        rows: 1,
      },
      {
        key: "department",
        label: "Department",
        placeholder: "e.g. Product Engineering - Core Platform Team",
        rows: 1,
      },
      {
        key: "experience_level_required",
        label: "Experience Level Required",
        placeholder: "e.g. 2-4 years of hands-on backend development experience in production environments with strong understanding of scalable architecture patterns.",
        rows: 3,
      },
      {
        key: "employment_level",
        label: "Employment Level",
        placeholder: "e.g. Mid-Level Individual Contributor responsible for owning backend modules independently.",
        rows: 2,
      },
    ],
  },
  {
    title: "Skills & Technology",
    subtitle: "Required technical skills, tools, and proficiency expectations",
    icon: Code2,
    color: "text-emerald-400",
    fields: [
      {
        key: "core_skills_required",
        label: "Core Skills Required",
        placeholder: "e.g. Strong proficiency in Python programming. Deep understanding of FastAPI or similar asynchronous frameworks. Strong experience with PostgreSQL including indexing, query optimization, joins, and transactions.",
        rows: 4,
      },
      {
        key: "secondary_skills_required",
        label: "Secondary Skills Required",
        placeholder: "e.g. Experience with Docker containerization and environment management. Basic knowledge of AWS services such as EC2, S3, and RDS.",
        rows: 4,
      },
      {
        key: "tools_and_technologies",
        label: "Tools & Technologies",
        placeholder: "e.g. Python 3.10+, FastAPI, PostgreSQL, Supabase, Redis, Docker, Git, GitHub, Linux-based servers, Postman, Swagger.",
        rows: 3,
      },
      {
        key: "expected_proficiency_level",
        label: "Expected Proficiency Level",
        placeholder: "e.g. Candidate should demonstrate intermediate to advanced backend knowledge including independent API design, optimized database querying, debugging production issues, and implementing secure authentication systems.",
        rows: 3,
      },
    ],
  },
  {
    title: "Role Objectives & Impact",
    subtitle: "What the role is meant to achieve for the business",
    icon: Target,
    color: "text-violet-400",
    fields: [
      {
        key: "objective_role",
        label: "Role Objective",
        placeholder: "e.g. Design, develop, and maintain scalable backend systems that power the AI-driven interview platform. Ensure performance optimization, high availability, secure data handling, and smooth integration with AI services.",
        rows: 4,
      },
      {
        key: "key_performance_indicator",
        label: "Key Performance Indicators (KPIs)",
        placeholder: "e.g. API average response time below 200ms under standard load. Zero critical security vulnerabilities. Code coverage above 80 percent. Minimal production defects.",
        rows: 3,
      },
      {
        key: "expected_output",
        label: "Expected Output",
        placeholder: "e.g. Production-ready REST APIs, optimized database schema, efficient queries, proper documentation, structured Git commits, successful integration with frontend and AI modules.",
        rows: 3,
      },
      {
        key: "business_impact_role",
        label: "Business Impact of Role",
        placeholder: "e.g. Backend performance directly influences interview latency, candidate experience, client satisfaction, and infrastructure cost efficiency. This role ensures the platform scales reliably as user demand increases.",
        rows: 3,
      },
    ],
  },
  {
    title: "Collaboration & Communication",
    subtitle: "How the candidate is expected to work with the team",
    icon: Users,
    color: "text-amber-400",
    fields: [
      {
        key: "communication_level",
        label: "Communication Level",
        placeholder: "e.g. Must clearly explain technical decisions, justify architectural trade-offs, describe debugging approaches, and proactively communicate blockers or risks to the team.",
        rows: 3,
      },
      {
        key: "team_collaboration_expectation",
        label: "Team Collaboration Expectation",
        placeholder: "e.g. Collaborate closely with frontend developers for API integration, DevOps engineers for deployment and scaling, and AI engineers for model integration. Participate actively in code reviews and architectural discussions.",
        rows: 3,
      },
    ],
  },
  {
    title: "Leadership & Growth",
    subtitle: "Leadership expectations and adaptability requirements",
    icon: TrendingUp,
    color: "text-rose-400",
    fields: [
      {
        key: "leadership_requirements",
        label: "Leadership Requirements",
        placeholder: "e.g. No direct people management required. However, expected to take ownership of backend components, mentor junior developers when needed, and demonstrate accountability and initiative.",
        rows: 3,
      },
      {
        key: "learning_and_adaptability",
        label: "Learning & Adaptability",
        placeholder: "e.g. Demonstrate continuous learning mindset. Stay updated with backend best practices and adapt to evolving AI system requirements. Be open to feedback and iterative improvements.",
        rows: 3,
      },
    ],
  },
  {
    title: "Decision Making",
    subtitle: "Scope of independent judgment expected from the candidate",
    icon: Brain,
    color: "text-cyan-400",
    fields: [
      {
        key: "decision_making_capability",
        label: "Decision Making Capability",
        placeholder: "e.g. Capable of independently deciding database schema design, API structure, caching strategies, error handling mechanisms, and system improvements while justifying decisions with strong technical reasoning.",
        rows: 3,
      },
    ],
  },
];

// ─── Reusable field components ────────────────────────────────────────────────

const FieldInput = ({
  label,
  value,
  onChange,
  placeholder,
  rows = 1,
  hasError,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  rows?: number;
  hasError?: boolean;
}) => (
  <div className="flex flex-col gap-2">
    <label className="text-sm font-semibold text-slate-300">{label}</label>
    {rows <= 1 ? (
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full p-3 rounded-lg border outline-none transition-all bg-slate-900/60 text-slate-100 placeholder:text-slate-600 ${hasError
          ? "border-rose-500 focus:border-rose-400"
          : "border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
          }`}
      />
    ) : (
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className={`w-full p-3 rounded-lg border outline-none transition-all resize-y bg-slate-900/60 text-slate-100 placeholder:text-slate-600 leading-relaxed ${hasError
          ? "border-rose-500 focus:border-rose-400"
          : "border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
          }`}
      />
    )}
    {hasError && <p className="text-xs text-rose-400">This field is required.</p>}
  </div>
);

// ─── Collapsible Section ──────────────────────────────────────────────────────

const Section = ({
  section,
  index,
  formData,
  errors,
  onChange,
}: {
  section: SectionDef;
  index: number;
  formData: FormData;
  errors: Set<keyof FormData>;
  onChange: (key: keyof FormData, value: string) => void;
}) => {
  const [open, setOpen] = useState(true);
  const Icon = section.icon;
  const sectionErrors = section.fields.filter((f) => errors.has(f.key)).length;

  return (
    <m.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden"
    >
      {/* Section Header */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-slate-800 ${section.color}`}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="text-left">
            <p className="font-semibold text-white">
              {index + 1}. {section.title}
            </p>
            <p className="text-xs text-slate-500">{section.subtitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {sectionErrors > 0 && (
            <span className="text-xs text-rose-400 font-medium">{sectionErrors} required</span>
          )}
          {open ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </div>
      </button>

      {/* Section Body */}
      {open && (
        <div className="px-6 pb-6 pt-2 grid grid-cols-1 gap-5">
          {section.fields.map((f) => (
            <FieldInput
              key={f.key}
              label={f.label}
              value={formData[f.key]}
              onChange={(v) => onChange(f.key, v)}
              placeholder={f.placeholder}
              rows={f.rows}
              hasError={errors.has(f.key)}
            />
          ))}
        </div>
      )}
    </m.div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CompanyJobIntake() {
  const navigate = useNavigate();

  // ─── Step 1: Weights Collection ───────────────────────────────────────────
  const [step, setStep] = useState<0 | 1>(0); // 0 = weights, 1 = objective form
  const [weightsData, setWeightsData] = useState<WeightsData>(EMPTY_WEIGHTS);
  const [weightsErrors, setWeightsErrors] = useState<Set<keyof WeightsData>>(new Set());
  const [isCreatingInterview, setIsCreatingInterview] = useState(false);
  const [interviewId, setInterviewId] = useState<string>("");
  const [weightsValidationError, setWeightsValidationError] = useState("");

  // ─── Step 2: Objective Form ───────────────────────────────────────────────
  const [formData, setFormData] = useState<FormData>(EMPTY);
  const [errors, setErrors] = useState<Set<keyof FormData>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [validationError, setValidationError] = useState("");

  const REQUIRED: (keyof FormData)[] = [
    "interview_name",
    "role_title",
    "department",
    "core_skills_required",
    "objective_role",
  ];

  // ─── Weights Form Handlers ────────────────────────────────────────────────

  const handleWeightsChange = (key: keyof WeightsData, value: string | number) => {
    setWeightsData((prev) => ({ ...prev, [key]: value }));
    if (weightsErrors.has(key)) {
      setWeightsErrors((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  const validateWeights = (): boolean => {
    const missing = new Set<keyof WeightsData>();
    if (!weightsData.date.trim()) missing.add("date");
    if (!weightsData.time.trim()) missing.add("time");

    // Validate weightages sum to 100
    const total =
      weightsData.aptitude_weightage +
      weightsData.coding_weightage +
      weightsData.technical_interview_weightage;

    if (total === 0) {
      setWeightsValidationError("Please set at least one weightage.");
      return false;
    }

    setWeightsErrors(missing);
    if (missing.size > 0) {
      setWeightsValidationError("Please fill in the required fields.");
      return false;
    }
    setWeightsValidationError("");
    return true;
  };

  const handleWeightsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateWeights()) return;

    setIsCreatingInterview(true);

    const cmpy_id =
      localStorage.getItem("cmpy_id") || "default_company_" + Date.now();

    const payload = {
      cmpy_id,
      date: weightsData.date,
      time: weightsData.time,
      aptitude_weightage: weightsData.aptitude_weightage,
      coding_weightage: weightsData.coding_weightage,
      technical_interview_weightage: weightsData.technical_interview_weightage,
    };

    console.log("📅 Interview Creation Payload:", JSON.stringify(payload, null, 2));

    try {
      const result = await createInterviewDetails(payload);

      if (result.success && result.interview_id) {
        localStorage.setItem("interviewId", result.interview_id);
        setInterviewId(result.interview_id);
        toast.success("Interview created successfully!");
        setStep(1); // Move to objective form
      } else {
        throw new Error(result.message || "Failed to create interview.");
      }
    } catch (err: any) {
      console.error("Interview creation error:", err);
      setWeightsValidationError(err.message || "Failed to create interview. Please try again.");
      toast.error("Failed to create interview.");
    } finally {
      setIsCreatingInterview(false);
    }
  };

  // ─── Objective Form Handlers ──────────────────────────────────────────────

  const handleChange = (key: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    if (errors.has(key)) {
      setErrors((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  const validate = (): boolean => {
    const missing = new Set<keyof FormData>();
    REQUIRED.forEach((k) => {
      if (!formData[k].trim()) missing.add(k);
    });
    setErrors(missing);
    if (missing.size > 0) {
      setValidationError("Please fill in the required fields highlighted above.");
      return false;
    }
    setValidationError("");
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);

    const cmpy_id =
      localStorage.getItem("cmpy_id") ||
      formData.interview_name.toLowerCase().replace(/[^a-z0-9]+/g, "_");

    const storedInterviewId = localStorage.getItem("interviewId") || interviewId;

    const payload = {
      cmpy_id,
      interview_id: storedInterviewId,
      ...formData,
    };

    console.log("📋 Objective API Payload:", JSON.stringify(payload, null, 2));

    try {
      const result = await submitObjectiveDatabase(payload);

      if (result.success) {
        const aptitudeSyncFailed = !!result?.data?.aptitudeError;
        localStorage.setItem("jobIntakeComplete", "true");
        localStorage.setItem("jobConfiguration", JSON.stringify(payload));
        if (result?.data?.aptitude?.interview_id) {
          localStorage.setItem("aptitudeInterviewId", result.data.aptitude.interview_id);
        }
        const successMsg = result.message || "Objective database created successfully.";
        if (aptitudeSyncFailed) {
          toast.error("Objective saved, but aptitude setup failed. Please retry.");
        } else {
          toast.success(successMsg);
        }
        setSubmitSuccess(true);
        setTimeout(() => {
          setIsSubmitting(false);
          navigate("/company/dashboard");
        }, 1500);
      } else if (result.message?.toLowerCase().includes("already exists")) {
        toast("An objective already exists for this interview.", { icon: "ℹ️" });
        localStorage.setItem("jobIntakeComplete", "true");
        setIsSubmitting(false);
        navigate("/company/dashboard");
      } else {
        throw new Error(result.message || "Submission failed.");
      }
    } catch (err: any) {
      console.error("Submission error:", err);
      setValidationError(err.message || "Failed to submit. Please try again.");
      toast.error("Failed to save interview objective.");
      setIsSubmitting(false);
    }
  };

  // Progress tracking (for objective form)
  const filled = Object.values(formData).filter((v) => v.trim()).length;
  const total = Object.keys(formData).length;
  const progress = Math.round((filled / total) * 100);

  // ─── Weights Form UI ──────────────────────────────────────────────────────
  if (step === 0) {
    return (
      <div className="min-h-screen bg-[#020617] text-slate-100">
        <main className="max-w-2xl mx-auto px-5 pt-24 pb-20">
          <div className="mb-8">
            <h1 className="text-4xl font-black tracking-tight mb-2">Interview Setup: Step 1</h1>
            <p className="text-slate-400 text-lg">
              Set the interview date, time, and evaluation weightages before creating the interview.
            </p>
          </div>

          <m.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 space-y-6"
          >
            <form onSubmit={handleWeightsSubmit} className="space-y-6">
              {/* Date & Time */}
              <div className="p-5 rounded-xl bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50 space-y-5">
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-400" />
                  Schedule Interview
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Date Input */}
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-300">Interview Date</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium">Required</span>
                    </div>
                    <div className="relative">
                      <input
                        type="date"
                        value={weightsData.date}
                        onChange={(e) => handleWeightsChange("date", e.target.value)}
                        className={`w-full p-3 pl-4 pr-10 rounded-lg border outline-none transition-all bg-slate-900/80 text-slate-100 placeholder:text-slate-600 cursor-pointer ${
                          weightsErrors.has("date")
                            ? "border-rose-500 focus:border-rose-400 focus:ring-2 focus:ring-rose-500/30"
                            : "border-slate-600 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/30"
                        }`}
                      />
                      <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    </div>
                    {weightsErrors.has("date") && (
                      <p className="text-xs text-rose-400 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> Date is required
                      </p>
                    )}
                    {weightsData.date && (
                      <p className="text-xs text-slate-400">
                        📅 {new Date(weightsData.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                      </p>
                    )}
                  </div>

                  {/* Time Input */}
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-300">Interview Time</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium">Required</span>
                    </div>
                    <div className="relative">
                      <input
                        type="time"
                        value={weightsData.time}
                        onChange={(e) => handleWeightsChange("time", e.target.value)}
                        className={`w-full p-3 pl-4 pr-10 rounded-lg border outline-none transition-all bg-slate-900/80 text-slate-100 placeholder:text-slate-600 cursor-pointer ${
                          weightsErrors.has("time")
                            ? "border-rose-500 focus:border-rose-400 focus:ring-2 focus:ring-rose-500/30"
                            : "border-slate-600 focus:border-blue-400 focus:ring-2 focus:ring-blue-500/30"
                        }`}
                      />
                      <Clock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                    </div>
                    {weightsErrors.has("time") && (
                      <p className="text-xs text-rose-400 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" /> Time is required
                      </p>
                    )}
                    {weightsData.time && (
                      <p className="text-xs text-slate-400">
                        🕐 {new Date(`2000-01-01T${weightsData.time}`).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })}
                      </p>
                    )}
                  </div>
                </div>

                {/* DateTime Preview Card */}
                {weightsData.date && weightsData.time && (
                  <m.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-lg border border-blue-500/30 bg-blue-500/10 flex items-center gap-3"
                  >
                    <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <CheckCircle2 className="w-6 h-6 text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-blue-300">Interview Scheduled</p>
                      <p className="text-xs text-slate-400">
                        {new Date(weightsData.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })} at {new Date(`2000-01-01T${weightsData.time}`).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })}
                      </p>
                    </div>
                  </m.div>
                )}
              </div>

              {/* Weightages */}
              <div className="pt-4 border-t border-slate-700">
                <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-violet-400" />
                  Evaluation Weightages
                </h3>

                <div className="space-y-4">
                  {/* Aptitude */}
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-semibold text-slate-300">Aptitude Test</label>
                      <span className="px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/40 text-sm font-bold text-blue-300">
                        {weightsData.aptitude_weightage}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={weightsData.aptitude_weightage}
                      onChange={(e) =>
                        handleWeightsChange("aptitude_weightage", parseInt(e.target.value))
                      }
                      className="w-full h-2 rounded-lg bg-slate-700 accent-blue-500"
                    />
                  </div>

                  {/* Coding */}
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-semibold text-slate-300">Coding Challenge</label>
                      <span className="px-3 py-1 rounded-full bg-cyan-500/20 border border-cyan-500/40 text-sm font-bold text-cyan-300">
                        {weightsData.coding_weightage}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={weightsData.coding_weightage}
                      onChange={(e) =>
                        handleWeightsChange("coding_weightage", parseInt(e.target.value))
                      }
                      className="w-full h-2 rounded-lg bg-slate-700 accent-cyan-500"
                    />
                  </div>

                  {/* Technical Interview */}
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-semibold text-slate-300">Technical Interview</label>
                      <span className="px-3 py-1 rounded-full bg-violet-500/20 border border-violet-500/40 text-sm font-bold text-violet-300">
                        {weightsData.technical_interview_weightage}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={weightsData.technical_interview_weightage}
                      onChange={(e) =>
                        handleWeightsChange("technical_interview_weightage", parseInt(e.target.value))
                      }
                      className="w-full h-2 rounded-lg bg-slate-700 accent-violet-500"
                    />
                  </div>
                </div>

                {/* Summary */}
                <div className="mt-4 p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                  <div className="grid grid-cols-3 gap-3 text-center text-xs">
                    <div>
                      <p className="text-slate-500">Aptitude</p>
                      <p className="text-blue-300 font-bold">{weightsData.aptitude_weightage}%</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Coding</p>
                      <p className="text-cyan-300 font-bold">{weightsData.coding_weightage}%</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Technical</p>
                      <p className="text-violet-300 font-bold">{weightsData.technical_interview_weightage}%</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Validation error */}
              {weightsValidationError && (
                <m.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 p-4 rounded-lg border bg-rose-500/10 border-rose-500/30"
                >
                  <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
                  <p className="text-sm text-rose-300">{weightsValidationError}</p>
                </m.div>
              )}

              {/* Submit Button */}
              <div className="pt-4 flex flex-col items-center gap-3">
                <m.button
                  type="submit"
                  disabled={isCreatingInterview}
                  whileTap={{ scale: 0.97 }}
                  className="px-12 py-4 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-bold rounded-xl shadow-lg shadow-blue-900/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-lg flex items-center gap-2"
                >
                  {isCreatingInterview ? "Creating Interview..." : <>Create Interview<ArrowRight className="w-5 h-5" /></>}
                </m.button>
                <p className="text-xs text-slate-600">
                  This creates the interview and generates an interview_id for the next step
                </p>
              </div>
            </form>
          </m.div>
        </main>
      </div>
    );
  }

  // ─── Objective Form UI (Step 2) ──────────────────────────────────────────
  return (
    <div className="min-h-screen bg-[#020617] text-slate-100">
      <main className="max-w-4xl mx-auto px-5 pt-24 pb-20">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-black tracking-tight mb-2">Interview Objective Setup: Step 2</h1>
          <p className="text-slate-400 text-lg">
            Define the interview parameters for the AI agent. All fields feed directly into the backend objective database.
          </p>
          <p className="text-slate-500 text-sm mt-2">
            <strong>Interview ID:</strong> {interviewId || localStorage.getItem("interviewId")}
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-8 p-4 rounded-xl border border-slate-800 bg-slate-900/40">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-400">Form completion</span>
            <span className="text-sm font-bold text-white">{filled} / {total} fields</span>
          </div>
          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
            <m.div
              className="h-full bg-gradient-to-r from-blue-600 to-violet-500 rounded-full"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <p className="text-xs text-slate-600 mt-2">
            Fields marked as required: interview_name, role_title, department, core_skills_required, objective_role
          </p>
        </div>

        {/* Validation error banner */}
        {validationError && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 p-4 mb-6 rounded-lg border bg-rose-500/10 border-rose-500/30"
          >
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <p className="text-sm text-rose-300">{validationError}</p>
          </m.div>
        )}

        {/* Success banner */}
        {submitSuccess && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3 p-4 mb-6 rounded-lg border bg-green-500/10 border-green-500/30"
          >
            <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
            <p className="text-sm text-green-300">Objective saved! Redirecting to dashboard...</p>
          </m.div>
        )}

        {/* Sections */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {SECTIONS.map((section, idx) => (
            <Section
              key={section.title}
              section={section}
              index={idx}
              formData={formData}
              errors={errors}
              onChange={handleChange}
            />
          ))}

          {/* Submit */}
          <div className="pt-4 flex flex-col items-center gap-3">
            <m.button
              type="submit"
              disabled={isSubmitting || submitSuccess}
              whileTap={{ scale: 0.97 }}
              className="px-12 py-4 bg-gradient-to-r from-blue-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white font-bold rounded-xl shadow-lg shadow-blue-900/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed text-lg"
            >
              {isSubmitting ? "Saving..." : "Save Interview Objective"}
            </m.button>
            <p className="text-xs text-slate-600">
              Submits to <code className="text-slate-500">/db/objective_database</code> · cmpy_id read from localStorage
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}
