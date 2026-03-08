/**
 * PulseX-WDD API Client — Adapted to Backend Contract
 *
 * Chat endpoints use the WDD PulseX backend contract exactly:
 *   POST /api/chat        → JSON response
 *   POST /api/chat/stream → SSE text/event-stream
 *
 * Payload: { session_id, messages: [{role, content}], locale: "en" }
 */

// ── Types mirroring WDD PulseX backend schemas ───────────────────────────────────

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export interface ChatPayload {
    session_id: string;
    messages: ChatMessage[];
    locale: string;
}

export interface ChatResponse {
    message: string;
    retrieved_projects: string[];
    mode: 'concierge' | 'lead_capture';
}

/** Done frame emitted at end of SSE stream */
export interface StreamDoneFrame {
    done: true;
    retrieved_projects: string[];
    mode: 'concierge' | 'lead_capture';
}

// ── Admin types (unchanged) ─────────────────────────────────────────────────

export interface KPISummary {
    total_leads: number;
    last_24h: number;
    unique_contacts: number;
    top_project?: string;
    top_region?: string;
    median_budget_min?: number;
    median_budget_max?: number;
}

export interface DailyCount { date: string; count: number; }
export interface ProjectCount { label: string; count: number; }
export interface RegionCount { label: string; count: number; }

export interface FunnelMetrics {
    stage_0: number;
    stage_1: number;
    stage_2: number;
    stage_3: number;
    stage_4: number;
    stage_5: number;
    stage_6: number;
}

export interface AdminDashboard {
    kpi: KPISummary;
    timeseries: DailyCount[];
    breakdowns: {
        by_project: ProjectCount[];
        by_region: RegionCount[];
        by_unit_type: { label: string; count: number }[];
        by_purpose: { label: string; count: number }[];
        by_timeline: { label: string; count: number }[];
        by_tag: { label: string; count: number }[];
    };
    funnel?: FunnelMetrics;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(path, {
        headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
        ...init,
    });
    if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText);
        throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
}

// ── Chat (non-streaming) ────────────────────────────────────────────────────

export async function sendChat(payload: ChatPayload): Promise<ChatResponse> {
    return apiFetch<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

// ── Chat (streaming SSE with robust line buffering) ─────────────────────────

export interface StreamCallbacks {
    onToken?: (token: string) => void;
    onDone?: (meta: StreamDoneFrame | null) => void;
}

/**
 * POST to /api/chat/stream and parse the SSE response with proper
 * buffer handling (never assumes 1 chunk == 1 event).
 *
 * SSE frames emitted by backend:
 *   data: {"token": "..."}        — text token
 *   data: {"done": true, "retrieved_projects": [...], "mode": "..."}  — end
 */
export function streamChat(
    payload: ChatPayload,
    callbacks: StreamCallbacks,
): AbortController {
    const ctrl = new AbortController();

    fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: ctrl.signal,
    })
        .then(async (res) => {
            if (!res.ok || !res.body) {
                callbacks.onDone?.(null);
                return;
            }

            const reader = res.body.getReader();
            const dec = new TextDecoder();
            let buffer = ''; // SSE line buffer — critical for robust parsing

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += dec.decode(value, { stream: true });

                // Process all complete lines
                const lines = buffer.split('\n');
                // Keep the last (possibly incomplete) line in the buffer
                buffer = lines.pop() ?? '';

                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed || !trimmed.startsWith('data: ')) continue;

                    const dataStr = trimmed.slice(6); // Remove "data: " prefix
                    if (dataStr === '[DONE]') {
                        callbacks.onDone?.(null);
                        return;
                    }

                    try {
                        const parsed = JSON.parse(dataStr);

                        if (parsed.done === true) {
                            // Done frame with metadata
                            callbacks.onDone?.({
                                done: true,
                                retrieved_projects: parsed.retrieved_projects ?? [],
                                mode: parsed.mode ?? 'concierge',
                            });
                            return;
                        }

                        if (typeof parsed.token === 'string') {
                            callbacks.onToken?.(parsed.token);
                        }
                    } catch {
                        // Ignore malformed JSON chunks — never break UI
                    }
                }
            }

            // If we exit the read loop without a done signal, still finalize
            callbacks.onDone?.(null);
        })
        .catch(() => callbacks.onDone?.(null));

    return ctrl;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function adminLogin(password: string): Promise<{ success: boolean; message: string }> {
    return apiFetch('/api/admin/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
    });
}

export async function adminLogout(): Promise<void> {
    await apiFetch('/api/admin/logout', { method: 'POST' });
}

export async function fetchAdminStats(range: string = 'all'): Promise<AdminDashboard> {
    return apiFetch<AdminDashboard>(`/api/admin/dashboard?range=${range}`);
}

export interface LeadFilter {
    time_filter?: '24h' | '7d' | '30d' | 'all';
    range?: '24h' | '7d' | '30d' | 'all';
    project?: string;
    region?: string;
    unit_type?: string;
    purpose?: string;
}

export interface LeadRecord {
    timestamp: string;
    session_id?: string;
    name?: string;
    phone?: string;
    contact?: string;
    email?: string;
    projects?: string[];
    interest_projects?: string;
    region?: string;
    preferred_region?: string;
    unit_type?: string;
    purpose?: string;
    budget_band?: string;
    budget_min?: number;
    budget_max?: number;
    timeline?: string;
    tags?: string[];
    summary?: string;
    reason_codes?: string;
    lead_temperature?: string;
    confirmed_by_user?: string;
    consent_callback?: string;
    consent_contact?: string;
    [key: string]: any;
}

export async function fetchLeads(params?: LeadFilter): Promise<{ total: number; leads: LeadRecord[] }> {
    const q = new URLSearchParams(
        Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][]
    ).toString();
    return apiFetch(`/api/admin/leads${q ? `?${q}` : ''}`);
}

// ── Sheet Management ──────────────────────────────────────────────────────────

export interface SheetMetadata {
    name: string;
    rows: number;
    cols: number;
    size_bytes: number;
    modified_at: string;
    type: 'csv' | 'xlsx';
}

export async function fetchSheets(): Promise<SheetMetadata[]> {
    return apiFetch<SheetMetadata[]>('/api/admin/sheets');
}

export async function fetchSheetRows(
    sheet: 'leads' | 'audit' | 'leads_seed' | 'sessions' | string,
    limit = 200,
    offset = 0,
): Promise<{ total: number; rows: Record<string, any>[]; offset: number; limit: number; columns: string[] }> {
    return apiFetch(`/api/admin/sheets/${sheet}/rows?limit=${limit}&offset=${offset}`);
}

export function downloadSheetUrl(sheet: string, format: 'csv' | 'xlsx'): string {
    return `/api/admin/sheets/${sheet}/download/${format}`;
}
