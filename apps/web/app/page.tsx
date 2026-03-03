'use client';
import React, { useState } from 'react';
import Image from 'next/image';
import ChatWidget from '@/components/widget/ChatWidget';
import InitScreen from '@/components/InitScreen';
import OverlayMenu from '@/components/OverlayMenu';
import { gtm } from '@/lib/gtm';

export default function ConciergePage() {
    const [ready, setReady] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const [lang, setLang] = useState<'en' | 'ar'>('en');

    // WDD Hotlines
    const hotline = "16662"; // Placeholder or can be env-based

    return (
        <main className="min-h-screen bg-white flex flex-col font-isidora relative" dir={lang === 'ar' ? 'rtl' : 'ltr'}>

            {/* 1. Initialization Ritual */}
            {!ready && <InitScreen onReady={() => setReady(true)} />}

            {/* 2. Global Overlay Menu */}
            <OverlayMenu open={menuOpen} onClose={() => setMenuOpen(false)} lang={lang} />

            {/* 3. Official WDD-like Navbar */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)] shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

                    {/* Left: Branding */}
                    <div className="flex items-center gap-4">
                        <Image src="/brand/WDD_fullLogo.png" width={160} height={42} alt="Wadi Degla Developments" className="object-contain h-8 w-auto" />
                        <div className="hidden md:flex items-center gap-2 border-l border-[var(--wdd-border)] pl-4 ml-2">
                            <span className="text-xs font-semibold text-[var(--wdd-black)] tracking-wider">PULSEX AI</span>
                        </div>
                    </div>

                    {/* Right: Actions */}
                    <nav className="flex items-center gap-5 md:gap-8">
                        {/* Language Toggle */}
                        <button
                            onClick={() => setLang(l => l === 'en' ? 'ar' : 'en')}
                            className="text-xs font-medium text-[var(--wdd-text)] hover:text-[var(--wdd-red)] transition-colors hidden md:block"
                        >
                            {lang === 'en' ? '🇦🇪 العربية' : '🇬🇧 English'}
                        </button>

                        {/* Hotline Call */}
                        <a
                            href={`tel:${hotline}`}
                            onClick={() => gtm.customEvent('click_hotline')}
                            className="text-sm font-semibold text-[var(--wdd-black)] hover:text-[var(--wdd-red)] transition-colors hidden sm:flex items-center gap-2"
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            {hotline}
                        </a>

                        <button
                            onClick={() => { gtm.customEvent('click_request_call'); setMenuOpen(true); }} // Placeholder for triggering lead form directly
                            className="text-xs tracking-wide font-medium bg-[var(--wdd-red)] text-white px-4 py-2 rounded-full hover:bg-[#b01c28] transition-all shadow-sm hidden md:block"
                        >
                            {lang === 'ar' ? 'طلب مكالمة مبيعات' : 'REQUEST A SALES CALL'}
                        </button>

                        {/* Hamburger */}
                        <button
                            onClick={() => setMenuOpen(true)}
                            className="w-10 h-10 flex flex-col items-center justify-center gap-1.5 rounded-full hover:bg-[var(--wdd-surface)] transition-colors"
                            aria-label="Menu"
                        >
                            <span className="w-5 h-[2px] bg-[var(--wdd-black)] rounded-full"></span>
                            <span className="w-5 h-[2px] bg-[var(--wdd-black)] rounded-full"></span>
                            <span className="w-5 h-[2px] bg-[var(--wdd-black)] rounded-full"></span>
                        </button>
                    </nav>
                </div>
            </header>

            {/* 4. Full Page Chat Area */}
            <section className="flex-1 flex flex-col w-full h-[calc(100vh-64px)] overflow-hidden relative">
                <ChatWidget embedded={true} headerLangToggle={false} />
            </section>
        </main>
    );
}
