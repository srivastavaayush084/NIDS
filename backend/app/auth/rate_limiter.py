import time
from typing import Dict, List, Tuple
from backend.app.core.config import settings


class LoginRateLimiter:
    """
    Sliding window in-memory rate limiter tracking failed authentication attempts.
    Blocks brute-force dictionary attacks per client IP or account identifier.
    """

    def __init__(
        self,
        max_attempts: int = settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS,
        window_seconds: int = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # key -> list of failure timestamps
        self._failures: Dict[str, List[float]] = {}

    def _cleanup_old(self, key: str, now: float) -> None:
        if key in self._failures:
            threshold = now - self.window_seconds
            self._failures[key] = [t for t in self._failures[key] if t > threshold]
            if not self._failures[key]:
                del self._failures[key]

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if client is currently rate limited.
        Returns: (is_blocked, seconds_remaining)
        """
        now = time.time()
        self._cleanup_old(key, now)
        attempts = self._failures.get(key, [])
        if len(attempts) >= self.max_attempts:
            oldest = attempts[0]
            remaining = int(self.window_seconds - (now - oldest))
            return True, max(1, remaining)
        return False, 0

    def record_failure(self, key: str) -> None:
        """Record an authentication failure timestamp for the given key."""
        now = time.time()
        self._cleanup_old(key, now)
        if key not in self._failures:
            self._failures[key] = []
        self._failures[key].append(now)

    def record_success(self, key: str) -> None:
        """Clear failed attempts upon successful login."""
        if key in self._failures:
            del self._failures[key]

    def reset(self) -> None:
        """Reset all rate limiter state (useful for test isolation)."""
        self._failures.clear()


login_rate_limiter = LoginRateLimiter()
