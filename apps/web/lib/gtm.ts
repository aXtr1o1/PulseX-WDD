/**
 * PulseX-WDD GTM Event Hooks
 * Fires Google Tag Manager dataLayer events.
 * No-op when window.dataLayer is not available.
 */

declare global {
    interface Window {
        dataLayer?: Record<string, unknown>[];
    }
}

function push(event: string, params?: Record<string, unknown>): void {
    if (typeof window !== 'undefined' && window.dataLayer) {
        window.dataLayer.push({ event, ...params });
    }
}

export const gtm = {
    sessionStart: (sessionId: string, lang: string) =>
        push('pulseX_session_start', { session_id: sessionId, lang }),

    intentSelected: (intent: string, lang: string) =>
        push('pulseX_intent_selected', { intent, lang }),

    leadQualified: (sessionId: string, intent: string) =>
        push('pulseX_lead_qualified', { session_id: sessionId, intent }),

    handoffSuccess: (sessionId: string, lane: string) =>
        push('pulseX_handoff_success', { session_id: sessionId, lane }),

    callbackRequested: (sessionId: string) =>
        push('pulseX_callback_requested', { session_id: sessionId }),

    consentOptIn: (sessionId: string, types: string[]) =>
        push('pulseX_consent_opt_in', { session_id: sessionId, consent_types: types }),

    customEvent: (eventName: string, params?: Record<string, unknown>) =>
        push(eventName, params),
};
