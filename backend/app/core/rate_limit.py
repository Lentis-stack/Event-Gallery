# ============================================================
# Lentis Gallery — Login Rate Limiter
# ------------------------------------------------------------
# Protects the login endpoint from brute-force attacks.
#
# HOW IT WORKS (simple, for local dev):
#   We keep an in-memory dict keyed by a client identifier
#   (falling back to "unknown"). It records timestamps of failed
#   login attempts. If too many failures happen within a window,
#   the client is locked out for a period.
#
# WHY IN-MEMORY?
#   For local development and single-process deployment this is
#   simple and has no extra dependencies (no Redis). For a
#   multi-instance production deployment, this state would need to
#   live in a shared store (e.g. Redis) so all instances see the
#   same counter. That is documented as a production note.
#
# SECURITY NOTE:
#   We key on IP address. This is a reasonable first defense but can
#   be bypassed with distributed attacks; production should also add
#   per-account throttling and consider a CDN/edge rate limiter.
# ============================================================

import threading
import time
from collections import defaultdict, deque

from app.core.config import settings

# client_key -> deque of failure timestamps
_failures: dict[str, deque] = defaultdict(deque)
# client_key -> lockout_until_timestamp
_lockouts: dict[str, float] = {}

# A lock so concurrent requests don't corrupt the dicts.
_lock = threading.Lock()


def _client_key(ip: str | None) -> str:
    return ip or "unknown"


def is_locked_out(ip: str | None) -> bool:
    """Return True if the client is currently locked out."""
    key = _client_key(ip)
    with _lock:
        until = _lockouts.get(key, 0)
        now = time.time()
        if now < until:
            return True
        # Lockout expired — clear it.
        if until:
            _lockouts.pop(key, None)
        return False


def record_failure(ip: str | None) -> bool:
    """
    Record a failed login attempt. Returns True if the client is
    now locked out (too many failures in the window).
    """
    key = _client_key(ip)
    now = time.time()
    with _lock:
        q = _failures[key]
        # Drop attempts older than the window.
        while q and now - q[0] > settings.LOGIN_WINDOW_SECONDS:
            q.popleft()
        q.append(now)
        if len(q) >= settings.LOGIN_MAX_ATTEMPTS:
            # Lock out for LOGIN_LOCKOUT_SECONDS.
            _lockouts[key] = now + settings.LOGIN_LOCKOUT_SECONDS
            _failures.pop(key, None)  # reset the counter
            return True
        return False


def reset_failures(ip: str | None) -> None:
    """Clear recorded failures (called on successful login)."""
    key = _client_key(ip)
    with _lock:
        _failures.pop(key, None)
        _lockouts.pop(key, None)
