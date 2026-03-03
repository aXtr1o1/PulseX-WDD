'use client';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { sendChat, streamChat } from '@/lib/api';
import { gtm } from '@/lib/gtm';
import type { Lang } from '@/lib/i18n';
import MessageBubble, { type Msg } from './MessageBubble';
import Spinner from '@/components/ui/Spinner';

function genSessionId() {
    return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

interface ChatWidgetProps {
    initialProject?: string;
    initialRegion?: string;
    embedded?: boolean;
    headerLangToggle?: boolean;
}

export default function ChatWidget({ initialProject, initialRegion, embedded = false, headerLangToggle = false }: ChatWidgetProps) {
    const [lang] = useState<Lang>('en'); // Forced English
    const [session] = useState(genSessionId);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const scroll = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    useEffect(scroll, [messages]);

    // Initialize conversation grammar (PalmX style)
    useEffect(() => {
        if (messages.length === 0) {
            // User requested to remove initial conversational triggers so the chat natively starts on the first user message
            gtm.sessionStart(session, lang);
        }
    }, [lang, session, messages.length]);

    const handleSend = useCallback(async (text?: string) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setInput('');
        if (inputRef.current) inputRef.current.style.height = 'auto';
        setLoading(true);

        const userMsg: Msg = { role: 'user', content: msg };
        setMessages((prev) => [...prev, userMsg]);

        const placeholder: Msg = { role: 'assistant', content: '', streaming: true };
        setMessages((prev) => [...prev, placeholder]);

        let finalContent = '';
        let streamMetadata: any = null;

        streamChat(
            msg, session, lang,
            { url: typeof window !== 'undefined' ? window.location.href : undefined, project_slug: initialProject },
            (token) => {
                finalContent += token;
                setMessages((prev) => {
                    const copy = [...prev];
                    const last = copy[copy.length - 1];
                    if (last?.streaming) {
                        let display = finalContent;
                        const pIdx = display.indexOf('<payload>');
                        if (pIdx !== -1) display = display.substring(0, pIdx);
                        copy[copy.length - 1] = { ...last, content: display };
                    }
                    return copy;
                });
            },
            (meta) => {
                streamMetadata = meta;
                if (meta?.evidence && meta.evidence.length > 0) {
                    setMessages((prev) => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) {
                            copy[copy.length - 1] = {
                                ...last,
                                evidence: meta.evidence,
                                shortlist: meta.shortlist
                            };
                        }
                        return copy;
                    });
                }
            },
            async () => {
                try {
                    let answerText = finalContent;
                    let payloadData: any = {};

                    const pIdx = finalContent.indexOf('<payload>');
                    if (pIdx !== -1) {
                        const endIdx = finalContent.indexOf('</payload>', pIdx);
                        if (endIdx !== -1) {
                            const jsonStr = finalContent.substring(pIdx + 9, endIdx).trim();
                            try {
                                payloadData = JSON.parse(jsonStr);
                            } catch (e) { console.error("Failed to parse LLM JSON payload", e); }
                            answerText = finalContent.substring(0, pIdx).trim();
                        } else {
                            // Unclosed tag
                            answerText = finalContent.substring(0, pIdx).trim();
                        }
                    }

                    setMessages((prev) => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) {
                            copy[copy.length - 1] = {
                                role: 'assistant',
                                content: answerText,
                                evidence: streamMetadata?.evidence,
                                lead_suggestions: payloadData?.lead_suggestions,
                                focused_project: payloadData?.focused_project,
                                lead_trigger: streamMetadata?.lead_trigger,
                                streaming: false,
                            };
                        }
                        return copy;
                    });
                } catch {
                    setMessages((prev) => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) copy[copy.length - 1] = { ...last, streaming: false };
                        return copy;
                    });
                } finally {
                    setLoading(false);
                    if (!embedded) inputRef.current?.focus();
                }
            },
        );
    }, [input, loading, session, lang, initialProject, embedded]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const containerClass = embedded
        ? "w-full h-full flex flex-col bg-white"
        : "w-full max-w-4xl mx-auto h-[70vh] min-h-[500px] flex flex-col bg-white rounded-2xl shadow-[var(--wdd-shadow-lg)] border border-[var(--wdd-border)]";

    return (
        <div className={containerClass} dir="ltr">

            {/* Header (optional based on embedding, but always premium) */}
            {!embedded && (
                <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--wdd-border)] bg-gray-50/50">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center overflow-hidden border border-[var(--wdd-border)] shadow-sm">
                            <Image src="/brand/WDD_blockLogo.png" width={22} height={22} alt="WDD" className="object-contain" />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-[var(--wdd-black)] leading-tight">WDD Concierge</p>
                            <p className="text-[11px] text-[var(--wdd-muted)] tracking-wide">
                                Verified Information Only
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Chat Body - Scrollbar flush by moving padding inward */}
            <div className={`flex-1 overflow-y-auto ${!embedded ? 'scroll-smooth' : ''} ${embedded ? 'w-full' : ''}`}>
                <div className="px-4 md:px-8 py-8 space-y-8 max-w-4xl mx-auto w-full">
                    {messages.map((msg, i) => (
                        <MessageBubble
                            key={i}
                            message={msg}
                            lang={lang}
                            onConfirm={() => handleSend('Yes, I confirm my details and consent to a callback.')}
                            onChipClick={(name) => handleSend(`I'm interested in ${name}`)}
                        />
                    ))}
                    <div ref={bottomRef} className="h-4" />
                </div>
            </div>

            {/* Input Dock - Minimalist Floating Pill */}
            <div className={`w-full bg-white pt-2 pb-6 md:pb-10 ${embedded ? 'px-4' : 'px-4 md:px-8'}`}>
                <div className={`w-full relative ${embedded ? 'max-w-4xl mx-auto' : ''}`}>
                    <div className="flex items-end bg-[#f9f9f9] rounded-none px-5 py-3 transition-all duration-300 group focus-within:bg-[var(--wdd-surface)] focus-within:shadow-sm">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={(e) => {
                                setInput(e.target.value);
                                e.target.style.height = 'auto';
                                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
                            }}
                            onKeyDown={handleKeyDown}
                            placeholder="The journey to your dream starts here..."
                            className="flex-1 bg-transparent text-[15px] font-medium text-[#1a1a1a] placeholder:text-gray-400 outline-none resize-none min-h-[24px] max-h-[150px] py-1 hide-scrollbar"
                            rows={1}
                            dir="ltr"
                            disabled={loading}
                        />
                        {loading ? (
                            <div className="pl-3 pb-0.5 animate-fade-in flex items-center justify-center">
                                <Spinner size="sm" />
                            </div>
                        ) : (
                            <button
                                onClick={() => handleSend()}
                                disabled={!input.trim()}
                                className="ml-3 mb-0.5 w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-none bg-[#E5E5E5] text-[#1a1a1a] hover:bg-[#d4d4d4] disabled:opacity-50 transition-colors cursor-pointer"
                                aria-label="Send message"
                            >
                                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                                    <path d="M1 7.5h12M8 2.5l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
