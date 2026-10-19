import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

// The browser talks ONLY to this origin; /api/v1 is proxied server-side to the API (no CORS,
// no API URL or credentials exposed to the client). The /internal/* routes are NOT proxied.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  // TODO(P09): tighten with a nonce-based CSP once the UI is complete.
];

const nextConfig: NextConfig = {
  output: "standalone", // small production image (see Dockerfile)
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
