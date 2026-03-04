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

    // WDD Hotlines
    const hotline = "16662";

    return (
        <main className="min-h-screen bg-white flex flex-col font-isidora relative" dir="ltr">

            {/* 1. Initialization Ritual */}
            {!ready && <InitScreen onReady={() => setReady(true)} />}

            {/* 2. Global Overlay Menu */}
            <OverlayMenu open={menuOpen} onClose={() => setMenuOpen(false)} />

            {/* 3. Official WDD Navbar */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between relative">

                    {/* Left: Hamburger Menu */}
                    <div className="flex-1 flex justify-start">
                        <button
                            onClick={() => setMenuOpen(true)}
                            className="w-12 h-12 flex flex-col items-center justify-center gap-2 hover:opacity-70 transition-opacity"
                            aria-label="Menu"
                        >
                            <span className="w-7 h-[1px] bg-[#333]"></span>
                            <span className="w-7 h-[1px] bg-[#333]"></span>
                            <span className="w-7 h-[1px] bg-[#333]"></span>
                        </button>
                    </div>

                    {/* Center: Absolute Centered Branding */}
                    <div className="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 flex flex-col items-center gap-1.5">
                        <div className="flex items-center gap-3">
                            <Image src="/brand/WDD_fullLogo.png" width={180} height={48} alt="Wadi Degla Developments" className="object-contain h-9 w-auto" />
                        </div>
                        <span className="text-[9px] font-bold text-[var(--wdd-red)] tracking-[0.2em] uppercase">PULSEX AI</span>
                    </div>

                    {/* Right: Actions */}
                    <nav className="flex-1 flex items-center justify-end gap-5 md:gap-7">
                        {/* Hotline Call */}
                        <a
                            href={`tel:${hotline}`}
                            onClick={() => gtm.customEvent('click_hotline')}
                            className="text-[11px] font-bold tracking-widest text-[#1a1a1a] hover:text-[var(--wdd-red)] transition-colors hidden sm:block"
                        >
                            {hotline}
                        </a>

                        <div className="w-[1px] h-3 bg-gray-200 hidden md:block"></div>

                        {/* Black Action Button */}
                        <a
                            href="https://wadidegladevelopments.com/contact-us/"
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={() => gtm.customEvent('click_request_call')}
                            className="text-[10px] tracking-[0.15em] font-bold bg-[#1a1a1a] text-white px-6 py-3 rounded-none hover:bg-[var(--wdd-red)] hover:text-white transition-all hidden md:block inline-block cursor-pointer"
                        >
                            REQUEST A SALES CALL
                        </a>
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
