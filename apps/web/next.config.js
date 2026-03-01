/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    async rewrites() {
        const apiBase = process.env.NODE_ENV === 'production'
            ? 'http://api:8000'
            : 'http://localhost:8000';
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
