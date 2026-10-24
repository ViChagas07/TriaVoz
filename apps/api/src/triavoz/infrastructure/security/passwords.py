from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Explicit OWASP-aligned parameters (Argon2id, 64 MiB, 3 iterations, 4 lanes) so a library
# default change cannot silently weaken existing password hashes. Verify accepts older hashes.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(hashed: str, plain: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)
