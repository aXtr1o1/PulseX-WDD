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

    const groups = [
        {
            title: 'Lead Profile',
            fields: [
                { label: 'Full Name', value: lead.name || 'Anonymous' },
                { label: 'Phone', value: lead.phone || lead.contact || '—', mono: true },
                { label: 'Email', value: lead.email || '—', mono: true },
                { label: 'Session ID', value: lead.session_id || '—', mono: true },
            ]
        },
        {
            title: 'Acquisition Intent',
            fields: [
                { label: 'Projects', value: (lead.projects || []).join(', ') || '—' },
                { label: 'Region', value: lead.region || lead.preferred_region || '—' },
                { label: 'Unit Type', value: lead.unit_type || '—' },
                { label: 'Budget', value: lead.budget_band || '—' },
                { label: 'Purpose', value: lead.purpose || '—' },
                { label: 'Timeline', value: lead.timeline || '—' },
            ]
        }
    ];

    return (
        <Drawer
            open={open}
            onClose={onClose}
            title={`Lead Detail: ${lead.name || 'Anonymous'}`}
            width="w-full md:w-[650px]"
        >
            <div className="space-y-10 pb-20">
                {/* Status Indicator */}
                <div className="flex items-center gap-2 mb-4">
                    <span className="bg-[var(--wdd-red)] text-white text-[9px] font-bold px-2 py-0.5 rounded tracking-widest uppercase">QUALIFIED</span>
                    <span className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-tighter">Verified Lead</span>
                </div>

                {/* RAG Strategy Highlight */}
                {lead.reason_codes && (
                    <div className="bg-[var(--wdd-black)] text-white p-6 rounded-2xl relative overflow-hidden shadow-xl">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 blur-2xl rounded-full -mr-16 -mt-16" />
                        <h4 className="text-[9px] font-bold tracking-[0.2em] uppercase mb-3 text-gray-400">RAG Intelligence Insight</h4>
                        <p className="text-sm font-light leading-relaxed italic opacity-95">“{lead.reason_codes}”</p>
                    </div>
                )}

                {/* Conversation Summary */}
                {lead.summary && (
                    <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest">Executive Summary</h4>
                        <p className="text-sm leading-relaxed font-medium text-[var(--wdd-black)] bg-[var(--wdd-surface)] p-4 rounded-xl border border-[var(--wdd-border)]">
                            {lead.summary}
                        </p>
                    </div>
                )}

                {/* Field Groups Grid */}
                {groups.map((group, idx) => (
                    <div key={idx} className="space-y-4">
                        <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-[0.2em] border-b border-[var(--wdd-border)] pb-2">{group.title}</h4>
                        <div className="grid grid-cols-2 gap-y-4 gap-x-8">
                            {group.fields.map((f: any, fIdx: number) => (
                                <div key={fIdx} className="space-y-1">
                                    <p className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase opacity-60">{f.label}</p>
                                    <p className={`text-xs font-bold ${f.mono ? 'font-mono opacity-80' : 'text-[var(--wdd-black)]'}`}>{f.value}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}

                {/* Tags Strip */}
                {(lead.tags || []).length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest">Platform Tags</h4>
                        <div className="flex flex-wrap gap-2">
                            {lead.tags?.map((t: string) => (
                                <span key={t} className="px-3 py-1 bg-white border border-[var(--wdd-border)] rounded-full text-[10px] font-bold text-[var(--wdd-black)] hover:border-[var(--wdd-red)] transition-colors cursor-default">
                                    #{t.toUpperCase()}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Technical Meta */}
                <div className="pt-8 border-t border-[var(--wdd-border)]">
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest">Telemetry Metadata</span>
                        <button onClick={copyRaw} className="text-[10px] font-bold text-[var(--wdd-red)] hover:opacity-70 transition-opacity">
                            {copied ? 'COPIED TO CLIPBOARD' : 'COPY RAW JSON'}
                        </button>
                    </div>
                    <pre className="p-4 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-xl text-[10px] font-mono text-[var(--wdd-muted)] max-h-40 overflow-y-auto whitespace-pre-wrap">
                        {JSON.stringify(lead, null, 4)}
                    </pre>
                </div>
            </div>
        </Drawer>
    );
}
