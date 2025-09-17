# app/core/middleware.py
"""
Enhanced logging middleware with comprehensive request tracking and performance monitoring.

This middleware provides:
- Automatic request/response logging with correlation IDs
- Performance monitoring with detailed metrics
- Error tracking with stack traces
- Security event logging
- Integration with OpenTelemetry tracing
"""

import time
import uuid
from typing import Dict, Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.core.logging import get_logger, set_correlation_context
from app.config import settings


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced logging middleware with comprehensive request tracking.

    Features:
    - Request/response correlation with unique IDs
    - Performance metrics collection
    - Automatic error logging with stack traces
    - Security event detection
    - Query parameter and header sanitization
    - Body size monitoring
    """

    # Sensitive headers to redact
    SENSITIVE_HEADERS = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-auth-token",
        "x-access-token",
        "x-refresh-token",
        "authorization",
    }

    # Endpoints to exclude from verbose logging (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/ready",
        "/live",
        "/_internal",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app, exclude_paths: Optional[set] = None):
        super().__init__(app)
        self.exclude_paths = self.EXCLUDED_PATHS | (exclude_paths or set())

    async def dispatch(self, request: Request, call_next):
        # Generate correlation IDs
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Set correlation context
        set_correlation_context(request_id=request_id, correlation_id=correlation_id)

        # Start OpenTelemetry span for request tracing
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}", kind=trace.SpanKind.SERVER
        ) as span:
            # Add span attributes
            span.set_attributes(
                {
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.route": request.url.path,
                    "http.user_agent": request.headers.get("user-agent", ""),
                    "http.client_ip": self._get_client_ip(request),
                    "request.id": request_id,
                    "correlation.id": correlation_id,
                }
            )

            # Skip verbose logging for excluded paths
            should_log_verbose = request.url.path not in self.exclude_paths

            start_time = time.perf_counter()
            request_size = await self._get_request_size(request)

            # Log incoming request
            if should_log_verbose:
                await self._log_request(
                    request, request_id, correlation_id, request_size
                )

            try:
                # Process request
                response = await call_next(request)

                # Calculate metrics
                duration = time.perf_counter() - start_time
                response_size = self._get_response_size(response)

                # Update span with response data
                span.set_attributes(
                    {
                        "http.status_code": response.status_code,
                        "http.response_size": response_size,
                        "request.duration_ms": round(duration * 1000, 2),
                    }
                )

                # Set span status
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))
                else:
                    span.set_status(Status(StatusCode.OK))

                # Log response
                if should_log_verbose:
                    self._log_response(response, duration, request_size, response_size)
                else:
                    # Minimal logging for health checks
                    logger.logger.debug(
                        "request_completed",
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        duration_ms=round(duration * 1000, 2),
                    )

                # Log performance metrics
                self._log_performance_metrics(
                    request, response, duration, request_size, response_size
                )

                # Add response headers for correlation
                response.headers["x-request-id"] = request_id
                response.headers["x-correlation-id"] = correlation_id

                return response

            except Exception as e:
                duration = time.perf_counter() - start_time

                # Update span with error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Log the error with full context
                await self._log_error(request, e, duration, request_size)

                raise

    async def _log_request(
        self, request: Request, request_id: str, correlation_id: str, request_size: int
    ) -> None:
        """Log incoming request with sanitized details."""

        # Sanitize headers
        headers = self._sanitize_headers(dict(request.headers))

        # Parse and sanitize query parameters
        query_params = self._sanitize_query_params(dict(request.query_params))

        # Extract user context if available
        user_context = await self._extract_user_context(request)

        # Log request
        logger.logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=query_params if query_params else None,
            headers=headers,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_size_bytes=request_size,
            user_context=user_context,
            content_type=request.headers.get("content-type"),
        )

    def _log_response(
        self, response: Response, duration: float, request_size: int, response_size: int
    ) -> None:
        """Log response with performance metrics."""

        level = (
            "error"
            if response.status_code >= 500
            else "warning"
            if response.status_code >= 400
            else "info"
        )

        log_data = {
            "event": "request_completed",
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "request_size_bytes": request_size,
            "response_size_bytes": response_size,
            "content_type": response.headers.get("content-type"),
        }

        # Log based on status code
        if level == "error":
            logger.logger.error(**log_data)
        elif level == "warning":
            logger.logger.warning(**log_data)
        else:
            logger.logger.info(**log_data)

    async def _log_error(
        self, request: Request, error: Exception, duration: float, request_size: int
    ) -> None:
        """Log unhandled errors with comprehensive context."""

        logger.logger.error(
            "unhandled_exception",
            error_type=type(error).__name__,
            error_message=str(error),
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration * 1000, 2),
            request_size_bytes=request_size,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            exc_info=True,  # This will include the stack trace
        )

    def _log_performance_metrics(
        self,
        request: Request,
        response: Response,
        duration: float,
        request_size: int,
        response_size: int,
    ) -> None:
        """Log performance metrics for monitoring."""

        # Only log performance metrics for certain conditions
        should_log = (
            duration > settings.SLOW_REQUEST_THRESHOLD  # Slow requests
            or response.status_code >= 400  # Error responses
            or request_size > settings.LARGE_REQUEST_THRESHOLD  # Large requests
            or response_size > settings.LARGE_RESPONSE_THRESHOLD  # Large responses
        )

        if should_log:
            logger.performance(
                "request_metrics",
                duration=duration,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                request_size_bytes=request_size,
                response_size_bytes=response_size,
                slow_request=duration > settings.SLOW_REQUEST_THRESHOLD,
                large_request=request_size > settings.LARGE_REQUEST_THRESHOLD,
                large_response=response_size > settings.LARGE_RESPONSE_THRESHOLD,
            )

    async def _extract_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user context from request if available."""
        try:
            # This would integrate with your auth system
            # For example, if you're using JWT tokens:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Extract user info from token (implement based on your auth)
                return {"auth_type": "bearer"}

            # Check for API key
            api_key = request.headers.get("x-api-key")
            if api_key:
                return {"auth_type": "api_key"}

            return None
        except Exception:
            return None

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize sensitive headers for logging."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "[REDACTED]"
            elif key.lower().startswith("x-") and "token" in key.lower():
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_query_params(self, params: Dict[str, str]) -> Dict[str, str]:
        """Sanitize sensitive query parameters."""
        sanitized = {}
        sensitive_params = {"token", "key", "secret", "password", "auth"}

        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_params):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers."""
        # Check for common proxy headers
        for header in ["x-forwarded-for", "x-real-ip", "x-client-ip"]:
            value = request.headers.get(header)
            if value:
                # Take the first IP in case of comma-separated list
                return value.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def _get_request_size(self, request: Request) -> int:
        """Get request body size."""
        try:
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)

            # For streaming requests, we might need to read the body
            # This is a simplified approach - in production you might want
            # to be more careful about memory usage
            body = await request.body()
            return len(body) if body else 0
        except Exception:
            return 0

    def _get_response_size(self, response: Response) -> int:
        """Get response size from headers."""
        try:
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)

            # If no content-length header, try to estimate from body
            if hasattr(response, "body") and response.body:
                if isinstance(response.body, bytes):
                    return len(response.body)
                elif isinstance(response.body, str):
                    return len(response.body.encode("utf-8"))

            return 0
        except Exception:
            return 0


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Specialized middleware for security event logging.
    """

    async def dispatch(self, request: Request, call_next):
        # Log potential security events
        await self._check_security_events(request)

        response = await call_next(request)

        # Log security response events
        self._check_security_response(request, response)

        return response

    async def _check_security_events(self, request: Request):
        """Check for potential security events in requests."""

        # Check for suspicious patterns in path
        suspicious_patterns = [
            "../",
            "..\\",
            "<script>",
            "javascript:",
            "data:",
            "union select",
            "drop table",
            "exec(",
            "eval(",
        ]

        path = request.url.path.lower()
        for pattern in suspicious_patterns:
            if pattern in path:
                logger.security(
                    "suspicious_request_pattern",
                    pattern=pattern,
                    path=request.url.path,
                    client_ip=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent"),
                )
                break

        # Check for rate limiting indicators
        if request.headers.get("x-forwarded-for"):
            # Log requests from proxies for security monitoring
            logger.logger.debug(
                "proxied_request",
                x_forwarded_for=request.headers.get("x-forwarded-for"),
                x_real_ip=request.headers.get("x-real-ip"),
            )

    def _check_security_response(self, request: Request, response: Response):
        """Check for security events in responses."""

        # Log authentication failures
        if response.status_code == 401:
            logger.security(
                "authentication_failure",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
            )

        # Log authorization failures
        elif response.status_code == 403:
            logger.security(
                "authorization_failure",
                path=request.url.path,
                method=request.method,
                client_ip=request.client.host if request.client else "unknown",
            )
