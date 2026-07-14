/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Emit a minimal standalone server for lean Docker images
  output: 'standalone',
  poweredByHeader: false,
  // Pin the workspace root to this app (avoids picking up a parent lockfile).
  outputFileTracingRoot: import.meta.dirname,
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
};

export default nextConfig;
