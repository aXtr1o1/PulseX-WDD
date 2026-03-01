'use client';
import React from 'react';
import Link from 'next/link';

interface OverlayMenuProps {
    open: boolean;
    onClose: () => void;
    lang?: 'en' | 'ar';
}

export default function OverlayMenu({ open, onClose, lang = 'en' }: OverlayMenuProps) {
    if (!open) return null;

    const rtl = lang === 'ar';

    const links = [
        { label: rtl ? 'الكونسيرج (الرئيسية)' : 'Concierge', href: '/' },
        { label: rtl ? 'ذكاء العملاء المحتملين' : 'Lead Intelligence Dashboard', href: '/admin' },
        { label: rtl ? 'مصادر البيانات המאומת' : 'Data Sources (Verified Intelligence)', href: '/sources' },
        { label: rtl ? 'جودة الاسترجاع' : 'Retrieval Quality / System Health', href: '/quality' },
    ];

    return (
        <div
            className="fixed inset-0 z-[90] bg-[var(--wdd-bg)] flex flex-col md:flex-row animate-fade-in"
            dir={rtl ? 'rtl' : 'ltr'}
        >
            {/* Close Button */}
            <button
                onClick={onClose}
                className={`absolute top-6 ${rtl ? 'left-6' : 'right-6'} w-10 h-10 flex items-center justify-center rounded-full hover:bg-[var(--wdd-surface)] text-[var(--wdd-icon-grey)] transition-colors z-[91]`}
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
                </svg>
            </button>

            {/* Left/Top: Links */}
            <div className="flex-1 flex flex-col justify-center px-10 md:px-20 pt-20 md:pt-0">
                <nav className="flex flex-col gap-8">
                    {links.map((l) => (
                        <Link
                            key={l.href}
                            href={l.href}
                            onClick={onClose}
                            className="text-2xl md:text-4xl font-light text-[var(--wdd-black)] hover:text-[var(--wdd-red)] transition-colors inline-block w-fit"
                        >
                            {l.label}
                        </Link>
                    ))}
                </nav>
            </div>

            {/* Right/Bottom: Context & Trust info */}
            <div className="w-full md:w-[450px] bg-[var(--wdd-surface)] p-10 md:p-16 flex flex-col justify-between border-t md:border-t-0 md:border-l border-[var(--wdd-border)]">
                <div className="space-y-10">
                    <div>
                        <h4 className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-4">
                            {rtl ? 'ما يفعله هذا النظام' : 'What this system does'}
                        </h4>
                        <ul className="space-y-3 text-sm text-[var(--wdd-text)]">
                            <li className="flex gap-2"><span>—</span> <span>Verified information only</span></li>
                            <li className="flex gap-2"><span>—</span> <span>Conversation-based lead capture</span></li>
                            <li className="flex gap-2"><span>—</span> <span>Consent-aware operations</span></li>
                            <li className="flex gap-2"><span>—</span> <span>Measurable (audit + quality)</span></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="text-xs font-semibold tracking-widest text-[var(--wdd-muted)] uppercase mb-4">
                            {rtl ? 'النطاق' : 'Scope'}
                        </h4>
                        <div className="space-y-2 text-sm text-[var(--wdd-text)]">
                            <p><span className="text-[var(--wdd-black)] font-medium">In-scope:</span> project discovery, shortlist, brochure request, callback request</p>
                            <p><span className="text-[var(--wdd-muted)]">Out-of-scope:</span> live inventory/pricing promises unless explicitly verified by WDD sources</p>
                        </div>
                    </div>
                </div>

                <div className="mt-12 md:mt-0">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-[var(--wdd-border)] rounded-full text-xs font-medium text-[var(--wdd-muted)] mb-8">
                        <span className="w-2 h-2 rounded-full bg-green-500"></span>
                        PulseX-WDD_buyerKB.csv · Schema strict
                    </div>

                    <p className="text-xs text-[var(--wdd-muted)]">
                        &copy; {new Date().getFullYear()} Wadi Degla Developments.<br />
                        All rights reserved.<br />
                        <span className="opacity-50 mt-1 inline-block">Developed by CloudGate</span>
                    </p>
                </div>
            </div>
        </div>
    );
}
