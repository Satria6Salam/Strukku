from collections import deque
from threading import Lock
from time import monotonic

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError


class LoginRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _key(self, kind: str, value: str) -> str:
        return f"{kind}:{value.strip().lower()}"

    def _prune(self, events: deque[float], now: float, window_seconds: float) -> None:
        while events and now - events[0] >= window_seconds:
            events.popleft()

    def check(self, email: str, ip_address: str) -> None:
        now = monotonic()
        window_seconds = settings.LOGIN_RATE_WINDOW_MINUTES * 60
        keys = (self._key("email", email), self._key("ip", ip_address))
        with self._lock:
            retry_after = 0
            for key in keys:
                events = self._events.setdefault(key, deque())
                self._prune(events, now, window_seconds)
                if len(events) >= settings.LOGIN_RATE_LIMIT:
                    retry_after = max(retry_after, int(window_seconds - (now - events[0])) + 1)
            if retry_after:
                raise TooManyRequestsError(
                    "Terlalu banyak percobaan login. Coba lagi setelah beberapa saat.",
                    retry_after=retry_after,
                )

    def record_failure(self, email: str, ip_address: str) -> None:
        now = monotonic()
        window_seconds = settings.LOGIN_RATE_WINDOW_MINUTES * 60
        with self._lock:
            for key in (self._key("email", email), self._key("ip", ip_address)):
                events = self._events.setdefault(key, deque())
                self._prune(events, now, window_seconds)
                events.append(now)

    def record_success(self, email: str, ip_address: str) -> None:
        with self._lock:
            self._events.pop(self._key("email", email), None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


login_rate_limiter = LoginRateLimiter()
