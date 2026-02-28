import type { Config } from 'tailwindcss';

const config: Config = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './lib/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                wdd: {
                    red: '#CB2030',
                    bg: '#FFFFFF',
                    text: '#191919',
                    black: '#000000',
                    grey: '#55575A',
                    surface: '#FAFAFA',
                    border: '#E6E6E6',
                    muted: '#6B6B6B',
                },
            },
            fontFamily: {
                isidora: ['"Isidora Sans"', '"Segoe UI"', 'system-ui', 'sans-serif'],
                arabic: ['"Isidora Sans"', '"Noto Sans Arabic"', 'system-ui', 'sans-serif'],
            },
            animation: {
                'fade-in': 'fadeIn 0.3s ease-out',
                'slide-up': 'slideUp 0.35s ease-out',
                'slide-in-right': 'slideInRight 0.3s ease-out',
                'count-up': 'countUp 0.6s ease-out',
            },
            keyframes: {
                fadeIn: { from: { opacity: '0' }, to: { opacity: '1' } },
                slideUp: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
                slideInRight: { from: { opacity: '0', transform: 'translateX(20px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
                countUp: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
            },
        },
    },
    plugins: [],
};

export default config;
