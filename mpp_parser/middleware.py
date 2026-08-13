import time
import uuid
import logging
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("mpp_parser.middleware")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class CorrelationIdFilter(logging.Filter):
    """Logging filter that injects request_id into log records."""
    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates or extracts X-Request-ID, assigns it to contextvars,
    logs request metrics, and returns X-Request-ID header in response.
    """
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(req_id)

        start_time = time.time()
        path = request.url.path
        method = request.method

        logger.info(f"[{req_id}] Started {method} '{path}'")

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"[{req_id}] Completed {method} '{path}' status={response.status_code} in {duration_ms}ms")
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[{req_id}] Failed {method} '{path}' with error: {exc} in {duration_ms}ms")
            raise
        finally:
            request_id_var.reset(token)
