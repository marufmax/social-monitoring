import functools
import contextvars


def capture_contextvars():
    """Capture current contextvars snapshot"""
    ctx = contextvars.copy_context()
    return {k.name: ctx[k] for k in ctx}


def with_request_context(func):
    """Decorator to preserve structlog contextvars in async functions"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        snapshot = capture_contextvars()
        token_map = {}
        try:
            # Re-bind all contextvars from snapshot
            for key, val in snapshot.items():
                var = contextvars.ContextVar(key)
                token_map[key] = var.set(val)

            return await func(*args, **kwargs)
        finally:
            # Reset contextvars after function execution
            for key, token in token_map.items():
                var = contextvars.ContextVar(key)
                var.reset(token)

    return wrapper
