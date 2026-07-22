"""Process-local + optional Redis cache for hot read paths (auth actor, summaries)."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_memory: dict[str, tuple[float, str]] = {}
_lock = threading.RLock()
_redis_client: Any | None = None
_redis_disabled = False


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _deserialize(raw: str) -> Any:
    return json.loads(raw)


def _redis():
    global _redis_client, _redis_disabled
    if _redis_disabled or not settings.redis_url:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis

        client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.4,
            socket_timeout=0.4,
            retry_on_timeout=False,
        )
        client.ping()
        _redis_client = client
        logger.info("Redis cache connected")
        return _redis_client
    except Exception as exc:  # noqa: BLE001 — cache must never break requests
        _redis_disabled = True
        _redis_client = None
        logger.warning("Redis unavailable, falling back to in-process cache: %s", exc)
        return None


def cache_get(key: str) -> Any | None:
    client = _redis()
    if client is not None:
        try:
            raw = client.get(key)
            if raw is not None:
                return _deserialize(raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis get failed for %s: %s", key, exc)

    now = time.monotonic()
    with _lock:
        entry = _memory.get(key)
        if not entry:
            return None
        expires_at, raw = entry
        if expires_at <= now:
            _memory.pop(key, None)
            return None
        return _deserialize(raw)


def cache_set(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    ttl = max(1, int(ttl_seconds if ttl_seconds is not None else settings.cache_default_ttl_seconds))
    raw = _serialize(value)
    client = _redis()
    if client is not None:
        try:
            client.setex(key, ttl, raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis set failed for %s: %s", key, exc)

    with _lock:
        _memory[key] = (time.monotonic() + ttl, raw)
        if len(_memory) > 4096:
            # Drop cheapest expired / oldest-ish entries under pressure.
            now = time.monotonic()
            stale = [k for k, (exp, _) in _memory.items() if exp <= now]
            for stale_key in stale[:512]:
                _memory.pop(stale_key, None)


def cache_delete(key: str) -> None:
    client = _redis()
    if client is not None:
        try:
            client.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis delete failed for %s: %s", key, exc)
    with _lock:
        _memory.pop(key, None)


def cache_delete_prefix(prefix: str) -> None:
    client = _redis()
    if client is not None:
        try:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=f"{prefix}*", count=200)
                if keys:
                    client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis delete_prefix failed for %s: %s", prefix, exc)
    with _lock:
        for key in [k for k in _memory if k.startswith(prefix)]:
            _memory.pop(key, None)
