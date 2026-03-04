/**
 * PulseX-WDD i18n — English-only (Arabic removed for Path B)
 */

export type Lang = 'en';

export const STRINGS = {
    en: {
        greeting: 'Hi — how can I help you today?',
        langSelect: 'Select your language',
        intentLabel: 'What are you looking for?',
        intents: {
            projects: 'Projects & Properties',
            payment: 'Payment Services',
            complaint: 'Complaints',
            gate: 'Gate Access',
            everStay: 'Ever Stay (Rent)',
            hotels: 'Hotels',
            referral: 'Grow The Family',
            sales: 'Talk to Sales',
        },
        inputPlaceholder: 'Ask about our projects, pricing, or services...',
        send: 'Send',
        callbackCta: 'Request a Sales Call',
        leadFormTitle: 'Let\'s get you connected',
        nameLabel: 'Your name',
        phoneLabel: 'Phone number',
        emailLabel: 'Email address (optional)',
        projectsLabel: 'Project(s) you\'re interested in',
        consentCallback: 'I agree to be contacted by the WDD team by phone',
        consentMarketing: 'I\'d like to receive updates on projects and offers',
        submit: 'Send my details',
        successMsg: 'Thank you! Our team will be in touch shortly.',
        evidenceLabel: 'Verified from',
        typingLabel: 'Typing…',
        errorMsg: 'Something went wrong. Please try again.',
        poweredBy: 'Powered by WDD Concierge',
        adminLogin: 'Admin Login',
        password: 'Password',
        loginBtn: 'Log in',
        logout: 'Log out',
        dashboard: 'Dashboard',
        leads: 'Leads',
        dataViewer: 'Data Viewer',
        kpiTotal: 'Total Leads',
        kpi24h: 'Last 24 Hours',
        kpiContacts: 'Unique Contacts',
        kpiTopProject: 'Top Project',
        kpiTopRegion: 'Top Region',
        kpiMedianBudget: 'Median Budget',
        noData: 'No data yet',
        download: 'Download CSV',
        exportXlsx: 'Export XLSX',
        refresh: 'Refresh',
        filter: 'Filter',
        timeAll: 'All time',
        time24h: 'Last 24h',
        time7d: 'Last 7 days',
        time30d: 'Last 30 days',
        copyRaw: 'Copy Raw JSON',
        copied: 'Copied!',
    },
} as const;

export type StringKey = keyof typeof STRINGS.en;

export function t(key: StringKey, lang: Lang = 'en'): string {
    return STRINGS[lang][key] as string ?? STRINGS.en[key] as string;
}

export function isRTL(_lang: Lang): boolean {
    return false;
}
