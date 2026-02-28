import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import ChatWidget from '@/components/widget/ChatWidget';

export default function HomePage() {
    return (
        <main className="min-h-screen bg-white">
            {/* Navbar */}
            <header className="sticky top-0 z-30 bg-white border-b border-[var(--wdd-border)] shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
                <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                    <Image src="/brand/WDD_fullLogo.png" width={180} height={48} alt="Wadi Degla Developments" className="object-contain h-9 w-auto" />
                    <nav className="flex items-center gap-6">
                        <Link href="/widget" className="text-sm text-[var(--wdd-muted)] hover:text-[var(--wdd-red)] transition-colors">
                            Widget Demo
                        </Link>
                        <Link
                            href="/admin"
                            className="text-sm font-medium text-[var(--wdd-red)] border border-[var(--wdd-red)] px-4 py-1.5 rounded-full hover:bg-[var(--wdd-red)] hover:text-white transition-all"
                        >
                            Admin →
                        </Link>
                    </nav>
                </div>
            </header>

            {/* Hero */}
            <section className="max-w-6xl mx-auto px-6 py-20">
                <div className="max-w-2xl">
                    <p className="text-xs font-semibold tracking-widest text-[var(--wdd-red)] uppercase mb-4">
                        PulseX · Wadi Degla Developments
                    </p>
                    <h1 className="text-4xl md:text-5xl font-bold text-[var(--wdd-black)] leading-tight mb-6">
                        Your Property<br />Concierge, Reimagined.
                    </h1>
                    <p className="text-lg text-[var(--wdd-muted)] leading-relaxed mb-8 max-w-xl">
                        PulseX brings WDD&apos;s entire portfolio and knowledge base into a single conversational interface — grounded in verified data, available 24/7.
                    </p>
                    <div className="flex flex-wrap gap-4">
                        <Link
                            href="/widget"
                            className="inline-flex items-center gap-2 px-6 py-3 bg-[var(--wdd-red)] text-white rounded-full font-medium text-sm hover:bg-[#b01c28] transition-colors"
                        >
                            Try the Widget
                            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                <path d="M1 7h12M8 2l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </Link>
                        <Link
                            href="/admin"
                            className="inline-flex items-center gap-2 px-6 py-3 border border-[var(--wdd-border)] text-[var(--wdd-text)] rounded-full font-medium text-sm hover:border-[var(--wdd-red)] hover:text-[var(--wdd-red)] transition-all"
                        >
                            Admin Dashboard
                        </Link>
                    </div>
                </div>
            </section>

            {/* Feature grid */}
            <section className="border-t border-[var(--wdd-border)] bg-[var(--wdd-surface)]">
                <div className="max-w-6xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-8">
                    {[
                        { icon: '🧠', title: 'Hybrid RAG', desc: 'BM25 keyword + vector search with hard project/region gating — no hallucinated inventory.' },
                        { icon: '💬', title: 'Concierge Widget', desc: 'Embeddable chat widget with streaming responses, intent routing, and progressive lead profiling.' },
                        { icon: '📊', title: 'Lead Intelligence', desc: 'Auto-capture, validate, and score leads. Full admin dashboard with CSV/XLSX export.' },
                    ].map((f) => (
                        <div key={f.title} className="p-6 bg-white rounded-[var(--wdd-radius-lg)] border border-[var(--wdd-border)]">
                            <div className="text-3xl mb-4">{f.icon}</div>
                            <h3 className="font-semibold text-[var(--wdd-black)] mb-2">{f.title}</h3>
                            <p className="text-sm text-[var(--wdd-muted)] leading-relaxed">{f.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Embed snippet */}
            <section className="max-w-6xl mx-auto px-6 py-16">
                <h2 className="text-2xl font-bold text-[var(--wdd-black)] mb-4">Embed on your website</h2>
                <p className="text-sm text-[var(--wdd-muted)] mb-6">
                    Add one script tag to your existing website to dock the PulseX widget.
                </p>
                <pre className="bg-[#191919] text-[#E5E5E5] text-xs rounded-xl p-5 overflow-x-auto font-mono leading-relaxed">
                    {`<script
  src="${process.env.NEXT_PUBLIC_WIDGET_BASE_URL ?? 'https://your-pulsex-domain.com'}/widget.js"
  data-project="murano"
  data-lang="en"
  defer
></script>`}
                </pre>
            </section>

            {/* Floating chat widget on this page */}
            <ChatWidget />
        </main>
    );
}
