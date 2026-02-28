import React from 'react';
import clsx from 'clsx';

interface SpinnerProps {
    size?: 'sm' | 'md' | 'lg';
    className?: string;
    color?: string;
}

const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-9 h-9' };

export default function Spinner({ size = 'md', className, color = 'var(--wdd-red)' }: SpinnerProps) {
    return (
        <svg
            className={clsx('animate-spin', sizes[size], className)}
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
        >
            <circle className="opacity-20" cx="12" cy="12" r="10" stroke={color} strokeWidth="3" />
            <path
                className="opacity-80"
                fill={color}
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
        </svg>
    );
}
