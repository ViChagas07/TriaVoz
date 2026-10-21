from __future__ import annotations

from datetime import datetime

from fastapi import Response

from triavoz.config import Settings, get_settings

# The refresh token is httpOnly + SameSite=Lax; scoping it to "/" lets the Next.js proxy rotate
# it after the 15-minute access cookie disappears instead of bouncing the user to /login.
REFRESH_PATH = "/"


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, refresh_expires: datetime
) -> None:
    s: Settings = get_settings()
    response.set_cookie(
        s.access_cookie_name,
        access_token,
        max_age=s.jwt_access_ttl_seconds,
        path="/",
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
    )
    response.set_cookie(
        s.refresh_cookie_name,
        refresh_token,
        expires=refresh_expires,
        path=REFRESH_PATH,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
    )


def clear_auth_cookies(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.access_cookie_name, path="/")
    response.delete_cookie(s.refresh_cookie_name, path=REFRESH_PATH)
