import React from 'react';
import clsx from 'clsx';
import type { Lang } from '@/lib/i18n';

interface Intent {
    id: string;
    icon: string;
    label: string;
    labelAr: string;
}

const INTENTS: Intent[] = [
    { id: 'property_question', icon: '🏡', label: 'Projects & Properties', labelAr: 'المشاريع والعقارات' },
    { id: 'payment_services', icon: '💳', label: 'Payment Services', labelAr: 'خدمات الدفع' },
    { id: 'complaint', icon: '📋', label: 'Complaints', labelAr: 'الشكاوى' },
    { id: 'gate_access', icon: '🔑', label: 'Gate Access', labelAr: 'الدخول والبوابات' },
    { id: 'rentals_ever_stay', icon: '🏖️', label: 'Ever Stay (Rent)', labelAr: 'إيفر ستاي (الإيجار)' },
    { id: 'hotels', icon: '🏨', label: 'Hotels', labelAr: 'الفنادق' },
    { id: 'referral_grow_the_family', icon: '🤝', label: 'Grow The Family', labelAr: 'انمِ العائلة' },
    { id: 'sales_intent', icon: '📞', label: 'Talk to Sales', labelAr: 'تحدث مع المبيعات' },
];

interface IntentChipsProps {
    lang: Lang;
    onSelect: (intentId: string, label: string) => void;
    disabled?: boolean;
}

export default function IntentChips({ lang, onSelect, disabled }: IntentChipsProps) {
    const rtl = lang === 'ar';

    return (
        <div
            className="grid grid-cols-2 gap-2 p-1 animate-slide-up"
            dir={rtl ? 'rtl' : 'ltr'}
        >
            {INTENTS.map((intent) => (
                <button
                    key={intent.id}
                    onClick={() => onSelect(intent.id, rtl ? intent.labelAr : intent.label)}
                    disabled={disabled}
                    className={clsx(
                        'flex items-center gap-2.5 px-3.5 py-2.5 rounded-[var(--wdd-radius)] border',
                        'text-xs font-medium text-left transition-all duration-150',
                        'bg-white border-[var(--wdd-border)] text-[var(--wdd-text)]',
                        'hover:border-[var(--wdd-red)] hover:text-[var(--wdd-red)] hover:bg-[#FFF8F8]',
                        'active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed',
                        rtl && 'flex-row-reverse text-right',
                    )}
                >
                    <span className="text-base leading-none flex-shrink-0">{intent.icon}</span>
                    <span className="leading-snug">{rtl ? intent.labelAr : intent.label}</span>
                </button>
            ))}
        </div>
    );
}
