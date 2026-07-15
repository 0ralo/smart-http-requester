"""Tests for the Prometheus metrics endpoint."""
from httpx import AsyncClient, ASGITransport
import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text(app, client: AsyncClient):
    response = await client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert b"# HELP" in response.content or b"python_info" in response.content
