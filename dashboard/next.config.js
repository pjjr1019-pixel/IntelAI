const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  experimental: {
    optimizeCss: true,
    scrollRestoration: true,
  },
  turbopack: {},
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  images: {
    formats: ['image/webp', 'image/avif'],
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
      {
        source: '/static/(.*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
  },
  ...(process.env.VS_STATIC_EXPORT === '1'
    ? {
        output: 'export',
        distDir: 'out',
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {
        async rewrites() {
          return [
            { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
            { source: '/ws/:path*', destination: 'http://localhost:8000/ws/:path*' },
          ];
        },
      }),
};

module.exports = withBundleAnalyzer(nextConfig);
