'use client';
import React, { useState } from 'react';
import Drawer from '@/components/ui/Drawer';
import Badge from '@/components/ui/Badge';
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

    function tempVariant(temp?: string): 'hot' | 'warm' | 'cold' | 'muted' {
        const t = (temp || '').toLowerCase();
        if (t === 'hot') return 'hot';
        if (t === 'warm') return 'warm';
        if (t === 'cold') return 'cold';
        return 'muted';
    }

    const fields = [
        { label: 'Session ID', key: 'session_id', mono: true },
        { label: 'Contact', key: 'phone', mono: true },
        { label: 'Email', key: 'email', mono: true },
        { label: 'Project(s)', key: 'interest_projects' },
        { label: 'Region', key: 'preferred_region' },
        { label: 'Unit Type', key: 'unit_type' },
        { label: 'Budget Min', key: 'budget_min' },
        { label: 'Budget Max', key: 'budget_max' },
        { label: 'Purpose', key: 'purpose' },
        { label: 'Timeline', key: 'timeline' },
        { label: 'Lead Record Status', key: 'confirmed_by_user' },
    ];

    return (
        <Drawer
            open={open}
            onClose={onClose}
            title={`Lead — ${lead.name || 'Unknown'}`}
            width="w-full md:w-[600px]"
        >
            {/* Header / Temperature + Tags */}
            <div className="space-y-4 mb-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        {lead.lead_temperature && (
                            <Badge variant={tempVariant(lead.lead_temperature)}>{lead.lead_temperature} LEAD</Badge>
                        )}
                        <span className="text-[11px] font-semibold text-[var(--wdd-muted)] tracking-wider">
                            {lead.timestamp ? new Date(lead.timestamp).toLocaleString() : '—'}
                        </span>
                    </div>
                    {lead.budget_band && (
                        <span className="text-xs font-bold text-[var(--wdd-red)] uppercase tracking-tighter">Budget: {lead.budget_band}</span>
                    )}
                </div>

                {/* Tags Strip */}
                {lead.tags && (
                    <div className="flex flex-wrap gap-1.5">
                        {lead.tags.map((t: string) => (
                            <span key={t} className="px-2 py-0.5 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-md text-[10px] font-bold text-[var(--wdd-muted)] uppercase">
                                #{t}
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* AI Insights Segment */}
            {lead.reason_codes && (
                <div className="mb-8 p-4 bg-[#F9FAFB] border border-[var(--wdd-border)] rounded-xl">
                    <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest mb-2">Concierge Intelligence (Reason Codes)</h4>
                    <p className="text-sm text-[var(--wdd-black)] leading-relaxed italic">“{lead.reason_codes}”</p>
                </div>
            )}

            {/* Conversation Summary */}
            {lead.summary && (
                <div className="mb-8">
                    <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest mb-2">Executive Summary</h4>
                    <p className="text-sm text-[var(--wdd-black)] leading-relaxed">{lead.summary}</p>
                </div>
            )}

            {/* Field list */}
            <div className="space-y-3.5 border-t border-[var(--wdd-border)] pt-6">
                <h4 className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest mb-4">Lead Profile Details</h4>
                {fields.map(({ label, key, mono }) => {
                    let val = lead[key];
                    if (val === undefined || val === null || val === 'None' || val === '') return null;

                    // Format lists
                    if (Array.isArray(val)) val = val.join(', ');

                    return (
                        <div key={key} className="grid grid-cols-[140px_1fr] gap-2 items-start">
                            <span className="text-[11px] font-semibold text-[var(--wdd-muted)] uppercase tracking-tight">{label}</span>
                            <span className={`text-sm text-[var(--wdd-black)] break-words ${mono ? 'font-mono text-[11px] opacity-70' : ''}`}>
                                {String(val)}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Raw JSON */}
            <div className="mt-12 pt-4 border-t border-[var(--wdd-border)]">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest">Metadata</span>
                    <button
                        onClick={copyRaw}
                        className="text-xs text-[var(--wdd-red)] hover:underline"
                    >
                        {copied ? '✓ Copied!' : 'Copy JSON'}
                    </button>
                </div>
                <pre className="bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-lg p-3 text-[10px] text-[var(--wdd-muted)] overflow-x-auto whitespace-pre-wrap break-all font-mono max-h-[150px] overflow-y-auto">
                    {JSON.stringify(lead, null, 2)}
                </pre>
            </div>
        </Drawer>
    );
}
