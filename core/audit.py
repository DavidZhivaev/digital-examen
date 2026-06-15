import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.middleware import _client_ip, _extract_auth_context

logger = logging.getLogger("api.audit")

MAX_BODY_SIZE = 16 * 1024

BODY_METHODS = {
    "POST",
    "PUT",
    "PATCH",
}

SKIP_PATHS = {
    "/api/health",
}

SENSITIVE_FIELDS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "secret",
    "api_key",
}

SUSPICIOUS_PATTERNS = (
    "union",
    "select",
    "drop",
    "insert",
    "update",
    "delete",
    "../",
    "<script",
    "--",
    "' or ",
    "\" or ",
)


def _mask_data(data):
    if isinstance(data, dict):
        result = {}

        for key, value in data.items():
            if key.casefold() in SENSITIVE_FIELDS:
                result[key] = "***"
            else:
                result[key] = _mask_data(value)

        return result

    if isinstance(data, list):
        return [_mask_data(item) for item in data]

    return data


def _is_suspicious(query, body):
    try:
        payload = json.dumps(
            {
                "query": query,
                "body": body,
            },
            ensure_ascii=False,
        ).lower()

        return any(x in payload for x in SUSPICIOUS_PATTERNS)

    except Exception:
        return False


class AuthAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            request.url.path in SKIP_PATHS
            or request.url.path.startswith("/docs")
            or request.url.path.startswith("/redoc")
            or request.url.path.startswith("/openapi")
        ):
            return await call_next(request)

        auth_context = _extract_auth_context(request)

        if auth_context is None:
            return await call_next(request)

        start = time.perf_counter()

        query_params = _mask_data(dict(request.query_params))

        body = None

        if request.method in BODY_METHODS:
            content_type = request.headers.get("content-type", "")

            if "application/json" in content_type:
                try:
                    raw = await request.body()

                    if raw:
                        if len(raw) <= MAX_BODY_SIZE:
                            body = json.loads(
                                raw.decode(errors="replace")
                            )

                            body = _mask_data(body)

                        else:
                            body = "<too_large>"

                        async def receive():
                            return {
                                "type": "http.request",
                                "body": raw,
                                "more_body": False,
                            }

                        request._receive = receive

                except Exception:
                    body = "<invalid_json>"

        response = None

        try:
            response = await call_next(request)
            return response

        finally:
            duration_ms = round(
                (time.perf_counter() - start) * 1000,
                2,
            )

            log_data = {
                    "user_id": auth_context.get("user_id"),
                    "person_id": auth_context.get("person_id"),
                    "role": auth_context.get("role"),
                    "session_id": auth_context.get("session_id"),

                    "service": "api",
                    "env": "prod",

                    "http_method": request.method,
                    "http_path": request.url.path,

                    "query_params": json.dumps(query_params, ensure_ascii=False),
                    "request_body": json.dumps(body, ensure_ascii=False),

                    "http_status": (
                        response.status_code
                        if response
                        else 500
                    ),
                    "request_id": str(uuid.uuid4()),
                    "request_body_size": len(raw) if raw else 0,

                    "duration_ms": duration_ms,

                    "client_ip": _client_ip(request),
                    "user_agent": request.headers.get(
                        "user-agent"
                    ),

                    "suspicious": _is_suspicious(
                        query_params,
                        body,
                    ),
                }

            logger.info(json.dumps(
                log_data, ensure_ascii=False
            ))