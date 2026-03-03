'use client';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';

interface HealthResponse {
    status: string;
    index_ready: boolean;
    kb_hash: string;
    last_indexed_at?: string;
    message?: string;
}

interface InitScreenProps {
    onReady: () => void;
}

export default function InitScreen({ onReady }: InitScreenProps) {
    const [statusText, setStatusText] = useState('Initializing WDD PulseX AI');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Cycle status text softly
        const interval = setInterval(() => {
            setStatusText(prev =>
                prev === 'Initializing WDD PulseX AI'
                    ? 'Loading verified project information...'
                    : 'Initializing WDD PulseX AI'
            );
        }, 2500);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        let mounted = true;

        const pollHealth = async () => {
            try {
                const res = await fetch('/api/health'); // assumed proxies through next.config.js
                if (!res.ok) throw new Error('Network error');

                const data: HealthResponse = await res.json();
                if (data.index_ready && mounted) {
                    // Enforce a 2.5 second minimum display time so the brand initialization animation is visible
                    setTimeout(() => {
                        if (mounted) onReady();
                    }, 2500);
                } else {
                    if (mounted) setTimeout(pollHealth, 2000);
                }
            } catch (err) {
                if (mounted) {
                    setError('Connection to PulseX core paused. Retrying...');
                    setTimeout(pollHealth, 4000);
                }
            }
        };

        pollHealth();
        return () => { mounted = false; };
    }, [onReady]);

    return (
        <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[var(--wdd-bg)] animate-fade-in">
            <div className="flex flex-col items-center animate-pulse-soft">
                <Image
                    src="/brand/WDD_blockLogo.png"
                    width={80}
                    height={80}
                    alt="WDD PulseX AI"
                    className="object-contain mb-8"
                    priority
                />
                <p className="text-[var(--wdd-muted)] text-sm tracking-wide transition-opacity duration-1000 ease-in-out">
                    {error || statusText}
                </p>
            </div>
        </div>
    );
}
