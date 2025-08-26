/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/conceptdb/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
  webpack: (config) => {
    // Fix for cytoscape
    config.externals = config.externals || {};
    config.externals['canvas'] = 'canvas';
    return config;
  },
};

module.exports = nextConfig;