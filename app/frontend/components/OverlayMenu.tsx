'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface OverlayMenuProps {
    open: boolean;
    onClose: () => void;
}

export default function OverlayMenu({ open, onClose }: OverlayMenuProps) {
    const pathname = usePathname();

    React.useEffect(() => {
        if (open) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [open]);

    if (!open) return null;

    const links = [
        { label: 'Concierge', href: '/' },
        { label: 'Dashboard', href: '/admin' },
        { label: 'Data Sources', href: '/sources' },
    ];

    return (
        <div
            className="fixed inset-0 z-[90] text-white flex flex-col md:flex-row animate-fade-in font-isidora overflow-y-auto hide-scrollbar [&::-webkit-scrollbar]:hidden [-ms-overflow-style:'none'] [scrollbar-width:'none']"
            style={{ background: 'linear-gradient(135deg, #6C192E 0%, #3B0E19 100%)' }}
            dir="ltr"
        >
            {/* Close Button */}
            <button
                onClick={onClose}
                className="absolute top-8 right-8 w-12 h-12 flex items-center justify-center rounded-full hover:bg-white/10 text-white transition-colors z-[91]"
                aria-label="Close menu"
            >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" />
                </svg>
            </button>

            {/* Left Column: Routes & Scope */}
            <div className="flex-1 flex flex-col justify-center px-10 md:px-24 pt-24 md:pt-0 border-b md:border-b-0 md:border-r border-white/20 min-h-screen md:min-h-0 relative">
                <div className="mb-12">
                    <h4 className="text-[10px] font-bold tracking-[0.3em] text-white/50 uppercase mb-8 ml-1">
                        System Routes
                    </h4>
                    <nav className="flex flex-col gap-5">
                        {links.map((l) => {
                            const isActive = pathname === l.href || (pathname !== '/' && l.href !== '/' && pathname?.startsWith(l.href));
                            return (
                                <Link
                                    key={l.href}
                                    href={l.href}
                                    onClick={onClose}
                                    className={`text-5xl md:text-[5rem] leading-[1.05] tracking-tight transition-colors inline-block w-fit font-light ${isActive ? 'text-white font-medium' : 'text-white/60 hover:text-white'
                                        }`}
                                >
                                    {l.label}
                                </Link>
                            )
                        })}
                    </nav>
                </div>

                <div className="mt-14 pt-8 border-t border-white/20 max-w-sm">
                    <h4 className="text-[10px] font-bold tracking-[0.3em] text-white/50 uppercase mb-6 ml-1">
                        POC Scope
                    </h4>
                    <ul className="space-y-4 text-[13px] tracking-wide text-white/80 font-light ml-1">
                        <li className="flex items-center gap-4">
                            <span className="bg-white block w-1 h-1 rounded-full shrink-0"></span>
                            AI concierge trained on verified WDD portfolio
                        </li>
                        <li className="flex items-center gap-4">
                            <span className="bg-white block w-1 h-1 rounded-full shrink-0"></span>
                            Lead capture with structured buyer-intent data
                        </li>
                        <li className="flex items-center gap-4">
                            <span className="bg-white block w-1 h-1 rounded-full shrink-0"></span>
                            Real-time analytics dashboard with export
                        </li>
                        <li className="flex items-center gap-4">
                            <span className="bg-white block w-1 h-1 rounded-full shrink-0"></span>
                            RAG-powered retrieval from official listings
                        </li>
                    </ul>
                </div>
            </div>

            {/* Right Column: System Info */}
            <div className="flex-1 flex flex-col justify-center px-10 md:px-24 py-16 md:py-0 min-h-screen md:min-h-0 relative">
                <div className="max-w-md">
                    <div className="w-8 h-[2px] bg-white mb-8"></div>
                    <h4 className="text-[11px] font-bold tracking-[0.3em] text-white uppercase mb-6">
                        The Concierge System
                    </h4>
                    <p className="text-[14px] leading-relaxed text-white/80 font-light mb-16">
                        Experience a new standard of property discovery. Our AI Concierge is exclusively trained on the verified Wadi Degla Developments portfolio, ensuring accuracy, privacy, and seamless guidance.
                    </p>

                    <div className="grid grid-cols-1 gap-12 mb-16 border-b border-white/20 pb-16 md:grid-cols-2">
                        <div>
                            <h4 className="text-[9px] font-bold tracking-[0.2em] text-white uppercase mb-4 opacity-90">
                                Data Integrity
                            </h4>
                            <p className="text-[12px] leading-relaxed text-white/60 font-medium">
                                Sourced directly from official active listings.
                            </p>
                        </div>
                        <div>
                            <h4 className="text-[9px] font-bold tracking-[0.2em] text-white uppercase mb-4 opacity-90">
                                System Scope
                            </h4>
                            <p className="text-[12px] leading-relaxed text-white/60 font-medium">
                                Proof of Concept (POC) v1.0.<br />Future: Voice & Real-time CRM.
                            </p>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <p className="text-[10px] font-bold tracking-[0.2em] text-white/60 uppercase">
                            Crafted by <span className="text-white font-medium">CloudGate</span>
                        </p>
                        <p className="text-[10px] font-bold tracking-[0.2em] text-white/60 uppercase">
                            CTA <span className="text-white font-medium pl-1">(091) 99945 66311</span>
                        </p>
                        <p className="text-[10px] font-bold tracking-[0.2em] text-white/40 uppercase pt-4">
                            &copy; {new Date().getFullYear()} Wadi Degla Developments.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
