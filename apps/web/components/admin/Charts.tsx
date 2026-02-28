'use client';
import React from 'react';
import {
    AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend,
} from 'recharts';
import type { DailyCount, ProjectCount, RegionCount } from '@/lib/api';

interface LeadsTimeChartProps { data: DailyCount[]; }
export function LeadsTimeChart({ data }: LeadsTimeChartProps) {
    if (!data.length) return <EmptyChart label="No lead data yet" />;
    return (
        <ChartCard title="Leads Over Time">
            <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                    <defs>
                        <linearGradient id="wddGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#CB2030" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#CB2030" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E6E6E6" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B6B6B' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#6B6B6B' }} tickLine={false} axisLine={false} />
                    <Tooltip
                        contentStyle={{ border: '1px solid #E6E6E6', borderRadius: 8, fontSize: 12 }}
                        labelStyle={{ fontWeight: 600 }}
                    />
                    <Area type="monotone" dataKey="count" stroke="#CB2030" strokeWidth={2} fill="url(#wddGrad)" dot={false} activeDot={{ r: 4, fill: '#CB2030' }} name="Leads" />
                </AreaChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

interface TopProjectsChartProps { data: ProjectCount[]; }
export function TopProjectsChart({ data }: TopProjectsChartProps) {
    if (!data.length) return <EmptyChart label="No project data" />;
    return (
        <ChartCard title="Top Projects">
            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E6E6E6" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#6B6B6B' }} tickLine={false} />
                    <YAxis type="category" dataKey="project" width={120} tick={{ fontSize: 11, fill: '#191919' }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ border: '1px solid #E6E6E6', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" fill="#CB2030" radius={[0, 4, 4, 0]} name="Leads" />
                </BarChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

interface TopRegionsChartProps { data: RegionCount[]; }
export function TopRegionsChart({ data }: TopRegionsChartProps) {
    if (!data.length) return <EmptyChart label="No region data" />;
    return (
        <ChartCard title="Top Regions">
            <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E6E6E6" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#6B6B6B' }} tickLine={false} />
                    <YAxis type="category" dataKey="region" width={110} tick={{ fontSize: 11, fill: '#191919' }} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ border: '1px solid #E6E6E6', borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="count" fill="#55575A" radius={[0, 4, 4, 0]} name="Leads" />
                </BarChart>
            </ResponsiveContainer>
        </ChartCard>
    );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-white border border-[var(--wdd-border)] rounded-[var(--wdd-radius-lg)] p-5">
            <h3 className="text-sm font-semibold text-[var(--wdd-black)] mb-4">{title}</h3>
            {children}
        </div>
    );
}

function EmptyChart({ label }: { label: string }) {
    return (
        <ChartCard title="">
            <div className="h-[220px] flex items-center justify-center text-sm text-[var(--wdd-muted)]">{label}</div>
        </ChartCard>
    );
}
