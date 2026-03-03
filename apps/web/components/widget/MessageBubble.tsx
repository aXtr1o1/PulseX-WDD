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
    shortlist?: any[];
    lead_suggestions?: any;
    lead_trigger?: boolean;
}

interface MessageBubbleProps {
    message: Msg;
    lang: 'en' | 'ar';
    onConfirm?: () => void;
    onChipClick?: (name: string) => void;
}

export default function MessageBubble({ message, lang, onConfirm, onChipClick }: MessageBubbleProps) {
    const isUser = message.role === 'user';

    return (
        <div
            className={clsx(
                'flex flex-col gap-2 animate-fade-in w-full',
                isUser ? 'items-end' : 'items-start',
            )}
            dir="ltr"
        >
            {/* Main Bubble */}
            <div
                className={clsx(
                    'max-w-[85%] md:max-w-[75%] px-5 py-3.5 text-[14px] leading-[1.6] rounded-none',
                    isUser
                        ? 'bg-[var(--wdd-red)] text-white'
                        : 'bg-white text-[var(--wdd-text)] shadow-sm border border-[var(--wdd-border)]'
                )}
            >
                <div
                    className="whitespace-pre-wrap"
                    dangerouslySetInnerHTML={{
                        __html: message.content
                            // basic markdown bold parsing with static inline Brand Red highlight to bypass Tailwind purging
                            .replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--wdd-red); font-weight: 600;">$1</strong>')
                            // newlines
                            .replace(/\ng/, '<br/>')
                    }}
                />

                {message.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-current ml-1 animate-blink rounded-sm align-middle" />
                )}
            </div>

            {/* Shortlist Cards (legacy) */}
            {!isUser && message.shortlist && message.shortlist.length > 0 && typeof message.shortlist[0] === 'object' && (
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

            {/* Verified Shortlist Chips (Strictly from Backend Metadata Shortlist) */}
            {!isUser && message.shortlist && message.shortlist.length > 0 && typeof message.shortlist[0] === 'string' && (
                <div className="flex flex-wrap gap-2 mt-2 max-w-[85%]">
                    {message.shortlist.map((name: string, idx: number) => (
                        <button
                            key={idx}
                            onClick={() => onChipClick?.(name)}
                            className="px-3 py-1.5 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] text-xs font-medium text-[var(--wdd-black)] shadow-sm hover:shadow hover:bg-gray-50 transition-all rounded-none cursor-pointer"
                        >
                            {name.toUpperCase()}
                        </button>
                    ))}
                </div>
            )}

            {/* Stage 5 Confirmation Block */}
            {!isUser && !message.streaming && message.lead_trigger && !message.lead_suggestions?.confirmed_by_user && (
                <div className="mt-2 w-[85%] md:w-[75%] p-4 bg-[#f9f9f9] border border-[var(--wdd-border)] rounded-none">
                    <p className="text-xs font-semibold text-[var(--wdd-black)] uppercase tracking-wider mb-3">
                        Confirm Your Details
                    </p>
                    <div className="grid grid-cols-2 gap-3 mb-4 text-xs xl:text-sm text-[var(--wdd-text)]">
                        {message.lead_suggestions.phone && <div><span className="text-[var(--wdd-muted)]">Phone:</span> {message.lead_suggestions.phone}</div>}
                        {message.lead_suggestions.budget_min && <div><span className="text-[var(--wdd-muted)]">Budget:</span> ~{message.lead_suggestions.budget_min.toLocaleString()}</div>}
                        {message.lead_suggestions.region && <div><span className="text-[var(--wdd-muted)]">Region:</span> {message.lead_suggestions.region}</div>}
                        {message.lead_suggestions.purpose && <div><span className="text-[var(--wdd-muted)]">Purpose:</span> {message.lead_suggestions.purpose}</div>}
                        {message.lead_suggestions.unit_type && <div><span className="text-[var(--wdd-muted)]">Unit:</span> {message.lead_suggestions.unit_type}</div>}
                    </div>
                    {onConfirm && (
                        <button
                            onClick={onConfirm}
                            className="w-full py-2.5 bg-[var(--wdd-black)] text-white text-sm font-semibold hover:bg-[var(--wdd-red)] transition-colors rounded-none"
                        >
                            Confirm & Consent to Callback
                        </button>
                    )}
                    <p className="text-[10px] text-[var(--wdd-muted)] mt-3 text-center leading-relaxed">
                        By confirming, you consent to our terms and allow our sales team to contact you.
                    </p>
                </div>
            )}

            {/* Evidence Micro-Band */}
            {!isUser && message.evidence && message.evidence.length > 0 && (
                <div className="flex flex-wrap items-center gap-2 mt-0.5 ml-2 max-w-[90%]">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--wdd-red)] flex items-center gap-1 opacity-80">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        Verified
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
