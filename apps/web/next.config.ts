import type { NextConfig } from "next";

/** Intranet CAD uploads (STP/GLB) can be multi‑GB; do not keep the default ~10MB proxy buffer. */
const LARGE_UPLOAD_BODY = "4gb";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    proxyClientMaxBodySize: LARGE_UPLOAD_BODY,
    serverActions: {
      bodySizeLimit: LARGE_UPLOAD_BODY,
    },
  },
};

export default nextConfig;
