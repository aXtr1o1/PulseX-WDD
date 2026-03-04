'use client';
import React, { useCallback, useEffect, useState } from 'react';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import { fetchSheetRows, downloadSheetUrl } from '@/lib/api';

type Sheet = 'leads' | 'audit' | 'leads_seed' | 'sessions';

interface DataViewerProps {
    forceSheet?: Sheet;
}

const SHEETS: { id: Sheet; label: string }[] = [
    { id: 'leads', label: 'leads.csv' },
    { id: 'audit', label: 'audit.csv' },
    { id: 'leads_seed', label: 'leads_seed.csv' },
    { id: 'sessions', label: 'sessions.csv' },
];

export default function DataViewer({ forceSheet }: DataViewerProps) {
    const [activeSheet, setActiveSheet] = useState<Sheet>(forceSheet || 'leads');
    const [rows, setRows] = useState<Record<string, string>[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const load = useCallback(async (sheet: Sheet) => {
        setLoading(true);
        setError('');
        try {
            const res = await fetchSheetRows(sheet, 100, 0);
            setRows(res.rows);
            setTotal(res.total);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to load sheet');
            setRows([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(activeSheet); }, [activeSheet, load]);

    const cols = rows.length ? Object.keys(rows[0]) : [];

    return (
        <div className="space-y-4">
            {/* Action Bar */}
            <div className="flex items-center justify-between flex-wrap gap-4 border-b border-[var(--wdd-border)] pb-4">
                {/* Sheet selector (only if not forced) */}
                <div className="flex items-center gap-2 flex-wrap">
                    {!forceSheet ? SHEETS.map((s) => (
                        <button
                            key={s.id}
                            onClick={() => setActiveSheet(s.id)}
                            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all ${activeSheet === s.id
                                    ? 'bg-[var(--wdd-black)] text-white border-[var(--wdd-black)]'
                                    : 'bg-white text-[var(--wdd-muted)] border-[var(--wdd-border)] hover:border-[var(--wdd-black)]'
                                }`}
                        >
                            {s.label}
                        </button>
                    )) : (
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-[var(--wdd-black)] bg-[var(--wdd-surface)] px-3 py-1.5 rounded-full border border-[var(--wdd-border)] shadow-sm">
                                {activeSheet}.csv
                            </span>
                            <span className="text-xs text-[var(--wdd-muted)]">
                                {total} total rows · showing {rows.length}
                            </span>
                        </div>
                    )}
                </div>

                {/* Controls */}
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => load(activeSheet)} disabled={loading}>
                        ↻ Refresh
                    </Button>
                    <a href={downloadSheetUrl(activeSheet, 'csv')} download>
                        <Button variant="ghost" size="sm">⬇ CSV</Button>
                    </a>
                    <a href={downloadSheetUrl(activeSheet, 'xlsx')} download>
                        <Button variant="primary" size="sm">⬇ XLSX</Button>
                    </a>
                </div>
            </div>

            {/* Meta (if not forced) */}
            {!forceSheet && (
                <p className="text-xs text-[var(--wdd-muted)]">
                    {total} total rows · showing {rows.length}
                </p>
            )}

            {/* Table */}
            {loading ? (
                <div className="py-12 flex justify-center"><Spinner /></div>
            ) : error ? (
                <div className="py-8 text-center text-sm text-[var(--wdd-red)] bg-red-50 rounded-xl">{error}</div>
            ) : !rows.length ? (
                <div className="py-12 text-center text-sm text-[var(--wdd-muted)] border border-dashed border-[var(--wdd-border)] rounded-xl">No rows found in this sheet.</div>
            ) : (
                <div className="overflow-x-auto rounded-xl border border-[var(--wdd-border)] shadow-sm">
                    <table className="w-full text-xs border-collapse min-w-max">
                        <thead>
                            <tr className="bg-[var(--wdd-surface)] border-b border-[var(--wdd-border)]">
                                {cols.map((c) => (
                                    <th key={c} className="px-4 py-3 text-left font-semibold text-[var(--wdd-black)] uppercase tracking-wider whitespace-nowrap">
                                        {c.replace(/_/g, ' ')}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row, i) => (
                                <tr key={i} className={`border-b border-[var(--wdd-border)] hover:bg-gray-50/50 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-transparent'}`}>
                                    {cols.map((c) => (
                                        <td key={c} className="px-4 py-2.5 text-[var(--wdd-text)] whitespace-nowrap max-w-[250px] truncate" title={row[c]}>
                                            {row[c] ?? '—'}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
