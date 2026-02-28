'use client';
import React, { useCallback, useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
    adminLogin, adminLogout, fetchAdminStats, fetchLeads,
    type AdminDashboard, type LeadFilter,
} from '@/lib/api';
import KPITile from '@/components/admin/KPITile';
import { LeadsTimeChart, TopProjectsChart, TopRegionsChart } from '@/components/admin/Charts';
import LeadTable from '@/components/admin/LeadTable';
import LeadDrawer from '@/components/admin/LeadDrawer';
import DataViewer from '@/components/admin/DataViewer';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';

type Tab = 'dashboard' | 'leads' | 'data';

export default function AdminPage() {
    const [authed, setAuthed] = useState(false);
    const [password, setPassword] = useState('');
    const [loginErr, setLoginErr] = useState('');
    const [loginLoading, setLoginLoading] = useState(false);

    const [tab, setTab] = useState<Tab>('dashboard');
    const [stats, setStats] = useState<AdminDashboard | null>(null);
    const [statsLoading, setStatsLoading] = useState(false);

    const [leads, setLeads] = useState<Record<string, string>[]>([]);
    const [leadsTotal, setLeadsTotal] = useState(0);
    const [leadsLoading, setLeadsLoading] = useState(false);
    const [filters, setFilters] = useState<LeadFilter>({ time_filter: 'all' });

    const [selectedLead, setSelectedLead] = useState<Record<string, string> | null>(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    // ── Check existing auth on mount ──
    useEffect(() => {
        fetchAdminStats()
            .then((s) => { setStats(s); setAuthed(true); })
            .catch(() => setAuthed(false));
    }, []);

    async function handleLogin(e: React.FormEvent) {
        e.preventDefault();
        setLoginErr('');
        setLoginLoading(true);
        try {
            await adminLogin(password);
            setAuthed(true);
        } catch {
            setLoginErr('Invalid password. Please try again.');
        } finally {
            setLoginLoading(false);
        }
    }

    const loadStats = useCallback(async () => {
        setStatsLoading(true);
        try { setStats(await fetchAdminStats()); } catch { /* noop */ }
        finally { setStatsLoading(false); }
    }, []);

    const loadLeads = useCallback(async () => {
        setLeadsLoading(true);
        try {
            const res = await fetchLeads(filters);
            setLeads(res.leads);
            setLeadsTotal(res.total);
        } catch { /* noop */ }
        finally { setLeadsLoading(false); }
    }, [filters]);

    useEffect(() => { if (authed) { loadStats(); } }, [authed, loadStats]);
    useEffect(() => { if (authed && tab === 'leads') { loadLeads(); } }, [authed, tab, loadLeads]);

    // ── Login screen ────────────────────────────────────────────────────────────
    if (!authed) {
        return (
            <div className="min-h-screen bg-[var(--wdd-surface)] flex items-center justify-center px-4">
                <div className="w-full max-w-sm">
                    <div className="flex flex-col items-center mb-8">
                        <Image src="/brand/WDD_blockLogo.png" width={64} height={64} alt="WDD" className="object-contain mb-4" />
                        <h1 className="text-xl font-bold text-[var(--wdd-black)]">PulseX Admin</h1>
                        <p className="text-sm text-[var(--wdd-muted)] mt-1">Wadi Degla Developments</p>
                    </div>
                    <form onSubmit={handleLogin} className="bg-white border border-[var(--wdd-border)] rounded-[var(--wdd-radius-lg)] p-6 shadow-[var(--wdd-shadow)] space-y-4">
                        <div className="space-y-1.5">
                            <label className="block text-xs font-medium text-[var(--wdd-text)]">Admin Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter admin password"
                                className="w-full px-3 py-2 text-sm rounded-[var(--wdd-radius)] border border-[var(--wdd-border)] focus:outline-none focus:ring-2 focus:ring-[var(--wdd-red)] focus:border-transparent"
                                autoFocus
                            />
                        </div>
                        {loginErr && <p className="text-xs text-[var(--wdd-red)] font-medium">{loginErr}</p>}
                        <Button type="submit" variant="primary" size="md" loading={loginLoading} className="w-full">
                            Log in
                        </Button>
                    </form>
                    <p className="text-center text-[10px] text-[var(--wdd-muted)] mt-4">
                        ADMIN_PASSWORD is set in your .env file
                    </p>
                </div>
            </div>
        );
    }

    // ── Dashboard ───────────────────────────────────────────────────────────────
    return (
        <div className="min-h-screen bg-[var(--wdd-surface)]">
            {/* Sticky header */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)] shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
                <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-7 w-auto object-contain" />
                        <span className="text-xs text-[var(--wdd-muted)] border-l border-[var(--wdd-border)] pl-3">PulseX Admin</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link href="/" className="text-xs text-[var(--wdd-muted)] hover:text-[var(--wdd-red)]">← Back to site</Link>
                        <button
                            onClick={async () => { await adminLogout(); setAuthed(false); }}
                            className="text-xs text-[var(--wdd-muted)] hover:text-[var(--wdd-red)] transition-colors"
                        >
                            Log out
                        </button>
                    </div>
                </div>
            </header>

            {/* Tab bar */}
            <div className="bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-7xl mx-auto px-6 flex items-center gap-1">
                    {([
                        { id: 'dashboard' as Tab, label: '📊 Dashboard' },
                        { id: 'leads' as Tab, label: '👤 Leads' },
                        { id: 'data' as Tab, label: '🗂 Data Viewer' },
                    ] as const).map((t) => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id)}
                            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${tab === t.id
                                    ? 'border-[var(--wdd-red)] text-[var(--wdd-red)]'
                                    : 'border-transparent text-[var(--wdd-muted)] hover:text-[var(--wdd-text)]'
                                }`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-6 py-8">

                {/* ── DASHBOARD TAB ── */}
                {tab === 'dashboard' && (
                    <div className="space-y-8 animate-fade-in">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold text-[var(--wdd-black)]">Overview</h2>
                            <Button variant="ghost" size="sm" onClick={loadStats} disabled={statsLoading}>
                                {statsLoading ? <Spinner size="sm" /> : '↻ Refresh'}
                            </Button>
                        </div>

                        {stats ? (
                            <>
                                {/* KPI tiles */}
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                                    <KPITile label="Total Leads" value={stats.kpi.total_leads} icon="📋" accent />
                                    <KPITile label="Last 24 Hours" value={stats.kpi.last_24h} icon="⏱" />
                                    <KPITile label="Unique Contacts" value={stats.kpi.unique_contacts} icon="👤" />
                                    <KPITile label="Top Project" value={stats.kpi.top_project ?? '—'} icon="🏡" />
                                    <KPITile label="Top Region" value={stats.kpi.top_region ?? '—'} icon="📍" />
                                    <KPITile
                                        label="Median Budget"
                                        value={stats.kpi.median_budget_min != null ? `${(stats.kpi.median_budget_min / 1e6).toFixed(1)}–${((stats.kpi.median_budget_max ?? stats.kpi.median_budget_min) / 1e6).toFixed(1)}M` : '—'}
                                        icon="💰"
                                    />
                                </div>

                                {/* Charts */}
                                <div className="grid md:grid-cols-1 gap-6">
                                    <LeadsTimeChart data={stats.daily_leads} />
                                </div>
                                <div className="grid md:grid-cols-2 gap-6">
                                    <TopProjectsChart data={stats.top_projects} />
                                    <TopRegionsChart data={stats.top_regions} />
                                </div>
                            </>
                        ) : (
                            <div className="py-16 flex justify-center"><Spinner size="lg" /></div>
                        )}
                    </div>
                )}

                {/* ── LEADS TAB ── */}
                {tab === 'leads' && (
                    <div className="space-y-5 animate-fade-in">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-bold text-[var(--wdd-black)]">Leads <span className="text-sm font-normal text-[var(--wdd-muted)]">({leadsTotal})</span></h2>
                            <Button variant="ghost" size="sm" onClick={loadLeads} disabled={leadsLoading}>
                                {leadsLoading ? <Spinner size="sm" /> : '↻ Refresh'}
                            </Button>
                        </div>

                        {/* Filters */}
                        <div className="flex flex-wrap items-center gap-3 bg-white border border-[var(--wdd-border)] rounded-[var(--wdd-radius-lg)] px-4 py-3">
                            {(['all', '24h', '7d', '30d'] as const).map((tf) => (
                                <button
                                    key={tf}
                                    onClick={() => setFilters((f) => ({ ...f, time_filter: tf }))}
                                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${filters.time_filter === tf
                                            ? 'bg-[var(--wdd-red)] text-white border-[var(--wdd-red)]'
                                            : 'bg-white text-[var(--wdd-text)] border-[var(--wdd-border)] hover:border-[var(--wdd-red)]'
                                        }`}
                                >
                                    {tf === 'all' ? 'All time' : tf === '24h' ? 'Last 24h' : tf === '7d' ? 'Last 7d' : 'Last 30d'}
                                </button>
                            ))}
                            <select
                                value={filters.purpose ?? ''}
                                onChange={(e) => setFilters((f) => ({ ...f, purpose: e.target.value || undefined }))}
                                className="ml-auto px-3 py-1.5 text-xs border border-[var(--wdd-border)] rounded-lg bg-white text-[var(--wdd-text)] focus:outline-none focus:ring-1 focus:ring-[var(--wdd-red)]"
                            >
                                <option value="">All purposes</option>
                                <option value="buy">Buy</option>
                                <option value="rent">Rent</option>
                                <option value="invest">Invest</option>
                            </select>
                        </div>

                        <LeadTable
                            leads={leads}
                            onSelect={(lead) => { setSelectedLead(lead); setDrawerOpen(true); }}
                            loading={leadsLoading}
                        />

                        <LeadDrawer
                            lead={selectedLead}
                            open={drawerOpen}
                            onClose={() => setDrawerOpen(false)}
                        />
                    </div>
                )}

                {/* ── DATA VIEWER TAB ── */}
                {tab === 'data' && (
                    <div className="space-y-5 animate-fade-in">
                        <h2 className="text-xl font-bold text-[var(--wdd-black)]">Runtime Data Viewer</h2>
                        <DataViewer />
                    </div>
                )}
            </main>
        </div>
    );
}
