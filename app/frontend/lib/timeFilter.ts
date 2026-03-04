/**
 * PulseX-WDD timeFilter utility
 * Robust client-side filtering and metrics computation for PalmX parity.
 */

export type TimeRange = 'all' | '24h' | '7d' | '30d';

export function parseTimestamp(ts: any): number {
    if (!ts) return 0;
    try {
        const d = new Date(String(ts).replace(' ', 'T').replace(/Z$/, '') + 'Z');
        return d.getTime();
    } catch {
        return 0;
    }
}

export function withinRange(ts: any, range: TimeRange, now: number): boolean {
    if (range === 'all') return true;
    const t = parseTimestamp(ts);
    if (t === 0) return false;

    const diffMs = now - t;
    const rangeMsMap = {
        '24h': 24 * 60 * 60 * 1000,
        '7d': 7 * 24 * 60 * 60 * 1000,
        '30d': 30 * 24 * 60 * 60 * 1000,
    };

    return diffMs >= 0 && diffMs <= rangeMsMap[range];
}

export function filterByRange<T>(items: T[], range: TimeRange, now: number = Date.now()): T[] {
    return items.filter(item => {
        const row = item as any;
        return withinRange(row.timestamp || row.time, range, now);
    });
}

export function normalizePhone(phone: any): string {
    if (!phone) return '';
    return String(phone).replace(/\D/g, '');
}

/**
 * Compute PalmX-style lead analytics from a filtered set of leads.
 */
export function computeLeadAnalytics(leads: any[]) {
    if (!leads.length) return null;

    const distributions = {
        projects: {} as Record<string, number>,
        regions: {} as Record<string, number>,
        unitTypes: {} as Record<string, number>,
        purposes: {} as Record<string, number>,
        timelines: {} as Record<string, number>,
        tags: {} as Record<string, number>,
        temperatures: {} as Record<string, number>,
        budgetBands: {} as Record<string, number>,
    };

    const budgets: number[] = [];
    const uniquePhones = new Set<string>();
    let intake24 = 0;
    const now = Date.now();
    const cutoff24 = now - 24 * 60 * 60 * 1000;

    leads.forEach(l => {
        // Independent 24h intake
        if (parseTimestamp(l.timestamp) >= cutoff24) intake24++;
        // Unique contacts
        uniquePhones.add(normalizePhone(l.phone || l.contact));

        // Projects
        (l.projects || []).forEach((p: string) => distributions.projects[p] = (distributions.projects[p] || 0) + 1);

        // Fields
        if (l.region) distributions.regions[l.region] = (distributions.regions[l.region] || 0) + 1;
        if (l.unit_type) distributions.unitTypes[l.unit_type] = (distributions.unitTypes[l.unit_type] || 0) + 1;
        if (l.purpose) distributions.purposes[l.purpose] = (distributions.purposes[l.purpose] || 0) + 1;
        if (l.timeline) distributions.timelines[l.timeline] = (distributions.timelines[l.timeline] || 0) + 1;
        if (l.lead_temperature) distributions.temperatures[l.lead_temperature] = (distributions.temperatures[l.lead_temperature] || 0) + 1;
        if (l.budget_band) distributions.budgetBands[l.budget_band] = (distributions.budgetBands[l.budget_band] || 0) + 1;

        // Tags
        (l.tags || []).forEach((t: string) => distributions.tags[t] = (distributions.tags[t] || 0) + 1);

        // Budget Median
        const bmin = Number(l.budget_min);
        const bmax = Number(l.budget_max);
        if (bmin > 0 && bmax > 0) {
            budgets.push((bmin + bmax) / 2);
        } else if (bmin > 0) {
            budgets.push(bmin);
        }
    });

    const topProj = Object.entries(distributions.projects).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';
    const topReg = Object.entries(distributions.regions).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';

    // Median
    budgets.sort((a, b) => a - b);
    const mid = Math.floor(budgets.length / 2);
    const medianBudget = budgets.length > 0
        ? (budgets.length % 2 !== 0 ? budgets[mid] : (budgets[mid - 1] + budgets[mid]) / 2)
        : 0;

    return {
        totalLeads: leads.length,
        uniqueContacts: uniquePhones.size,
        intake24,
        topProj,
        topReg,
        medianBudget,
        distributions: {
            projects: Object.entries(distributions.projects).map(([label, count]) => ({ label, count })),
            regions: Object.entries(distributions.regions).map(([label, count]) => ({ label, count })),
            unitTypes: Object.entries(distributions.unitTypes).map(([name, value]) => ({ name, value })),
            purposes: Object.entries(distributions.purposes).map(([label, count]) => ({ label, count })),
            timelines: Object.entries(distributions.timelines).map(([label, count]) => ({ label, count })),
            tags: Object.entries(distributions.tags).map(([label, count]) => ({ label, count })),
            temperatures: Object.entries(distributions.temperatures).map(([name, value]) => ({ name, value })),
            budgetBands: Object.entries(distributions.budgetBands).map(([label, count]) => ({ label, count })),
        }
    };
}

/**
 * Compute PalmX-style audit quality analytics.
 */
export function computeAuditAnalytics(auditRows: any[]) {
    if (!auditRows.length) return null;

    let emptyCount = 0;
    const entities: Record<string, number> = {};

    auditRows.forEach(row => {
        if (row.empty_retrieval === true || row.empty_retrieval === 'true') {
            emptyCount++;
        }

        let ents = [];
        try {
            ents = typeof row.top_entities_json === 'string' ? JSON.parse(row.top_entities_json) : (row.top_entities_json || []);
        } catch { ents = []; }

        ents.forEach((e: string) => entities[e] = (entities[e] || 0) + 1);
    });

    const topEnt = Object.entries(entities).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';

    return {
        totalQueries: auditRows.length,
        emptyRetrievalRate: emptyCount / auditRows.length,
        topEntity: topEnt,
    };
}
