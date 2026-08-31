"""
Async Redis connection management.

Mirrors db/session.py's approach: one process-wide connection pool created
at import time, reused across requests. redis-py's async client is itself
backed by a connection pool internally, so we don't need to hand-roll
pooling logic the way older Redis clients sometimes required.

We deliberately keep this module free of any *business* logic (no cache
keys, no TTLs, no serialization). Its only job is "give me a working Redis
connection." Where and how it's used is a decision for the service layer,
same separation of concerns you already have between repos and services.
"""

import redis.asyncio as redis

from url_shortener.core.config import settings

# `redis.asyncio.from_url` returns a Redis client backed by a connection
# pool (default max 2**31 connections, effectively unbounded — the pool
# grows lazily and reuses idle connections). This is analogous to
# `create_async_engine()` for Postgres: cheap to call once at import time,
# and each Redis command borrows a connection from the pool, uses it, and
# returns it — you don't manually acquire/release like a raw socket.
#
# decode_responses=True means Redis returns Python `str` instead of raw
# `bytes` for command results — this saves us from having to call
# `.decode("utf-8")` everywhere we read a cached value.

redis_client = redis.from_url(settings.REDIS_URL, decode_responses = True)