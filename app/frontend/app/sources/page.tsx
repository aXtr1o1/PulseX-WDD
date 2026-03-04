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
        <div className="min-h-screen bg-white text-[var(--wdd-black)] font-isidora selection:bg-[var(--wdd-black)] selection:text-white">

            {/* Header */}
            <header className="fixed top-0 w-full bg-white/95 backdrop-blur-md z-40 border-b border-[var(--wdd-border)] px-6 md:px-12 h-[88px] grid grid-cols-3 items-center">
                <Link href="/" className="flex items-center gap-4 group justify-self-start">
                    <div className="w-10 h-10 bg-white border border-[var(--wdd-border)] rounded-full flex items-center justify-center text-[var(--wdd-black)] group-hover:bg-[var(--wdd-black)] group-hover:text-white transition-colors duration-300">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5M5 12L12 19M5 12L12 5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </div>
                    <span className="text-xs tracking-widest font-bold text-[var(--wdd-black)] uppercase hidden md:block group-hover:translate-x-1 transition-transform duration-300">Back to Concierge</span>
                </Link>

                <div className="flex flex-col items-center justify-center justify-self-center">
                    <div className="flex items-center gap-3 mb-2">
                        <Image src="/brand/WDD_fullLogo.png" width={140} height={36} alt="WDD" className="h-[22px] w-auto object-contain" />
                    </div>
                    <span className="text-[9px] uppercase tracking-[0.3em] text-[var(--wdd-red)] font-bold">Data Transparency</span>
                </div>

                <div className="justify-self-end">
                    {/* Placeholder for future actions */}
                </div>
            </header>

            {/* Main Content */}
            <main className="pt-40 px-6 md:px-12 pb-24 max-w-5xl mx-auto animate-fade-in">

                <div className="text-center mb-20 space-y-6">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-[var(--wdd-surface)] rounded-full mb-4 border border-[var(--wdd-border)]">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--wdd-red)]">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        <span className="text-[10px] uppercase tracking-[0.2em] font-medium text-[var(--wdd-muted)]">System Source of Truth</span>
                    </div>
                    <h1 className="text-5xl md:text-6xl font-light text-[var(--wdd-black)] leading-tight tracking-tight">Verified Intelligence<span className="text-[var(--wdd-red)] font-bold">.</span></h1>

                    <p className="text-[var(--wdd-muted)] font-light text-[17px] max-w-2xl mx-auto leading-relaxed pt-2">
                        The Concierge is powered exclusively by validated data from the official Wadi Degla Developments portfolio. We strictly mandate the active master-sheet to ensure truthfulness and absolute privacy.
                    </p>

                    <div className="mt-8 max-w-2xl mx-auto p-5 bg-[#FCEDF0] border border-[#EAC2CA] rounded-xl text-left flex gap-4 items-start shadow-sm">
                        <div className="w-8 h-8 rounded-full bg-[var(--wdd-red)] flex items-center justify-center shrink-0 mt-0.5">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </div>
                        <div>
                            <h4 className="text-[13px] font-bold text-[var(--wdd-red)] tracking-wider uppercase mb-1">Pricing Policy Disclaimer</h4>
                            <p className="text-[14px] text-[var(--wdd-black)] leading-relaxed font-light">
                                The WDD Knowledge Base contains <strong className="font-semibold text-[var(--wdd-black)]">no publicly listed pricing ranges</strong> for any property or project. All pricing is dynamic and strictly available upon request from our official sales channels.
                            </p>
                        </div>
                    </div>
                </div>

                {loading ? (
                    <div className="py-20 flex justify-center"><Spinner size="lg" /></div>
                ) : error ? (
                    <div className="p-4 bg-red-50 text-[var(--wdd-red)] text-sm rounded-lg border border-red-100">{error}</div>
                ) : data && (
                    <>
                        {/* Data Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
                            {data.regions.map((portfolio, idx) => (
                                <div key={idx} className="bg-[var(--wdd-surface)] p-8 rounded-3xl border border-[var(--wdd-border)] hover:border-[var(--wdd-black)] transition-all duration-500 group">
                                    <h3 className="text-2xl text-[var(--wdd-black)] font-light mb-6 px-4 border-l-2 border-[var(--wdd-red)]">{portfolio.region}</h3>
                                    <ul className="space-y-4">
                                        {portfolio.projects.map((project) => (
                                            <li key={project} className="flex items-center gap-3 px-4 py-3 bg-white rounded-xl shadow-sm border border-[var(--wdd-border)] group-hover:translate-x-1 transition-transform duration-300">
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--wdd-red)] flex-shrink-0">
                                                    <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                                                </svg>
                                                <span className="text-[14px] font-medium tracking-wide text-[var(--wdd-black)]">{project}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ))}
                        </div>

                        {/* File Meta */}
                        <div className="bg-[#191919] text-white p-10 rounded-3xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--wdd-red)]/10 blur-[80px] rounded-full pointer-events-none"></div>

                            <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
                                <div className="space-y-4">
                                    <div className="flex items-center gap-3 text-white/50">
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round" />
                                            <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
                                            <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round" />
                                            <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round" />
                                            <polyline points="10 9 9 9 8 9" strokeLinecap="round" strokeLinejoin="round" />
                                        </svg>
                                        <span className="text-xs uppercase tracking-[0.2em] font-bold text-[var(--wdd-red)]">Primary Knowledge Base</span>
                                    </div>
                                    <h4 className="text-3xl font-light">{data.kb_health.filename}</h4>

                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-4 text-sm text-[#888] font-mono mt-6">
                                        <div>
                                            <p className="text-[10px] uppercase mb-1">Status</p>
                                            <span className="text-white">Active</span>
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase mb-1">Indexed</p>
                                            <span className="text-white">{new Date(data.kb_health.last_indexed_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase mb-1">Entities</p>
                                            <span className="text-white">{data.kb_health.total_entities}</span>
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase mb-1">Schema</p>
                                            <span className={data.kb_health.schema_strict ? "text-green-400" : "text-amber-400"}>
                                                {data.kb_health.schema_strict ? "Strict" : "Lenient"}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="pt-2 text-[#888] font-mono text-xs">
                                        <p className="text-[10px] uppercase mb-1">SHA-256 Checksum</p>
                                        <span className="break-all">{data.kb_health.kb_hash}</span>
                                    </div>
                                </div>

                                <div className="flex flex-col gap-2 shrink-0 md:min-w-[140px]">
                                    <div className="px-6 py-6 bg-white/5 rounded-2xl text-center backdrop-blur-sm border border-white/10">
                                        <span className="block text-4xl font-light text-white mb-1">100%</span>
                                        <span className="text-[9px] uppercase tracking-widest text-[#888] font-bold">Verified Data</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-12 text-center border-t border-[var(--wdd-border)] pt-8">
                            <p className="text-xs text-[var(--wdd-muted)] font-light">
                                *This data transparency report is generated automatically by the PulseX System for Wadi Degla Developments.
                            </p>
                        </div>
                    </>
                )}
            </main>
        </div>
    );
}
