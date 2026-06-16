import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.security import decode_token

logger = logging.getLogger("api.requests")

def client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def extract_auth_context(request: Request) -> dict | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None

    try:
        payload = decode_token(auth[7:].strip())
    except Exception:
        return None

    if payload.get("type") != "access":
        return None

    return {
        "user_id": payload.get("sub"),
        "person_id": payload.get("person_id"),
        "role": payload.get("role"),
        "session_id": payload.get("sid"),
    }


class AuthRequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        auth_context = extract_auth_context(request)
        response = await call_next(request)

        if auth_context is not None:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info({
                "event": "request",

                "user_id": auth_context["user_id"],
                "person_id": auth_context["person_id"],
                "role": auth_context["role"],
                "session_id": auth_context["session_id"],

                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,

                "ip": client_ip(request),
            })

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
