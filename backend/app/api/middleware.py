import time
import uuid
from typing import Callable, Dict, List, Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches defensive HTTP security headers to all API responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["X-XSS-Protection"] = "0"
            response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"

            # Content Security Policy (allows Swagger UI & ReDoc on docs endpoints while protecting API)
            if not (request.url.path.startswith("/docs") or request.url.path.startswith("/redoc")):
                response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

            # Strict-Transport-Security (Only in production or when explicitly enabled)
            if settings.is_production or settings.STRICT_TRANSPORT_SECURITY_ENABLED:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Protects API against oversized payloads (DoS mitigation).
    Rejects requests exceeding MAX_REQUEST_BODY_BYTES with HTTP 413.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length_str = request.headers.get("content-length")
        if content_length_str:
            try:
                content_length = int(content_length_str)
                # Allow higher limit for PCAP upload/replay if applicable
                max_allowed = (
                    settings.MAX_PCAP_FILE_BYTES
                    if "/monitoring/" in request.url.path
                    else settings.MAX_REQUEST_BODY_BYTES
                )
                if content_length > max_allowed:
                    request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
                    logger.warning(
                        f"[{request_id}] Payload too large: {content_length} bytes exceeds limit of {max_allowed} bytes on {request.method} {request.url.path}"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request payload size of {content_length} bytes exceeds maximum allowed limit ({max_allowed} bytes).",
                                "status_code": 413,
                                "request_id": request_id,
                            },
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


class GeneralRateLimiter:
    """
    Sliding window in-memory rate limiter tracking requests per client IP.
    """

    def __init__(self, requests_per_minute: Optional[int] = None, window_seconds: int = 60):
        self._requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}

    @property
    def requests_per_minute(self) -> int:
        if self._requests_per_minute is not None:
            return self._requests_per_minute
        return getattr(settings, "API_RATE_LIMIT_DEFAULT_PER_MINUTE", 120)

    def _cleanup_old(self, key: str, now: float) -> None:
        if key in self._requests:
            threshold = now - self.window_seconds
            self._requests[key] = [t for t in self._requests[key] if t > threshold]
            if not self._requests[key]:
                del self._requests[key]

    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        self._cleanup_old(key, now)
        reqs = self._requests.get(key, [])
        if len(reqs) >= self.requests_per_minute:
            oldest = reqs[0]
            remaining = int(self.window_seconds - (now - oldest))
            return True, max(1, remaining)
        return False, 0

    def record_request(self, key: str) -> None:
        now = time.time()
        self._cleanup_old(key, now)
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append(now)

    def reset(self) -> None:
        self._requests.clear()


general_api_rate_limiter = GeneralRateLimiter()


class ApiRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Global sliding window rate limiting middleware per client IP.
    Exempts health probes and API docs from rate limiting.
    """

    EXEMPT_PATHS = {"/health", "/api/health", "/api/v1/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Do not rate limit exempt monitoring/documentation paths
        if not settings.API_RATE_LIMIT_ENABLED or path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        is_blocked, retry_after = general_api_rate_limiter.is_rate_limited(client_ip)

        if is_blocked:
            request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
            logger.warning(f"[{request_id}] Rate limit exceeded for IP {client_ip} on {request.method} {path}")
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "success": False,
                    "error": {
                        "code": "TOO_MANY_REQUESTS",
                        "message": f"Too many requests. Please slow down and retry in {retry_after} seconds.",
                        "status_code": 429,
                        "request_id": request_id,
                    },
                },
            )

        general_api_rate_limiter.record_request(client_ip)
        return await call_next(request)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns or propagates a unique correlation Request ID (X-Request-ID),
    measures execution duration, and logs structured access metrics.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate Request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req-{uuid.uuid4().hex[:12]}"

        # Store in request state for access in route handlers and error loggers
        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                f"[{request_id}] Unhandled exception on {request.method} {request.url.path} "
                f"after {process_time:.2f}ms: {e}",
                exc_info=True
            )
            raise e

        process_time = (time.perf_counter() - start_time) * 1000.0

        # Attach headers
        if settings.REQUEST_ID_ENABLED:
            response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # Structured log
        if not request.url.path.endswith("/health") and not request.url.path.endswith("/openapi.json"):
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"Status: {response.status_code} ({process_time:.2f}ms)"
            )

        return response

