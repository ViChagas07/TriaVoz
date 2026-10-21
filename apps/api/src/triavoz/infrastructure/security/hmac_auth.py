"""HMAC-SHA256 request signing between the voice worker and the API.

signature = HMAC(secret, f"{timestamp}.{nonce}." + raw_body), sent with:
  X-Triavoz-Timestamp, X-Triavoz-Nonce, X-Triavoz-Signature

The nonce is signed and single-use (Redis, with a process-local fallback), so a captured request
cannot be replayed inside the timestamp window. Constant-time comparison + timestamp tolerance.
"""

from __future__ import annotations

import hashlib
import hmac
import time

TIMESTAMP_HEADER = "X-Triavoz-Timestamp"
NONCE_HEADER = "X-Triavoz-Nonce"
SIGNATURE_HEADER = "X-Triavoz-Signature"


def sign(secret: str, timestamp: int, body: bytes, nonce: str = "") -> str:
    msg = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify(
    secret: str,
    timestamp_header: str | None,
    signature_header: str | None,
    body: bytes,
    tolerance_seconds: int,
    now: float | None = None,
    nonce_header: str | None = None,
) -> bool:
    if not timestamp_header or not signature_header or not nonce_header:
        return False
    try:
        ts = int(timestamp_header)
    except ValueError:
        return False
    current = time.time() if now is None else now
    if abs(current - ts) > tolerance_seconds:
        return False
    expected = sign(secret, ts, body, nonce_header)
    return hmac.compare_digest(expected, signature_header)


def replay_key(nonce: str, signature: str) -> str:
    digest = hashlib.sha256(f"{nonce}:{signature}".encode()).hexdigest()
    return f"triavoz:hmac:replay:{digest}"
