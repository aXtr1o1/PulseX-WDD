'use client';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import clsx from 'clsx';
import { sendChat, streamChat } from '@/lib/api';
import { gtm } from '@/lib/gtm';
import type { Lang } from '@/lib/i18n';
import MessageBubble, { type Msg } from './MessageBubble';
import IntentChips from './IntentChips';
import LeadForm from './LeadForm';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';

// ── Session ID ────────────────────────────────────────────────────────────────
function genSessionId() {
    return 'sess_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

type Phase = 'lang' | 'intent' | 'chat' | 'lead' | 'success';

interface ChatWidgetProps {
    initialProject?: string;
    initialRegion?: string;
    embedded?: boolean;
}

export default function ChatWidget({ initialProject, initialRegion, embedded = false }: ChatWidgetProps) {
    const [open, setOpen] = useState(embedded);
    const [phase, setPhase] = useState<Phase>('lang');
    const [lang, setLang] = useState<Lang>('en');
    const [session] = useState(genSessionId);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [leadId, setLeadId] = useState('');
    const [showLead, setShowLead] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const rtl = lang === 'ar';

    const scroll = () => bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    useEffect(scroll, [messages]);

    // Set greeting when entering chat phase
    useEffect(() => {
        if (phase === 'chat' && messages.length === 0) {
            setMessages([{
                role: 'assistant',
                content: lang === 'ar'
                    ? 'أهلاً! كيف يمكنني مساعدتك اليوم؟'
                    : 'Hi — how can I help you today?',
            }]);
        }
    }, [phase, lang, messages.length]);

    const handleLangSelect = useCallback((l: Lang) => {
        setLang(l);
        setPhase('intent');
        gtm.sessionStart(session, l);
    }, [session]);

    const handleIntentSelect = useCallback((intentId: string, label: string) => {
        gtm.intentSelected(intentId, lang);
        setMessages([{
            role: 'assistant',
            content: lang === 'ar' ? `أهلاً! يسعدني مساعدتك في "${label}".` : `Got it — I can help with "${label}". What would you like to know?`,
        }]);
        setPhase('chat');
    }, [lang]);

    const handleSend = useCallback(async (text?: string) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setInput('');
        setLoading(true);

        const userMsg: Msg = { role: 'user', content: msg };
        setMessages((prev) => [...prev, userMsg]);

        // Streaming placeholder
        const placeholder: Msg = { role: 'assistant', content: '', streaming: true };
        setMessages((prev) => [...prev, placeholder]);

        let finalContent = '';

        streamChat(
            msg, session, lang,
            { url: typeof window !== 'undefined' ? window.location.href : undefined, project_slug: initialProject },
            (token) => {
                finalContent += token;
                setMessages((prev) => {
                    const copy = [...prev];
                    const last = copy[copy.length - 1];
                    if (last?.streaming) copy[copy.length - 1] = { ...last, content: finalContent };
                    return copy;
                });
            },
            async () => {
                // On done: fetch non-streaming for evidence
                try {
                    const full = await sendChat(msg, session, lang, {
                        url: typeof window !== 'undefined' ? window.location.href : undefined,
                        project_slug: initialProject,
                    });
                    setMessages((prev) => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) {
                            copy[copy.length - 1] = {
                                role: 'assistant',
                                content: full.answer,
                                evidence: full.evidence,
                                streaming: false,
                            };
                        }
                        return copy;
                    });
                    if (full.lead_trigger || full.handoff_cta) {
                        setTimeout(() => setShowLead(true), 600);
                    }
                } catch {
                    setMessages((prev) => {
                        const copy = [...prev];
                        const last = copy[copy.length - 1];
                        if (last?.streaming) copy[copy.length - 1] = { ...last, streaming: false };
                        return copy;
                    });
                } finally {
                    setLoading(false);
                    inputRef.current?.focus();
                }
            },
        );
    }, [input, loading, session, lang, initialProject]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleLeadSuccess = (id: string) => {
        setLeadId(id);
        setShowLead(false);
        setPhase('success');
    };

    // ── Trigger button (when not embedded) ────────────────────────────────────
    if (!embedded && !open) {
        return (
            <button
                onClick={() => setOpen(true)}
                id="pulsex-trigger"
                className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-5 py-3 bg-[var(--wdd-red)] text-white rounded-full shadow-[var(--wdd-shadow-lg)] hover:bg-[#b01c28] transition-all duration-200 active:scale-95 text-sm font-medium"
            >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {lang === 'ar' ? 'تحدث معنا' : 'Chat with us'}
            </button>
        );
    }

    // ── Widget panel ──────────────────────────────────────────────────────────
    const panelClass = embedded
        ? 'w-full h-full flex flex-col bg-white'
        : 'fixed bottom-6 right-6 z-50 w-[380px] max-h-[600px] flex flex-col bg-white rounded-2xl shadow-[var(--wdd-shadow-lg)] border border-[var(--wdd-border)] animate-slide-up';

    return (
        <div className={panelClass} dir={rtl ? 'rtl' : 'ltr'}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--wdd-border)] bg-white rounded-t-2xl">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-[var(--wdd-surface)] flex items-center justify-center overflow-hidden border border-[var(--wdd-border)]">
                        <Image src="/brand/WDD_blockLogo.png" width={28} height={28} alt="WDD" className="object-contain" />
                    </div>
                    <div>
                        <p className="text-xs font-semibold text-[var(--wdd-black)] leading-tight">WDD Concierge</p>
                        <p className="text-[10px] text-[var(--wdd-muted)]">{lang === 'ar' ? 'في الخدمة الآن' : 'Here to help'}</p>
                    </div>
                </div>
                {!embedded && (
                    <button
                        onClick={() => setOpen(false)}
                        className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-[var(--wdd-surface)] text-[var(--wdd-icon-grey)] transition-colors"
                    >
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                            <path d="M11 3L3 11M3 3l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">

                {/* Language screen */}
                {phase === 'lang' && (
                    <div className="flex flex-col items-center justify-center h-full gap-6 py-6 animate-fade-in">
                        <Image src="/brand/WDD_blockLogo.png" width={72} height={72} alt="WDD" className="object-contain" />
                        <div className="text-center">
                            <p className="text-[var(--wdd-black)] font-semibold text-base">Wadi Degla Developments</p>
                            <p className="text-[var(--wdd-muted)] text-sm mt-1">Select your language / اختر لغتك</p>
                        </div>
                        <div className="flex gap-3">
                            {(['en', 'ar'] as const).map((l) => (
                                <button
                                    key={l}
                                    onClick={() => handleLangSelect(l)}
                                    className="px-6 py-2.5 rounded-full border border-[var(--wdd-border)] text-sm font-medium text-[var(--wdd-text)] hover:border-[var(--wdd-red)] hover:text-[var(--wdd-red)] transition-all"
                                >
                                    {l === 'en' ? '🇬🇧 English' : '🇦🇪 العربية'}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Intent chips */}
                {phase === 'intent' && (
                    <div className="space-y-3">
                        <p className="text-xs font-medium text-[var(--wdd-muted)] text-center">
                            {lang === 'ar' ? 'ماذا تبحث عن؟' : 'What are you looking for?'}
                        </p>
                        <IntentChips lang={lang} onSelect={handleIntentSelect} disabled={loading} />
                    </div>
                )}

                {/* Chat messages */}
                {(phase === 'chat' || phase === 'lead' || phase === 'success') && (
                    <div className="space-y-3">
                        {messages.map((msg, i) => (
                            <MessageBubble key={i} message={msg} lang={lang} />
                        ))}

                        {/* Lead form */}
                        {showLead && (
                            <div className="border border-[var(--wdd-border)] rounded-xl p-4 bg-[var(--wdd-surface)] animate-slide-up">
                                <LeadForm
                                    lang={lang}
                                    sessionId={session}
                                    initialProjects={initialProject ? [initialProject] : []}
                                    onSuccess={handleLeadSuccess}
                                    onCancel={() => setShowLead(false)}
                                />
                            </div>
                        )}

                        {/* Success state */}
                        {phase === 'success' && (
                            <div className="text-center py-4 animate-fade-in space-y-2">
                                <div className="text-3xl">✅</div>
                                <p className="text-sm font-semibold text-[var(--wdd-black)]">
                                    {lang === 'ar' ? 'شكراً!' : 'Thank you!'}
                                </p>
                                <p className="text-xs text-[var(--wdd-muted)]">
                                    {lang === 'ar'
                                        ? `تم تسجيل طلبك (${leadId}). سيتواصل فريقنا معك قريباً.`
                                        : `Your request (${leadId}) has been recorded. Our team will be in touch soon.`}
                                </p>
                            </div>
                        )}

                        <div ref={bottomRef} />
                    </div>
                )}
            </div>

            {/* Callback CTA (when in chat) */}
            {phase === 'chat' && !showLead && (
                <div className="px-4 pb-2">
                    <button
                        onClick={() => { setShowLead(true); gtm.callbackRequested(session); }}
                        className="w-full text-xs text-[var(--wdd-red)] text-center py-1.5 hover:underline font-medium"
                    >
                        {lang === 'ar' ? '📞 طلب مكالمة من المبيعات' : '📞 Request a Sales Call'}
                    </button>
                </div>
            )}

            {/* Input bar */}
            {phase === 'chat' && !showLead && (
                <div className="px-3 pb-3 pt-1">
                    <div className="flex items-center gap-2 bg-[var(--wdd-surface)] border border-[var(--wdd-border)] rounded-xl px-3 py-2 focus-within:border-[var(--wdd-red)] transition-colors">
                        <input
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={lang === 'ar' ? 'اسأل عن مشاريعنا...' : 'Ask about our projects...'}
                            className="flex-1 bg-transparent text-sm text-[var(--wdd-text)] placeholder:text-[var(--wdd-muted)] outline-none"
                            dir={rtl ? 'rtl' : 'ltr'}
                            disabled={loading}
                        />
                        {loading ? (
                            <Spinner size="sm" />
                        ) : (
                            <button
                                onClick={() => handleSend()}
                                disabled={!input.trim()}
                                className="w-7 h-7 flex items-center justify-center rounded-lg bg-[var(--wdd-red)] text-white disabled:opacity-40 transition-opacity active:scale-95"
                            >
                                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                                    <path d="M1 6.5h11M7 1.5l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </button>
                        )}
                    </div>
                    <p className="text-center text-[10px] text-[var(--wdd-muted)] mt-1.5">Powered by WDD Concierge</p>
                </div>
            )}
        </div>
    );
}
