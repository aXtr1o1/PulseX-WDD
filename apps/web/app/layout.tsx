import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'PulseX — Wadi Degla Developments Concierge',
    description: 'Your intelligent property concierge for Wadi Degla Developments.',
    openGraph: {
        title: 'PulseX — Wadi Degla Developments',
        description: 'Discover premium WDD projects with AI-powered concierge assistance.',
        type: 'website',
    },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <meta charSet="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <link rel="icon" href="/brand/WDD_blockLogo.png" />
            </head>
            <body className="font-isidora bg-white text-wdd-text antialiased">
                {children}
            </body>
        </html>
    );
}
