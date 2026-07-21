"""Middleware for collecting Prometheus metrics."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time

from services.logger import logger
from services.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes,
    http_requests_in_progress,
    get_endpoint_name,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next) -> None:
        # Get endpoint name for labeling
        endpoint = get_endpoint_name(request.url.path)
        method = request.method

        # Record request size
        try:
            body_size = int(request.headers.get("content-length", 0))
        except ValueError:
            body_size = 0
        
        if body_size > 0:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(body_size)

        # Mark request as in progress
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()

        # Record start time
        start_time = time.time()

        logger.debug("HTTP request started: method=%s endpoint=%s", method, endpoint)
        try:
            # Process request
            response = await call_next(request)

            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Record total requests and status
            status_code = response.status_code
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            # Record response size if available
            if "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                    http_response_size_bytes.labels(
                        method=method,
                        endpoint=endpoint
                    ).observe(response_size)
                except ValueError:
                    pass

            logger.debug(
                "HTTP request completed: method=%s endpoint=%s status=%s duration=%.4fs",
                method,
                endpoint,
                response.status_code,
                duration,
            )
            return response

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()
