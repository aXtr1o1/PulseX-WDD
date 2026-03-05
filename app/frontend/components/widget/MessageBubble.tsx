import React from 'react';
import clsx from 'clsx';
import type { EvidenceItem } from '@/lib/api';

type Role = 'user' | 'assistant' | 'system';

export interface Msg {
    role: Role;
    content: string;
    streaming?: boolean;
    retrievedProjects?: string[];
    evidence?: EvidenceItem[];
    mode?: 'concierge' | 'lead_capture';
    stage?: string;
}

interface MessageBubbleProps {
    message: Msg;
    onChipClick?: (name: string) => void;
}

export default function MessageBubble({ message, onChipClick }: MessageBubbleProps) {
    const isUser = message.role === 'user';
    const evidence = message.evidence ?? [];
    const hasEvidence = !isUser && !message.streaming && evidence.length > 0;

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
                            // basic markdown bold parsing with Brand Red highlight
                            .replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--wdd-red); font-weight: 600;">$1</strong>')
                            // bullet lists
                            .replace(/^- /gm, '• ')
                            // newlines
                            .replace(/\n/g, '<br/>')
                    }}
                />

                {message.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-current ml-1 animate-blink rounded-sm align-middle" />
                )}
            </div>

            {/* Evidence-Driven Project Chips — metadata from KB, NOT LLM free text */}
            {hasEvidence && (
                <div className="flex flex-wrap gap-2 mt-2 max-w-[85%]">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--wdd-red)] flex items-center gap-1 opacity-80 mr-1">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        Verified
                    </span>
                    {evidence.map((ev, idx) => (
                        <button
                            key={ev.project_id || idx}
                            onClick={() => onChipClick?.(ev.project_name)}
                            className="group px-3 py-1.5 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] text-xs font-medium text-[var(--wdd-black)] shadow-sm hover:shadow hover:bg-gray-50 transition-all rounded-none cursor-pointer flex items-center gap-2"
                            title={[ev.region, ev.city_area].filter(Boolean).join(', ')}
                        >
                            <span>{ev.project_name}</span>
                            {ev.region && (
                                <span className="text-[10px] text-[var(--wdd-muted)] font-normal">
                                    {ev.region}
                                </span>
                            )}
                            {ev.has_brochure && (
                                <span className="text-[9px] bg-green-100 text-green-700 px-1.5 py-0.5 font-semibold tracking-wide uppercase">
                                    PDF
                                </span>
                            )}
                        </button>
                    ))}
                </div>
            )}

            {/* Fallback: legacy retrievedProjects chips (when no evidence) */}
            {!isUser && !message.streaming && !hasEvidence && message.retrievedProjects && message.retrievedProjects.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2 max-w-[85%]">
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--wdd-red)] flex items-center gap-1 opacity-80 mr-1">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                        </svg>
                        Related
                    </span>
                    {message.retrievedProjects.map((name: string, idx: number) => (
                        <button
                            key={idx}
                            onClick={() => onChipClick?.(name)}
                            className="px-3 py-1.5 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] text-xs font-medium text-[var(--wdd-black)] shadow-sm hover:shadow hover:bg-gray-50 transition-all rounded-none cursor-pointer"
                        >
                            {name}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
