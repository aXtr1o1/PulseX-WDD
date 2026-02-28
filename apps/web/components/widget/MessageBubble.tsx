import React from 'react';
import clsx from 'clsx';
import type { EvidenceSnippet } from '@/lib/api';

type Role = 'user' | 'assistant' | 'system';

interface Msg {
    role: Role;
    content: string;
    evidence?: EvidenceSnippet[];
    streaming?: boolean;
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
                'flex flex-col gap-1.5 animate-slide-up',
                isUser ? 'items-end' : 'items-start',
            )}
        >
            <div
                className={clsx(
                    'max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed',
                    isUser
                        ? 'bg-[var(--wdd-red)] text-white rounded-br-sm'
                        : 'bg-[var(--wdd-surface)] text-[var(--wdd-text)] border border-[var(--wdd-border)] rounded-bl-sm',
                    rtl && 'text-right',
                )}
                dir={rtl ? 'rtl' : 'ltr'}
            >
                {message.content}
                {message.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-current ml-1 animate-blink rounded-sm" />
                )}
            </div>

            {/* Evidence snippets */}
            {!isUser && message.evidence && message.evidence.length > 0 && (
                <div className="max-w-[85%] space-y-1">
                    <p className="text-[10px] font-medium text-[var(--wdd-muted)] uppercase tracking-wider px-1">
                        {lang === 'ar' ? 'مصدر موثّق' : 'Verified from'}
                    </p>
                    {message.evidence.slice(0, 3).map((ev, i) => (
                        <div
                            key={i}
                            className="px-3 py-2 bg-[#FFF8F8] border border-[#FFE5E8] rounded-lg text-xs text-[var(--wdd-text)]"
                        >
                            <span className="font-semibold text-[var(--wdd-red)]">{ev.display_name}</span>
                            {ev.snippet && (
                                <span className="text-[var(--wdd-muted)] ml-1">— {ev.snippet.slice(0, 90)}{ev.snippet.length > 90 ? '…' : ''}</span>
                            )}
                            {ev.source_url && (
                                <a
                                    href={ev.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block mt-0.5 text-[10px] text-[var(--wdd-muted)] hover:text-[var(--wdd-red)] truncate"
                                >
                                    {ev.source_url}
                                </a>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export type { Msg };
