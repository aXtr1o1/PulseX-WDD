import React from 'react';
import clsx from 'clsx';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    padding?: 'none' | 'sm' | 'md' | 'lg';
    shadow?: boolean;
    border?: boolean;
}

export default function Card({
    children,
    className,
    padding = 'md',
    shadow = true,
    border = true,
}: CardProps) {
    const paddings = {
        none: '',
        sm: 'p-3',
        md: 'p-5',
        lg: 'p-7',
    };

    return (
        <div
            className={clsx(
                'bg-white rounded-[var(--wdd-radius-lg)]',
                border && 'border border-[var(--wdd-border)]',
                shadow && 'shadow-[var(--wdd-shadow)]',
                paddings[padding],
                className,
            )}
        >
            {children}
        </div>
    );
}
