import { useState, useEffect } from "react";
import { m } from "framer-motion";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  Briefcase,
  Building2,
  Users,
  Zap,
  Calendar,
  Clock,
  Eye,
  Loader,
  UserPlus,
  X,
  Mail,
  User,
  Trophy,
  Medal,
  Hash,
  Code,
  Video,
} from "lucide-react";
import {
  getInterviewsByCompany,
  getInterviewDetailsById,
  insertCandidate,
  fetchCandidatesByInterview,
  getCandidateRanking,
} from "../services/companyAuthService";
import type { CandidateRanking } from "../services/companyAuthService";
import toast from "react-hot-toast";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Candidate {
  cade_id: string;
  interview_id: string;
  name: string;
  email: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function CompanyJobPostings() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState<string>("Company");
  const [companyUsername, setCompanyUsername] = useState<string>("");
  const [cmpy_id, setCmpy_id] = useState<string>("");

  // Interview listing
  const [interviewsWithDetails, setInterviewsWithDetails] = useState<any[]>([]);
  const [isLoadingInterviews, setIsLoadingInterviews] = useState(false);

  // View Details modal
  const [selectedInterviewDetails, setSelectedInterviewDetails] = useState<any>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Add Candidate modal
  const [showAddCandidateModal, setShowAddCandidateModal] = useState(false);
  const [addCandidateInterviewId, setAddCandidateInterviewId] = useState<string>("");
  const [addCandidateInterviewName, setAddCandidateInterviewName] = useState<string>("");
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [isSubmittingCandidate, setIsSubmittingCandidate] = useState(false);

  // View Candidates modal
  const [showCandidatesModal, setShowCandidatesModal] = useState(false);
  const [candidatesInterviewName, setCandidatesInterviewName] = useState<string>("");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false);

  // Rank List modal
  const [showRankModal, setShowRankModal] = useState(false);
  const [rankInterviewName, setRankInterviewName] = useState<string>("");
  const [rankings, setRankings] = useState<CandidateRanking[]>([]);
  const [isLoadingRankings, setIsLoadingRankings] = useState(false);

  useEffect(() => {
    const name = localStorage.getItem("company_name") || localStorage.getItem("companyUsername") || "Company";
    const username = localStorage.getItem("companyUsername") || "";
    const companyId = localStorage.getItem("cmpy_id") || "";

    setCompanyName(name);
    setCompanyUsername(username);
    setCmpy_id(companyId);

    if (companyId) {
      fetchAllInterviewsWithDetails(companyId);
    }
  }, []);

  const fetchAllInterviewsWithDetails = async (companyId: string) => {
    setIsLoadingInterviews(true);
    try {
      const result = await getInterviewsByCompany(companyId);
      if (result.success && result.interviews.length > 0) {
        const details = await Promise.all(
          result.interviews.map(async (interview: any) => {
            const detailResult = await getInterviewDetailsById(interview.interview_id);
            return detailResult.success && detailResult.interview
              ? { preview: interview, details: detailResult.interview }
              : null;
          })
        );
        setInterviewsWithDetails(details.filter(Boolean));
      } else {
        setInterviewsWithDetails([]);
      }
    } catch (err) {
      console.error("Error fetching interviews:", err);
      toast.error("Error fetching interviews");
    } finally {
      setIsLoadingInterviews(false);
    }
  };

  const fetchInterviewDetails = async (interview_id: string) => {
    setIsLoadingDetails(true);
    try {
      const result = await getInterviewDetailsById(interview_id);
      if (result.success && result.interview) {
        setSelectedInterviewDetails(result.interview);
        setShowDetailsModal(true);
      } else {
        toast.error("Failed to load interview details");
      }
    } catch (err) {
      console.error("Error fetching interview details:", err);
      toast.error("Error fetching interview details");
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // ── Add Candidate handlers ──────────────────────────────────────────────────

  const openAddCandidateModal = (e: React.MouseEvent, interview_id: string, interview_name: string) => {
    e.stopPropagation();
    setAddCandidateInterviewId(interview_id);
    setAddCandidateInterviewName(interview_name);
    setCandidateName("");
    setCandidateEmail("");
    setShowAddCandidateModal(true);
  };

  const handleAddCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateName.trim() || !candidateEmail.trim()) {
      toast.error("Please fill in all fields");
      return;
    }
    setIsSubmittingCandidate(true);
    try {
      const data = await insertCandidate(addCandidateInterviewId, candidateName.trim(), candidateEmail.trim());
      if (data.success) {
        toast.success("Candidate registered successfully!");
        setShowAddCandidateModal(false);
      } else {
        toast.error(data.message || "Failed to register candidate");
      }
    } catch (err) {
      console.error("Error adding candidate:", err);
      toast.error("Error registering candidate");
    } finally {
      setIsSubmittingCandidate(false);
    }
  };

  // ── View Candidates handlers ────────────────────────────────────────────────

  const openCandidatesModal = async (e: React.MouseEvent, interview_id: string, interview_name: string) => {
    e.stopPropagation();
    setCandidatesInterviewName(interview_name);
    setCandidates([]);
    setShowCandidatesModal(true);
    setIsLoadingCandidates(true);
    try {
      const data = await fetchCandidatesByInterview(interview_id);
      if (data.success) {
        setCandidates(data.candidates || []);
      } else {
        toast.error(data.message || "Failed to load candidates");
      }
    } catch (err) {
      console.error("Error fetching candidates:", err);
      toast.error("Error fetching candidates");
    } finally {
      setIsLoadingCandidates(false);
    }
  };

  // ── View Rankings handler ──────────────────────────────────────────────────

  const openRankingsModal = async (e: React.MouseEvent, interview_id: string, interview_name: string) => {
    e.stopPropagation();
    setRankInterviewName(interview_name);
    setRankings([]);
    setShowRankModal(true);
    setIsLoadingRankings(true);
    try {
      const data = await getCandidateRanking(interview_id);
      if (data.success) {
        setRankings(data.rankings || []);
      } else {
        toast.error(data.message || "Failed to load rankings");
      }
    } catch (err) {
      console.error("Error fetching rankings:", err);
      toast.error("Error fetching rankings");
    } finally {
      setIsLoadingRankings(false);
    }
  };

  const handleAddNewJob = () => navigate("/company/job-intake");

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <main className="px-4 pt-32 pb-12 mx-auto max-w-7xl">
        {/* Header */}
        <m.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-[#0d59f2]/20 text-[#0d59f2]">
                  <Building2 className="w-6 h-6" />
                </div>
                <h1 className="text-4xl font-bold">Welcome, {companyName}!</h1>
              </div>
              {companyUsername && (
                <p className="text-sm text-slate-500 ml-1 mt-1">
                  Signed in as <span className="text-slate-400 font-medium">{companyUsername}</span>
                </p>
              )}
              <p className="mt-3 text-slate-400">Manage your company's job postings and conduct technical interviews</p>
            </div>
            <m.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleAddNewJob}
              className="flex items-center justify-center gap-2 min-w-[280px] h-14 px-8 bg-[#0d59f2] text-white text-lg font-bold rounded-xl shadow-xl shadow-[#0d59f2]/20 hover:bg-blue-600 transition-all active:scale-[0.98]"
            >
              <Plus className="w-5 h-5" />
              <span>Add New Job Posting</span>
            </m.button>
          </div>
        </m.div>

        {/* Stats */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 gap-4 mb-12 md:grid-cols-3"
        >
          <div className="p-6 rounded-xl border border-slate-800 bg-[#0f172a]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Interviews</p>
                <p className="text-3xl font-bold text-[#0d59f2]">{interviewsWithDetails.length}</p>
              </div>
              <Briefcase className="w-10 h-10 text-slate-700" />
            </div>
          </div>
          <div className="p-6 rounded-xl border border-slate-800 bg-[#0f172a]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Candidates</p>
                <p className="text-3xl font-bold text-emerald-400">0</p>
              </div>
              <Users className="w-10 h-10 text-slate-700" />
            </div>
          </div>
          <div className="p-6 rounded-xl border border-slate-800 bg-[#0f172a]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">Total Completed</p>
                <p className="text-3xl font-bold text-purple-400">0</p>
              </div>
              <Zap className="w-10 h-10 text-slate-700" />
            </div>
          </div>
        </m.div>

        {/* Interviews List */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-12"
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">Your Interviews</h2>
          </div>

          {isLoadingInterviews ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-6 h-6 animate-spin text-[#0d59f2]" />
            </div>
          ) : interviewsWithDetails.length > 0 ? (
            <div className="space-y-4">
              {interviewsWithDetails.map((item, idx) => {
                const interview = item.details;
                const preview = item.preview;

                return (
                  <m.div
                    key={interview.interview_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="group p-6 rounded-xl border border-blue-500/30 bg-[#0f172a] hover:border-blue-500/60 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10 cursor-pointer"
                    onClick={() => fetchInterviewDetails(interview.interview_id)}
                  >
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      {/* Main Info */}
                      <div className="flex-1">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <div>
                            <h3 className="text-2xl font-bold text-white">{interview.interview_name}</h3>
                            <p className="text-sm text-blue-300 font-medium mt-1">
                              {interview.role_title} • {interview.department}
                            </p>
                            <p className="text-xs text-slate-500 font-mono mt-1">ID: {interview.interview_id}</p>
                          </div>
                          <span className="px-3 py-1 text-xs font-semibold border rounded-full whitespace-nowrap bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                            Active
                          </span>
                        </div>

                        <p className="max-w-3xl text-sm leading-relaxed text-slate-400 mb-4 line-clamp-2">
                          {interview.objective_role}
                        </p>

                        {/* Tags */}
                        <div className="flex flex-wrap gap-3 mt-4">
                          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
                            <Calendar className="w-4 h-4 text-slate-400" />
                            <span className="text-xs font-medium text-slate-300">
                              {new Date(preview.date).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
                            <Clock className="w-4 h-4 text-slate-400" />
                            <span className="text-xs font-medium text-slate-300">
                              {new Date(`2000-01-01T${preview.time}`).toLocaleTimeString("en-US", {
                                hour: "2-digit",
                                minute: "2-digit",
                                hour12: true,
                              })}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700">
                            <Briefcase className="w-4 h-4 text-slate-400" />
                            <span className="text-xs font-medium text-slate-300 line-clamp-1 max-w-[200px]">
                              {interview.employment_level || "Full-Time"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex flex-col gap-2 lg:min-w-[160px]" onClick={(e) => e.stopPropagation()}>
                        {/* View Details */}
                        <button
                          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0d59f2]/10 border border-[#0d59f2]/30 rounded-lg text-[#0d59f2] font-semibold text-sm hover:bg-[#0d59f2]/20 transition-colors group-hover:border-[#0d59f2]/60 w-full"
                          onClick={(e) => {
                            e.stopPropagation();
                            fetchInterviewDetails(interview.interview_id);
                          }}
                        >
                          <Eye className="w-4 h-4" />
                          View Details
                        </button>

                        {/* Add Candidate */}
                        <button
                          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 font-semibold text-sm hover:bg-emerald-500/20 transition-colors w-full"
                          onClick={(e) => openAddCandidateModal(e, interview.interview_id, interview.interview_name)}
                        >
                          <UserPlus className="w-4 h-4" />
                          Add Candidate
                        </button>

                        {/* View Candidates */}
                        <button
                          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-500/10 border border-purple-500/30 rounded-lg text-purple-400 font-semibold text-sm hover:bg-purple-500/20 transition-colors w-full"
                          onClick={(e) => openCandidatesModal(e, interview.interview_id, interview.interview_name)}
                        >
                          <Users className="w-4 h-4" />
                          View Candidates
                        </button>

                        {/* View Rankings */}
                        <button
                          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-400 font-semibold text-sm hover:bg-amber-500/20 transition-colors w-full"
                          onClick={(e) => openRankingsModal(e, interview.interview_id, interview.interview_name)}
                        >
                          <Trophy className="w-4 h-4" />
                          View Rankings
                        </button>
                      </div>
                    </div>
                  </m.div>
                );
              })}
            </div>
          ) : (
            <m.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <div className="text-center py-16 px-8 rounded-xl border border-dashed border-slate-700 bg-[#0f172a]/50">
                <Calendar className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                <p className="mb-4 text-slate-400">No interviews created yet. Create your first one!</p>
                <button
                  onClick={handleAddNewJob}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#0d59f2] text-white font-semibold rounded-lg hover:bg-blue-600 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Create Interview
                </button>
              </div>
            </m.div>
          )}
        </m.div>

        {/* ── Interview Details Modal ── */}
        {showDetailsModal && selectedInterviewDetails && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setShowDetailsModal(false)}
          >
            <m.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[#0f172a] rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-y-auto border border-slate-700 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="sticky top-0 bg-[#0f172a] border-b border-slate-700 p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-white">{selectedInterviewDetails.interview_name}</h3>
                  <p className="text-sm text-slate-400 mt-1">{selectedInterviewDetails.role_title}</p>
                </div>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800">
                    <p className="text-xs text-slate-500 font-semibold uppercase mb-2">Department</p>
                    <p className="text-sm text-slate-300">{selectedInterviewDetails.department}</p>
                  </div>
                </div>

                {[
                  { label: "Experience Level Required", value: selectedInterviewDetails.experience_level_required },
                  { label: "Employment Level", value: selectedInterviewDetails.employment_level },
                  { label: "Core Skills Required", value: selectedInterviewDetails.core_skills_required },
                  { label: "Secondary Skills Required", value: selectedInterviewDetails.secondary_skills_required },
                  { label: "Tools & Technologies", value: selectedInterviewDetails.tools_and_technologies },
                  { label: "Expected Proficiency Level", value: selectedInterviewDetails.expected_proficiency_level },
                  { label: "Objective Role", value: selectedInterviewDetails.objective_role },
                  { label: "Key Performance Indicator", value: selectedInterviewDetails.key_performance_indicator },
                  { label: "Expected Output", value: selectedInterviewDetails.expected_output },
                  { label: "Business Impact", value: selectedInterviewDetails.business_impact_role },
                  { label: "Communication Level", value: selectedInterviewDetails.communication_level },
                  { label: "Team Collaboration", value: selectedInterviewDetails.team_collaboration_expectation },
                  { label: "Leadership Requirements", value: selectedInterviewDetails.leadership_requirements },
                  { label: "Learning & Adaptability", value: selectedInterviewDetails.learning_and_adaptability },
                  { label: "Decision Making", value: selectedInterviewDetails.decision_making_capability },
                ].map((section, i) => (
                  <div key={i} className="border-t border-slate-800 pt-4">
                    <p className="text-xs text-slate-500 font-semibold uppercase mb-2 tracking-wider">{section.label}</p>
                    <p className="text-sm text-slate-300 leading-relaxed">{section.value}</p>
                  </div>
                ))}
              </div>

              <div className="sticky bottom-0 bg-[#0f172a] border-t border-slate-700 p-6 flex gap-3">
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </m.div>
          </m.div>
        )}

        {/* ── Add Candidate Modal ── */}
        {showAddCandidateModal && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
            onClick={() => setShowAddCandidateModal(false)}
          >
            <m.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className="bg-[#0f172a] rounded-2xl max-w-md w-full border border-emerald-500/20 shadow-2xl shadow-emerald-500/5"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/15 text-emerald-400">
                    <UserPlus className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">Add Candidate</h3>
                    <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[220px]">{addCandidateInterviewName}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowAddCandidateModal(false)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleAddCandidate} className="p-6 space-y-5">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Full Name <span className="text-emerald-400">*</span>
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="text"
                      value={candidateName}
                      onChange={(e) => setCandidateName(e.target.value)}
                      placeholder="e.g. Rahul Kumar"
                      className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all"
                      required
                    />
                  </div>
                </div>

                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Email Address <span className="text-emerald-400">*</span>
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="email"
                      value={candidateEmail}
                      onChange={(e) => setCandidateEmail(e.target.value)}
                      placeholder="e.g. rahul@gmail.com"
                      className="w-full pl-10 pr-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all"
                      required
                    />
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddCandidateModal(false)}
                    className="flex-1 px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingCandidate}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors"
                  >
                    {isSubmittingCandidate ? (
                      <Loader className="w-4 h-4 animate-spin" />
                    ) : (
                      <UserPlus className="w-4 h-4" />
                    )}
                    {isSubmittingCandidate ? "Registering…" : "Register Candidate"}
                  </button>
                </div>
              </form>
            </m.div>
          </m.div>
        )}

        {/* ── View Candidates Modal ── */}
        {showCandidatesModal && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50"
            onClick={() => setShowCandidatesModal(false)}
          >
            <m.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className="bg-[#0f172a] rounded-2xl max-w-lg w-full max-h-[75vh] flex flex-col border border-purple-500/20 shadow-2xl shadow-purple-500/5"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-purple-500/15 text-purple-400">
                    <Users className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">Candidates</h3>
                    <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[250px]">{candidatesInterviewName}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowCandidatesModal(false)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6">
                {isLoadingCandidates ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader className="w-6 h-6 animate-spin text-purple-400" />
                  </div>
                ) : candidates.length === 0 ? (
                  <div className="text-center py-12">
                    <Users className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                    <p className="text-slate-400 text-sm">No candidates registered yet.</p>
                    <p className="text-slate-600 text-xs mt-1">Use "Add Candidate" to assign candidates to this interview.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-4">
                      {candidates.length} candidate{candidates.length !== 1 ? "s" : ""} registered
                    </p>
                    {candidates.map((c, i) => (
                      <m.div
                        key={c.cade_id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="flex items-center gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/30 transition-colors"
                      >
                        {/* Avatar */}
                        <div className="w-10 h-10 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-sm flex-shrink-0">
                          {c.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-white truncate">{c.name}</p>
                          <p className="text-xs text-slate-400 truncate">{c.email}</p>
                          <p className="text-[10px] text-slate-500 font-mono mt-0.5">ID: {c.cade_id}</p>
                        </div>
                      </m.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-slate-800 flex-shrink-0">
                <button
                  onClick={() => setShowCandidatesModal(false)}
                  className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </m.div>
          </m.div>
        )}
        {/* ── Rank List Modal ── */}
        {showRankModal && (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50 overflow-hidden"
            onClick={() => setShowRankModal(false)}
          >
            <m.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className="bg-[#0f172a] rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col border border-amber-500/20 shadow-2xl shadow-amber-500/5"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-6 border-b border-slate-800 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-amber-500/15 text-amber-400">
                    <Trophy className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">Candidate Rankings</h3>
                    <p className="text-xs text-slate-500 mt-0.5 truncate max-w-[300px]">{rankInterviewName}</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowRankModal(false)}
                  className="p-2 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700">
                {isLoadingRankings ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader className="w-6 h-6 animate-spin text-amber-400" />
                  </div>
                ) : rankings.length === 0 ? (
                  <div className="text-center py-12">
                    <Trophy className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                    <p className="text-slate-400 text-sm">No rankings available yet.</p>
                    <p className="text-slate-600 text-xs mt-1">Rankings will appear once candidates complete their interviews.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">
                      {rankings.length} candidate{rankings.length !== 1 ? "s" : ""} ranked
                    </p>
                    {rankings.map((r, i) => {
                      const rank = r.rank ?? i + 1;
                      const medalColor =
                        rank === 1
                          ? "text-yellow-400 bg-yellow-500/20"
                          : rank === 2
                            ? "text-slate-300 bg-slate-400/20"
                            : rank === 3
                              ? "text-amber-600 bg-amber-700/20"
                              : "text-slate-500 bg-slate-700/30";

                      return (
                        <m.div
                          key={r.cade_id || i}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className={`flex flex-col p-5 rounded-xl border transition-colors ${rank <= 3
                              ? "bg-amber-500/5 border-amber-500/30"
                              : "bg-slate-900/60 border-slate-700"
                            }`}
                        >
                          {/* Top Row: Basic Info */}
                          <div className="flex items-start md:items-center gap-4 flex-wrap">
                            {/* Rank Badge */}
                            <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg flex-shrink-0 ${medalColor}`}>
                              {rank <= 3 ? (
                                <Medal className="w-6 h-6" />
                              ) : (
                                <span>#{rank}</span>
                              )}
                            </div>

                            {/* Info */}
                            <div className="flex-1 min-w-[200px]">
                              <p className="text-lg font-bold text-white truncate">{r.name}</p>
                              <p className="text-sm text-slate-400 truncate">{r.email}</p>
                            </div>

                            {/* Main Scores */}
                            <div className="flex items-center gap-4 flex-wrap">
                              {r.aptitude_score != null && (
                                <div className="text-center bg-blue-500/10 px-3 py-1.5 rounded-lg border border-blue-500/20">
                                  <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Aptitude</p>
                                  <p className="text-sm font-bold text-blue-400">{r.aptitude_score}</p>
                                </div>
                              )}
                              {r.coding_score != null && (
                                <div className="text-center bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">
                                  <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Coding</p>
                                  <p className="text-sm font-bold text-emerald-400">{r.coding_score}</p>
                                </div>
                              )}
                              {r.technical_interview_score != null && (
                                <div className="text-center bg-purple-500/10 px-3 py-1.5 rounded-lg border border-purple-500/20">
                                  <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Tech</p>
                                  <p className="text-sm font-bold text-purple-400">{r.technical_interview_score}</p>
                                </div>
                              )}
                              <div className="text-center bg-amber-500/10 px-4 py-1.5 rounded-lg border border-amber-500/30">
                                <p className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Total Score</p>
                                <p className="text-lg font-black text-amber-400">{r.total_score ?? "—"}</p>
                              </div>
                            </div>
                          </div>

                          {/* Extra Detailed Data Grid */}
                          <div className="mt-5 pt-5 border-t border-slate-700/60 grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Technical Review Breakdown */}
                            <div className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/50">
                              <p className="text-xs font-bold text-purple-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Code className="w-4 h-4" /> Technical Interview Breakdown
                              </p>
                              <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Knowledge</p>
                                  <p className="text-white font-medium">{r.tech_knowledge?.toFixed(2) ?? "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Relevance</p>
                                  <p className="text-white font-medium">{r.tech_revelance?.toFixed(2) ?? "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Language Proficiency</p>
                                  <p className="text-white font-medium">{r.tech_language_proficency?.toFixed(2) ?? "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Questions Evaluated</p>
                                  <p className="text-white font-medium">{r.tech_count ?? 0}</p>
                                </div>
                              </div>
                            </div>

                            {/* Proctoring & Confidence Breakdown */}
                            <div className="bg-slate-800/40 rounded-xl p-4 border border-slate-700/50">
                              <p className="text-xs font-bold text-rose-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Video className="w-4 h-4" /> Behavioral & Proctoring
                              </p>
                              <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Overall Confidence</p>
                                  <p className="text-emerald-300 font-medium">{r.final_confidence_score != null ? Number(r.final_confidence_score).toFixed(4) : "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Eye Contact Consistency</p>
                                  <p className="text-white font-medium">{r.eye_contact_score != null ? Number(r.eye_contact_score).toFixed(4) : "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Movement (Agitation)</p>
                                  <p className="text-white font-medium">{r.movement_score != null ? Number(r.movement_score).toFixed(4) : "—"}</p>
                                </div>
                                <div>
                                  <p className="text-slate-400 text-xs mb-0.5">Blink Rate (per min)</p>
                                  <p className="text-white font-medium">{r.blink_score != null ? Number(r.blink_score).toFixed(4) : "—"}</p>
                                </div>
                              </div>
                            </div>
                          </div>
                        </m.div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-slate-800 flex-shrink-0">
                <button
                  onClick={() => setShowRankModal(false)}
                  className="w-full px-4 py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors"
                >
                  Close
                </button>
              </div>
            </m.div>
          </m.div>
        )}
      </main>
    </div>
  );
}
