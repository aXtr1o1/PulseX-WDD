/**
 * PulseX-WDD Typed API Client
 * All requests go through Next.js rewrite proxy -> FastAPI backend.
 */

const isServer = typeof window === 'undefined';
const API_BASE = isServer
    ? (process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || '')
    : (process.env.NEXT_PUBLIC_API_BASE_URL || '');

// ── Types mirroring backend schemas ─────────────────────────────────────────

export interface PageContext {
    url?: string;
    project_slug?: string;
    page_title?: string;
}

export interface EvidenceSnippet {
    entity_id: string;
    display_name: string;
    source_url?: string;
    snippet: string;
    confidence: number;
}

export interface ChatResponse {
    session_id: string;
    request_id: string;
    intent: string;
    answer: string;
    evidence: EvidenceSnippet[];
    shortlist?: Record<string, any>[];
    lead_suggestions?: Record<string, any>;
    focused_project?: string;
    intent_lane?: string;
    lead_trigger: boolean;
    handoff_cta: boolean;
    lang: string;
    latency_ms?: number;
}

export interface LeadPayload {
    session_id: string;
    lang: string;
    name?: string;
    phone?: string;
    email?: string;
    interest_projects?: string[];
    preferred_region?: string;
    unit_type?: string;
    budget_min?: number;
    budget_max?: number;
    purpose?: string;
    timeline?: string;
    consent_callback: boolean;
    consent_marketing: boolean;
    source_url?: string;
    page_title?: string;
    tags?: string[];
    summary?: string;
}

export interface LeadResponse {
    success: boolean;
    lead_id: string;
    message: string;
}

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
export interface ProjectCount { project: string; count: number; }
export interface RegionCount { region: string; count: number; }

export interface AdminDashboard {
    kpi: KPISummary;
    daily_leads: DailyCount[];
    top_projects: ProjectCount[];
    top_regions: RegionCount[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${API_BASE}${path}`;
    const res = await fetch(url, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
        ...init,
    });
    if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText);
        throw new Error(`API ${res.status}: ${detail}`);
    }
    return res.json() as Promise<T>;
}

// ── Chat ─────────────────────────────────────────────────────────────────────

export async function sendChat(
    message: string,
    sessionId: string,
    lang: string,
    pageContext?: PageContext,
): Promise<ChatResponse> {
    return apiFetch<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, lang, message, page_context: pageContext }),
    });
}

export function streamChat(
    message: string,
    sessionId: string,
    lang: string,
    pageContext?: PageContext,
    onToken?: (token: string) => void,
    onDone?: () => void,
): AbortController {
    const ctrl = new AbortController();
    const url = `${API_BASE}/api/chat/stream`;

    fetch(url, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, lang, message, page_context: pageContext }),
        signal: ctrl.signal,
    })
        .then(async (res) => {
            if (!res.ok || !res.body) { onDone?.(); return; }
            const reader = res.body.getReader();
            const dec = new TextDecoder();
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const text = dec.decode(value);
                for (const line of text.split('\n')) {
                    if (line.startsWith('data: ')) {
                        const tok = line.slice(6);
                        if (tok === '[DONE]') { onDone?.(); return; }
                        onToken?.(tok);
                    }
                }
            }
            onDone?.();
        })
        .catch(() => onDone?.());

    return ctrl;
}

// ── Lead ─────────────────────────────────────────────────────────────────────

export async function submitLead(payload: LeadPayload): Promise<LeadResponse> {
    return apiFetch<LeadResponse>('/api/lead', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
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

export async function fetchAdminStats(): Promise<AdminDashboard> {
    return apiFetch<AdminDashboard>('/api/admin/dashboard');
}

export interface LeadFilter {
    time_filter?: '24h' | '7d' | '30d' | 'all';
    project?: string;
    region?: string;
    unit_type?: string;
    purpose?: string;
}

export async function fetchLeads(params?: LeadFilter): Promise<{ total: number; leads: Record<string, string>[] }> {
    const q = new URLSearchParams(
        Object.entries(params ?? {}).filter(([, v]) => v != null) as [string, string][]
    ).toString();
    return apiFetch(`/api/admin/leads${q ? `?${q}` : ''}`);
}

export async function fetchSheetRows(
    sheet: 'leads' | 'audit' | 'leads_seed' | 'sessions',
    limit = 200,
    offset = 0,
): Promise<{ total: number; rows: Record<string, string>[]; offset: number; limit: number }> {
    return apiFetch(`/api/admin/sheets/${sheet}/rows?limit=${limit}&offset=${offset}`);
}

export function downloadSheetUrl(sheet: string, format: 'csv' | 'xlsx'): string {
    return `${API_BASE}/api/admin/sheets/${sheet}/download/${format}`;
}
