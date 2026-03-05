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
        <main className="h-[100dvh] bg-white flex flex-col font-isidora relative overflow-hidden" dir="ltr">

            {/* 1. Initialization Ritual */}
            {!ready && <InitScreen onReady={() => setReady(true)} />}

            {/* 2. Global Overlay Menu */}
            <OverlayMenu open={menuOpen} onClose={() => setMenuOpen(false)} />

            {/* 3. Official WDD Navbar */}
            <header className="flex-none sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)]">
                <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-16 md:h-20 flex items-center justify-between relative">

                    {/* Left: Hamburger Menu */}
                    <div className="flex-none flex justify-start z-10">
                        <button
                            onClick={() => setMenuOpen(true)}
                            className="w-10 h-10 md:w-12 md:h-12 flex flex-col items-center justify-center gap-1.5 md:gap-2 hover:opacity-70 transition-opacity"
                            aria-label="Menu"
                        >
                            <span className="w-6 md:w-7 h-[1px] bg-[#333]"></span>
                            <span className="w-6 md:w-7 h-[1px] bg-[#333]"></span>
                            <span className="w-6 md:w-7 h-[1px] bg-[#333]"></span>
                        </button>
                    </div>

                    {/* Center: Absolute Centered Branding */}
                    <div className="absolute w-full left-0 top-1/2 -translate-y-1/2 flex flex-col items-center gap-1 md:gap-1.5 pointer-events-none px-14 sm:px-20">
                        <div className="flex items-center justify-center w-full">
                            {/* Desktop Logo */}
                            <Image
                                src="/brand/WDD_fullLogo.png"
                                width={180}
                                height={48}
                                alt="Wadi Degla Developments"
                                className="hidden md:block object-contain h-9 w-auto"
                                priority
                            />
                            {/* Mobile Logo */}
                            <Image
                                src="/brand/WDD_blockLogo.png"
                                width={48}
                                height={48}
                                alt="WDD"
                                className="md:hidden object-contain h-8 w-auto"
                                priority
                            />
                        </div>
                        <span className="text-[7px] md:text-[9px] font-bold text-[var(--wdd-red)] tracking-[0.2em] uppercase">PULSEX AI</span>
                    </div>

                    {/* Right: Actions */}
                    <nav className="flex-none flex items-center justify-end z-10 gap-3 md:gap-7">
                        {/* Hotline Call */}
                        <a
                            href={`tel:${hotline}`}
                            onClick={() => gtm.customEvent('click_hotline')}
                            className="text-[10px] md:text-[11px] font-bold tracking-widest text-[#1a1a1a] hover:text-[var(--wdd-red)] transition-colors hidden sm:block"
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
                            className="text-[9px] md:text-[10px] tracking-[0.1em] md:tracking-[0.15em] font-bold bg-[#1a1a1a] text-white px-3 py-2 md:px-6 md:py-3 rounded-none hover:bg-[var(--wdd-red)] hover:text-white transition-all inline-block cursor-pointer whitespace-nowrap"
                        >
                            <span className="hidden sm:inline">REQUEST A SALES CALL</span>
                            <span className="sm:hidden">SALES</span>
                        </a>
                    </nav>
                </div>
            </header>

            {/* 4. Full Page Chat Area */}
            <section className="flex-1 flex flex-col w-full min-h-0 relative">
                <ChatWidget embedded={true} />
            </section>
        </main>
    );
}
