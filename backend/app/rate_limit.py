from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from app.config import settings


class SlidingWindowRateLimiter:
    """Small in-process limiter for the single-instance deployment model."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, maximum: int, window_seconds: int = 60) -> None:
        if maximum <= 0:
            return
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= maximum:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "rate_limit_exceeded",
                        "message": "Zu viele Anfragen. Bitte später erneut versuchen.",
                        "retry_after_seconds": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


limiter = SlidingWindowRateLimiter()


def _request_origin(request: Request) -> str:
    # Rate-limit keys are never logged. X-Forwarded-For is intentionally not
    # trusted here; the deployment proxy and application share one network.
    return request.client.host if request.client else "local"


def enforce_login_rate_limit(request: Request) -> None:
    limiter.check(
        f"login:{_request_origin(request)}", settings.login_rate_limit_per_minute
    )


def enforce_smtp_rate_limit(request: Request) -> None:
    limiter.check(
        f"smtp:{_request_origin(request)}", settings.smtp_rate_limit_per_minute
    )
