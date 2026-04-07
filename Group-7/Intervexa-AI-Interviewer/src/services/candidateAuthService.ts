import { safeFetchJson } from "../utils/apiWrapper";

// Route through the local proxy backend to bypass browser CORS to NGROK
const BASE_URL = "http://localhost:8000";

const headers = {
  'Content-Type': 'application/json',
  'ngrok-skip-browser-warning': 'true' // essential for ngrok
};

// ============================================================
// TYPES
// ============================================================

export type CandidateLoginPayload = {
  candidate_id: string;
  interview_id: string;
};

export type CandidateLoginResponse = {
  status: boolean;
  message: string;
  candidate_id?: string;
  interview_id?: string;
};

export type ResumeUploadResponse = {
  status: boolean;
  message: string;
  file_path?: string;
};

// ============================================================
// CANDIDATE LOGIN
// ============================================================

/**
 * Authenticate candidate using candidate ID and interview ID
 */
export async function candidateLogin(
  payload: CandidateLoginPayload
): Promise<CandidateLoginResponse> {
  const loginPayload = {
    cade_id: payload.candidate_id,
    interview_id: payload.interview_id,
  };
  const loginUrl = `${BASE_URL.replace(/\/$/, '')}/db/check_candidate_login`;

  console.log("[candidateAuth] POST /db/check_candidate_login to", loginUrl);

  const data = await safeFetchJson<any>(
    "check_candidate_login",
    loginUrl,
    { method: "POST", headers, body: JSON.stringify(loginPayload) }
  );

  if (data === null) {
    return {
      status: false,
      message: "Server is unreachable. Please check if the backend is running.",
    };
  }

  const exists = data?.exists === true;
  return {
    status: exists,
    message: exists
      ? (data.message || "Login successful")
      : (data.message || "Invalid candidate or interview ID"),
    candidate_id: payload.candidate_id,
    interview_id: payload.interview_id,
  };
}

// ============================================================
// RESUME UPLOAD
// ============================================================

/**
 * Upload resume file for a candidate
 * @param candidateId - The candidate ID (cade_id)
 * @param interviewId - The interview ID
 * @param file - The file to upload
 * @returns { message, filename, path? }
 */
export async function uploadResume(
  candidateId: string,
  interviewId: string,
  file: File
): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("cade_id", candidateId);
  formData.append("interview_id", interviewId);
  formData.append("file", file);

  const uploadUrl = `${BASE_URL.replace(/\/$/, '')}/upload_resume`;

  console.log("[candidateAuth] POST /upload_resume to", uploadUrl);

  const data = await safeFetchJson<any>(
    "upload_resume",
    uploadUrl,
    { 
      method: "POST", 
      headers: { "ngrok-skip-browser-warning": "true" }, 
      body: formData 
    }
  );

  if (data === null) {
    return {
      status: false,
      message: "Server is unreachable. Please check if the backend is running.",
    };
  }

  return {
    status: data?.status === true,
    message: data?.message || "Upload completed",
    file_path: data?.saved_path || data?.path,
  };
}

// ============================================================
// LOCAL STORAGE HELPERS
// ============================================================

/**
 * Save candidate session to localStorage
 */
export function saveCandidateSession(candidateId: string, interviewId: string) {
  // Canonical keys used by Interview.tsx / InterviewRoom.tsx.
  localStorage.setItem("intervexa-cade-id", candidateId);
  localStorage.setItem("interviewId", interviewId);

  // Compatibility with older keys still used in some places.
  localStorage.setItem("candidate_id", candidateId);
  localStorage.setItem("interview_id", interviewId);
  localStorage.setItem("candidate_authenticated", "true");
}

/**
 * Get candidate session from localStorage
 */
export function getCandidateSession() {
  const candidateId =
    localStorage.getItem("intervexa-cade-id") ?? localStorage.getItem("candidate_id");
  const interviewId =
    localStorage.getItem("interviewId") ?? localStorage.getItem("interview_id");
  return {
    candidateId,
    interviewId,
    isAuthenticated: localStorage.getItem("candidate_authenticated") === "true",
  };
}

/**
 * Clear candidate session from localStorage
 */
export function clearCandidateSession() {
  localStorage.removeItem("intervexa-cade-id");
  localStorage.removeItem("interviewId");
  localStorage.removeItem("candidate_id");
  localStorage.removeItem("interview_id");
  localStorage.removeItem("candidate_authenticated");
}
