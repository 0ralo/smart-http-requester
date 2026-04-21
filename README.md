# Async HTTP Requester

**High‑throughput asynchronous HTTP client with message queue, horizontally scalable workers, and full observability.**

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.0+-green.svg)](https://fastapi.tiangolo.com/)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8.svg)](https://golang.org/)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12+-FF6600.svg)](https://www.rabbitmq.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18+-4169E1.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-24.0+-2496ED.svg)](https://www.docker.com/)

---

## Overview

**Async HTTP Requester** is a production‑ready distributed system for executing HTTP requests asynchronously via a message queue. The project demonstrates expertise in:

- Asynchronous architectures (FastAPI + RabbitMQ)
- Horizontal scaling (Go workers)
- Reliable task processing (retries, DLQ, graceful shutdown)
- Instant session revocation (opaque tokens in Redis)
- Real‑time updates (WebSocket)
- Full observability (Prometheus + Grafana)

---

## Architecture
Client → FastAPI Gateway → (auth: Redis, storage: PostgreSQL, queue: RabbitMQ)
↓
Workers (Go / Rust)
↓
External API → result → PostgreSQL + Redis cache

**Data flow:**
1. User submits HTTP request → saved to DB + published to RabbitMQ
2. Worker consumes task, executes HTTP call, updates status
3. Client polls `GET /requests/{id}` or receives WebSocket push
4. On failure: exponential backoff (5s, 10s, 20s, 40s) → Dead Letter Queue

---

## Tech Stack

| Component            | Technology             | Purpose                                    |
|----------------------|------------------------|--------------------------------------------|
| **API Gateway**      | FastAPI + Uvicorn      | REST API, auth, WebSocket                  |
| **Worker**           | Go 1.21+ \ Rust 1.95.0 | HTTP execution, retry logic                |
| **Message Queue**    | RabbitMQ 3.12          | Task buffering, DLX, retry queues          |
| **Database**         | PostgreSQL 15          | Tasks, users, logs                         |
| **Cache & Sessions** | Redis 7                | Session store, rate limiting, result cache |
| **Monitoring**       | Prometheus + Grafana   | Metrics collection, dashboards, alerts     |
| **Orchestration**    | Docker Compose         | Local development & testing                |

---

## Key Features

| Feature            | Implementation                                                     |
|--------------------|--------------------------------------------------------------------|
| Async processing   | FastAPI + RabbitMQ – non‑blocking                                  |
| Horizontal scaling | Multiple Go\Rust workers                                           |
| Reliability        | Dead Letter Queue, exponential retry, graceful shutdown            |
| Instant revocation | Opaque session tokens in Redis (no JWT blind spots)                |
| Real‑time updates  | WebSocket status push                                              |
| Rate limiting      | Sliding window (Redis)                                             |
| Observability      | Prometheus metrics (RPS, latency, queue depth, worker utilization) |

---

## Quick Start

TODO

Why Opaque Tokens Instead of JWT?
This project uses Redis‑backed opaque sessions for authentication because:

✅ Instant revocation – ban/logout takes effect immediately

✅ No refresh token complexity – single session ID

✅ Simple infrastructure – Redis already present for caching

JWT would introduce a 5–15 minute ban delay unless paired with Redis (hybrid), which adds complexity without real benefit for this workload.