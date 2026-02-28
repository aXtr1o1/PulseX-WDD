/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        return [
            {
                source: '/api/:path*',
                destination: `${apiBase}/api/:path*`,
            },
        ];
    },
    images: {
        domains: ['wadidegladevelopments.com'],
    },
};

module.exports = nextConfig;
