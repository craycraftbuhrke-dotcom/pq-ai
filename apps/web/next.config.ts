import type { NextConfig } from "next";

/** Bulk files are capped at 50 MiB; 3D models use 512 KiB chunk requests. */
const PROXY_BODY_LIMIT = "64mb";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    proxyClientMaxBodySize: PROXY_BODY_LIMIT,
    serverActions: {
      bodySizeLimit: "8mb",
    },
  },
};

export default nextConfig;
