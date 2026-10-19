"""Short-lived JWT access tokens.

The clinic id for tenant context comes ONLY from a verified token.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import jwt

from triavoz.config import get_settings

ALGORITHM = "HS256"


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    clinic_id: UUID
    role: str  # 'admin' | 'attendant'


def create_access_token(principal: Principal) -> str:
    s = get_settings()
    now = int(time.time())
    claims = {
        "sub": str(principal.user_id),
        "cid": str(principal.clinic_id),
        "role": principal.role,
        "typ": "access",
        "iat": now,
        "exp": now + s.jwt_access_ttl_seconds,
    }
    return jwt.encode(claims, s.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Principal:
    s = get_settings()
    claims = jwt.decode(
        token,
        s.jwt_secret.get_secret_value(),
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub", "cid", "role", "typ"]},
    )
    if claims.get("typ") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return Principal(UUID(claims["sub"]), UUID(claims["cid"]), str(claims["role"]))
