// WebGen Backend API Service
// Connects ChillBuild's AI mode to the WebGen backend (LLaMA + Gemini pipeline)

const BACKEND_URL = '/api';

export interface DBConfig {
    host: string;
    port: string;
    user: string;
    password: string;
    database: string;
}

export const defaultDBConfig: DBConfig = {
    host: 'localhost',
    port: '5433',
    user: 'postgres',
    password: '',
    database: 'postgres',
};

export interface QuestionField {
    id: string;
    name?: string;
    label: string;
    type: 'text' | 'single_select' | 'multi_select' | 'select' | 'textarea' | 'checkbox' | 'color';
    options?: string[];
    placeholder?: string;
    required?: boolean;
    default?: string;
}

export interface GenerateResult {
    success: boolean;
    plan?: {
        projectName: string;
        description: string;
        pages: string[];
        needsDatabase: boolean;
        styleTokens?: Record<string, unknown>;
    };
    project?: {
        projectName: string;
        description: string;
        frontend: Record<string, string>;
        backend: Record<string, string> | null;
    };
    previewUrl?: string;
    backendPort?: number;
    error?: string;
}

export interface EditResult {
    success: boolean;
    projectName?: string;
    previewUrl?: string;
    error?: string;
}

export interface ProjectMeta {
    projectName: string;
    description: string;
    pages: string[];
    style: string;
    palette: Record<string, string>;
    needsDatabase: boolean;
    createdAt: string;
    previewUrl: string;
}

class WebgenService {
    /**
     * Step 1: Send a website idea → get a questionnaire with form fields
     */
    async getQuestionnaire(idea: string): Promise<{ success: boolean; questions: QuestionField[]; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/chat/questionnaire`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idea }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || `Server error: ${res.status}`);
            }

            return await res.json();
        } catch (error) {
            return {
                success: false,
                questions: [],
                error: error instanceof Error ? error.message : 'Failed to connect to backend',
            };
        }
    }

    /**
     * Step 2: Submit prompt + questionnaire answers → full website generation
     */
    async generateWebsite(
        prompt: string,
        dbConfig?: DBConfig,
        chatHistory?: Array<{ role: string; content: string }>
    ): Promise<GenerateResult> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/website`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, dbConfig, chatHistory }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || `Server error: ${res.status}`);
            }

            return await res.json();
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Failed to generate website',
            };
        }
    }

    /**
     * Step 2 (STREAMING): Generate website with real-time artifact SSE events.
     * Calls onEvent for each SSE event type: 'plan', 'progress', 'artifact', 'done', 'error'.
     */
    async generateWebsiteStream(
        prompt: string,
        dbConfig: DBConfig | undefined,
        onEvent: (type: string, data: Record<string, unknown>) => void,
        signal?: AbortSignal
    ): Promise<void> {
        const response = await fetch(`${BACKEND_URL}/generate/stream-website`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, dbConfig }),
            signal,
        });

        if (!response.ok || !response.body) {
            const errText = await response.text().catch(() => 'Unknown error');
            throw new Error(`Stream failed: ${response.status} ${errText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const parseBuffer = (raw: string): { events: Array<{ type: string; data: Record<string, unknown> }>; remaining: string } => {
            const events: Array<{ type: string; data: Record<string, unknown> }> = [];
            const blocks = raw.split('\n\n');
            const remaining = blocks.pop() ?? '';
            for (const block of blocks) {
                let eventType = 'message';
                let dataLine = '';
                for (const line of block.split('\n')) {
                    if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                    if (line.startsWith('data: ')) dataLine = line.slice(6).trim();
                }
                if (dataLine) {
                    try { events.push({ type: eventType, data: JSON.parse(dataLine) }); }
                    catch { /* malformed */ }
                }
            }
            return { events, remaining };
        };

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const { events, remaining } = parseBuffer(buffer);
            buffer = remaining;
            for (const { type, data } of events) {
                onEvent(type, data);
            }
        }
    }

    /**
     * Step 3: Edit an existing generated project with a text prompt
     */
    async editWebsite(projectName: string, prompt: string): Promise<EditResult> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/edit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ projectName, prompt }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || `Server error: ${res.status}`);
            }

            return await res.json();
        } catch (error) {
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Failed to edit website',
            };
        }
    }

    /**
     * Get the preview URL for a generated project
     */
    getPreviewUrl(projectName: string): string {
        return `${BACKEND_URL}/preview/${projectName}`;
    }

    /**
     * Download project as ZIP
     */
    getDownloadUrl(projectName: string): string {
        return `${BACKEND_URL}/generate/download/${projectName}`;
    }

    /**
     * Export to GitHub
     */
    async exportToGitHub(projectName: string): Promise<{ success: boolean; repoUrl?: string; error?: string }> {
        try {
            const repoName = projectName.toLowerCase().replace(/\s+/g, '-');
            const res = await fetch(`${BACKEND_URL}/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repoName, projectName }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || `Export failed: ${res.status}`);
            }
            return await res.json();
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Export failed' };
        }
    }

    /**
     * Recolor — swap palette on existing project
     */
    async recolor(
        projectName: string,
        oldPalette: Record<string, string>,
        newPalette: Record<string, string>
    ): Promise<{ success: boolean; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/recolor`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ projectName, oldPalette, newPalette }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Recolor failed');
            }
            return { success: true };
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Recolor failed' };
        }
    }

    /**
     * Upload image to project
     */
    async uploadImage(projectName: string, file: File): Promise<{ success: boolean; url?: string; error?: string }> {
        try {
            const formData = new FormData();
            formData.append('image', file);
            formData.append('projectName', projectName);
            const res = await fetch(`${BACKEND_URL}/generate/upload-image`, {
                method: 'POST',
                body: formData,
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Upload failed');
            }
            return await res.json();
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Upload failed' };
        }
    }

    /**
     * Visual edit — patch an element's text/styles in the generated HTML
     */
    async patchElement(
        projectName: string,
        selector: string,
        changes: { text?: string; oldText?: string; color?: string; backgroundColor?: string; fontSize?: string }
    ): Promise<{ success: boolean; changed?: boolean; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/patch-element`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ projectName, selector, changes }),
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || 'Patch failed');
            }
            return await res.json();
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Patch failed' };
        }
    }

    /**
     * Health check — verify backend is running
     */
    async checkHealth(): Promise<boolean> {
        try {
            const res = await fetch(`${BACKEND_URL}/health`);
            return res.ok;
        } catch {
            return false;
        }
    }

    /**
     * List all previously generated projects
     */
    async listProjects(): Promise<{ projects: ProjectMeta[]; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/projects`);
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            return await res.json();
        } catch (error) {
            return { projects: [], error: error instanceof Error ? error.message : 'Failed to list projects' };
        }
    }

    /**
     * Delete a generated project
     */
    async deleteProject(projectName: string): Promise<{ success: boolean; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/projects/${encodeURIComponent(projectName)}`, {
                method: 'DELETE',
            });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            return await res.json();
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Delete failed' };
        }
    }

    /**
     * Regenerate a single page within an existing project
     */
    async regeneratePage(projectName: string, pageName: string): Promise<{ success: boolean; previewUrl?: string; html?: string; error?: string }> {
        try {
            const res = await fetch(`${BACKEND_URL}/generate/regenerate-page`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ projectName, pageName }),
            });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            return await res.json();
        } catch (error) {
            return { success: false, error: error instanceof Error ? error.message : 'Regeneration failed' };
        }
    }
}

export interface SelectedElement {
    tag: string;
    text: string;
    styles: {
        color: string;
        backgroundColor: string;
        fontSize: string;
        fontWeight: string;
        textAlign: string;
    };
    selector: string;
    outerHTML: string;
}

export const webgenService = new WebgenService();


