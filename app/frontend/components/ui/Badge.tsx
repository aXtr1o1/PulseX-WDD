import React from 'react';
import clsx from 'clsx';

type BadgeVariant = 'default' | 'hot' | 'warm' | 'cold' | 'verified' | 'muted';

interface BadgeProps {
    children: React.ReactNode;
    variant?: BadgeVariant;
    className?: string;
}

const styles: Record<BadgeVariant, string> = {
    default: 'bg-[var(--wdd-surface)] text-[var(--wdd-text)] border border-[var(--wdd-border)]',
    hot: 'bg-[#FFF0F1] text-[var(--wdd-red)] border border-[#FFCED2]',
    warm: 'bg-amber-50 text-amber-700 border border-amber-200',
    cold: 'bg-sky-50 text-sky-700 border border-sky-200',
    verified: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
    muted: 'bg-[var(--wdd-border)] text-[var(--wdd-muted)]',
};

export default function Badge({ children, variant = 'default', className }: BadgeProps) {
    return (
        <span
            className={clsx(
                'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                styles[variant],
                className,
            )}
        >
            {children}
        </span>
    );
}
