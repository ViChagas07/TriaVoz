from __future__ import annotations

from functools import cached_property

from triavoz.infrastructure.security.passwords import hash_password, verify_password
from triavoz.infrastructure.security.tokens import (
    Principal,
    create_access_token,
    decode_access_token,
)


class Argon2PasswordHasher:
    @cached_property
    def dummy_hash(self) -> str:
        # Same work factor as a real hash so an unknown user is not obviously faster.
        return hash_password("triavoz-dummy-password-not-used")

    def hash(self, plain: str) -> str:
        return hash_password(plain)

    def verify(self, hashed: str, plain: str) -> bool:
        return verify_password(hashed, plain)


class JwtAccessTokenIssuer:
    def issue(self, principal: Principal) -> str:
        return create_access_token(principal)


def decode_principal(token: str) -> Principal:
    return decode_access_token(token)
