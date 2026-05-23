"""Prometheus metrics collection for FastAPI endpoints."""

from prometheus_client import Counter, Histogram, Gauge
import time
from typing import Callable

# HTTP Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000)
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000)
)

# Active requests gauge
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"]
)

# Task-specific metrics
tasks_created_total = Counter(
    "tasks_created_total",
    "Total number of tasks created"
)

tasks_completed_total = Counter(
    "tasks_completed_total",
    "Total number of completed tasks",
    ["status"]
)

tasks_in_queue = Gauge(
    "tasks_in_queue",
    "Number of tasks currently in queue"
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["type", "status"]
)


def get_endpoint_name(path: str) -> str:
    """Convert path to endpoint name by replacing IDs with placeholders."""
    import re
    # Replace UUID patterns with {id}
    endpoint = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '{id}',
        path,
        flags=re.IGNORECASE
    )
    # Replace numeric IDs with {id}
    endpoint = re.sub(r'/\d+/', '/{id}/', endpoint)
    return endpoint
