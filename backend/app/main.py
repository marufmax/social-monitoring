import signal
import sys
import time

from fastapi import FastAPI, Request, status
from contextlib import asynccontextmanager

from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy import text
from starlette.responses import JSONResponse

from app.api.universal.router import api_universal_router
from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import LoggingMiddleware, SecurityLoggingMiddleware
from app.api.v1.router import apiV1_router
from app.database import async_engine as engine, Base

# Application Logging
logger_provider, tracer_provider = setup_logging(
    service_name="smm_api_application",
    env=settings.ENVIRONMENT,
    otlp_endpoint=settings.OTLP_ENDPOINT,
    log_level=settings.LOG_LEVEL.value,
)

# Get logger instance
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_start_time = time.perf_counter()

    try:
        logger.logger.info(
            "application_startup_initiated",
            service_name="smm_api",
            environment=settings.ENVIRONMENT,
            version=settings.SERVICE_VERSION,
            debug_mode=settings.DEBUG,
        )

        # Initialize database
        await initialize_database()

        # Register shutdown handlers
        register_signal_handlers()

        startup_duration = time.perf_counter() - startup_start_time

        logger.logger.info(
            "application_startup_completed",
            startup_duration_ms=round(startup_duration * 1000, 2),
            database_ready=True,
            logging_ready=True,
        )

        # Application runs here
        yield

    except Exception as e:
        startup_duration = time.perf_counter() - startup_start_time
        logger.logger.error(
            "application_startup_failed",
            error=str(e),
            startup_duration_ms=round(startup_duration * 1000, 2),
            exc_info=True,
        )
        raise

    finally:
        # Shutdown sequence
        shutdown_start_time = time.perf_counter()

        logger.logger.info("application_shutdown_initiated")

        try:
            # Close database connections
            await engine.dispose()
            logger.logger.info("database_connections_closed")

            # Flush remaining logs
            if hasattr(logger_provider, "_log_record_processors"):
                for processor in logger_provider._log_record_processors:
                    if hasattr(processor, "force_flush"):
                        processor.force_flush(timeout_millis=5000)

            shutdown_duration = time.perf_counter() - shutdown_start_time

            logger.logger.info(
                "application_shutdown_completed",
                shutdown_duration_ms=round(shutdown_duration * 1000, 2),
            )

        except Exception as e:
            logger.logger.error(
                "application_shutdown_error",
                error=str(e),
                exc_info=True,
            )


async def initialize_database():
    """Initialize database with proper error handling and logging."""
    try:
        logger.logger.info("database_initialization_started")

        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)

            # Test database connection (SQLAlchemy 2.0 requires `text`)
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        logger.logger.info(
            "database_initialization_completed",
            database_url=settings.DATABASE_URL.split("@")[1]
            if "@" in settings.DATABASE_URL
            else "masked",
        )

    except Exception as e:
        logger.logger.error(
            "database_initialization_failed",
            error=str(e),
            database_url=settings.DATABASE_URL.split("@")[1]
            if "@" in settings.DATABASE_URL
            else "masked",
            exc_info=True,
        )
        raise


def register_signal_handlers():
    """Register signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.logger.info(
            "shutdown_signal_received",
            signal=signal.Signals(signum).name,
        )
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


app = FastAPI(
    title="Social Media Monitoring",
    lifespan=lifespan,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

# Middlewares
if settings.LOG_SECURITY_EVENTS:
    app.add_middleware(SecurityLoggingMiddleware)

app.add_middleware(
    LoggingMiddleware,
    exclude_paths={"/health", "/metrics", "/ready", "/docs", "/redoc", "/openapi.json"},
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed logging."""
    logger.logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "status_code": 422,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with comprehensive logging."""
    logger.logger.error(
        "unhandled_exception",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred. Please try again later.",
                "status_code": 500,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
                "status_code": 500,
            },
        )


# Routes
app.include_router(apiV1_router, prefix="/api/v1")
app.include_router(api_universal_router)


# Health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "Social Media Monitoring API is running"}
