import React from 'react';
import clsx from 'clsx';

type Role = 'user' | 'assistant' | 'system';

export interface Msg {
    role: Role;
    content: string;
    streaming?: boolean;
    retrievedProjects?: string[];
    mode?: 'concierge' | 'lead_capture';
}

interface MessageBubbleProps {
    message: Msg;
    onChipClick?: (name: string) => void;
}

export default function MessageBubble({ message, onChipClick }: MessageBubbleProps) {
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
                            // markdown headers (supports #, ##, ###)
                            .replace(/^###\s+(.*$)/gim, '<h3 class="text-base font-bold text-[var(--wdd-black)] mt-3 mb-1">$1</h3>')
                            .replace(/^##\s+(.*$)/gim, '<h2 class="text-lg font-bold text-[var(--wdd-black)] mt-4 mb-1">$1</h2>')
                            .replace(/^#\s+(.*$)/gim, '<h1 class="text-xl font-bold text-[var(--wdd-black)] mt-4 mb-2">$1</h1>')
                            // styling important keywords with a premium highlight using exact #CB2030
                            .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-[var(--wdd-red)] bg-[#CB2030]/5 px-1 py-0.5 rounded-sm inline-block">$1</strong>')
                            // newlines
                            .replace(/\n/g, '<br/>')
                    }}
                />

                {message.streaming && (
                    <span className="inline-block w-1.5 h-4 bg-current ml-1 animate-blink rounded-sm align-middle" />
                )}
            </div>

            {/* Verified Project Chips — strictly from backend retrieved_projects metadata */}
            {!isUser && !message.streaming && message.retrievedProjects && message.retrievedProjects.length > 0 && (
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
