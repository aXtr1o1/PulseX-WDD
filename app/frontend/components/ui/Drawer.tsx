'use client';
import React, { useEffect, useRef } from 'react';
import clsx from 'clsx';

interface DrawerProps {
    open: boolean;
    onClose: () => void;
    title?: string;
    children: React.ReactNode;
    side?: 'right' | 'left';
    width?: string;
}

export default function Drawer({
    open,
    onClose,
    title,
    children,
    side = 'right',
    width = 'w-full md:w-[480px]',
}: DrawerProps) {
    const panelRef = useRef<HTMLDivElement>(null);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        if (open) document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [open, onClose]);

    // Prevent body scroll when open
    useEffect(() => {
        if (open) document.body.style.overflow = 'hidden';
        else document.body.style.overflow = '';
        return () => { document.body.style.overflow = ''; };
    }, [open]);

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                className={clsx(
                    'fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] transition-opacity duration-300',
                    open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
                )}
                aria-hidden="true"
            />

            {/* Panel */}
            <div
                ref={panelRef}
                role="dialog"
                aria-modal="true"
                aria-label={title}
                className={clsx(
                    'fixed top-0 bottom-0 z-50 flex flex-col bg-white shadow-[var(--wdd-shadow-lg)]',
                    'transition-transform duration-300 ease-out',
                    width,
                    side === 'right' ? 'right-0' : 'left-0',
                    open
                        ? 'translate-x-0'
                        : side === 'right'
                            ? 'translate-x-full'
                            : '-translate-x-full',
                )}
            >
                {/* Header */}
                {title && (
                    <div className="flex items-center justify-between px-8 py-6 border-b border-[var(--wdd-border)]">
                        <h2 className="text-[22px] font-semibold text-[var(--wdd-black)] tracking-tight">{title}</h2>
                        <button
                            onClick={onClose}
                            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-[var(--wdd-surface)] text-[var(--wdd-icon-grey)] transition-colors"
                            aria-label="Close drawer"
                        >
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                            </svg>
                        </button>
                    </div>
                )}

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-8 py-8">{children}</div>
            </div>
        </>
    );
}
