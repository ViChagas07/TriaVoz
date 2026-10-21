import time

import jwt
import pytest

from triavoz.infrastructure.security import hmac_auth
from triavoz.infrastructure.security.passwords import hash_password, verify_password
from triavoz.infrastructure.security.tokens import (
    Principal,
    create_access_token,
    decode_access_token,
)
from triavoz.shared_kernel.rate_limit import TokenBucket

SECRET = "unit-test-secret"


def test_hmac_roundtrip_and_tamper_detection() -> None:
    ts = int(time.time())
    body = b'{"clinic_id":"x"}'
    nonce = "nonce-1"
    sig = hmac_auth.sign(SECRET, ts, body, nonce)
    assert hmac_auth.verify(SECRET, str(ts), sig, body, tolerance_seconds=60, nonce_header=nonce)
    assert not hmac_auth.verify(
        SECRET, str(ts), sig, body + b" ", tolerance_seconds=60, nonce_header=nonce
    )
    assert not hmac_auth.verify(
        "other-secret", str(ts), sig, body, tolerance_seconds=60, nonce_header=nonce
    )
    assert not hmac_auth.verify(SECRET, None, sig, body, tolerance_seconds=60)
    assert not hmac_auth.verify(
        SECRET, "not-a-number", sig, body, tolerance_seconds=60, nonce_header=nonce
    )
    # The nonce is part of the signed message: swapping it invalidates the signature.
    assert not hmac_auth.verify(
        SECRET, str(ts), sig, body, tolerance_seconds=60, nonce_header="other-nonce"
    )


def test_hmac_rejects_replayed_old_timestamp() -> None:
    ts = int(time.time()) - 3600
    body = b"{}"
    nonce = "nonce-2"
    sig = hmac_auth.sign(SECRET, ts, body, nonce)
    assert not hmac_auth.verify(
        SECRET, str(ts), sig, body, tolerance_seconds=60, nonce_header=nonce
    )


def test_password_hash_verifies_only_the_right_password() -> None:
    h = hash_password("correct horse")
    assert h.startswith("$argon2")
    assert verify_password(h, "correct horse")
    assert not verify_password(h, "wrong")
    assert not verify_password("not-a-hash", "anything")


def test_access_token_roundtrip_and_rejects_garbage() -> None:
    import uuid

    p = Principal(uuid.uuid4(), uuid.uuid4(), "attendant")
    assert decode_access_token(create_access_token(p)) == p
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("garbage")


def test_token_bucket_burst_then_refill() -> None:
    b = TokenBucket(capacity=3, refill_per_second=1)
    assert [b.allow(now=0.0) for _ in range(4)] == [True, True, True, False]
    assert b.allow(now=1.0) is True  # one token refilled
    assert b.allow(now=1.0) is False
    assert b.allow(now=100.0) is True  # capped at capacity, not unbounded
