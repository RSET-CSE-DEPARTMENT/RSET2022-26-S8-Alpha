import { Navigate } from "react-router-dom";

/**
 * Dashboard — smart redirect:
 *   Interviewers  → /company/dashboard  (CompanyJobPostings)
 *   Candidates    → /login (since dashboard not needed)
 */
export default function Dashboard() {
  const isInterviewer = localStorage.getItem("userType") === "interviewer";
  return isInterviewer
    ? <Navigate to="/company/dashboard" replace />
    : <Navigate to="/login" replace />;
}
