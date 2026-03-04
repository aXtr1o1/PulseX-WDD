'use client';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import Spinner from '@/components/ui/Spinner';

interface SourceGroup {
    region: string;
    projects: string[];
}

interface SourcesData {
    kb_health: {
        filename: string;
        kb_hash: string;
        last_indexed_at: string;
        schema_strict: boolean;
        total_entities: number;
    };
    regions: SourceGroup[];
}

export default function SourcesPage() {
    const [data, setData] = useState<SourcesData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchSources = async () => {
            try {
                const res = await fetch('/api/admin/sources');
                if (!res.ok) throw new Error('Failed to load sources');
                setData(await res.json());
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            } finally {
                setLoading(false);
            }
        };
        fetchSources();
    }, []);

    return (
        <div className="min-h-screen bg-[var(--wdd-surface)] font-isidora">
            {/* Header */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1200px] mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-7 w-auto object-contain hover:opacity-80 transition-opacity" />
                        </Link>
                        <div className="flex items-center gap-2 border-l border-[var(--wdd-border)] pl-4">
                            <span className="text-xs font-semibold text-[var(--wdd-black)] tracking-wider">VERIFIED INTELLIGENCE</span>
                        </div>
                    </div>
                    <Link href="/" className="text-xs font-semibold text-[var(--wdd-muted)] hover:text-[var(--wdd-black)] transition-colors">
                        ← Back to Concierge
                    </Link>
                </div>
            </header>

            <main className="max-w-[1200px] mx-auto px-6 py-12 animate-fade-in">

                <div className="mb-10 max-w-2xl">
                    <h1 className="text-3xl font-bold text-[var(--wdd-black)] mb-3">Data Sources</h1>
                    <p className="text-sm text-[var(--wdd-muted)] leading-relaxed">
                        PulseX relies strictly on verified WDD information. Below is the ground truth database powering retrieval, gated by hard metadata rules to prevent hallucinated inventory or pricing.
                    </p>
                </div>

                {loading ? (
                    <div className="py-20 flex justify-center"><Spinner size="lg" /></div>
                ) : error ? (
                    <div className="p-4 bg-red-50 text-[var(--wdd-red)] text-sm rounded-lg border border-red-100">{error}</div>
                ) : data && (
                    <div className="grid lg:grid-cols-3 gap-8">

                        {/* Summary / Health Card */}
                        <div className="lg:col-span-1 space-y-6">
                            <div className="bg-[#191919] text-white rounded-[24px] p-6 shadow-sm border border-[#333]">
                                <h3 className="text-xs font-bold uppercase tracking-wider text-[#A0A0A0] mb-6">Knowledge Base Health</h3>

                                <div className="space-y-5">
                                    <div>
                                        <p className="text-[10px] text-[#888] uppercase mb-1">Source File</p>
                                        <p className="text-sm font-medium">{data.kb_health.filename}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-[#888] uppercase mb-1">SHA-256 Hash</p>
                                        <p className="text-[11px] font-mono break-all text-[#CCC]">{data.kb_health.kb_hash}</p>
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <p className="text-[10px] text-[#888] uppercase mb-1">Index Date</p>
                                            <p className="text-xs font-medium">{new Date(data.kb_health.last_indexed_at).toLocaleDateString()}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-[#888] uppercase mb-1">Total Entities</p>
                                            <p className="text-xs font-medium">{data.kb_health.total_entities}</p>
                                        </div>
                                    </div>

                                    <div className="pt-4 border-t border-[#333] mt-2 flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="w-2.5 h-2.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)] block"></span>
                                            <span className="text-xs font-semibold tracking-wider uppercase">Schema Strict</span>
                                        </div>
                                        {data.kb_health.schema_strict && (
                                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-green-500"><path d="M20 6L9 17l-5-5" /></svg>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white border border-[var(--wdd-border)] rounded-[24px] p-6 shadow-sm">
                                <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--wdd-black)] mb-3">Retrieval Gating</h3>
                                <p className="text-sm text-[var(--wdd-muted)] leading-relaxed">
                                    Queries are gated by region and project parameters. Answers fallback to <span className="text-[var(--wdd-black)] font-medium">&quot;I don&apos;t have verified info... but I can arrange a callback&quot;</span> if exact match trust falls below 0.72.
                                </p>
                            </div>
                        </div>

                        {/* Regions List */}
                        <div className="lg:col-span-2 space-y-4">
                            {data.regions.map((group, idx) => (
                                <div key={idx} className="bg-white border border-[var(--wdd-border)] rounded-[20px] p-6 shadow-sm">
                                    <h2 className="text-lg font-bold text-[var(--wdd-black)] mb-4">{group.region}</h2>
                                    <div className="flex flex-wrap gap-2.5">
                                        {group.projects.map((proj, i) => (
                                            <span
                                                key={i}
                                                className="px-3 py-1.5 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] text-sm font-medium text-[var(--wdd-text)] rounded-lg"
                                            >
                                                {proj}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                    </div>
                )}
            </main>
        </div>
    );
}
