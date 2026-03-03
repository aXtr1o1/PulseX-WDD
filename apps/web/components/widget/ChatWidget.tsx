'use client';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { sendChat, streamChat } from '@/lib/api';
import { gtm } from '@/lib/gtm';
import type { Lang } from '@/lib/i18n';
import MessageBubble, { type Msg } from './MessageBubble';
import LeadForm from './LeadForm';
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
    useEffect(scroll, [messages, showLead]);

    // Initialize conversation grammar (PalmX style)
    useEffect(() => {
        if (messages.length === 0) {
            setMessages([{
                role: 'assistant',
                content: lang === 'ar'
                    ? 'أهلاً بك في دجلة للتطوير العقاري. ما هي المنطقة أو المشروع الذي تهتم به؟'
                    : 'Welcome to Wadi Degla Developments. What region or project are you interested in today?',
            }]);
            gtm.sessionStart(session, lang);
        }
    }, [lang, session, messages.length]);

    const handleSend = useCallback(async (text?: string) => {
        const msg = (text ?? input).trim();
        if (!msg || loading) return;
        setInput('');
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
                        if (last?.streaming) copy[copy.length - 1] = { ...last, evidence: meta.evidence };
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
                                streaming: false,
                            };
                        }
                        return copy;
                    });

                    // Trigger lead if intent matches SALES or handoff matches
                    if (streamMetadata?.lead_trigger || payloadData?.lead_suggestions?.ready_for_handoff) {
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
                    if (!embedded) inputRef.current?.focus();
                }
            },
        );
    }, [input, loading, session, lang, initialProject, embedded]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    const handleLeadSuccess = (id: string) => {
        setLeadId(id);
        setShowLead(false);
        setMessages((prev) => [...prev, {
            role: 'assistant',
            content: lang === 'ar'
                ? `شكراً لك. تم تسجيل طلبك (${id}). سيتواصل فريقنا معك قريباً. هل هناك أي معلومات أخرى تبحث عنها؟`
                : `Thank you. Your request (${id}) has been recorded. Our team will be in touch soon. Is there any other information you're looking for?`
        }]);
    };

    const containerClass = embedded
        ? "w-full h-full flex flex-col bg-white"
        : "w-full max-w-4xl mx-auto h-[70vh] min-h-[500px] flex flex-col bg-white rounded-2xl shadow-[var(--wdd-shadow-lg)] border border-[var(--wdd-border)]";

    return (
        <div className={containerClass} dir={rtl ? 'rtl' : 'ltr'}>

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
                                {lang === 'ar' ? 'معلومات موثقة فقط' : 'Verified Information Only'}
                            </p>
                        </div>
                    </div>
                    {headerLangToggle && (
                        <button
                            onClick={() => setLang(l => l === 'en' ? 'ar' : 'en')}
                            className="text-xs font-medium text-[var(--wdd-text)] hover:text-[var(--wdd-red)] transition-colors"
                        >
                            {lang === 'en' ? '🇦🇪 العربية' : '🇬🇧 English'}
                        </button>
                    )}
                </div>
            )}

            {/* Chat Body */}
            <div className={`flex-1 overflow-y-auto px-4 md:px-8 py-8 space-y-8 ${!embedded ? 'scroll-smooth' : ''} ${embedded ? 'max-w-4xl mx-auto w-full' : ''}`}>
                {messages.map((msg, i) => (
                    <MessageBubble key={i} message={msg} lang={lang} />
                ))}

                {/* Progressive Lead Form Injection */}
                {showLead && (
                    <div className="border border-[var(--wdd-border)] rounded-2xl p-5 md:p-6 bg-[var(--wdd-surface)] animate-slide-up shadow-sm mb-4">
                        <div className="mb-4">
                            <h4 className="text-[var(--wdd-black)] font-medium text-sm">
                                {lang === 'ar' ? 'تأكيد طلبك' : 'Confirm your request'}
                            </h4>
                            <p className="text-[var(--wdd-muted)] text-xs mt-1">
                                {lang === 'ar' ? 'نحتاج لبعض التفاصيل الإضافية لمساعدتك بشكل أفضل.' : 'We just need a few details to assist you better.'}
                            </p>
                        </div>
                        <LeadForm
                            lang={lang}
                            sessionId={session}
                            initialProjects={initialProject ? [initialProject] : []}
                            onSuccess={handleLeadSuccess}
                            onCancel={() => setShowLead(false)}
                        />
                    </div>
                )}

                <div ref={bottomRef} className="h-4" />
            </div>

            {/* Input Dock */}
            <div className={`w-full bg-gradient-to-t from-white via-white to-transparent pt-6 pb-8 md:pb-12 ${embedded ? 'px-4' : 'px-4 md:px-8 pb-6 pt-4'}`}>
                <div className={`w-full relative ${embedded ? 'max-w-4xl mx-auto' : ''}`}>
                    <div className="flex items-center bg-white border border-[var(--wdd-border)] rounded-full px-5 py-3.5 shadow-[0_2px_16px_rgba(0,0,0,0.03)] focus-within:border-[var(--wdd-red)] focus-within:shadow-[0_4px_24px_rgba(203,32,48,0.06)] transition-all duration-300">
                        <input
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={lang === 'ar' ? 'رحلتك إلى منزل أحلامك تبدأ من هنا...' : 'The journey to your dream starts here...'}
                            className="flex-1 bg-transparent text-[15px] font-medium text-[var(--wdd-black)] placeholder:text-[var(--wdd-muted)] placeholder:font-normal outline-none"
                            dir={rtl ? 'rtl' : 'ltr'}
                            disabled={loading}
                        />
                        {loading ? (
                            <div className="pl-3 animate-fade-in flex items-center justify-center">
                                <Spinner size="sm" />
                            </div>
                        ) : (
                            <button
                                onClick={() => handleSend()}
                                disabled={!input.trim()}
                                className="ml-3 w-9 h-9 flex items-center justify-center rounded-full bg-[var(--wdd-black)] text-white hover:bg-[var(--wdd-red)] disabled:opacity-50 disabled:hover:bg-[var(--wdd-black)] transition-all duration-300 active:scale-95"
                                aria-label="Send message"
                            >
                                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                                    <path d="M1 7.5h12M8 2.5l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
                {!embedded && (
                    <div className="flex justify-between items-center mt-4 px-3 max-w-4xl mx-auto">
                        <p className="text-[11px] text-[var(--wdd-muted)] flex items-center gap-2">
                            <span>{lang === 'ar' ? 'الردود مبنية على معلومات موثقة' : 'Responses grounded in verified information'}</span>
                            <span className="w-1 h-1 rounded-full bg-[var(--wdd-border)]"></span>
                            <a href="tel:16662" className="hover:text-[var(--wdd-red)] transition-colors inline-flex items-center gap-1 font-medium"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 16.92z" /></svg> 16662</a>
                        </p>
                        <button
                            onClick={() => { setShowLead(true); gtm.callbackRequested(session); }}
                            className="text-[11px] font-medium text-[var(--wdd-red)] hover:underline"
                        >
                            {lang === 'ar' ? 'طلب مكالمة مبيعات' : 'Request Sales Call'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
