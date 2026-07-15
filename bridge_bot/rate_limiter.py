"""RateLimiter — single class with pluggable backend.

Replaces the dual in-memory rate limiters in validators.py and routes/auth.py.
Backend is swappable: DictBackend for dev/test, RedisBackend for production.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class RateLimitBackend(ABC):
    """Interface for rate limit storage."""

    @abstractmethod
    def get_timestamps(self, key: str) -> List[float]:
        """Return list of timestamps for the given key."""
        ...

    @abstractmethod
    def add_timestamp(self, key: str, timestamp: float) -> None:
        """Record a timestamp for the given key."""
        ...

    @abstractmethod
    def cleanup(self, key: str, cutoff: float) -> None:
        """Remove timestamps older than cutoff for the given key."""
        ...


class DictBackend(RateLimitBackend):
    """In-memory dict backend. Works for single-worker deployments."""

    def __init__(self) -> None:
        self._store: Dict[str, List[float]] = {}

    def get_timestamps(self, key: str) -> List[float]:
        return self._store.get(key, [])

    def add_timestamp(self, key: str, timestamp: float) -> None:
        self._store.setdefault(key, []).append(timestamp)

    def cleanup(self, key: str, cutoff: float) -> None:
        if key in self._store:
            self._store[key] = [t for t in self._store[key] if t > cutoff]


class RedisBackend(RateLimitBackend):
    """Redis backend. For multi-worker deployments."""

    def __init__(self, redis_client, prefix: str = "rl:") -> None:
        self._redis = redis_client
        self._prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get_timestamps(self, key: str) -> List[float]:
        raw = self._redis.lrange(self._key(key), 0, -1)
        return [float(t) for t in raw]

    def add_timestamp(self, key: str, timestamp: float) -> None:
        rk = self._key(key)
        self._redis.rpush(rk, str(timestamp))
        self._redis.expire(rk, 3600)

    def cleanup(self, key: str, cutoff: float) -> None:
        rk = self._key(key)
        timestamps = self.get_timestamps(key)
        if timestamps:
            valid = [str(t) for t in timestamps if t > cutoff]
            self._redis.delete(rk)
            if valid:
                self._redis.rpush(rk, *valid)
                self._redis.expire(rk, 3600)


class RateLimiter:
    """Configurable rate limiter with pluggable backend.

    Usage:
        limiter = RateLimiter(window_seconds=1.0, max_hits=1)
        if limiter.allow("my_key"):
            # proceed
        else:
            # rate limited

        login_limiter = RateLimiter(
            window_seconds=300, max_hits=10,
            backend=DictBackend(),
        )
    """

    def __init__(
        self,
        window_seconds: float,
        max_hits: int,
        backend: Optional[RateLimitBackend] = None,
    ) -> None:
        self.window_seconds = window_seconds
        self.max_hits = max_hits
        self._backend = backend or DictBackend()

    def allow(self, key: str) -> bool:
        """Check if the key is allowed. Records the attempt if allowed."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._backend.cleanup(key, cutoff)

        timestamps = self._backend.get_timestamps(key)
        if len(timestamps) >= self.max_hits:
            return False

        self._backend.add_timestamp(key, now)
        return True

    def reset(self, key: str) -> None:
        """Clear all timestamps for a key."""
        self._backend.cleanup(key, float("inf"))

    def reset_all(self) -> None:
        """Clear all stored timestamps. Useful for tests."""
        if isinstance(self._backend, DictBackend):
            self._backend._store.clear()
