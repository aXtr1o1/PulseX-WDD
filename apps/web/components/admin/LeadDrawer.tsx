'use client';
import React, { useState } from 'react';
import Drawer from '@/components/ui/Drawer';
import Badge from '@/components/ui/Badge';

type LeadRow = Record<string, string>;

interface LeadDrawerProps {
    lead: LeadRow | null;
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

    function bandVariant(band: string): 'hot' | 'warm' | 'cold' | 'muted' {
        if (band === 'high' || band === 'ultra_high') return 'hot';
        if (band === 'mid') return 'warm';
        if (band === 'low') return 'cold';
        return 'muted';
    }

    const fields = [
        { label: 'Session ID', key: 'session_id', mono: true },
        { label: 'Language', key: 'lang' },
        { label: 'Name', key: 'name' },
        { label: 'Phone', key: 'phone', mono: true },
        { label: 'Email', key: 'email', mono: true },
        { label: 'Project(s)', key: 'interest_projects' },
        { label: 'Region', key: 'preferred_region' },
        { label: 'Unit Type', key: 'unit_type' },
        { label: 'Budget Min', key: 'budget_min' },
        { label: 'Budget Max', key: 'budget_max' },
        { label: 'Purpose', key: 'purpose' },
        { label: 'Timeline', key: 'timeline' },
        { label: 'Callback Consent', key: 'consent_callback' },
        { label: 'Marketing Consent', key: 'consent_marketing' },
        { label: 'Consent Timestamp', key: 'consent_timestamp', mono: true },
        { label: 'Source URL', key: 'source_url' },
        { label: 'Summary', key: 'summary' },
        { label: 'Tags', key: 'tags' },
    ];

    return (
        <Drawer
            open={open}
            onClose={onClose}
            title={`Lead — ${lead.name || 'Unknown'}`}
            width="w-full md:w-[520px]"
        >
            {/* Time + budget */}
            <div className="flex items-center gap-2 mb-5">
                <span className="text-xs text-[var(--wdd-muted)]">
                    {lead.timestamp ? new Date(lead.timestamp).toLocaleString() : '—'}
                </span>
                {lead.budget_band && (
                    <Badge variant={bandVariant(lead.budget_band)}>{lead.budget_band}</Badge>
                )}
            </div>

            {/* Field list */}
            <div className="space-y-3">
                {fields.map(({ label, key, mono }) => {
                    let val = lead[key];
                    if (!val || val === 'None') return null;
                    // Parse JSON arrays
                    if (val.startsWith('[') || val.startsWith('{')) {
                        try { val = JSON.parse(val); if (Array.isArray(val)) val = val.join(', '); } catch { /* noop */ }
                    }
                    return (
                        <div key={key} className="grid grid-cols-[130px_1fr] gap-2">
                            <span className="text-xs font-medium text-[var(--wdd-muted)] pt-0.5">{label}</span>
                            <span className={`text-sm text-[var(--wdd-text)] break-words ${mono ? 'font-mono text-xs' : ''}`}>{String(val)}</span>
                        </div>
                    );
                })}
            </div>

            {/* Raw JSON */}
            <div className="mt-6 pt-4 border-t border-[var(--wdd-border)]">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-[var(--wdd-muted)]">Raw JSON</span>
                    <button
                        onClick={copyRaw}
                        className="text-xs text-[var(--wdd-red)] hover:underline"
                    >
                        {copied ? '✓ Copied!' : 'Copy'}
                    </button>
                </div>
                <pre className="bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-lg p-3 text-[10px] text-[var(--wdd-text)] overflow-x-auto whitespace-pre-wrap break-all font-mono max-h-[200px] overflow-y-auto">
                    {JSON.stringify(lead, null, 2)}
                </pre>
            </div>
        </Drawer>
    );
}
