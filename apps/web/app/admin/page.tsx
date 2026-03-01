'use client';
import React, { useCallback, useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
    fetchAdminStats, fetchLeads,
    type AdminDashboard, type LeadFilter,
} from '@/lib/api';
import KPITile from '@/components/admin/KPITile';
import { LeadsTimeChart, TopProjectsChart, TopRegionsChart } from '@/components/admin/Charts';
import LeadTable from '@/components/admin/LeadTable';
import LeadDrawer from '@/components/admin/LeadDrawer';
import DataViewer from '@/components/admin/DataViewer';
import Spinner from '@/components/ui/Spinner';

export default function AdminPage() {
    const [stats, setStats] = useState<AdminDashboard | null>(null);
    const [statsLoading, setStatsLoading] = useState(false);

    const [leads, setLeads] = useState<Record<string, string>[]>([]);
    const [leadsTotal, setLeadsTotal] = useState(0);
    const [leadsLoading, setLeadsLoading] = useState(false);

    const [timeFilter, setTimeFilter] = useState<'all' | '24h' | '7d' | '30d'>('all');
    const [sheetView, setSheetView] = useState<'dashboard' | 'leads' | 'audit' | 'sessions'>('dashboard');

    const [selectedLead, setSelectedLead] = useState<Record<string, string> | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    const loadStats = useCallback(async () => {
        setStatsLoading(true);
        try { setStats(await fetchAdminStats()); } catch { /* noop */ }
        finally { setStatsLoading(false); }
    }, []);

    const loadLeads = useCallback(async () => {
        setLeadsLoading(true);
        try {
            const res = await fetchLeads({ time_filter: timeFilter });
            setLeads(res.leads);
            setLeadsTotal(res.total);
        } catch { /* noop */ }
        finally { setLeadsLoading(false); }
    }, [timeFilter]);

    useEffect(() => { loadStats(); }, [loadStats]);
    useEffect(() => { loadLeads(); }, [loadLeads]);

    if (!stats && statsLoading) {
        return (
            <div className="min-h-screen bg-[var(--wdd-bg)] flex flex-col items-center justify-center animate-pulse-soft">
                <Image src="/brand/WDD_blockLogo.png" width={72} height={72} alt="Loading..." className="object-contain mb-6" priority />
                <p className="text-sm font-medium text-[var(--wdd-muted)] tracking-wider uppercase">Loading Intelligence...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[var(--wdd-surface)] font-isidora">

            {/* Header / Command Bar */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">

                    {/* Left: Branding */}
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-7 w-auto object-contain hover:opacity-80 transition-opacity" />
                        </Link>
                        <div className="flex items-center gap-2 border-l border-[var(--wdd-border)] pl-4">
                            <span className="text-xs font-semibold text-[var(--wdd-black)] tracking-wider">LEAD INTELLIGENCE</span>
                        </div>
                    </div>

                    {/* Right: Controls & Filters */}
                    <div className="flex items-center gap-4">

                        {/* Time Filter */}
                        <div className="flex bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-full p-1">
                            {([
                                { id: 'all', label: 'All' },
                                { id: '24h', label: '24h' },
                                { id: '7d', label: '7d' },
                                { id: '30d', label: '30d' }
                            ] as const).map(tf => (
                                <button
                                    key={tf.id}
                                    onClick={() => setTimeFilter(tf.id)}
                                    className={`px-3 py-1 text-[11px] font-semibold rounded-full transition-colors ${timeFilter === tf.id
                                        ? 'bg-white text-[var(--wdd-black)] shadow-sm'
                                        : 'text-[var(--wdd-muted)] hover:text-[var(--wdd-black)]'
                                        }`}
                                >
                                    {tf.label}
                                </button>
                            ))}
                        </div>

                        {/* View/Sheet Selector */}
                        <select
                            value={sheetView}
                            onChange={(e) => setSheetView(e.target.value as any)}
                            className="bg-white border border-[var(--wdd-border)] text-xs font-medium text-[var(--wdd-black)] rounded-full px-4 py-1.5 focus:outline-none focus:ring-1 focus:ring-[var(--wdd-red)]"
                        >
                            <option value="dashboard">Executive Dashboard</option>
                            <option value="leads">leads.csv</option>
                            <option value="audit">audit.csv</option>
                            <option value="sessions">sessions.csv</option>
                        </select>

                        {/* Refresh */}
                        <button
                            onClick={() => { loadStats(); loadLeads(); }}
                            className="text-xs font-semibold text-[var(--wdd-muted)] hover:text-[var(--wdd-black)] transition-colors flex items-center gap-1.5"
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.26l5.08 5.08" /></svg>
                            Refresh
                        </button>
                    </div>
                </div>
            </header>

            <main className="max-w-[1400px] mx-auto px-6 py-8 animate-fade-in">

                {/* ── Dashboard Segment ── */}
                {sheetView === 'dashboard' && stats && (
                    <div className="space-y-8">
                        {/* KPI Strip */}
                        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                            <KPITile label="Total Active Leads" value={stats.kpi.total_leads} accent icon="" />
                            <KPITile label="Intake (Last 24h)" value={stats.kpi.last_24h} icon="" />
                            <KPITile label="Unique Contacts" value={stats.kpi.unique_contacts} icon="" />
                            <KPITile label="Top Project Demand" value={stats.kpi.top_project ?? '—'} icon="" />
                            <KPITile label="Top District Demanded" value={stats.kpi.top_region ?? '—'} icon="" />
                            <KPITile
                                label="Median Target Budget"
                                value={stats.kpi.median_budget_min != null ? `${(stats.kpi.median_budget_min / 1e6).toFixed(1)}–${((stats.kpi.median_budget_max ?? stats.kpi.median_budget_min) / 1e6).toFixed(1)}M` : '—'}
                                icon=""
                            />
                        </div>

                        {/* Charts Strip */}
                        <div className="grid lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2 bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                                <h3 className="text-sm font-semibold text-[var(--wdd-black)] mb-6">Lead Acquisition Velocity</h3>
                                <LeadsTimeChart data={stats.daily_leads} />
                            </div>
                            <div className="space-y-6 flex flex-col">
                                <div className="flex-1 bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                                    <h3 className="text-sm font-semibold text-[var(--wdd-black)] mb-6">Volume by Project</h3>
                                    <TopProjectsChart data={stats.top_projects} />
                                </div>
                            </div>
                        </div>

                        {/* Recent Leads Preview */}
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                            <div className="flex items-center justify-between mb-6">
                                <h3 className="text-sm font-semibold text-[var(--wdd-black)]">Recent Qualified Leads</h3>
                                <button
                                    onClick={() => setSheetView('leads')}
                                    className="text-xs font-semibold text-[var(--wdd-red)] hover:underline"
                                >
                                    View all {leadsTotal} leads →
                                </button>
                            </div>
                            <LeadTable
                                leads={leads.slice(0, 5)}
                                onSelect={(lead) => { setSelectedLead(lead); setDrawerOpen(true); }}
                                loading={leadsLoading}
                            />
                        </div>
                    </div>
                )}

                {/* ── Raw Sheets Segments ── */}
                {sheetView === 'leads' && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold text-[var(--wdd-black)]">
                                Qualified Leads Rollup <span className="text-sm font-normal text-[var(--wdd-muted)]">({leadsTotal})</span>
                            </h2>
                        </div>
                        <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-2 shadow-sm">
                            <LeadTable
                                leads={leads}
                                onSelect={(lead) => { setSelectedLead(lead); setDrawerOpen(true); }}
                                loading={leadsLoading}
                            />
                        </div>
                    </div>
                )}

                {sheetView === 'audit' && (
                    <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                        <h2 className="text-xl font-bold text-[var(--wdd-black)] mb-6">Platform Audit Logs (audit.csv)</h2>
                        <DataViewer forceSheet="audit" />
                    </div>
                )}

                {sheetView === 'sessions' && (
                    <div className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                        <h2 className="text-xl font-bold text-[var(--wdd-black)] mb-6">Session Telemetry (sessions.csv)</h2>
                        <DataViewer forceSheet="sessions" />
                    </div>
                )}

            </main>

            {/* Global Lead Drawer */}
            <LeadDrawer lead={selectedLead} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        </div>
    );
}
