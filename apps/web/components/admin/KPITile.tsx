'use client';
import React, { useEffect, useState } from 'react';
import clsx from 'clsx';

interface KPITileProps {
    label: string;
    value: string | number | null | undefined;
    icon?: string;
    accent?: boolean;
    suffix?: string;
}

export default function KPITile({ label, value, icon, accent, suffix }: KPITileProps) {
    const [displayed, setDisplayed] = useState<string | number>(0);

    // Count-up animation for numeric values
    useEffect(() => {
        if (typeof value !== 'number' || value === 0) {
            setDisplayed(value ?? '—');
            return;
        }
        let start = 0;
        const steps = 40;
        const stepVal = value / steps;
        const timer = setInterval(() => {
            start += stepVal;
            if (start >= value) { setDisplayed(value); clearInterval(timer); }
            else setDisplayed(Math.floor(start));
        }, 16);
        return () => clearInterval(timer);
    }, [value]);

    return (
        <div
            className={clsx(
                'relative overflow-hidden rounded-[var(--wdd-radius-lg)] border p-5 bg-white',
                'transition-shadow duration-200 hover:shadow-[var(--wdd-shadow)]',
                accent
                    ? 'border-[var(--wdd-red)] bg-[#FFF8F8]'
                    : 'border-[var(--wdd-border)]',
            )}
        >
            {accent && (
                <div className="absolute inset-0 bg-gradient-to-br from-[#FFF0F1] to-transparent pointer-events-none" />
            )}
            <div className="relative">
                {icon && <div className="text-2xl mb-2 leading-none">{icon}</div>}
                <p className="text-[11px] font-medium text-[var(--wdd-muted)] uppercase tracking-wider mb-1">{label}</p>
                <p
                    className={clsx(
                        'text-2xl font-bold leading-tight',
                        accent ? 'text-[var(--wdd-red)]' : 'text-[var(--wdd-black)]',
                    )}
                >
                    {displayed != null && displayed !== '' ? (
                        <>
                            {typeof displayed === 'number' && value != null
                                ? Number(value).toLocaleString()
                                : displayed}
                            {suffix && <span className="text-sm font-normal text-[var(--wdd-muted)] ml-1">{suffix}</span>}
                        </>
                    ) : '—'}
                </p>
            </div>
        </div>
    );
}
