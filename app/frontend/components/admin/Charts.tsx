'use client';
import React from 'react';
import {
    AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';

const ACCENT = '#CB2030';
const SECONDARY = '#55575A';
const MUTED = '#9A9A9A';
const CHART_ACCENT = ['#CB2030', '#D32F2F', '#E53935', '#55575A', '#191919', '#E6E6E6'];

// Color palettes for varied shade bars
const WDD_REDS = ['#9D1523', '#B71C1C', '#CB2030', '#D32F2F', '#E53935', '#EF5350', '#E57373'];
const WDD_GREYS = ['#191919', '#3A3A3A', '#55575A', '#74777B', '#9A9A9A', '#BABABA', '#D5D5D5'];

// --- Components ---


interface DataPoint { label: string; count: number; }
interface PiePoint { name: string; value: number; }

export function LeadsTimeChart({ data }: { data: any[] }) {
    if (!data.length) return <EmptyChart label="No trend data" />;
    return (
        <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                <defs>
                    <linearGradient id="wddGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={ACCENT} stopOpacity={0.15} />
                        <stop offset="95%" stopColor={ACCENT} stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E6E6" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6B6B6B' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#6B6B6B' }} tickLine={false} axisLine={false} />
                <Tooltip
                    contentStyle={{ border: '1px solid #E6E6E6', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ fontWeight: 600 }}
                />
                <Area type="monotone" dataKey="count" stroke={ACCENT} strokeWidth={2} fill="url(#wddGrad)" dot={false} activeDot={{ r: 4, fill: ACCENT }} name="Leads" />
            </AreaChart>
        </ResponsiveContainer>
    );
}

export function DistributionBar({ data, layout = 'horizontal', color = ACCENT }: { data: DataPoint[], layout?: 'horizontal' | 'vertical', color?: string | 'mixed' }) {
    if (!data.length) return <EmptyChart label="No data" />;
    return (
        <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data} layout={layout} margin={{ top: 0, right: 12, left: layout === 'vertical' ? 0 : -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E6E6" horizontal={layout === 'horizontal'} vertical={layout === 'vertical'} />
                {layout === 'horizontal' ? (
                    <>
                        <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#6B6B6B' }} tickLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: '#6B6B6B' }} tickLine={false} axisLine={false} />
                    </>
                ) : (
                    <>
                        <XAxis type="number" tick={{ fontSize: 10, fill: '#6B6B6B' }} tickLine={false} />
                        <YAxis type="category" dataKey="label" width={100} tick={{ fontSize: 10, fill: '#191919' }} tickLine={false} axisLine={false} />
                    </>
                )}
                <Tooltip contentStyle={{ border: '1px solid #E6E6E6', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" radius={layout === 'vertical' ? [0, 4, 4, 0] : [4, 4, 0, 0]} name="Leads">
                    {data.map((entry, index) => {
                        const palette = color === 'mixed' ? CHART_ACCENT : (color === ACCENT ? WDD_REDS : WDD_GREYS);
                        return <Cell key={`cell-${index}`} fill={palette[index % palette.length]} />;
                    })}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
}

export function DistributionDonut({ data, colors = CHART_ACCENT }: { data: PiePoint[], colors?: string[] }) {
    if (!data.length) return <EmptyChart label="No data" />;
    return (
        <ResponsiveContainer width="100%" height={260}>
            <PieChart>
                <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                    labelLine={{ stroke: '#9A9A9A', strokeWidth: 0.5 }}
                    label={({ index, name, value, cx, cy, midAngle, outerRadius }) => {
                        const RADIAN = Math.PI / 180;
                        const radius = outerRadius + 20;
                        const x = cx + radius * Math.cos(-midAngle * RADIAN);
                        const y = cy + radius * Math.sin(-midAngle * RADIAN);
                        const textAnchor = x > cx ? 'start' : 'end';
                        return (
                            <text x={x} y={y} fill={colors[index % colors.length]} textAnchor={textAnchor} dominantBaseline="central" fontSize={11} fontWeight={600}>
                                {name} ({value})
                            </text>
                        );
                    }}
                >
                    {data.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                    ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            </PieChart>
        </ResponsiveContainer>
    );
}

export function FunnelStrip({ captureCount }: { captureCount: number }) {
    // Generate mock funnel numbers based on captures
    const funnel = [
        { label: 'GREETING', count: Math.round(captureCount * 1.5) },
        { label: 'MATCH', count: Math.round(captureCount * 1.3) },
        { label: 'FEASIBILITY', count: Math.round(captureCount * 1.2) },
        { label: 'SHORTLIST', count: Math.round(captureCount * 1.1) },
        { label: 'CAPTURE', count: captureCount },
        { label: 'CONFIRM', count: Math.round(captureCount * 0.55) },
        { label: 'SAVE', count: Math.round(captureCount * 0.26) },
    ];
    // Colors gradient from dark red to light pink
    const colors = ['#B71C1C', '#C62828', '#D32F2F', '#E53935', '#EF5350', '#E57373', '#EF9A9A'];

    return (
        <div className="flex w-full h-14 md:h-16 rounded-xl overflow-x-auto no-scrollbar">
            <div className="flex min-w-[600px] w-full h-full">
                {funnel.map((step, idx) => (
                    <div
                        key={step.label}
                        className="flex-1 flex flex-col items-center justify-center text-white"
                        style={{ backgroundColor: colors[idx] }}
                    >
                        <span className="text-[8px] md:text-[9px] font-bold tracking-widest leading-tight">{step.label}</span>
                        <span className="text-xs md:text-sm font-bold">{step.count}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export function EmptyChart({ label }: { label: string }) {
    return (
        <div className="h-[220px] flex items-center justify-center text-sm text-[var(--wdd-muted)] italic font-light">
            {label}
        </div>
    );
}
