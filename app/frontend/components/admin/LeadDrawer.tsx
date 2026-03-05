'use client';
import React, { useState } from 'react';
import Drawer from '@/components/ui/Drawer';
import { type LeadRecord } from '@/lib/api';

interface LeadDrawerProps {
    lead: LeadRecord | null;
    open: boolean;
    onClose: () => void;
}

export default function LeadDrawer({ lead, open, onClose }: LeadDrawerProps) {
    const [copied, setCopied] = useState(false);
    if (!lead) return null;

    async function copyRaw() {
        await navigator.clipboard.writeText(JSON.stringify(lead, null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }

    const formatBudget = () => {
        const band = lead.budget_band || '';
        const min = (lead as any).budget_min;
        const max = (lead as any).budget_max;
        if (min && max) {
            return `${(Number(min) / 1e6).toFixed(1)}M – ${(Number(max) / 1e6).toFixed(1)}M`;
        }
        return band || '—';
    };

    const formatDate = () => {
        const dateStr = lead.timestamp || lead.created_at;
        if (!dateStr) return '—';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch {
            return '—';
        }
    };

    const gridFields = [
        { label: 'Region', value: lead.region || lead.preferred_region || '—' },
        { label: 'Unit Type', value: lead.unit_type || '—' },
        { label: 'Purpose', value: lead.purpose || '—' },
        { label: 'Timeline', value: lead.timeline || '—' },
        { label: 'Budget', value: formatBudget() },
        { label: 'Date', value: formatDate() },
    ];

    const allProjects = lead.projects && lead.projects.length > 0 ? lead.projects : [];
    const allTags = lead.tags && lead.tags.length > 0 ? lead.tags : [];

    // Fallback to whichever summary is available
    const finalSummary = lead.customer_summary || lead.executive_summary || lead.summary;

    return (
        <Drawer
            open={open}
            onClose={onClose}
            title="Lead Detail"
            width="w-full xl:w-[600px] md:w-[40vw] md:min-w-[500px]"
        >
            <div className="flex flex-col pb-20 pt-2 lg:px-2">
                {/* Profile Header (Vertical) */}
                <div className="flex flex-col mb-6">
                    <div className="w-[56px] h-[56px] bg-[#0A0A0A] text-white rounded-full flex items-center justify-center text-[22px] font-medium shrink-0 shadow-sm">
                        {lead.name ? lead.name.charAt(0).toUpperCase() : 'A'}
                    </div>
                    <h2 className="text-[32px] font-medium text-[var(--wdd-black)] tracking-tight leading-none mt-5 mb-2">
                        {lead.name || 'Anonymous'}
                    </h2>
                    <div className="flex items-center gap-3">
                        <p className="text-[13px] font-mono text-zinc-600 tracking-[0.1em]">
                            {lead.phone || lead.contact || '—'}
                        </p>
                        {lead.lead_temperature && (
                            <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-sm ${lead.lead_temperature.toLowerCase() === 'hot' ? 'bg-red-100 text-red-700' : lead.lead_temperature.toLowerCase() === 'warm' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-700'}`}>
                                {lead.lead_temperature}
                            </span>
                        )}
                    </div>
                </div>

                <div className="w-full h-px bg-[var(--wdd-border)] opacity-60 mb-6"></div>

                {/* Grid (No Title) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-y-5 gap-x-12 mb-8">
                    {gridFields.map((f, idx) => (
                        <div key={idx} className="flex flex-col space-y-2">
                            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em]">{f.label}</span>
                            <span className="text-[14px] text-[var(--wdd-black)] font-medium leading-tight">{f.value}</span>
                        </div>
                    ))}
                </div>

                {/* Executive Summary */}
                {lead.executive_summary && (
                    <div className="mb-8">
                        <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-3">Executive Summary</h4>
                        <p className="text-[13px] font-medium text-[var(--wdd-black)] leading-relaxed">
                            {lead.executive_summary}
                        </p>
                    </div>
                )}

                {/* Projects of Interest */}
                {allProjects.length > 0 && (
                    <div className="mb-8">
                        <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-4">Projects of Interest</h4>
                        <div className="flex flex-wrap gap-2.5">
                            {allProjects.map((p, i) => (
                                <span key={i} className="px-4 py-1.5 border border-[var(--wdd-border)] bg-transparent rounded-full text-[12px] font-medium text-zinc-800">
                                    {p}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Tags */}
                {allTags.length > 0 && (
                    <div className="mb-8">
                        <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-4">Tags</h4>
                        <div className="flex flex-wrap gap-2">
                            {allTags.map((t, i) => (
                                <span key={i} className="px-3 py-1 bg-[#FFF4F4] border border-[#FFEAEA] rounded-[6px] text-[10px] font-bold text-red-500 lowercase">
                                    {t.replace(/_/g, '-')}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Next Action (if any, styled similar to summary or tags) */}
                {lead.next_action && (
                    <div className="mb-8">
                        <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-4">Next Action</h4>
                        <div className="p-4 rounded-[10px] bg-[#FFF6F6] border border-red-50">
                            <p className="text-[14px] font-medium leading-relaxed text-red-700">
                                → {lead.next_action}
                            </p>
                        </div>
                    </div>
                )}

                {/* Complete Summary */}
                {finalSummary && (
                    <div className="mb-8">
                        <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-4">Complete Summary</h4>
                        <div className="p-5 rounded-[12px] border border-[var(--wdd-border)] bg-[#FAFAFA]/50 shadow-sm">
                            <p className="text-[14px] leading-[1.6] font-normal text-zinc-800">
                                {finalSummary}
                            </p>
                        </div>
                    </div>
                )}

                {/* Raw Data */}
                <div className="pt-2">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em]">Raw Data</span>
                        <button onClick={copyRaw} className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-500 hover:text-[var(--wdd-black)] transition-colors">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            {copied ? 'Copied' : 'Copy JSON'}
                        </button>
                    </div>
                    <pre className="p-5 bg-[#0F0F0F] rounded-[12px] text-[11px] font-mono text-zinc-300 max-h-[300px] overflow-y-auto whitespace-pre-wrap shadow-inner border border-zinc-800/50">
                        {JSON.stringify(lead, null, 2)}
                    </pre>
                </div>
            </div>
        </Drawer>
    );
}
