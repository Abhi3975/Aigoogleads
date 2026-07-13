/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a minimal standalone server for lean Docker images
  output: 'standalone',
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
};

export default nextConfig;
