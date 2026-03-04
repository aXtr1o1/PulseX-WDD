'use client';
import React, { useState } from 'react';
import clsx from 'clsx';
import Badge from '@/components/ui/Badge';

type LeadRow = Record<string, string>;

interface LeadTableProps {
    leads: LeadRow[];
    onSelect: (lead: LeadRow) => void;
    loading?: boolean;
}

export default function LeadTable({ leads, onSelect, loading }: LeadTableProps) {
    const [sort, setSort] = useState<{ col: string; dir: 'asc' | 'desc' }>({ col: 'timestamp', dir: 'desc' });

    const sorted = [...leads].sort((a, b) => {
        const va = a[sort.col] ?? '';
        const vb = b[sort.col] ?? '';
        return sort.dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    });

    function toggleSort(col: string) {
        setSort((prev) => ({ col, dir: prev.col === col && prev.dir === 'asc' ? 'desc' : 'asc' }));
    }

    const cols = [
        { key: 'timestamp', label: 'Time' },
        { key: 'name', label: 'Name' },
        { key: 'phone', label: 'Phone' },
        { key: 'interest_projects', label: 'Project(s)' },
        { key: 'preferred_region', label: 'Region' },
        { key: 'budget_band', label: 'Budget Band' },
        { key: 'purpose', label: 'Purpose' },
        { key: 'consent_callback', label: 'Callback' },
    ];

    if (loading) {
        return (
            <div className="py-12 text-center text-sm text-[var(--wdd-muted)]">
                Loading leads…
            </div>
        );
    }

    if (!leads.length) {
        return (
            <div className="py-12 text-center text-sm text-[var(--wdd-muted)]">
                No leads found for the selected filters.
            </div>
        );
    }

    function bandVariant(band: string): 'hot' | 'warm' | 'cold' | 'muted' {
        if (band === 'high' || band === 'ultra_high') return 'hot';
        if (band === 'mid') return 'warm';
        if (band === 'low') return 'cold';
        return 'muted';
    }

    return (
        <div className="overflow-x-auto rounded-[var(--wdd-radius-lg)] border border-[var(--wdd-border)]">
            <table className="w-full text-sm border-collapse">
                <thead>
                    <tr className="bg-[var(--wdd-surface)] border-b border-[var(--wdd-border)]">
                        {cols.map((c) => (
                            <th
                                key={c.key}
                                onClick={() => toggleSort(c.key)}
                                className="px-4 py-3 text-left text-xs font-semibold text-[var(--wdd-muted)] uppercase tracking-wider cursor-pointer select-none hover:text-[var(--wdd-black)] whitespace-nowrap"
                            >
                                {c.label}
                                {sort.col === c.key && (
                                    <span className="ml-1">{sort.dir === 'asc' ? '↑' : '↓'}</span>
                                )}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {sorted.map((lead, i) => (
                        <tr
                            key={i}
                            onClick={() => onSelect(lead)}
                            className={clsx(
                                'cursor-pointer border-b border-[var(--wdd-border)] transition-colors',
                                'hover:bg-[#FFF8F8] hover:border-[var(--wdd-red)]',
                                i % 2 === 0 ? 'bg-white' : 'bg-[var(--wdd-surface)]',
                            )}
                        >
                            <td className="px-4 py-3 text-xs text-[var(--wdd-muted)] whitespace-nowrap">
                                {lead.timestamp ? new Date(lead.timestamp).toLocaleString() : '—'}
                            </td>
                            <td className="px-4 py-3 font-medium text-[var(--wdd-text)] whitespace-nowrap">
                                {lead.name || <span className="text-[var(--wdd-muted)]">—</span>}
                            </td>
                            <td className="px-4 py-3 text-[var(--wdd-text)] font-mono text-xs whitespace-nowrap">
                                {lead.phone || '—'}
                            </td>
                            <td className="px-4 py-3 text-xs max-w-[160px] truncate text-[var(--wdd-text)]">
                                {tryParseJson(lead.interest_projects) || '—'}
                            </td>
                            <td className="px-4 py-3 text-xs whitespace-nowrap text-[var(--wdd-text)]">
                                {lead.preferred_region || '—'}
                            </td>
                            <td className="px-4 py-3">
                                {lead.budget_band ? (
                                    <Badge variant={bandVariant(lead.budget_band)}>{lead.budget_band}</Badge>
                                ) : <span className="text-[var(--wdd-muted)]">—</span>}
                            </td>
                            <td className="px-4 py-3 text-xs text-[var(--wdd-text)] capitalize">
                                {lead.purpose || '—'}
                            </td>
                            <td className="px-4 py-3 text-center">
                                {lead.consent_callback === 'True' || lead.consent_callback === 'true'
                                    ? <span className="text-emerald-600 font-bold text-xs">✓</span>
                                    : <span className="text-[var(--wdd-muted)]">—</span>}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function tryParseJson(raw: string): string {
    if (!raw) return '';
    try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed.join(', ');
        return String(parsed);
    } catch {
        return raw;
    }
}
