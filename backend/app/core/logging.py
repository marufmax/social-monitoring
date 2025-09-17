# app/core/logging.py
"""
Production-grade logging configuration for FastAPI with OpenTelemetry and Loki integration.
- Colorful console logs in development
- JSON structured logs for OTLP/Grafana without ANSI colors
- Optimized for searchability with clear label/body separation
"""

import logging
import sys
import os
import time
import json
from typing import Any, Dict, Optional, Tuple
from contextvars import ContextVar
from functools import lru_cache

import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from app.config import settings, EnvEnum

# Context variables for correlation
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)

# ---------------------- Constants ----------------------

# Low-cardinality fields that should be labels in Loki
LABEL_FIELDS = {
    "service",  # Service name
    "environment",  # Environment (production, staging, dev)
    "level",  # Log level (INFO, WARNING, ERROR, etc.)
    "logger_name",  # Logger name
}

# High-cardinality fields that should be in the log body
BODY_FIELDS = {
    "timestamp",  # ISO 8601 timestamp
    "request_id",  # Request ID
    "user_id",  # User ID
    "correlation_id",  # Correlation ID
    "trace_id",  # OpenTelemetry trace ID
    "span_id",  # OpenTelemetry span ID
    "error",  # Error message
    "stacktrace",  # Stack trace
    "duration_ms",  # Duration in milliseconds
    "response_size_bytes",  # Response size in bytes
    "status_code",  # HTTP status code
    "memory_mb",  # Memory usage in MB
    "cpu_percent",  # CPU usage percentage
    "event",  # Event message
}

# Fields that indicate alertable conditions
ALERT_FIELDS = {
    "error",
    "duration_ms",
    "status_code",
    "memory_mb",
    "cpu_percent",
}

# ---------------------- Processors ----------------------


class LokiOptimizedProcessor:
    """Separates labels from body and adds trace/context info."""

    def __init__(self, service_name: str, environment: str):
        self.service_name = service_name
        self.environment = environment

    def __call__(self, logger, name, event_dict):
        # Extract the log level
        level = event_dict.get("level", "info").upper()

        # Create labels dictionary (low-cardinality fields)
        labels = {
            "service": self.service_name,
            "environment": self.environment,
            "level": level,
            "logger_name": name,
        }

        # Create body dictionary (high-cardinality fields)
        body = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event_dict.get("event", ""),
        }

        # Add trace information if available
        current_span = trace.get_current_span()
        if current_span.is_recording():
            span_context = current_span.get_span_context()
            body.update(
                {
                    "trace_id": format(span_context.trace_id, "032x"),
                    "span_id": format(span_context.span_id, "016x"),
                    "trace_flags": span_context.trace_flags,
                }
            )

        # Add correlation information
        body.update(
            {
                "request_id": request_id_ctx.get(),
                "user_id": user_id_ctx.get(),
                "correlation_id": correlation_id_ctx.get(),
            }
        )

        # Add remaining event_dict fields to body
        for key, value in event_dict.items():
            if key not in ["level", "event"]:
                body[key] = value

        # Remove None values
        body = {k: v for k, v in body.items() if v is not None}

        # Return a dictionary that separates labels and body
        result = {"_labels": labels, "_body": body}
        return result


class SecurityProcessor:
    """Redacts sensitive data."""

    SENSITIVE_KEYS = {
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "cookie",
        "api_key",
        "access_token",
        "refresh_token",
        "jwt",
        "credential",
    }

    def __call__(self, logger, name, event_dict):
        return self._sanitize_dict(event_dict)

    def _sanitize_dict(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if self._is_sensitive_key(k) else self._sanitize_dict(v)
                for k, v in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_dict(item) for item in data]
        elif isinstance(data, str) and len(data) > 100:
            return data[:100] + "...[truncated]"
        return data

    def _is_sensitive_key(self, key: str) -> bool:
        return any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS)


class PerformanceProcessor:
    """Adds performance metrics for all logs in production, DEBUG and ERROR in development."""

    def __call__(self, logger, name, event_dict):
        is_prod = settings.ENVIRONMENT == EnvEnum.PRODUCTION.value
        level = event_dict.get("level", "info").lower()

        # Always add performance metrics in production, or for DEBUG/ERROR in dev
        if is_prod or level in ("debug", "error"):
            try:
                import psutil

                process = psutil.Process()
                event_dict["memory_mb"] = round(
                    process.memory_info().rss / 1024 / 1024, 2
                )
                event_dict["cpu_percent"] = process.cpu_percent()
            except ImportError:
                pass
        return event_dict


class StripAnsiProcessor:
    """Removes ANSI color codes from log output."""

    def __call__(self, logger, name, event_dict):
        import re

        if isinstance(event_dict.get("event"), str):
            event_dict["event"] = re.sub(
                r"\x1B\[[0-?]*[ -/]*[@-~]", "", event_dict["event"]
            )
        return event_dict


class ExceptionFormatterProcessor:
    """Formats exception information consistently for better searchability."""

    def __call__(self, logger, name, event_dict):
        if "exc_info" in event_dict:
            exc_info = event_dict.pop("exc_info")
            if exc_info:
                # Handle both tuple and exception object
                if isinstance(exc_info, tuple):
                    exc_type, exc_value, exc_tb = exc_info
                elif isinstance(exc_info, BaseException):
                    exc_type = type(exc_info)
                    exc_value = exc_info
                    exc_tb = exc_info.__traceback__
                else:
                    # If it's not a tuple or exception, skip processing
                    return event_dict

                # Format exception and add to body
                import traceback

                event_dict["error"] = f"{exc_type.__name__}: {str(exc_value)}"
                event_dict["stacktrace"] = "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                )
        return event_dict


class LokiFormatter:
    """Formats logs specifically for Loki with labels and body separation."""

    def __call__(self, logger, name, event_dict):
        # If the event_dict has _labels and _body, format for Loki
        if "_labels" in event_dict and "_body" in event_dict:
            labels = event_dict["_labels"]
            body = event_dict["_body"]

            # Convert to JSON string for Loki
            return json.dumps({"labels": labels, "body": body})

        # Fallback to regular JSON formatting
        return json.dumps(event_dict)


# ---------------------- Configuration ----------------------


@lru_cache(maxsize=1)
def get_log_config() -> Dict[str, Any]:
    is_dev = settings.ENVIRONMENT == EnvEnum.DEVELOPMENT.value
    return {
        "console_level": logging.DEBUG if is_dev else logging.INFO,
        "otlp_level": logging.INFO if is_dev else logging.WARNING,
        "include_performance": True,  # Always include performance metrics
        "batch_timeout": 5000 if is_dev else 30000,
        "batch_size": 100 if is_dev else 500,
        "max_export_timeout": 30000,
        "enable_console": False,
    }


# ---------------------- Setup Logging ----------------------


def setup_logging(
    service_name: str = "smm_api",
    env: str = "dev",
    otlp_endpoint: str = "http://alloy:4317",
    log_level: Optional[str] = None,
) -> Tuple[LoggerProvider, TracerProvider]:
    config = get_log_config()

    if log_level:
        config["console_level"] = getattr(logging, log_level.upper())
        config["otlp_level"] = getattr(logging, log_level.upper())

    # OpenTelemetry Resource
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            "service.namespace": "social-media-monitor",
            "deployment.environment": env,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "host.name": os.getenv("HOSTNAME", "unknown"),
        }
    )

    # Tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Logger provider
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    # OTLP Exporter
    otlp_exporter = OTLPLogExporter(
        endpoint=otlp_endpoint,
        insecure=True,
        timeout=config["max_export_timeout"] // 1000,
    )
    batch_processor = BatchLogRecordProcessor(
        otlp_exporter,
        max_queue_size=2048,
        export_timeout_millis=config["max_export_timeout"],
        schedule_delay_millis=config["batch_timeout"],
        max_export_batch_size=config["batch_size"],
    )
    logger_provider.add_log_record_processor(batch_processor)

    # Handlers
    handlers = []
    if config["enable_console"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(config["console_level"])
        console_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(console_handler)

    otel_handler = LoggingHandler(
        level=config["otlp_level"], logger_provider=logger_provider
    )
    handlers.append(otel_handler)

    # Structlog processors
    base_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        SecurityProcessor(),
        PerformanceProcessor(),
        ExceptionFormatterProcessor(),
        LokiOptimizedProcessor(service_name, env),
    ]

    # Console renderer (colorful in dev)
    console_processors = list(base_processors)
    if config["enable_console"]:
        console_processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # OTLP renderer (JSON, no colors, Loki-optimized)
    otlp_processors = list(base_processors)
    otlp_processors.extend(
        [
            StripAnsiProcessor(),  # Ensure no ANSI codes in OTLP output
            structlog.processors.TimeStamper(fmt="iso"),
            LokiFormatter(),  # Custom formatter for Loki
        ]
    )

    # Configure structlog with separate processors for console and OTLP
    structlog.configure(
        processors=console_processors if config["enable_console"] else otlp_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Standard logging
    logging.basicConfig(
        format="%(message)s",
        level=config["console_level"],
        handlers=handlers,
        force=True,
    )

    LoggingInstrumentor().instrument(set_logging_format=True)

    # Reduce library noise
    _configure_library_loggers(config["console_level"])

    # Bind global context
    structlog.contextvars.bind_contextvars(
        service=service_name,
        service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
        environment=env,
        pid=os.getpid(),
    )

    logger = structlog.get_logger(__name__)
    logger.info(
        "logging_initialized",
        service_name=service_name,
        environment=env,
        otlp_endpoint=otlp_endpoint,
        console_enabled=config["enable_console"],
        performance_monitoring=config["include_performance"],
    )

    return logger_provider, tracer_provider


def _configure_library_loggers(base_level: int) -> None:
    library_levels = {
        "urllib3": logging.WARNING,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "asyncio": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
        "alembic": logging.INFO,
        "uvicorn": logging.INFO,
        "uvicorn.access": logging.WARNING,
        "fastapi": logging.INFO,
    }
    for name, level in library_levels.items():
        logging.getLogger(name).setLevel(max(level, base_level))


# ---------------------- Logger Adapter ----------------------


class LoggerAdapter:
    def __init__(self, logger_name: str):
        self.logger = structlog.get_logger(logger_name)

    def audit(self, event: str, **kwargs):
        self.logger.info(event, audit=True, **kwargs)

    def security(self, event: str, **kwargs):
        self.logger.warning(event, security=True, **kwargs)

    def business(self, event: str, **kwargs):
        self.logger.info(event, business=True, **kwargs)

    def performance(self, event: str, duration: float, **kwargs):
        self.logger.info(
            event, performance=True, duration_ms=round(duration * 1000, 2), **kwargs
        )

    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        if error:
            # Pass the exception object directly - the processor will handle it
            self.logger.error(event, exc_info=error, **kwargs)
        else:
            self.logger.error(event, **kwargs)


def get_logger(name: str) -> LoggerAdapter:
    return LoggerAdapter(name)


# ---------------------- Correlation Context ----------------------


def get_correlation_context() -> Dict[str, Optional[str]]:
    return {
        "request_id": request_id_ctx.get(),
        "user_id": user_id_ctx.get(),
        "correlation_id": correlation_id_ctx.get(),
    }


def set_correlation_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    if request_id:
        request_id_ctx.set(request_id)
    if user_id:
        user_id_ctx.set(user_id)
    if correlation_id:
        correlation_id_ctx.set(correlation_id)


def clear_correlation_context() -> None:
    """Clear all correlation context variables."""
    request_id_ctx.set(None)
    user_id_ctx.set(None)
    correlation_id_ctx.set(None)


# ---------------------- Health Check ----------------------


def logging_health_check() -> Dict[str, Any]:
    try:
        logger = structlog.get_logger(__name__)
        logger.debug("logging_health_check", status="ok")
        return {"status": "healthy", "timestamp": time.time()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}
