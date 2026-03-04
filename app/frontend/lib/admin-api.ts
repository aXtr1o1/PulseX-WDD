/**
 * PulseX-WDD Admin API Client — typed fetch wrappers for all admin endpoints.
 * Uses Next.js proxy rewrites (/api/admin/* → backend /api/admin/*).
 * Ported from PalmX admin-api.ts with WDD endpoint contract.
 */

const BASE = '/api/admin';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SheetInfo {
    name: string;
    path: string;
    type: 'csv' | 'xlsx';
    modified_at: string;
    rows: number;
    cols: number;
    columns: string[];
    error?: string;
}

export interface SheetPreview {
    sheet: string;
    columns: string[];
    rows: Record<string, string>[];
    total_rows: number;
    showing: number;
}

export interface NormalizedLead {
    timestamp: string;
    name: string;
    phone: string;
    contact: string;
    email: string;
    session_id: string;
    summary: string;
    projects: string[];
    interest_projects: string;
    project_primary: string | null;
    region: string | null;
    preferred_region: string | null;
    unit_type: string | null;
    purpose: string | null;
    budget_min: number | null;
    budget_max: number | null;
    budget_band: string | null;
    timeline: string | null;
    tags: string[];
    lead_temperature: string | null;
    lead_temperature_variant: string;
    reason_codes: string;
    consent_callback: string;
    confirmed_by_user: string;
    raw: Record<string, string>;
    [key: string]: any;
}

export interface KPIs {
    total_leads: number;
    last_24h: number;
    unique_contacts: number;
    top_project: string;
    top_region: string;
    median_budget_min: number | null;
    median_budget_max: number | null;
}

export interface BreakdownItem {
    label: string;
    count: number;
}

export interface TimeseriesItem {
    bucket: string;
    count: number;
}

export interface Funnel {
    stage_0: number;
    stage_1: number;
    stage_2: number;
    stage_3: number;
    stage_4: number;
    stage_5: number;
    stage_6: number;
}

export interface AnalyticsData {
    kpi: KPIs;
    timeseries: TimeseriesItem[];
    breakdowns: {
        by_project: BreakdownItem[];
        by_region: BreakdownItem[];
        by_unit_type: BreakdownItem[];
        by_purpose: BreakdownItem[];
        by_timeline: BreakdownItem[];
        by_tag: BreakdownItem[];
    };
    funnel: Funnel;
}

export interface AuditData {
    available: boolean;
    message?: string;
    total_queries?: number;
    top_retrieved_projects?: { project: string; count: number }[];
    score_histogram?: { range: string; count: number }[];
    intent_distribution?: { intent: string; count: number }[];
    query_volume?: { date: string; count: number }[];
    empty_retrieval_rate?: number;
}

export interface HealthData {
    status: string;
    resolved_runtime_dir: string;
    leads_dir: string;
    leads_dir_exists: boolean;
    available_sheets: string[];
    server_time: string;
}

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        ...init,
        cache: 'no-store',
    });
    if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`Admin API error ${res.status}: ${text}`);
    }
    return res.json();
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export const adminApi = {
    health: () => adminFetch<HealthData>('/health'),

    sheets: () => adminFetch<SheetInfo[]>('/sheets'),

    preview: (sheet: string, limit = 50) =>
        adminFetch<SheetPreview>(`/sheets/preview?sheet=${encodeURIComponent(sheet)}&limit=${limit}`),

    downloadUrl: (sheet: string, format: 'original' | 'csv' | 'xlsx' = 'original') =>
        `${BASE}/sheets/download?sheet=${encodeURIComponent(sheet)}&format=${format}`,

    leads: (sheet = 'leads.csv', range = 'all') =>
        adminFetch<{ total: number; leads: NormalizedLead[] }>(
            `/leads?sheet=${encodeURIComponent(sheet)}&range=${range}`
        ),

    analytics: (sheet = 'leads.csv', range = 'all') =>
        adminFetch<AnalyticsData>(
            `/dashboard?sheet=${encodeURIComponent(sheet)}&range=${range}`
        ),

    audit: () => adminFetch<AuditData>('/audit'),
};
