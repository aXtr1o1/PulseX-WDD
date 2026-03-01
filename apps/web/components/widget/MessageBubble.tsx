import React from 'react';
import clsx from 'clsx';
import type { EvidenceSnippet } from '@/lib/api';

type Role = 'user' | 'assistant' | 'system';

interface ProjectCardData {
    name: string;
    highlights: string[];
    ctas: string[];
}

interface Msg {
    role: Role;
    content: string;
    evidence?: EvidenceSnippet[];
    streaming?: boolean;
    focused_project?: string;
    shortlist?: ProjectCardData[];
    lead_suggestions?: any;
}

interface MessageBubbleProps {
    message: Msg;
    lang: 'en' | 'ar';
}

export default function MessageBubble({ message, lang }: MessageBubbleProps) {
    const isUser = message.role === 'user';
    const rtl = lang === 'ar';

    return (
        <div
            className={clsx(
                'flex flex-col gap-2 animate-fade-in w-full',
                isUser ? 'items-end' : 'items-start',
            )}
            dir={rtl ? 'rtl' : 'ltr'}
        >
            {/* Main Bubble */}
            <div
                className={clsx(
                    'max-w-[85%] md:max-w-[75%] px-5 py-3.5 text-[14px] leading-[1.6]',
                    isUser
                        ? 'bg-[var(--wdd-black)] text-white rounded-2xl rounded-tr-sm'
                        : 'bg-white text-[var(--wdd-text)] shadow-sm border border-[var(--wdd-border)] rounded-2xl rounded-tl-sm',
                    rtl && isUser && 'rounded-tl-sm rounded-tr-2xl',
                    rtl && !isUser && 'rounded-tr-sm rounded-tl-2xl'
                )}
            >
                <div
                    className="whitespace-pre-wrap"
                    dangerouslySetInnerHTML={{
                        __html: message.content
                            // basic markdown bold parsing
                            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                            // newlines
                            .replace(/\ng/, '<br/>')
                    }}
                />

                {message.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-current ml-1 animate-blink rounded-sm align-middle" />
                )}
            </div>

            {/* Shortlist Cards */}
            {!isUser && message.shortlist && message.shortlist.length > 0 && (
                <div className="flex flex-col gap-3 mt-1 w-[85%] md:w-[75%]">
                    {message.shortlist.map((proj, idx) => (
                        <div key={idx} className="bg-white border border-[var(--wdd-border)] rounded-xl p-4 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
                            <h4 className="font-semibold text-base text-[var(--wdd-black)] mb-2">{proj.name}</h4>
                            <ul className="mb-4 space-y-1">
                                {proj.highlights.map((hl, i) => (
                                    <li key={i} className="text-xs text-[var(--wdd-muted)] flex items-start gap-1.5">
                                        <span className="text-[var(--wdd-red)] mt-0.5">•</span>
                                        <span>{hl}</span>
                                    </li>
                                ))}
                            </ul>
                            <div className="flex flex-wrap gap-2">
                                {proj.ctas.map((cta, i) => (
                                    <button key={i} className="text-xs font-medium px-3 py-1.5 rounded-full border border-[var(--wdd-red)] text-[var(--wdd-red)] hover:bg-[var(--wdd-red)] hover:text-white transition-colors">
                                        {cta}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Evidence Micro-Band */}
            {!isUser && message.evidence && message.evidence.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mt-0.5 ml-2 rtl:mr-2 rtl:ml-0 max-w-[90%]">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--wdd-red)] flex items-center gap-1 opacity-80">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        {lang === 'ar' ? 'تم التحقق' : 'Verified'}
                    </span>

                    {message.evidence.slice(0, 4).map((ev, i) => (
                        <a
                            key={i}
                            href={ev.source_url || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-[var(--wdd-muted)] bg-[var(--wdd-surface)] border border-[var(--wdd-border)] px-2 py-0.5 rounded-md hover:border-[var(--wdd-red)] hover:text-[var(--wdd-red)] transition-colors inline-flex items-center gap-1 max-w-[120px]"
                            title={ev.snippet}
                        >
                            <span className="truncate">{ev.display_name}</span>
                        </a>
                    ))}
                </div>
            )}
        </div>
    );
}

export type { Msg, ProjectCardData };
