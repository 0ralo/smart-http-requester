"""Metrics endpoint for Prometheus."""

from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics", summary="Prometheus metrics export")
async def metrics() -> Response:
    """
    Export metrics in Prometheus text format.

    This endpoint returns all collected metrics in the Prometheus exposition format.
    Typically scraped by Prometheus scraper at regular intervals.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@metrics_router.get("/fake_status", summary="test-endpoint", include_in_schema=False)
async def fake_status(
    status_code: int = 200,
) -> Response:
    return Response(
        status_code=status_code,
    )
