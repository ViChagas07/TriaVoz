import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

// The browser talks ONLY to this origin; /api/v1 is proxied server-side to the API (no CORS,
// no API URL or credentials exposed to the client). The /internal/* routes are NOT proxied.
// CSP is issued per request with a nonce in src/proxy.ts; these are the static companions.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
];

const nextConfig: NextConfig = {
  output: "standalone", // small production image (see Dockerfile)
  poweredByHeader: false,
  async redirects() {
    // The product is intentionally nine routes. Old skeleton URLs keep working for bookmarks.
    return [
      { source: "/agenda", destination: "/agendamentos", permanent: true },
      {
        source: "/historico",
        destination: "/agendamentos?tab=history",
        permanent: true,
      },
      {
        source: "/solicitacoes",
        destination: "/agendamentos?tab=pending",
        permanent: true,
      },
      {
        source: "/solicitacoes/:id",
        destination: "/agendamentos?tab=pending&request=:id",
        permanent: true,
      },
      {
        source: "/equipe",
        destination: "/configuracoes?tab=team",
        permanent: true,
      },
      { source: "/agente/opcoes", destination: "/agente", permanent: true },
      { source: "/agente/saudacao", destination: "/agente", permanent: true },
      { source: "/agente/testar", destination: "/agente", permanent: true },
      { source: "/agente/transferencia", destination: "/agente", permanent: true },
    ];
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
