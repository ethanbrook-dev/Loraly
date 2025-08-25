import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',          // Static HTML export
  distDir: 'out',            // Exported folder is `out/`
  reactStrictMode: true,     
  trailingSlash: true,       // Needed for Netlify routing
  images: {
    unoptimized: true,       // Static export cannot optimize images
  },
};

export default nextConfig;
