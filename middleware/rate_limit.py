import datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from services.redis_service import check_rate_limit
from config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client = request.client
        if client is None:
            return JSONResponse(
                status_code=status.HTTP_423_LOCKED,
                content={"detail": "Cannot get ip address"},
            )
        ip = client.host
        allowed, total, reset_time = await check_rate_limit(
            f"rate_limit:{ip}", settings.rate_limit, 60
        )
        if allowed:
            response = await call_next(request)
        else:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests"},
            )
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(settings.rate_limit - total)
        response.headers["X-RateLimit-Reset"] = datetime.datetime.strftime(
            datetime.datetime.fromtimestamp(reset_time), "%H:%M:%S"
        )
        return response
