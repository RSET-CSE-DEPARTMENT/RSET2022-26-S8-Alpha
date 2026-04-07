// src/services/companyAuthService.ts
// Handles all calls to the company backend APIs (auth, signup, objective DB)

// All requests go through the Vite proxy at /company-api/* → ngrok backend.
// This avoids browser CORS restrictions — the browser sees a same-origin call.
// To change the ngrok URL: update VITE_COMPANY_API_URL in .env AND the fallback
// in vite.config.js, then restart the dev server.
const BASE_URL = "/company-api";
const APTITUDE_BASE_URL = import.meta.env.VITE_APTITUDE_API_URL ?? "/aptitude-api";

/** Common headers — ngrok-skip-browser-warning prevents the ngrok splash page */
const headers = {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
};

// ============================================================
// TYPES
// ============================================================

export type CompanySignInPayload = {
    username: string;
    password: string;
};

export type InsertCompanyDetailsPayload = {
    cmpy_id: string;
    company_name: string;
    industry_type: string;
    company_size: string;
    company_description: string;
};

export type InterviewDetailsPayload = {
    cmpy_id: string;
    date: string;
    time: string;
    aptitude_weightage: number;
    coding_weightage: number;
    technical_interview_weightage: number;
};

export type InterviewDetailsResponse = {
    status: boolean;
    message: string;
    interview_id: string;
};

export type ObjectiveDatabasePayload = {
    cmpy_id: string;
    interview_id: string;
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

export type ApiResponse = {
    success: boolean;
    status?: boolean;
    message?: string;
    data?: any;
    interview_id?: string;
};

export type AptitudeCreateInterviewResponse = {
    message: string;
    interview_id: string;
    role?: string;
    skills?: string[];
};

export type InterviewPreview = {
    cmpy_id: string;
    date: string;
    time: string;
    aptitude_weightage: number;
    coding_weightage: number;
    technical_interview_weightage: number;
    interview_id: string;
};

export type InterviewsByCompanyResponse = {
    status: boolean;
    count: number;
    interviews: InterviewPreview[];
};

export type InterviewDetailsFull = InterviewPreview & ObjectiveDatabasePayload;

export type InterviewDetailsByIdResponse = {
    status: boolean;
    interview: InterviewDetailsFull;
};

// ─── Logging helper ───────────────────────────────────────────────────────────

function logRequest(endpoint: string, payload: unknown) {
    console.group(`%c[API REQUEST] ${endpoint}`, 'color:#60a5fa;font-weight:bold');
    console.log('Payload:', JSON.stringify(payload, null, 2));
    console.groupEnd();
}

function logResponse(endpoint: string, data: unknown) {
    console.group(`%c[API RESPONSE] ${endpoint}`, 'color:#34d399;font-weight:bold');
    console.log('Response:', JSON.stringify(data, null, 2));
    console.groupEnd();
}

function logError(endpoint: string, err: unknown) {
    console.group(`%c[API ERROR] ${endpoint}`, 'color:#f87171;font-weight:bold');
    console.error('Error:', err);
    console.groupEnd();
}

// ============================================================
// COMPANY SIGN IN
// POST /auth/company_signin
// ============================================================

/**
 * Sign in a company user.
 * Returns { success: true } on 200 + status:true, else { success: false, message }
 */
export async function companySignIn(payload: CompanySignInPayload): Promise<ApiResponse> {
    const endpoint = '/auth/company_signin';
    try {
        logRequest(endpoint, payload);

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        logResponse(endpoint, data);

        if (res.ok && data.status === true) {
            localStorage.setItem('companyLoggedIn', 'true');
            localStorage.setItem('companyUsername', payload.username);
            localStorage.setItem('accessToken', `company-${Date.now()}`);
            localStorage.setItem('userType', 'company');
            localStorage.setItem('cmpy_id', payload.password);
            return { success: true, data };
        }

        return {
            success: false,
            message: data.message || 'Invalid username or password. Please try again.',
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// INSERT COMPANY DETAILS (SIGN UP)
// POST /signup/insert_company_details
// ============================================================

/**
 * Register a new company by inserting its details.
 * A response with status:false + "already exists" is treated as a soft warning.
 */
export async function insertCompanyDetails(payload: InsertCompanyDetailsPayload): Promise<ApiResponse> {
    const endpoint = '/signup/insert_company_details';
    try {
        logRequest(endpoint, payload);

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            message: data.message,
            data,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// CREATE INTERVIEW DETAILS
// POST /db/interview_details
// ============================================================

/**
 * Create an interview with weights (aptitude, coding, technical).
 * Returns { status: true, interview_id } on success.
 */
export async function createInterviewDetails(payload: InterviewDetailsPayload): Promise<ApiResponse> {
    const endpoint = '/db/interview_details';
    try {
        logRequest(endpoint, payload);

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify(payload),
        });

        const data: InterviewDetailsResponse = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            status: data.status,
            message: data.message,
            interview_id: data.interview_id,
            data,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// SUBMIT OBJECTIVE DATABASE
// POST /db/objective_database
// ============================================================

/**
 * Submit interview objective configuration to the backend.
 * A response with status:false + "already exists" is treated as a soft warning (not a fatal error).
 */
export async function submitObjectiveDatabase(payload: ObjectiveDatabasePayload): Promise<ApiResponse> {
    const objectiveEndpoint = '/db/objective_database';
    const aptitudeEndpoint = '/create-interview';
    try {
        logRequest(objectiveEndpoint, payload);
        logRequest(aptitudeEndpoint, payload);

        const [objectiveRes, aptitudeRes] = await Promise.all([
            fetch(`${BASE_URL}${objectiveEndpoint}`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            }),
            fetch(`${APTITUDE_BASE_URL}${aptitudeEndpoint}`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload),
            }),
        ]);

        const objectiveData = await objectiveRes.json();
        logResponse(objectiveEndpoint, objectiveData);

        let aptitudeData: AptitudeCreateInterviewResponse | null = null;
        let aptitudeError = '';
        if (aptitudeRes.ok) {
            aptitudeData = await aptitudeRes.json();
            logResponse(aptitudeEndpoint, aptitudeData);
        } else {
            aptitudeError = await aptitudeRes.text();
            logError(aptitudeEndpoint, aptitudeError);
        }

        const objectiveSuccess = objectiveData.status === true;

        return {
            success: objectiveSuccess,
            message: objectiveSuccess
                ? aptitudeError
                    ? `${objectiveData.message || 'Objective database created successfully.'} Aptitude interview sync failed.`
                    : objectiveData.message
                : objectiveData.message,
            data: {
                objective: objectiveData,
                aptitude: aptitudeData,
                aptitudeError: aptitudeError || undefined,
            },
        };
    } catch (err: any) {
        logError(objectiveEndpoint, err);
        return {
            success: false,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// GET INTERVIEWS BY COMPANY
// POST /db/interview_details/by_company
// ============================================================

/**
 * Fetch all interviews created by a specific company.
 * Returns { status: true, count, interviews: [...] }
 */
export async function getInterviewsByCompany(cmpy_id: string): Promise<{ success: boolean; interviews: InterviewPreview[]; count: number; message?: string }> {
    const endpoint = '/db/interview_details/by_company';
    try {
        logRequest(endpoint, { cmpy_id });

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ cmpy_id }),
        });

        const data: InterviewsByCompanyResponse = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            interviews: data.interviews || [],
            count: data.count || 0,
            message: data.status === false ? 'Failed to fetch interviews' : undefined,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            interviews: [],
            count: 0,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// GET INTERVIEW DETAILS BY ID
// POST /db/interview_details/by_id
// ============================================================

/**
 * Fetch full details of a specific interview by its ID.
 * Returns { status: true, interview: {...} }
 */
export async function getInterviewDetailsById(interview_id: string): Promise<{ success: boolean; interview: InterviewDetailsFull | null; message?: string }> {
    const endpoint = '/db/interview_details/by_id';
    try {
        logRequest(endpoint, { interview_id });

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ interview_id }),
        });

        const data: InterviewDetailsByIdResponse = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            interview: data.interview || null,
            message: data.status === false ? 'Interview not found' : undefined,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            interview: null,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// INSERT CANDIDATE
// POST /db/insert_candidate
// ============================================================

export async function insertCandidate(interview_id: string, name: string, email: string): Promise<ApiResponse> {
    const endpoint = '/db/insert_candidate';
    try {
        logRequest(endpoint, { interview_id, name, email });

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ interview_id, name, email }),
        });

        const data = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            status: data.status,
            message: data.message,
            data,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// GET CANDIDATES BY INTERVIEW
// POST /db/candidate_details/by_interview
// ============================================================

export type CandidateDetails = {
    cade_id: string;
    interview_id: string;
    name: string;
    email: string;
};

export async function fetchCandidatesByInterview(interview_id: string): Promise<{ success: boolean; candidates: CandidateDetails[]; message?: string }> {
    const endpoint = '/db/candidate_details/by_interview';
    try {
        logRequest(endpoint, { interview_id });

        const res = await fetch(`${BASE_URL}${endpoint}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ interview_id }),
        });

        const data = await res.json();
        logResponse(endpoint, data);

        return {
            success: data.status === true,
            candidates: data.candidates || [],
            message: data.status === false ? 'Failed to fetch candidates' : undefined,
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            candidates: [],
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// GET CANDIDATE RANKING
// POST /db/get_candidate_ranking
// ============================================================

export type CandidateRanking = {
    cade_id: string;
    name: string;
    email: string;
    rank: number;
    total_score: number;
    aptitude_score?: number;
    coding_score?: number;
    technical_interview_score?: number;
    [key: string]: any;
};

export async function getCandidateRanking(interview_id: string): Promise<{ success: boolean; rankings: CandidateRanking[]; message?: string }> {
    const endpoint = '/db/get_candidate_ranking';
    try {
        logRequest(endpoint, { interview_id });

        // Fetch rankings and candidate details concurrently
        const [rankRes, candRes] = await Promise.all([
            fetch(`${BASE_URL}${endpoint}`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ interview_id }),
            }),
            fetch(`${BASE_URL}/db/candidate_details/by_interview`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ interview_id }),
            })
        ]);

        const data = await rankRes.json();
        const candData = await candRes.json();
        
        logResponse(endpoint, data);

        if (data.status === true) {
            const rawRankings = data.data || [];
            const candidatesList: CandidateDetails[] = candData.candidates || [];

            // Merge rankings with candidate name/email and format scores
            const mappedRankings: CandidateRanking[] = rawRankings.map((r: any) => {
                const cand = candidatesList.find(c => c.cade_id === r.cade_id) || { name: 'Unknown Candidate', email: 'N/A' };
                
                // Calculate estimated tech score from the 3 rubrics (each out of 5, so 15 total)
                const techSum = (r.tech_knowledge || 0) + (r.tech_revelance || 0) + (r.tech_language_proficency || 0);
                const techPercent = (techSum / 15) * 100;

                return {
                    cade_id: r.cade_id,
                    name: cand.name,
                    email: cand.email,
                    rank: 0, // will be assigned next
                    total_score: r.candidate_final_score != null ? Number(r.candidate_final_score).toFixed(4) : undefined,
                    aptitude_score: r.aptitude_score != null ? Number(r.aptitude_score).toFixed(4) : undefined,
                    coding_score: r.coding_score != null ? Number(r.coding_score).toFixed(4) : undefined,
                    technical_interview_score: techPercent.toFixed(1),
                    ...r
                };
            });

            // Sort by final score descending and assign rank
            mappedRankings.sort((a, b) => b.candidate_final_score - a.candidate_final_score);
            mappedRankings.forEach((r, idx) => {
                r.rank = idx + 1;
            });

            return {
                success: true,
                rankings: mappedRankings,
            };
        }

        return {
            success: false,
            rankings: [],
            message: data.message || 'Failed to fetch rankings',
        };
    } catch (err: any) {
        logError(endpoint, err);
        return {
            success: false,
            rankings: [],
            message: 'Could not reach the server. Please check your connection.',
        };
    }
}

// ============================================================
// HELPERS
// ============================================================

/**
 * Generate a company ID from the company name.
 * e.g. "Infotech Co Pvt Ltd" → "infotech_co_pvt_ltd_38291"
 */
export function generateCompanyId(companyName: string): string {
    const base = companyName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    const suffix = Math.floor(100000 + Math.random() * 899999);
    return `${base}_${suffix}`;
}
