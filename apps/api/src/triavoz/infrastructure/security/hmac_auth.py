"""HMAC-SHA256 request signing between the voice worker and the API.

signature = HMAC(secret, f"{timestamp}.{raw_body}"), sent in the headers
X-Triavoz-Timestamp and X-Triavoz-Signature.
Constant-time comparison + timestamp tolerance (replay window).
Idempotency is handled per endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import time

TIMESTAMP_HEADER = "X-Triavoz-Timestamp"
SIGNATURE_HEADER = "X-Triavoz-Signature"


def sign(secret: str, timestamp: int, body: bytes) -> str:
    msg = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def verify(
    secret: str,
    timestamp_header: str | None,
    signature_header: str | None,
    body: bytes,
    tolerance_seconds: int,
    now: float | None = None,
) -> bool:
    if not timestamp_header or not signature_header:
        return False
    try:
        ts = int(timestamp_header)
    except ValueError:
        return False
    current = time.time() if now is None else now
    if abs(current - ts) > tolerance_seconds:
        return False
    expected = sign(secret, ts, body)
    return hmac.compare_digest(expected, signature_header)
