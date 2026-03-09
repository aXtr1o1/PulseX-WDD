/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim().replace(/\/$/, '');
        // Fallbacks preserve existing Docker/local behavior when no env is set.
        const apiBase = configuredApiBase || (process.env.NODE_ENV === 'production'
            ? 'https://pulse.axtr.in'
            : 'http://localhost:8081');
        return [
            {
                source: '/api/:path*',
                destination: `${apiBase}/api/:path*`,
            },
        ];
    },
    images: {
        remotePatterns: [
            {
                protocol: 'https',
                hostname: 'wadidegladevelopments.com',
            }
        ],
    },
};

module.exports = nextConfig;
