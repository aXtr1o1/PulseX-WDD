'use client';
import React from 'react';
import clsx from 'clsx';
import { type LeadRecord } from '@/lib/api';

interface LeadTableProps {
    leads: LeadRecord[];
    onSelect: (lead: LeadRecord) => void;
    loading?: boolean;
}

const ACCENT = '#CB2030';

export default function LeadTable({ leads, onSelect, loading }: LeadTableProps) {
    if (loading) return <div className="py-20 text-center animate-pulse text-xs font-bold uppercase tracking-widest text-[var(--wdd-muted)]">Syncing Leads...</div>;
    if (!leads.length) return <div className="py-20 text-center text-xs text-[var(--wdd-muted)] italic">No leads match the active filters.</div>;

    return (
        <div className="overflow-x-auto no-scrollbar pb-4">
            <table className="w-full text-left border-separate border-spacing-0">
                <thead>
                    <tr className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-[0.15em]">
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)]">Name</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)]">Contact</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)]">Interest</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)] hidden md:table-cell">Budget</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)] hidden lg:table-cell">Region</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)] whitespace-nowrap hidden xl:table-cell">Tags / Codes</th>
                        <th className="px-3 sm:px-6 py-4 border-b border-[var(--wdd-border)] text-right">Date</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[var(--wdd-border)]">
                    {leads.slice(0, 100).map((l, i) => {
                        const projects = l.projects || [];
                        const displayProject = projects[0] || '—';
                        const extraProjects = projects.length > 1 ? `(+${projects.length - 1})` : '';
                        const date = l.timestamp ? new Date(l.timestamp) : null;

                        return (
                            <tr
                                key={i}
                                onClick={() => onSelect(l)}
                                className="group cursor-pointer hover:bg-[var(--wdd-surface)] transition-all"
                            >
                                <td className="px-3 sm:px-6 py-4">
                                    <div className="font-bold text-sm text-[var(--wdd-black)] group-hover:text-[var(--wdd-red)] transition-colors">{l.name || 'Anonymous'}</div>
                                    <div className="text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-tighter">
                                        {l.lead_temperature || 'WARM'}
                                    </div>
                                </td>
                                <td className="px-3 sm:px-6 py-4">
                                    <div className="text-xs font-medium text-[var(--wdd-black)]">{l.phone || l.contact || '—'}</div>
                                    <div className="text-[10px] text-[var(--wdd-muted)] truncate max-w-[120px]">{l.email || 'No Email'}</div>
                                </td>
                                <td className="px-3 sm:px-6 py-4">
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs font-bold text-[var(--wdd-black)]">{displayProject}</span>
                                        {extraProjects && <span className="text-[10px] font-bold text-[var(--wdd-red)] bg-[#FFF0F1] px-1.5 py-0.5 rounded">{extraProjects}</span>}
                                    </div>
                                    <div className="text-[10px] text-[var(--wdd-muted)] capitalize">{l.unit_type || 'Residential'}</div>
                                </td>
                                <td className="px-3 sm:px-6 py-4 hidden md:table-cell">
                                    <div className="text-xs font-bold text-[var(--wdd-black)]">
                                        {l.budget_band || (l.budget_min ? `${(l.budget_min / 1e6).toFixed(1)}M` : '—')}
                                    </div>
                                    <div className="text-[10px] text-[var(--wdd-muted)] uppercase">{l.purpose || 'INVEST'}</div>
                                </td>
                                <td className="px-3 sm:px-6 py-4 hidden lg:table-cell">
                                    <div className="text-xs font-medium">{l.region || l.preferred_region || '—'}</div>
                                </td>
                                <td className="px-3 sm:px-6 py-4 hidden xl:table-cell">
                                    <div className="flex gap-1 flex-wrap max-w-[150px]">
                                        {(l.tags || []).slice(0, 2).map((t, idx) => (
                                            <span key={idx} className="text-[9px] font-bold border border-[var(--wdd-border)] px-1.5 py-0.5 rounded text-[var(--wdd-muted)] uppercase">{t}</span>
                                        ))}
                                        {l.reason_codes && <span className="text-[9px] font-bold text-[var(--wdd-red)] uppercase">{l.reason_codes}</span>}
                                    </div>
                                </td>
                                <td className="px-3 sm:px-6 py-4 text-right">
                                    <div className="text-xs font-bold text-[var(--wdd-black)]">{date ? date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}</div>
                                    <div className="text-[10px] text-[var(--wdd-muted)]">{date ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</div>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            <div className="py-6 border-t border-[var(--wdd-border)] text-center bg-[var(--wdd-surface)] 
                            text-[10px] font-bold text-[var(--wdd-muted)] uppercase tracking-widest mt-2 rounded-b-2xl">
                SHOWING {Math.min(100, leads.length)} OF {leads.length} LEADS
            </div>
        </div>
    );
}
