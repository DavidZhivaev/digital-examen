import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from core.config import settings

_attempts: dict[str, deque[float]] = defaultdict(deque)


def check_login_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
    max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS

    bucket = _attempts[ip]
    while bucket and bucket[0] <= now - window:
        bucket.popleft()

    if len(bucket) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток входа. Попробуйте позже.",
        )

    bucket.append(now)
