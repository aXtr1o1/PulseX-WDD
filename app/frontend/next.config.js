/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        // In Docker: 'http://pulsex_api:8000' (service name)
        // In local dev: 'http://localhost:8000'
        const apiBase = process.env.NODE_ENV === 'production'
            ? 'https://pulse.axtr.in'
            : 'http://localhost:8081';
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
