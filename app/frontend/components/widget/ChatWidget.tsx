'use client';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { streamChat, type ChatMessage, type StreamDoneFrame, type EvidenceItem } from '@/lib/api';
import { gtm } from '@/lib/gtm';
import MessageBubble, { type Msg } from './MessageBubble';
import Spinner from '@/components/ui/Spinner';

const SESSION_KEY = 'wdd_pulsex_session_id';
const HISTORY_KEY = 'wdd_pulsex_history';

function getOrCreateSessionId(): string {
    if (typeof window === 'undefined') return 'sess_ssr';
    let id = localStorage.getItem(SESSION_KEY);
    if (!id) {
        id = 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
        localStorage.setItem(SESSION_KEY, id);
    }
    return id;
}

function loadHistory(): ChatMessage[] {
    if (typeof window === 'undefined') return [];
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        if (raw) return JSON.parse(raw) as ChatMessage[];
    } catch { /* ignore */ }
    return [];
}

function saveHistory(msgs: ChatMessage[]) {
    if (typeof window === 'undefined') return;
    try {
        // Keep last 40 messages to avoid localStorage bloat
        const trimmed = msgs.slice(-40);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
    } catch { /* ignore */ }
}

interface ChatWidgetProps {
    initialProject?: string;
    initialRegion?: string;
    embedded?: boolean;
}

export default function ChatWidget({ initialProject, embedded = false }: ChatWidgetProps) {
    const [session] = useState(getOrCreateSessionId);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [history, setHistory] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const historyRef = useRef<ChatMessage[]>([]);

    // Keep ref in sync for use inside callbacks
    useEffect(() => { historyRef.current = history; }, [history]);

    const scroll = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    useEffect(scroll, [messages]);

    // Restore history from localStorage on mount
    useEffect(() => {
        const saved = loadHistory();
        if (saved.length > 0) {
            setHistory(saved);
            // Reconstruct display messages from saved history
            const displayMsgs: Msg[] = saved.map(m => ({
                role: m.role as 'user' | 'assistant',
                content: m.content,
            }));
            setMessages(displayMsgs);
        }
        gtm.sessionStart(session, 'en');
    }, [session]);

    const handleSend = useCallback(async (text?: string) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setInput('');
        if (inputRef.current) inputRef.current.style.height = 'auto';
        setLoading(true);

        // Append user message to both display and history
        const userMsg: ChatMessage = { role: 'user', content: msg };
        const updatedHistory = [...historyRef.current, userMsg];
        setHistory(updatedHistory);
        historyRef.current = updatedHistory;

        const userDisplay: Msg = { role: 'user', content: msg };
        setMessages(prev => [...prev, userDisplay]);

        // Create streaming placeholder
        const placeholder: Msg = { role: 'assistant', content: '', streaming: true };
        setMessages(prev => [...prev, placeholder]);

        let accumulatedContent = '';

        streamChat(
            {
                session_id: session,
                messages: updatedHistory,
                locale: 'en',
            },
            {
                onToken: (token: string) => {
                    accumulatedContent += token;
                    setMessages(prev => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) {
                            copy[copy.length - 1] = { ...last, content: accumulatedContent };
                        }
                        return copy;
                    });
                },
                onDone: (meta: StreamDoneFrame | null) => {
                    const finalContent = accumulatedContent.trim();

                    // Finalize display message with metadata chips
                    setMessages(prev => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) {
                            copy[copy.length - 1] = {
                                role: 'assistant',
                                content: finalContent,
                                retrievedProjects: meta?.retrieved_projects ?? [],
                                evidence: meta?.evidence ?? [],
                                mode: meta?.mode ?? 'concierge',
                                stage: meta?.stage ?? '',
                                streaming: false,
                            };
                        }
                        return copy;
                    });

                    // Append assistant message to history
                    if (finalContent) {
                        const assistantMsg: ChatMessage = { role: 'assistant', content: finalContent };
                        const newHistory = [...historyRef.current, assistantMsg];
                        setHistory(newHistory);
                        historyRef.current = newHistory;
                        saveHistory(newHistory);
                    }

                    setLoading(false);
                    if (!embedded) inputRef.current?.focus();
                },
            },
        );
    }, [input, loading, session, embedded]);

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleNewChat = () => {
        localStorage.removeItem(SESSION_KEY);
        localStorage.removeItem(HISTORY_KEY);
        setMessages([]);
        setHistory([]);
        historyRef.current = [];
        // Force new session by reloading
        window.location.reload();
    };

    const containerClass = embedded
        ? "w-full flex-1 min-h-0 flex flex-col bg-white"
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
                    {messages.length > 0 && (
                        <button
                            onClick={handleNewChat}
                            className="text-[10px] font-semibold text-[var(--wdd-muted)] hover:text-[var(--wdd-red)] transition-colors tracking-wider uppercase"
                        >
                            New Chat
                        </button>
                    )}
                </div>
            )}

            {/* Chat Body */}
            <div className={`flex-1 min-h-0 overflow-y-auto ${!embedded ? 'scroll-smooth' : ''} ${embedded ? 'w-full' : ''}`}>
                <div className="px-4 md:px-8 py-8 space-y-8 max-w-4xl mx-auto w-full">
                    {messages.map((msg, i) => (
                        <MessageBubble
                            key={i}
                            message={msg}
                            onChipClick={(name) => handleSend(`Tell me more about ${name}`)}
                        />
                    ))}
                    <div ref={bottomRef} className="h-4" />
                </div>
            </div>

            {/* New Chat button for embedded mode */}
            {embedded && messages.length > 2 && (
                <div className="flex-none flex justify-center py-1">
                    <button
                        onClick={handleNewChat}
                        className="text-[10px] font-semibold text-[var(--wdd-muted)] hover:text-[var(--wdd-red)] transition-colors tracking-wider uppercase"
                    >
                        New Chat
                    </button>
                </div>
            )}

            {/* Input Dock */}
            <div className={`flex-none w-full bg-white pt-2 pb-6 md:pb-10 ${embedded ? 'px-4' : 'px-4 md:px-8'}`}>
                <div className={`w-full relative ${embedded ? 'max-w-4xl mx-auto' : ''}`}>
                    <div className="flex items-end bg-[#f9f9f9] rounded-none px-5 py-3 transition-all duration-300 border border-transparent focus-within:bg-white focus-within:border-[var(--wdd-red)] focus-within:shadow-[0_0_12px_rgba(203,32,48,0.15)]">
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
                            className="flex-1 bg-transparent text-[15px] font-medium text-[#1a1a1a] placeholder:text-gray-400 outline-none resize-none min-h-[24px] max-h-[150px] py-1 hide-scrollbar caret-[var(--wdd-red)]"
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
                                className="ml-3 mb-0.5 w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-none bg-[#E5E5E5] text-[#1a1a1a] hover:bg-[var(--wdd-red)] hover:text-white disabled:opacity-50 disabled:hover:bg-[#E5E5E5] disabled:hover:text-[#1a1a1a] disabled:cursor-not-allowed transition-colors cursor-pointer"
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
