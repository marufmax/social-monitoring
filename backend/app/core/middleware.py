from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger
import time

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=f"{process_time:.2f}s"
        )
        return response
