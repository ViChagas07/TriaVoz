"""Pure Token Bucket (no I/O). The Redis adapter implements the same semantics atomically."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokenBucket:
    capacity: float
    refill_per_second: float
    tokens: float | None = None
    updated_at: float | None = None

    def allow(self, now: float, cost: float = 1.0) -> bool:
        if self.tokens is None or self.updated_at is None:
            self.tokens, self.updated_at = self.capacity, now
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False
