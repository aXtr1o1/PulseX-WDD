import React from 'react';
import clsx from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
}

export default function Button({
    variant = 'primary',
    size = 'md',
    loading = false,
    children,
    className,
    disabled,
    ...props
}: ButtonProps) {
    const base =
        'inline-flex items-center justify-center font-medium rounded-[var(--wdd-radius)] transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--wdd-red)] disabled:cursor-not-allowed disabled:opacity-50 select-none';

    const variants = {
        primary:
            'bg-[var(--wdd-red)] text-white hover:bg-[#b01c28] active:scale-[0.98]',
        secondary:
            'bg-transparent border border-[var(--wdd-red)] text-[var(--wdd-red)] hover:bg-[var(--wdd-red)] hover:text-white active:scale-[0.98]',
        ghost:
            'bg-transparent text-[var(--wdd-text)] hover:bg-[var(--wdd-surface)] border border-[var(--wdd-border)] active:scale-[0.98]',
        danger:
            'bg-red-600 text-white hover:bg-red-700 active:scale-[0.98]',
    };

    const sizes = {
        sm: 'text-xs px-3 py-1.5 gap-1.5',
        md: 'text-sm px-4 py-2 gap-2',
        lg: 'text-base px-6 py-3 gap-2.5',
    };

    return (
        <button
            className={clsx(base, variants[variant], sizes[size], className)}
            disabled={disabled || loading}
            {...props}
        >
            {loading && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
            )}
            {children}
        </button>
    );
}
