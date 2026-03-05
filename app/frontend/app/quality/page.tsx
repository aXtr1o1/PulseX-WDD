'use client';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import Spinner from '@/components/ui/Spinner';

interface QualityData {
    total_queries: number;
    empty_retrieval_pct: number;
    top_retrieved_entities: { name: string; count: number }[];
    intent_distribution: { intent: string; count: number }[];
    content_gaps: { query: string; reason: string }[];
}

export default function QualityPage() {
    const [data, setData] = useState<QualityData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchQuality = async () => {
            try {
                const res = await fetch('/api/admin/quality');
                if (!res.ok) throw new Error('Failed to load quality metrics');
                setData(await res.json());
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Unknown error');
            } finally {
                setLoading(false);
            }
        };
        fetchQuality();
    }, []);

    return (
        <div className="min-h-screen bg-[var(--wdd-surface)] font-isidora">
            {/* Header */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1200px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3 sm:gap-4">
                        <Link href="/" className="flex items-center gap-2 group">
                            <span className="p-1.5 rounded-full bg-[var(--wdd-surface)] text-[var(--wdd-black)] group-hover:bg-[var(--wdd-red)] group-hover:text-white transition-all">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="m15 18-6-6 6-6" /></svg>
                            </span>
                            <Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-6 sm:h-7 w-auto object-contain hover:opacity-80 transition-opacity hidden xs:block" />
                            <Image src="/brand/WDD_blockLogo.png" width={40} height={40} alt="WDD" className="h-6 w-auto object-contain xs:hidden" />
                        </Link>
                        <div className="flex items-center gap-2 border-l border-[var(--wdd-border)] pl-3 sm:pl-4">
                            <span className="text-[10px] sm:text-xs font-semibold text-[var(--wdd-black)] tracking-wider whitespace-nowrap">QUALITY</span>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-[1200px] mx-auto px-6 py-12 animate-fade-in">

                <div className="mb-10 max-w-3xl flex justify-between items-end">
                    <div>
                        <h1 className="text-3xl font-bold text-[var(--wdd-black)] mb-3">System Health</h1>
                        <p className="text-sm text-[var(--wdd-muted)] leading-relaxed max-w-2xl">
                            Continuous monitoring of retrieval metrics, intent recognition, and potential content gaps from the <code className="bg-[#EAEAEA] px-1.5 py-0.5 rounded text-xs text-[var(--wdd-black)] font-mono">audit.csv</code> telemetry.
                        </p>
                    </div>
                </div>

                {loading ? (
                    <div className="py-20 flex justify-center"><Spinner size="lg" /></div>
                ) : error ? (
                    <div className="p-4 bg-red-50 text-[var(--wdd-red)] text-sm rounded-lg border border-red-100">{error}</div>
                ) : data && (
                    <div className="grid lg:grid-cols-4 gap-6">

                        {/* Top Metrics Row */}
                        <div className="lg:col-span-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="bg-white border text-center border-[var(--wdd-border)] rounded-2xl p-6 shadow-sm">
                                <p className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-3">Total Queries</p>
                                <p className="text-3xl font-light text-[var(--wdd-black)]">{data.total_queries}</p>
                            </div>
                            <div className="bg-white border border-[var(--wdd-border)] rounded-2xl p-6 shadow-sm relative overflow-hidden">
                                <p className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-3 relative z-10 text-center">Empty Retrieval</p>
                                <p className={`text-3xl text-center font-light relative z-10 ${data.empty_retrieval_pct > 10 ? 'text-[var(--wdd-red)] font-semibold' : 'text-[var(--wdd-black)]'}`}>
                                    {data.empty_retrieval_pct.toFixed(1)}%
                                </p>
                                {data.empty_retrieval_pct > 10 && (
                                    <div className="absolute top-0 right-0 w-8 h-8 bg-[var(--wdd-red)] opacity-10 rounded-bl-full pointer-events-none"></div>
                                )}
                            </div>
                            <div className="bg-white border text-center border-[var(--wdd-border)] rounded-2xl p-6 shadow-sm lg:col-span-2">
                                <p className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-3">Primary User Intent</p>
                                <p className="text-3xl font-light text-[var(--wdd-black)] capitalize">
                                    {data.intent_distribution[0]?.intent || 'None'}
                                </p>
                            </div>
                        </div>

                        {/* Top Retrieved Entities */}
                        <div className="lg:col-span-2 bg-white border border-[var(--wdd-border)] rounded-2xl p-6 shadow-sm">
                            <h3 className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-6 flex items-center justify-between border-b border-[var(--wdd-border)] pb-3">
                                <span>Top Retrieved Entities</span>
                                <span className="opacity-60 text-[9px]">BY VOLUME</span>
                            </h3>
                            {data.top_retrieved_entities.length > 0 ? (
                                <ul className="space-y-4">
                                    {data.top_retrieved_entities.map((item, i) => (
                                        <li key={i} className="flex justify-between items-center text-sm group">
                                            <span className="text-[var(--wdd-black)] group-hover:text-[var(--wdd-red)] transition-colors">{item.name}</span>
                                            <span className="bg-[var(--wdd-surface)] text-[var(--wdd-muted)] px-2.5 py-0.5 rounded-md font-mono text-[11px] border border-[var(--wdd-border)]">{item.count}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="text-sm text-[var(--wdd-muted)] text-center py-8 border border-dashed border-[var(--wdd-border)] rounded-xl">No entities retrieved yet.</p>
                            )}
                        </div>

                        {/* Identified Content Gaps */}
                        <div className="lg:col-span-2 bg-[#FAF7F7] border border-[#F3E1E1] rounded-2xl p-6 shadow-sm">
                            <h3 className="text-xs font-bold tracking-widest text-[#B04C5A] uppercase mb-6 flex items-center justify-between border-b border-[#F3E1E1] pb-3">
                                <span>Identified Content Gaps</span>
                                <span className="flex h-2 w-2 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                                </span>
                            </h3>

                            {data.content_gaps.length > 0 ? (
                                <ul className="space-y-4">
                                    {data.content_gaps.map((gap, i) => (
                                        <li key={i} className="bg-white border border-[#F3E1E1] rounded-lg p-3 text-sm flex flex-col gap-1.5 shadow-[0_1px_2px_rgba(203,32,48,0.02)]">
                                            <span className="text-[var(--wdd-black)] truncate">&ldquo;{gap.query}&rdquo;</span>
                                            <span className="text-xs text-[#B04C5A] bg-[#FFF8F8] px-2 py-0.5 rounded w-fit capitalize block opacity-90">{gap.reason}</span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <div className="text-center py-8">
                                    <div className="text-3xl mb-2">🎉</div>
                                    <p className="text-sm text-[#B04C5A]">No content gaps detected.</p>
                                </div>
                            )}
                        </div>

                    </div>
                )}
            </main>
        </div>
    );
}
