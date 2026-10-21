import { NextResponse, type NextRequest } from "next/server";

const LOCALES = new Set(["pt-BR", "en"]);
const PROTECTED = ["/painel", "/chamadas", "/agendamentos", "/agente", "/configuracoes"];
const API_ORIGIN = (process.env.API_ORIGIN ?? "http://localhost:8000").replace(/\/$/, "");
const ACCESS_COOKIE = "triavoz_access";
const REFRESH_COOKIE = "triavoz_refresh";

function isProtected(pathname: string): boolean {
  return PROTECTED.some((path) => pathname === path || pathname.startsWith(`${path}/`));
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

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|icon.svg|opengraph-image).*)"],
};
