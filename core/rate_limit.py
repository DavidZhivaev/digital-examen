import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

from core.config import settings
from core.security import decode_token

HEALTH_SUFFIXES = ("/health",)
EXEMPT_PATHS = {
    "/api/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
} # на них решиь не стаивть лимиты, потому что смысла в этом нет


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        self._cleanup(now)

        bucket = self._buckets[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - bucket[0])) + 1
            return False, max(1, retry_after)

        bucket.append(now)
        return True, 0

    def cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 120:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds
        stale_keys = []
        for key, bucket in self._buckets.items():
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                stale_keys.append(key)
        for key in stale_keys:
            del self._buckets[key]


ip_limiter = SlidingWindowLimiter(
    settings.RATE_LIMIT_IP_MAX_REQUESTS,
    settings.RATE_LIMIT_IP_WINDOW_SECONDS,
)
user_limiter = SlidingWindowLimiter(
    settings.RATE_LIMIT_USER_MAX_REQUESTS,
    settings.RATE_LIMIT_USER_WINDOW_SECONDS,
)
login_limiter = SlidingWindowLimiter(
    settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
    settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
)


def client_ip(request):
    if request.client:
        return request.client.host
    return "unknown"


def extract_user_id(request: Request | StarletteRequest) -> str | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(auth[7:].strip())
    except Exception:
        return None
    if payload.get("type") != "access":
        return None
    return str(payload.get("sub"))


def is_exempt(path: str) -> bool: # простая оьертка, возвращает есть ли эндпоинт в белом списке для рэйт лимита
    if path in EXEMPT_PATHS:
        return True
    return any(path.endswith(suffix) for suffix in HEALTH_SUFFIXES)


def check_login_rate_limit(request: Request) -> None:
    allowed, retry_after = login_limiter.check(f"login:{client_ip(request)}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        path = request.url.path
        if is_exempt(path):
            return await call_next(request)

        user_id = extract_user_id(request)

        ip_key = f"ip:{client_ip(request)}"
        ip_allowed, ip_retry = ip_limiter.check(ip_key)

        if user_id:
            user_allowed, user_retry = user_limiter.check(f"user:{user_id}")

            allowed = ip_allowed and user_allowed
            retry_after = max(ip_retry, user_retry)
        else:
            allowed = ip_allowed
            retry_after = ip_retry

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Слишком много запросов. Попробуйте позже."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
