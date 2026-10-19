"""Atomic Token Bucket in Redis (Lua). Same semantics as shared_kernel.rate_limit.TokenBucket.

Keys MUST carry the tenant prefix, e.g. `clinic:{clinic_id}:rl:caller:{e164}`.
TODO(verify-docs): confirm redis-py `register_script` usage against the installed version.
"""

from __future__ import annotations

from redis.asyncio import Redis

_LUA = """
local key      = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill   = tonumber(ARGV[2])
local cost     = tonumber(ARGV[3])
local ttl      = tonumber(ARGV[4])
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then tokens = capacity; ts = now end
tokens = math.min(capacity, tokens + math.max(0, now - ts) * refill)
local allowed = 0
if tokens >= cost then tokens = tokens - cost; allowed = 1 end
redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, ttl)
return allowed
"""


class RedisTokenBucket:
    def __init__(self, redis: Redis) -> None:
        self._script = redis.register_script(_LUA)

    async def allow(
        self, key: str, capacity: float, refill_per_second: float, cost: float = 1.0
    ) -> bool:
        ttl = int(max(60, capacity / max(refill_per_second, 1e-6) * 2))
        result = await self._script(keys=[key], args=[capacity, refill_per_second, cost, ttl])
        return bool(result)
