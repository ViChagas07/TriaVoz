import { NextResponse, type NextRequest } from "next/server";

const LOCALES = new Set(["pt-BR", "en"]);
const PROTECTED = ["/painel", "/chamadas", "/agendamentos", "/agente", "/configuracoes"];
const API_ORIGIN = (process.env.API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
// Production sets COOKIE_PREFIX=__Host- so the API's Secure/Path=/ cookies cannot be shadowed by
// a subdomain. Keep it empty in local HTTP development.
const COOKIE_PREFIX = process.env.COOKIE_PREFIX ?? "";
const ACCESS_COOKIE = `${COOKIE_PREFIX}triavoz_access`;
const REFRESH_COOKIE = `${COOKIE_PREFIX}triavoz_refresh`;

function isProtected(pathname: string): boolean {
  return PROTECTED.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

function contentSecurityPolicy(nonce: string, secure: boolean): string {
  const dev = process.env.NODE_ENV !== "production";
  const livekit =
    process.env.NEXT_PUBLIC_LIVEKIT_CONNECT_SRC ??
    "https://*.livekit.cloud wss://*.livekit.cloud";
  const local = dev ? " http://localhost:* ws://localhost:*" : "";
  const script = dev
    ? `'self' 'nonce-${nonce}' 'unsafe-eval'`
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`;
  return [
    "default-src 'self'",
    `script-src ${script}`,
    // Next injects small style tags/attributes; scripts stay nonce-gated.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${livekit} https://*.ingest.sentry.io${local}`,
    "media-src 'self' blob:",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    secure ? "upgrade-insecure-requests" : "",
  ]
    .filter(Boolean)
    .join("; ");
}

function withNonce(request: NextRequest): { nonce: string; csp: string } {
  const nonce = btoa(crypto.randomUUID());
  const secure =
    request.nextUrl.protocol === "https:" ||
    request.headers.get("x-forwarded-proto") === "https";
  return { nonce, csp: contentSecurityPolicy(nonce, secure) };
}

/**
 * Two small concerns that belong before rendering:
 *  1. `?lang=pt-BR|en` sets the locale cookie and redirects to the clean URL (hreflang).
 *  2. When the 15-minute access cookie is gone but the refresh cookie is alive, rotate tokens
 *     server-side so a long dashboard session does not bounce to /login.
 * Auth is still enforced by the `(app)` layout; this is a convenience, not the gate.
 */
export async function proxy(request: NextRequest) {
  const requested = request.nextUrl.searchParams.get("lang");
  if (requested && LOCALES.has(requested)) {
    const url = request.nextUrl.clone();
    url.searchParams.delete("lang");
    const response = NextResponse.redirect(url);
    response.cookies.set("locale", requested, {
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
      sameSite: "lax",
    });
    return response;
  }

  if (
    isProtected(request.nextUrl.pathname) &&
    !request.cookies.has(ACCESS_COOKIE) &&
    request.cookies.has(REFRESH_COOKIE)
  ) {
    try {
      const refresh = await fetch(`${API_ORIGIN}/api/v1/auth/refresh`, {
        method: "POST",
        headers: {
          cookie: request.headers.get("cookie") ?? "",
          accept: "application/json",
        },
        cache: "no-store",
      });
      if (refresh.ok) {
        const response = NextResponse.redirect(request.nextUrl);
        for (const cookie of refresh.headers.getSetCookie()) {
          response.headers.append("set-cookie", cookie);
        }
        return response;
      }
    } catch {
      /* fall through to the normal auth redirect */
    }
    const login = new URL("/login", request.url);
    login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
    return NextResponse.redirect(login);
  }

  const { nonce, csp } = withNonce(request);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  // Next reads this request header to add the nonce to its own parser-inserted scripts.
  requestHeaders.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|icon.svg|opengraph-image).*)"],
};
