"""Opaque browser caller identity for the public voice demo.

The public `/api/v1/voice/session` cannot trust a browser-supplied phone number as proof of
ownership. Web calls receive an httpOnly random identity cookie; only its SHA-256 hash is stored
with the call. Phone calls use the provider-verified caller number instead.
"""

from __future__ import annotations

import hashlib
import re
import secrets

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")


def new_caller_identity() -> str:
    return secrets.token_urlsafe(32)


def is_valid_caller_identity(value: str | None) -> bool:
    return bool(value and _TOKEN_RE.fullmatch(value))


def caller_identity_hash(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()
