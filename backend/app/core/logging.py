import logging
import sys
import structlog
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

from app.config import settings, EnvEnum


def setup_logging(
    service_name: str = "api",
    env: str = "dev",
    otlp_endpoint: str = "http://alloy:4317",
) -> tuple[LoggerProvider, TracerProvider]:
    """Configure structlog + stdlib logging for JSON output and OTLP export"""
    service_version = "1.0.0"
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "service.namespace": "social-media-monitor",
            "deployment.environment": env,
        }
    )

    # Set up OpenTelemetry Tracing
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Set up OpenTelemetry Logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    # Set up OTLP Log Exporter
    otlp_log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))

    # Create a handler for stdlib logging that uses OpenTelemetry
    otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    # Console handler for local debugging
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use the OpenTelemetry handler
    if settings.ENVIRONMENT == EnvEnum.DEVELOPMENT.value:
        handlers = [console_handler, otel_handler]
    else:
        handlers = [otel_handler]

    logging.basicConfig(
        format="%(message)s", level=logging.INFO, handlers=[otel_handler]
    )

    # Add service metadata globally
    structlog.contextvars.bind_contextvars(
        service=service_name, service_version=service_version, env=env
    )

    return logger_provider, tracer_provider
