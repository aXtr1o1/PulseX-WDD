import React from 'react';
import clsx from 'clsx';
import type { Lang } from '@/lib/i18n';

interface ConsentBlockProps {
    lang: Lang;
    consentCallback: boolean;
    consentMarketing: boolean;
    onConsentCallback: (v: boolean) => void;
    onConsentMarketing: (v: boolean) => void;
    className?: string;
}

export default function ConsentBlock({
    lang,
    consentCallback,
    consentMarketing,
    onConsentCallback,
    onConsentMarketing,
    className,
}: ConsentBlockProps) {
    const rtl = lang === 'ar';

    const labels = {
        callback: lang === 'ar'
            ? 'أوافق على التواصل معي من فريق وادي دجلة بالهاتف'
            : 'I agree to be contacted by the WDD team by phone',
        marketing: lang === 'ar'
            ? 'أرغب في تلقي آخر تحديثات المشاريع والعروض'
            : "I'd like to receive updates on WDD projects and offers",
        note: lang === 'ar'
            ? 'سيتم استخدام بياناتك فقط للتواصل بشأن طلبك.'
            : 'Your details will only be used to respond to your enquiry.',
    };

    return (
        <div className={clsx('space-y-3', className)} dir={rtl ? 'rtl' : 'ltr'}>
            <CheckboxRow
                id="consent-callback"
                label={labels.callback}
                checked={consentCallback}
                onChange={onConsentCallback}
                rtl={rtl}
            />
            <CheckboxRow
                id="consent-marketing"
                label={labels.marketing}
                checked={consentMarketing}
                onChange={onConsentMarketing}
                rtl={rtl}
            />
            <p className="text-[11px] text-[var(--wdd-muted)] leading-relaxed">{labels.note}</p>
        </div>
    );
}

function CheckboxRow({
    id, label, checked, onChange, rtl,
}: {
    id: string; label: string; checked: boolean;
    onChange: (v: boolean) => void; rtl: boolean;
}) {
    return (
        <label
            htmlFor={id}
            className={clsx(
                'flex items-start gap-2.5 cursor-pointer group',
                rtl && 'flex-row-reverse',
            )}
        >
            <div className="relative mt-0.5 flex-shrink-0">
                <input
                    type="checkbox"
                    id={id}
                    checked={checked}
                    onChange={(e) => onChange(e.target.checked)}
                    className="sr-only"
                />
                <div
                    className={clsx(
                        'w-4 h-4 rounded border-2 flex items-center justify-center transition-all duration-150',
                        checked
                            ? 'bg-[var(--wdd-red)] border-[var(--wdd-red)]'
                            : 'bg-white border-[var(--wdd-border)] group-hover:border-[var(--wdd-red)]',
                    )}
                >
                    {checked && (
                        <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none">
                            <path d="M1.5 5L4 7.5L8.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    )}
                </div>
            </div>
            <span className={clsx('text-xs text-[var(--wdd-text)] leading-relaxed', rtl && 'text-right')}>
                {label}
            </span>
        </label>
    );
}
