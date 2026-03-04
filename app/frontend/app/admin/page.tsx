'use client';
import React, { useCallback, useEffect, useState, useMemo } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
    fetchLeads, fetchSheets, fetchSheetRows, downloadSheetUrl,
    type LeadRecord, type SheetMetadata,
} from '@/lib/api';
import {
    TimeRange, filterByRange, normalizePhone, parseTimestamp,
    computeLeadAnalytics, computeAuditAnalytics
} from '@/lib/timeFilter';
import KPITile from '@/components/admin/KPITile';
import { LeadsTimeChart, DistributionBar, DistributionDonut, FunnelStrip } from '@/components/admin/Charts';
import LeadTable from '@/components/admin/LeadTable';
import LeadDrawer from '@/components/admin/LeadDrawer';

export default function AdminPage() {
    const [leads, setLeads] = useState<LeadRecord[]>([]);
    const [audit, setAudit] = useState<any[]>([]);
    const [sheets, setSheets] = useState<SheetMetadata[]>([]);
    const [loading, setLoading] = useState(true);

    const [activeSheet, setActiveSheet] = useState('leads.csv');
    const [timeRange, setTimeRange] = useState<TimeRange>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [regionFilter, setRegionFilter] = useState('ALL');

    const [selectedLead, setSelectedLead] = useState<LeadRecord | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    const loadAll = useCallback(async () => {
        setLoading(true);
        try {
            const [lData, auData, sData] = await Promise.all([
                fetchLeads({ range: 'all' }),
                fetchSheetRows('audit', 500),
                fetchSheets()
            ]);
            setLeads(lData.leads);
            setAudit(auData.rows);
            setSheets(sData);
        } catch (err) {
            console.error('Dashboard load failed:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadAll(); }, [loadAll]);

    // --- Reactive Pipeline (PalmX Benchmark) ---
    const now = useMemo(() => Date.now(), []);

    const filteredLeads = useMemo(() => {
        let result = filterByRange(leads, timeRange, now);
        if (searchQuery) {
            const q = searchQuery.toLowerCase();
            result = result.filter(l =>
                (l.name ?? '').toLowerCase().includes(q) ||
                (l.phone ?? '').toLowerCase().includes(q) ||
                (l.contact ?? '').toLowerCase().includes(q) ||
                (l.projects || []).some((p: string) => p.toLowerCase().includes(q))
            );
        }
        if (regionFilter !== 'ALL') {
            result = result.filter(l => (l.region || l.preferred_region) === regionFilter);
        }
        return result;
    }, [leads, timeRange, searchQuery, regionFilter, now]);

    const activeMetrics = useMemo(() => computeLeadAnalytics(filteredLeads), [filteredLeads]);
    const qualityMetrics = useMemo(() => {
        const filteredAudit = filterByRange(audit, timeRange, now);
        return computeAuditAnalytics(filteredAudit);
    }, [audit, timeRange, now]);

    // Timeseries recomputation for chart
    const timeseries = useMemo(() => {
        const counts: Record<string, number> = {};
        const isSmallRange = timeRange === '24h' || timeRange === '7d';
        filteredLeads.forEach(l => {
            const date = new Date(parseTimestamp(l.timestamp));
            const bucket = isSmallRange ? date.toISOString().slice(0, 13) + ':00' : date.toISOString().slice(0, 10);
            counts[bucket] = (counts[bucket] || 0) + 1;
        });
        return Object.entries(counts)
            .map(([date, count]) => ({ date, count }))
            .sort((a, b) => a.date.localeCompare(b.date));
    }, [filteredLeads, timeRange]);

    const availableRegions = useMemo(() => {
        const set = new Set<string>(['ALL']);
        leads.forEach(l => {
            const reg = l.region || l.preferred_region;
            if (reg) set.add(reg);
        });
        return Array.from(set).sort();
    }, [leads]);

    if (loading && leads.length === 0) {
        return (
            <div className="min-h-screen bg-[var(--wdd-bg)] flex flex-col items-center justify-center animate-pulse-soft">
                <Image src="/brand/WDD_blockLogo.png" width={72} height={72} alt="WDD" className="object-contain mb-6" priority />
                <p className="text-sm font-medium text-[var(--wdd-muted)] tracking-wider uppercase">Loading Intelligence...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--wdd-surface)] font-isidora text-[var(--wdd-black)]">

            {/* Segment A: Header / Command Bar */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/"><Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-7 w-auto object-contain hover:opacity-80 transition-opacity" /></Link>
                        <div className="flex items-center gap-2 border-l border-[var(--wdd-border)] pl-4">
                            <span className="text-xs font-semibold tracking-wider">LEAD INTELLIGENCE</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        {/* Status Pills */}
                        <div className="hidden lg:flex items-center gap-2 mr-4">
                            <span className={`w-2 h-2 rounded-full ${loading ? 'bg-orange-400 animate-pulse' : 'bg-green-500'}`} />
                            <span className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-tighter">Live Dataset</span>
                        </div>

                        {/* Sheet Selection */}
                        <select
                            value={activeSheet}
                            onChange={(e) => setActiveSheet(e.target.value)}
                            className="bg-[var(--wdd-surface)] border border-[var(--wdd-border)] text-xs font-bold rounded-full px-4 py-1.5 focus:outline-none"
                        >
                            {sheets.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                        </select>

                        {/* Range Pills */}
                        <div className="flex bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-full p-1">
                            {(['all', '24h', '7d', '30d'] as const).map(r => (
                                <button
                                    key={r}
                                    onClick={() => setTimeRange(r)}
                                    className={`px-3 py-1 text-[11px] font-bold rounded-full transition-all ${timeRange === r ? 'bg-white text-[var(--wdd-black)] shadow-sm' : 'text-[var(--wdd-muted)] hover:text-[var(--wdd-black)]'}`}
                                >
                                    {r.toUpperCase()}
                                </button>
                            ))}
                        </div>

                        <button onClick={loadAll} className="p-2 hover:bg-[var(--wdd-surface)] rounded-full transition-colors">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.26l5.08 5.08" /></svg>
                        </button>

                        <Link href="/">
                            <button className="bg-[var(--wdd-black)] text-white text-[10px] font-bold px-4 py-1.5 rounded-full hover:brightness-125 transition-all tracking-widest">
                                CONCIERGE
                            </button>
                        </Link>
                    </div>
                </div>
            </header>

            <main className="max-w-[1400px] mx-auto px-6 py-8 space-y-12 animate-fade-in">

                {/* Segment B: KPI Strip */}
                <section>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        <KPITile label="Total leads" value={activeMetrics?.totalLeads} accent />
                        <KPITile label="Last 24h" value={activeMetrics ? (activeMetrics as any).intake24 : 0} />
                        <KPITile label="Unique contacts" value={activeMetrics?.uniqueContacts} />
                        <KPITile label="Top project" value={activeMetrics?.topProj} />
                        <KPITile label="Top region" value={activeMetrics?.topReg} />
                        <KPITile
                            label="Budget Median"
                            value={activeMetrics?.medianBudget ? `${(activeMetrics.medianBudget / 1e6).toFixed(1)}M` : '—'}
                        />
                    </div>
                </section>

                {/* Segment B.2: Funnel Strip */}
                <section>
                    <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                        <h3 className="text-sm font-semibold mb-6">Concierge Funnel Conversion</h3>
                        <FunnelStrip captureCount={activeMetrics?.totalLeads || 0} />
                    </div>
                </section>

                {/* Segment C: Analytics Section */}
                <section className="space-y-6">
                    <h2 className="text-xl font-bold tracking-tight border-l-4 border-[var(--wdd-red)] pl-4">Lead Acquisition & Distribution</h2>
                    <div className="grid lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2 bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-6 flex justify-between items-center">
                                Acquisition Velocity
                                <span className="text-[10px] text-[var(--wdd-muted)] uppercase tracking-widest font-bold">Trend Line</span>
                            </h3>
                            <LeadsTimeChart data={timeseries} />
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-6">Unit Type Distribution</h3>
                            <DistributionDonut data={activeMetrics?.distributions.unitTypes || []} />
                        </div>

                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-6">Top Project Demand</h3>
                            <DistributionBar data={activeMetrics?.distributions.projects.slice(0, 5) || []} layout="vertical" color="mixed" />
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-6">Volume by District</h3>
                            <DistributionBar data={activeMetrics?.distributions.regions.slice(0, 5) || []} layout="vertical" color="#55575A" />
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-4">Lead Purpose</h3>
                            <DistributionBar data={activeMetrics?.distributions.purposes || []} />
                        </div>
                    </div>

                    <div className="grid lg:grid-cols-3 gap-6 mt-6">
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-4">Temperature</h3>
                            <DistributionDonut data={activeMetrics?.distributions.temperatures || []} />
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-4">Budget Bands</h3>
                            <DistributionBar data={activeMetrics?.distributions.budgetBands || []} color="#55575A" />
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <h3 className="text-sm font-semibold mb-4">Timeline</h3>
                            <DistributionBar data={activeMetrics?.distributions.timelines || []} color="mixed" />
                        </div>
                    </div>
                </section>

                {/* Segment D: Qualified Leads Section */}
                <section className="bg-white border border-[var(--wdd-border)] rounded-[20px] shadow-sm overflow-hidden">
                    <div className="p-6 border-b border-[var(--wdd-border)] flex items-center justify-between flex-wrap gap-4">
                        <div className="flex items-center gap-6">
                            <h2 className="text-xl font-bold">Qualified Leads</h2>
                            <div className="flex overflow-x-auto no-scrollbar gap-2 max-w-md">
                                {availableRegions.map(reg => (
                                    <button
                                        key={reg}
                                        onClick={() => setRegionFilter(reg)}
                                        className={`px-3 py-1 rounded-full text-[10px] font-bold border transition-all whitespace-nowrap ${regionFilter === reg ? 'bg-[var(--wdd-red)] text-white border-[var(--wdd-red)]' : 'bg-[var(--wdd-surface)] text-[var(--wdd-muted)] border-[var(--wdd-border)] hover:border-[var(--wdd-black)] text-[var(--wdd-black)]'}`}
                                    >
                                        {reg}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="relative flex-1 max-w-sm">
                            <input
                                type="text"
                                placeholder="Search leads by name, phone, or project..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-full px-10 py-2.5 text-xs focus:ring-1 focus:ring-[var(--wdd-red)] outline-none"
                            />
                            <svg className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--wdd-muted)]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
                        </div>
                    </div>
                    <div className="p-2">
                        <LeadTable
                            leads={filteredLeads}
                            loading={loading}
                            onSelect={(l) => { setSelectedLead(l); setDrawerOpen(true); }}
                        />
                    </div>
                </section>

                {/* Segment E: Runtime Sheets */}
                <section className="space-y-6">
                    <h2 className="text-xl font-bold tracking-tight flex items-center gap-3">
                        <span className="w-2 h-8 bg-[var(--wdd-black)] rounded-full" />
                        Runtime Environment Sheets
                    </h2>
                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {sheets.map(s => (
                            <div key={s.name} className="bg-white border border-[var(--wdd-border)] rounded-xl p-5 hover:shadow-md transition-shadow group">
                                <div className="flex items-start justify-between mb-4">
                                    <div className="p-2 bg-[var(--wdd-surface)] rounded-lg text-lg">📄</div>
                                    <span className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase px-2 py-0.5 bg-[var(--wdd-surface)] rounded-md border border-[var(--wdd-border)]">{s.type}</span>
                                </div>
                                <h4 className="font-bold text-sm mb-1 truncate">{s.name}</h4>
                                <p className="text-[10px] text-[var(--wdd-muted)] mb-4">{s.rows} rows · {(s.size_bytes / 1024).toFixed(1)} KB</p>
                                <div className="flex gap-2">
                                    <button
                                        className="flex-1 bg-[var(--wdd-surface)] text-[var(--wdd-black)] text-[10px] font-bold py-2 rounded-lg hover:bg-[var(--wdd-border)] transition-colors"
                                        onClick={() => { setActiveSheet(s.name); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                                    >
                                        PREVIEW
                                    </button>
                                    <a href={downloadSheetUrl(s.name, 'csv')} download className="p-2 bg-[var(--wdd-surface)] rounded-lg hover:text-[var(--wdd-red)] transition-colors">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" /></svg>
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Segment F: Retrieval Quality */}
                <section className="bg-[var(--wdd-black)] text-white rounded-[24px] p-8 lg:p-12 overflow-hidden relative shadow-2xl">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 blur-3xl rounded-full -mr-32 -mt-32" />
                    <div className="relative z-10 grid lg:grid-cols-3 gap-12 items-center">
                        <div>
                            <span className="inline-block px-3 py-1 bg-white/10 rounded-full text-[10px] font-bold tracking-widest uppercase mb-4 text-[#FFD700]">RAG AUDIT</span>
                            <h2 className="text-3xl font-bold mb-4">Retrieval Quality</h2>
                            <p className="text-sm text-gray-400 font-light leading-relaxed">
                                Real-time telemetry monitoring the precision of the Hybrid-RAG engine.
                                We track empty retrievals and entity matching across all conversational intent.
                            </p>
                        </div>
                        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Total Queries</p>
                                <p className="text-4xl font-bold">{qualityMetrics?.totalQueries || 0}</p>
                            </div>
                            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Empty Retrieval %</p>
                                <p className="text-4xl font-bold">{(qualityMetrics?.emptyRetrievalRate || 0 * 100).toFixed(1)}%</p>
                            </div>
                            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 backdrop-blur-sm">
                                <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Top Retrieved</p>
                                <p className="text-xl font-bold truncate mt-2">{qualityMetrics?.topEntity}</p>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Segment G: Executive Summary */}
                <section className="bg-[var(--wdd-red)] text-white rounded-[24px] p-8 lg:p-12 shadow-xl">
                    <div className="max-w-3xl">
                        <h2 className="text-2xl font-bold mb-8">Executive Intelligence Summary</h2>
                        <div className="grid md:grid-cols-2 gap-8">
                            <div>
                                <h4 className="text-[10px] font-bold tracking-[0.2em] uppercase mb-4 opacity-70">What This Proves</h4>
                                <ul className="space-y-4 text-sm font-light">
                                    <li className="flex gap-3"><span className="text-[#FFD700]">✔</span> System handle {activeMetrics?.uniqueContacts} validated lead sessions.</li>
                                    <li className="flex gap-3"><span className="text-[#FFD700]">✔</span> Primary intent focused on {activeMetrics?.topProj}.</li>
                                    <li className="flex gap-3"><span className="text-[#FFD700]">✔</span> Demand concentration highest in {activeMetrics?.topReg}.</li>
                                </ul>
                            </div>
                            <div>
                                <h4 className="text-[10px] font-bold tracking-[0.2em] uppercase mb-4 opacity-70">Expansion Scope</h4>
                                <ul className="space-y-4 text-sm font-light">
                                    <li className="flex gap-3"><span className="opacity-50">○</span> Increase retrieval density for secondary projects.</li>
                                    <li className="flex gap-3"><span className="opacity-50">○</span> Deploy automated callback scheduling.</li>
                                    <li className="flex gap-3"><span className="opacity-50">○</span> Deepen integration with inventory API.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </section>

            </main>

            <LeadDrawer lead={selectedLead} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        </div>
    );
}
