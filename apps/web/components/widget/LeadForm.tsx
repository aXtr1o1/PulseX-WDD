'use client';
import React, { useState } from 'react';
import clsx from 'clsx';
import Button from '@/components/ui/Button';
import ConsentBlock from './ConsentBlock';
import type { LeadPayload } from '@/lib/api';
import { submitLead } from '@/lib/api';
import { gtm } from '@/lib/gtm';
import type { Lang } from '@/lib/i18n';

interface LeadFormProps {
    lang: Lang;
    sessionId: string;
    initialProjects?: string[];
    sourceUrl?: string;
    onSuccess?: (leadId: string) => void;
    onCancel?: () => void;
}

export default function LeadForm({
    lang, sessionId, initialProjects = [], sourceUrl, onSuccess, onCancel,
}: LeadFormProps) {
    const [name, setName] = useState('');
    const [phone, setPhone] = useState('');
    const [email, setEmail] = useState('');
    const [consentCb, setConsentCb] = useState(false);
    const [consentMkt, setConsentMkt] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const rtl = lang === 'ar';

    const labels = {
        title: lang === 'ar' ? 'دعنا نوصلك بفريقنا' : "Let's get you connected",
        nameL: lang === 'ar' ? 'الاسم' : 'Your name',
        phoneL: lang === 'ar' ? 'رقم الهاتف *' : 'Phone number *',
        emailL: lang === 'ar' ? 'البريد الإلكتروني (اختياري)' : 'Email (optional)',
        submitL: lang === 'ar' ? 'إرسال بياناتي' : 'Send my details',
        cancelL: lang === 'ar' ? 'إلغاء' : 'Cancel',
        phoneReq: lang === 'ar' ? 'رقم الهاتف مطلوب' : 'Phone number is required',
        consentReq: lang === 'ar' ? 'يرجى الموافقة على التواصل' : 'Please agree to be contacted',
    };

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError('');
        if (!phone.trim()) { setError(labels.phoneReq); return; }
        if (!consentCb) { setError(labels.consentReq); return; }

        setLoading(true);
        try {
            const payload: LeadPayload = {
                session_id: sessionId,
                lang,
                name: name.trim() || undefined,
                phone: phone.trim(),
                email: email.trim() || undefined,
                interest_projects: initialProjects,
                consent_callback: consentCb,
                consent_marketing: consentMkt,
                source_url: sourceUrl || (typeof window !== 'undefined' ? window.location.href : undefined),
                page_title: typeof document !== 'undefined' ? document.title : undefined,
                tags: [],
            };
            const res = await submitLead(payload);
            gtm.leadQualified(sessionId, 'sales_intent');
            if (consentCb || consentMkt) gtm.consentOptIn(sessionId, [consentCb ? 'callback' : '', consentMkt ? 'marketing' : ''].filter(Boolean));
            gtm.callbackRequested(sessionId);
            onSuccess?.(res.lead_id);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Submission failed. Please try again.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="space-y-4 animate-slide-up"
            dir={rtl ? 'rtl' : 'ltr'}
        >
            <h3 className="text-sm font-semibold text-[var(--wdd-black)]">{labels.title}</h3>

            <Field label={labels.nameL} rtl={rtl}>
                <input
                    type="text" value={name} onChange={(e) => setName(e.target.value)}
                    placeholder={rtl ? 'اسمك...' : 'Your name...'}
                    className={inputClass(rtl)}
                    autoComplete="name"
                />
            </Field>

            <Field label={labels.phoneL} rtl={rtl}>
                <input
                    type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
                    placeholder="+20 1XX XXX XXXX"
                    className={inputClass(rtl)}
                    autoComplete="tel"
                    required
                />
            </Field>

            <Field label={labels.emailL} rtl={rtl}>
                <input
                    type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@example.com"
                    className={inputClass(rtl)}
                    autoComplete="email"
                />
            </Field>

            <ConsentBlock
                lang={lang}
                consentCallback={consentCb}
                consentMarketing={consentMkt}
                onConsentCallback={setConsentCb}
                onConsentMarketing={setConsentMkt}
            />

            {error && (
                <p className="text-xs text-[var(--wdd-red)] font-medium">{error}</p>
            )}

            <div className={clsx('flex gap-2', rtl && 'flex-row-reverse')}>
                <Button type="submit" variant="primary" size="md" loading={loading} className="flex-1">
                    {labels.submitL}
                </Button>
                {onCancel && (
                    <Button type="button" variant="ghost" size="md" onClick={onCancel}>
                        {labels.cancelL}
                    </Button>
                )}
            </div>
        </form>
    );
}

function Field({ label, children, rtl }: { label: string; children: React.ReactNode; rtl: boolean }) {
    return (
        <div className="space-y-1.5">
            <label className={clsx('block text-xs font-medium text-[var(--wdd-text)]', rtl && 'text-right')}>
                {label}
            </label>
            {children}
        </div>
    );
}

function inputClass(rtl: boolean) {
    return clsx(
        'w-full px-3 py-2 text-sm rounded-[var(--wdd-radius)] border border-[var(--wdd-border)]',
        'bg-white text-[var(--wdd-text)] placeholder:text-[var(--wdd-muted)]',
        'focus:outline-none focus:ring-2 focus:ring-[var(--wdd-red)] focus:border-transparent',
        'transition-shadow duration-150',
        rtl && 'text-right',
    );
}
