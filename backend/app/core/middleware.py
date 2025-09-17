# app/core/middleware.py
"""
Enhanced logging middleware with comprehensive request tracking and performance monitoring.

This middleware provides:
- Automatic request/response logging with correlation IDs
- Performance monitoring with detailed metrics
- Error tracking with stack traces
- Security event logging
- Integration with OpenTelemetry tracing

Design Patterns Used:
- Strategy Pattern: For different logging strategies
- Chain of Responsibility: For processing log events
- Context Manager: For correlation context management
"""

import time
import uuid
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set
from enum import Enum

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.core.logging import (
    get_logger,
    set_correlation_context,
    clear_correlation_context,
)
from app.config import settings

logger = get_logger(__name__)


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogContext:
    """Context information for a single request"""

    request_id: str
    correlation_id: str
    start_time: float
    request_size: int
    user_context: Optional[Dict[str, Any]] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    duration: Optional[float] = None
    error: Optional[Exception] = None


@dataclass
class LogEntry:
    """Structured log entry"""

    event: str
    level: LogLevel
    context: LogContext
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class LogStrategy(ABC):
    """Abstract base class for logging strategies"""

    @abstractmethod
    def log(self, entry: LogEntry) -> None:
        """Log the entry"""
        pass


class RequestLogStrategy(LogStrategy):
    """Strategy for request logging"""

    def __init__(self, exclude_paths: Set[str]):
        self.exclude_paths = exclude_paths

    def log(self, entry: LogEntry) -> None:
        """Log request entries"""
        if entry.context.path in self.exclude_paths:
            return

        # Log request using the audit method
        logger.audit(
            entry.event,
            method=entry.context.method,
            path=entry.context.path,
            query_params=entry.data.get("query_params", {}),
            headers=entry.data.get("headers", {}),
            client_ip=entry.context.client_ip,
            user_agent=entry.context.user_agent,
            request_size_bytes=entry.context.request_size,
            user_context=entry.context.user_context,
            content_type=entry.data.get("content_type"),
        )


class ResponseLogStrategy(LogStrategy):
    """Strategy for response logging"""

    def __init__(self, exclude_paths: Set[str]):
        self.exclude_paths = exclude_paths

    def log(self, entry: LogEntry) -> None:
        """Log response entries"""
        if entry.context.path in self.exclude_paths:
            return

        # Determine log level based on status code
        if entry.context.status_code and entry.context.status_code >= 500:
            log_method = logger.error
        elif entry.context.status_code and entry.context.status_code >= 400:
            log_method = logger.logger.warning
        else:
            log_method = logger.logger.info

        # Log response
        log_method(
            entry.event,
            status_code=entry.context.status_code,
            duration_ms=round(entry.context.duration * 1000, 2)
            if entry.context.duration
            else None,
            request_size_bytes=entry.context.request_size,
            response_size_bytes=entry.context.response_size,
            content_type=entry.data.get("content_type"),
        )


class ErrorLogStrategy(LogStrategy):
    """Strategy for error logging"""

    def log(self, entry: LogEntry) -> None:
        """Log error entries"""
        if not entry.context.error:
            return

        # Log the error
        logger.error(
            entry.event,
            error=entry.context.error,
            method=entry.context.method,
            path=entry.context.path,
            duration_ms=round(entry.context.duration * 1000, 2)
            if entry.context.duration
            else None,
            request_size_bytes=entry.context.request_size,
            client_ip=entry.context.client_ip,
            user_agent=entry.context.user_agent,
        )


class PerformanceLogStrategy(LogStrategy):
    """Strategy for performance metrics logging"""

    def log(self, entry: LogEntry) -> None:
        """Log performance entries"""
        if not entry.context.duration:
            return

        # Only log performance metrics for certain conditions
        should_log = (
            entry.context.duration > settings.SLOW_REQUEST_THRESHOLD  # Slow requests
            or (
                entry.context.status_code and entry.context.status_code >= 400
            )  # Error responses
            or entry.context.request_size
            > settings.LARGE_REQUEST_THRESHOLD  # Large requests
            or (
                entry.context.response_size
                and entry.context.response_size > settings.LARGE_RESPONSE_THRESHOLD
            )  # Large responses
        )

        if should_log:
            logger.performance(
                entry.event,
                duration=entry.context.duration,
                method=entry.context.method,
                path=entry.context.path,
                status_code=entry.context.status_code,
                request_size_bytes=entry.context.request_size,
                response_size_bytes=entry.context.response_size,
                slow_request=entry.context.duration > settings.SLOW_REQUEST_THRESHOLD,
                large_request=entry.context.request_size
                > settings.LARGE_REQUEST_THRESHOLD,
                large_response=(
                    entry.context.response_size
                    and entry.context.response_size > settings.LARGE_RESPONSE_THRESHOLD
                ),
            )


class SecurityLogStrategy(LogStrategy):
    """Strategy for security event logging"""

    def log(self, entry: LogEntry) -> None:
        """Log security entries"""
        # Log security events
        logger.security(
            entry.event,
            threat_level=entry.data.get("threat_level", "medium"),
            pattern=entry.data.get("pattern"),
            path=entry.context.path,
            method=entry.context.method,
            client_ip=entry.context.client_ip,
            user_agent=entry.context.user_agent,
            response_size_bytes=entry.context.response_size,
        )


class BusinessLogStrategy(LogStrategy):
    """Strategy for business metrics logging"""

    def log(self, entry: LogEntry) -> None:
        """Log business metrics"""
        # Log business events
        logger.business(
            entry.event,
            metric_name=entry.data.get("metric_name", "unknown"),
            metric_value=entry.data.get("metric_value", 1),
            metric_unit=entry.data.get("metric_unit", "count"),
            **entry.data.get("metric_labels", {}),
        )


class LogStrategyFactory:
    """Factory for creating log strategies"""

    @staticmethod
    def create_request_strategy(exclude_paths: Set[str]) -> LogStrategy:
        return RequestLogStrategy(exclude_paths)

    @staticmethod
    def create_response_strategy(exclude_paths: Set[str]) -> LogStrategy:
        return ResponseLogStrategy(exclude_paths)

    @staticmethod
    def create_error_strategy() -> LogStrategy:
        return ErrorLogStrategy()

    @staticmethod
    def create_performance_strategy() -> LogStrategy:
        return PerformanceLogStrategy()

    @staticmethod
    def create_security_strategy() -> LogStrategy:
        return SecurityLogStrategy()

    @staticmethod
    def create_business_strategy() -> LogStrategy:
        return BusinessLogStrategy()


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
    - Business metrics tracking
    """

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

    # Security patterns to detect
    SECURITY_PATTERNS = [
        r"\.\./",  # Directory traversal
        r"\.\.\\",  # Directory traversal (Windows)
        r"<script",  # XSS
        r"javascript:",  # JavaScript injection
        r"data:",  # Data URI
        r"union\s+select",  # SQL injection
        r"drop\s+table",  # SQL injection
        r"exec\(",  # Command injection
        r"eval\(",  # Code injection
    ]

    def __init__(self, app, exclude_paths: Optional[set] = None):
        super().__init__(app)
        self.exclude_paths = self.EXCLUDED_PATHS | (exclude_paths or set())

        # Initialize logging strategies
        self.request_strategy = LogStrategyFactory.create_request_strategy(
            self.exclude_paths
        )
        self.response_strategy = LogStrategyFactory.create_response_strategy(
            self.exclude_paths
        )
        self.error_strategy = LogStrategyFactory.create_error_strategy()
        self.performance_strategy = LogStrategyFactory.create_performance_strategy()
        self.security_strategy = LogStrategyFactory.create_security_strategy()
        self.business_strategy = LogStrategyFactory.create_business_strategy()

    async def dispatch(self, request: Request, call_next):
        # Generate correlation IDs
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Extract user context if available
        user_context = await self._extract_user_context(request)

        # Create log context
        context = LogContext(
            request_id=request_id,
            correlation_id=correlation_id,
            start_time=time.perf_counter(),
            request_size=await self._get_request_size(request),
            user_context=user_context,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            path=request.url.path,
            method=request.method,
        )

        # Set correlation context
        set_correlation_context(
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_context.get("user_id") if user_context else None,
        )

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
                    "http.client_ip": context.client_ip,
                    "request.id": request_id,
                    "correlation.id": correlation_id,
                }
            )

            # Log incoming request
            if request.url.path not in self.exclude_paths:
                request_data = {
                    "content_type": request.headers.get("content-type"),
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params),
                }
                request_entry = LogEntry(
                    event="http_request_received",
                    level=LogLevel.INFO,
                    context=context,
                    data=request_data,
                )
                self.request_strategy.log(request_entry)

            try:
                # Process request
                response = await call_next(request)

                # Calculate metrics
                context.duration = time.perf_counter() - context.start_time
                context.response_size = self._get_response_size(response)
                context.status_code = response.status_code

                # Update span with response data
                span.set_attributes(
                    {
                        "http.status_code": response.status_code,
                        "http.response_size": context.response_size,
                        "request.duration_ms": round(context.duration * 1000, 2),
                    }
                )

                # Set span status
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))
                else:
                    span.set_status(Status(StatusCode.OK))

                # Log response
                if request.url.path not in self.exclude_paths:
                    response_data = {
                        "content_type": response.headers.get("content-type"),
                    }
                    response_entry = LogEntry(
                        event="http_response_sent",
                        level=LogLevel.INFO,
                        context=context,
                        data=response_data,
                    )
                    self.response_strategy.log(response_entry)
                else:
                    # Minimal logging for health checks
                    logger.logger.debug(
                        "request_completed",
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        duration_ms=round(context.duration * 1000, 2),
                    )

                # Log business metrics if applicable
                self._log_business_metrics(context)

                # Add response headers for correlation
                response.headers["x-request-id"] = request_id
                response.headers["x-correlation-id"] = correlation_id

                return response

            except Exception as e:
                context.duration = time.perf_counter() - context.start_time
                context.error = e

                # Update span with error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)

                # Log the error
                error_entry = LogEntry(
                    event="unhandled_exception",
                    level=LogLevel.ERROR,
                    context=context,
                    data={},
                )
                self.error_strategy.log(error_entry)

                raise
            finally:
                # Clear correlation context
                clear_correlation_context()

    def _log_business_metrics(self, context: LogContext) -> None:
        """Log business metrics for analytics"""
        # Example business metrics - customize based on your application needs
        if context.path and context.path.startswith("/api/"):
            # API endpoint metric
            business_entry = LogEntry(
                event="api_request",
                level=LogLevel.INFO,
                context=context,
                data={
                    "metric_name": "api_requests",
                    "metric_value": 1,
                    "metric_unit": "count",
                    "metric_labels": {
                        "endpoint": context.path,
                        "method": context.method,
                        "status_code": str(context.status_code),
                    },
                },
            )
            self.business_strategy.log(business_entry)

        # Track successful user logins
        if (
            context.path == "/api/auth/login"
            and context.status_code == 200
            and context.duration
        ):
            business_entry = LogEntry(
                event="user_login",
                level=LogLevel.INFO,
                context=context,
                data={
                    "metric_name": "login_duration",
                    "metric_value": context.duration * 1000,  # Convert to ms
                    "metric_unit": "ms",
                },
            )
            self.business_strategy.log(business_entry)

    async def _extract_user_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract user context from request if available"""
        try:
            # This would integrate with your auth system
            # For example, if you're using JWT tokens:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # Extract user info from token (implement based on your auth)
                return {
                    "auth_type": "bearer",
                    "user_id": "extracted_user_id",  # Replace with actual extraction
                    "session_id": "extracted_session_id",  # Replace with actual extraction
                    "tenant_id": "extracted_tenant_id",  # Replace with actual extraction
                }

            # Check for API key
            api_key = request.headers.get("x-api-key")
            if api_key:
                return {
                    "auth_type": "api_key",
                    "user_id": "api_user",  # Replace with actual extraction
                }

            return None
        except Exception:
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers"""
        # Check for common proxy headers
        for header in ["x-forwarded-for", "x-real-ip", "x-client-ip"]:
            value = request.headers.get(header)
            if value:
                # Take the first IP in case of comma-separated list
                return value.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def _get_request_size(self, request: Request) -> int:
        """Get request body size"""
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
        """Get response size from headers"""
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

    # Security patterns to detect
    SECURITY_PATTERNS = [
        r"\.\./",  # Directory traversal
        r"\.\.\\",  # Directory traversal (Windows)
        r"<script",  # XSS
        r"javascript:",  # JavaScript injection
        r"data:",  # Data URI
        r"union\s+select",  # SQL injection
        r"drop\s+table",  # SQL injection
        r"exec\(",  # Command injection
        r"eval\(",  # Code injection
    ]

    def __init__(self, app):
        super().__init__(app)
        self.security_strategy = LogStrategyFactory.create_security_strategy()

    async def dispatch(self, request: Request, call_next):
        # Generate correlation IDs for security events
        request_id = str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Create log context
        context = LogContext(
            request_id=request_id,
            correlation_id=correlation_id,
            start_time=time.perf_counter(),
            request_size=await self._get_request_size(request),
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            path=request.url.path,
            method=request.method,
        )

        # Set correlation context
        set_correlation_context(
            request_id=request_id,
            correlation_id=correlation_id,
        )

        # Log potential security events
        await self._check_security_events(context)

        response = await call_next(request)

        # Update context with response data
        context.response_size = self._get_response_size(response)
        context.status_code = response.status_code
        context.duration = time.perf_counter() - context.start_time

        # Log security response events
        self._check_security_response(context)

        # Clear correlation context
        clear_correlation_context()

        return response

    async def _check_security_events(self, context: LogContext):
        """Check for potential security events in requests"""
        if not context.path:
            return

        path = context.path.lower()

        # Check for suspicious patterns in path
        for pattern in self.SECURITY_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                security_entry = LogEntry(
                    event="suspicious_request_pattern",
                    level=LogLevel.WARNING,
                    context=context,
                    data={
                        "threat_level": "high",
                        "pattern": pattern,
                    },
                )
                self.security_strategy.log(security_entry)
                break

        # Check for authentication attempts
        if context.path and "/auth" in context.path:
            security_entry = LogEntry(
                event="authentication_attempt",
                level=LogLevel.WARNING,
                context=context,
                data={
                    "threat_level": "medium",
                },
            )
            self.security_strategy.log(security_entry)

    def _check_security_response(self, context: LogContext):
        """Check for security events in responses"""
        # Log authentication failures
        if context.status_code == 401:
            security_entry = LogEntry(
                event="authentication_failure",
                level=LogLevel.WARNING,
                context=context,
                data={
                    "threat_level": "medium",
                },
            )
            self.security_strategy.log(security_entry)

        # Log authorization failures
        elif context.status_code == 403:
            security_entry = LogEntry(
                event="authorization_failure",
                level=LogLevel.WARNING,
                context=context,
                data={
                    "threat_level": "medium",
                },
            )
            self.security_strategy.log(security_entry)

        # Log potential data breaches (large responses from sensitive endpoints)
        sensitive_endpoints = ["/api/users", "/api/admin", "/api/config"]
        if (
            context.path
            and any(endpoint in context.path for endpoint in sensitive_endpoints)
            and context.status_code == 200
            and context.response_size
            and context.response_size > 1024 * 1024  # 1MB
        ):
            security_entry = LogEntry(
                event="large_data_transfer",
                level=LogLevel.WARNING,
                context=context,
                data={
                    "threat_level": "low",
                    "response_size_bytes": context.response_size,
                },
            )
            self.security_strategy.log(security_entry)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP considering proxy headers"""
        # Check for common proxy headers
        for header in ["x-forwarded-for", "x-real-ip", "x-client-ip"]:
            value = request.headers.get(header)
            if value:
                # Take the first IP in case of comma-separated list
                return value.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def _get_request_size(self, request: Request) -> int:
        """Get request body size"""
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
        """Get response size from headers"""
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
