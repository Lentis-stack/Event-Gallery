# ============================================================
# Lentis Gallery — Rate Limiter
# ============================================================
# Redis-backed sliding window rate limiter for production.
# Falls back to in-memory for development (no Redis required).
#
# Supports:
#   - Per-IP rate limiting (login, guest registration)
#   - Per-IP-per-event rate limiting (media upload)
#   - Configurable limits via environment variables
#
# Redis keys use a TTL equal to the window, so expired entries
# are automatically cleaned up.
# ============================================================

import logging
import time
import threading
from collections import defaultdict, deque

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# In-memory fallback (development / no Redis)
# ============================================================

_failures: dict[str, deque] = defaultdict(deque)
_lockouts: dict[str, float] = {}
_rate_limits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _client_key(ip: str | None) -> str:
    return ip or "unknown"


# ============================================================
# Login rate limiting (SEC-008) — in-memory + optional Redis
# ============================================================

def is_locked_out(ip: str | None) -> bool:
    """Return True if the client is currently locked out."""
    key = _client_key(ip)
    with _lock:
        until = _lockouts.get(key, 0)
        now = time.time()
        if now < until:
            return True
        if until:
            _lockouts.pop(key, None)
        return False


def record_failure(ip: str | None) -> bool:
    """Record a failed login attempt. Returns True if now locked out."""
    key = _client_key(ip)
    now = time.time()
    with _lock:
        q = _failures[key]
        while q and now - q[0] > settings.LOGIN_WINDOW_SECONDS:
            q.popleft()
        q.append(now)
        if len(q) >= settings.LOGIN_MAX_ATTEMPTS:
            _lockouts[key] = now + settings.LOGIN_LOCKOUT_SECONDS
            _failures.pop(key, None)
            return True
        return False


def reset_failures(ip: str | None) -> None:
    """Clear recorded failures (called on successful login)."""
    key = _client_key(ip)
    with _lock:
        _failures.pop(key, None)
        _lockouts.pop(key, None)


# ============================================================
# General rate limiting (SEC-005/006) — sliding window
# ============================================================

def _get_redis():
    """Try to get a Redis connection. Returns None if unavailable."""
    try:
        from redis import Redis
        conn = Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        conn.ping()
        return conn
    except Exception:
        return None


_redis_client = None
_redis_checked = False


def _redis():
    """Get or lazily initialize the Redis client."""
    global _redis_client, _redis_checked
    if not _redis_checked:
        _redis_checked = True
        _redis_client = _get_redis()
        if _redis_client:
            logger.info("Rate limiter: using Redis backend")
        else:
            logger.info("Rate limiter: using in-memory backend (Redis unavailable)")
    return _redis_client


def check_rate_limit(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """
    Check if a rate limit has been exceeded.

    Args:
        key: Unique identifier (e.g., "guest_reg:192.168.1.1")
        max_requests: Maximum allowed requests in the window
        window_seconds: Window duration in seconds

    Returns:
        (allowed, retry_after_seconds)
    """
    r = _redis()

    if r:
        return _check_rate_limit_redis(r, key, max_requests, window_seconds)
    else:
        return _check_rate_limit_memory(key, max_requests, window_seconds)


def _check_rate_limit_redis(r, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """Redis-backed sliding window rate limit."""
    now = time.time()
    redis_key = f"ratelimit:{key}"

    pipe = r.pipeline()
    # Remove entries outside the window
    pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
    # Count current entries
    pipe.zcard(redis_key)
    results = pipe.execute()

    current_count = results[1]

    if current_count >= max_requests:
        # Get the oldest entry to calculate retry-after
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        if oldest:
            retry_after = int(window_seconds - (now - oldest[0][1])) + 1
        else:
            retry_after = window_seconds
        return False, max(1, retry_after)

    # Add this request
    pipe = r.pipeline()
    pipe.zadd(redis_key, {f"{now}:{id(key)}": now})
    pipe.expire(redis_key, window_seconds)
    pipe.execute()

    return True, 0


def _check_rate_limit_memory(key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    """In-memory sliding window rate limit (fallback for development)."""
    now = time.time()
    with _lock:
        q = _rate_limits[key]
        # Drop old entries
        while q and now - q[0] > window_seconds:
            q.popleft()

        if len(q) >= max_requests:
            retry_after = int(window_seconds - (now - q[0])) + 1
            return False, max(1, retry_after)

        q.append(now)
        return True, 0


def check_guest_registration_rate_limit(ip: str, event_slug: str) -> tuple[bool, int]:
    """Rate limit for guest registration: per IP per event."""
    key = f"guest_reg:{_client_key(ip)}:{event_slug}"
    return check_rate_limit(key, settings.RATE_LIMIT_GUEST_REGISTRATION, 3600)


def check_media_upload_rate_limit(ip: str, event_slug: str) -> tuple[bool, int]:
    """Rate limit for media uploads: per IP per event."""
    key = f"media_upload:{_client_key(ip)}:{event_slug}"
    return check_rate_limit(key, settings.RATE_LIMIT_EVENT_MEDIA_UPLOAD, 3600)


# ============================================================
# Reset (for tests)
# ============================================================

def reset_all_rate_limits() -> None:
    """Clear all in-memory rate limit state. Used by tests."""
    with _lock:
        _failures.clear()
        _lockouts.clear()
        _rate_limits.clear()
