# Smart HTTP Requester

**High‑throughput asynchronous HTTP client with message queue, reliable task processing, and full observability.**

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136.0+-green.svg)](https://fastapi.tiangolo.com/)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12+-FF6600.svg)](https://www.rabbitmq.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-4169E1.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-latest-FF6B35.svg)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-latest-F96688.svg)](https://grafana.com/)

---

## Overview

**Smart HTTP Requester** is a production‑ready distributed system for executing HTTP requests asynchronously via a message queue. The project demonstrates expertise in:

- **Asynchronous architectures** – FastAPI + RabbitMQ for non‑blocking request handling
- **Reliable task processing** – Dead Letter Queue, exponential retry strategy, graceful shutdown
- **Instant session revocation** – Opaque tokens (no JWT blind spots)
- **Full observability** – Prometheus metrics + Grafana dashboards
- **Secure authentication** – Password hashing with bcrypt, session-based auth



```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌──────────────────────────────────────┐
│     FastAPI Gateway (Port 8000)      │
│  - Auth                              │
│  - Metrics collection                │
└─────────┬──────────────────────┬─────┘
          │                      │
    PostgreSQL DB          RabbitMQ Queue
    (Port 5432)            (Port 5672)
          │                      │
    Task Storage           Task Distribution
          │                      │
          └──────────────────────┘
                    │
             [Prometheus Metrics]
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    Prometheus         Grafana Dashboards
    (Port 9090)        (Port 3000)
```

**Data flow:**
1. User registers/logs in → session token
2. User creates HTTP request task → saved to PostgreSQL + published to RabbitMQ
3. Task status updates are saved in PostgreSQL and available via API queries
4. Client can poll `GET /requests/{id}` for status updates
5. On failure: exponential backoff retry (5s, 10s, 20s, 40s) → Dead Letter Queue
6. All operations tracked in Prometheus metrics

---

## Tech Stack

| Component            | Technology                | Version    | Purpose                                    |
|----------------------|---------------------------|------------|------------------------------------------------|
| **Runtime**          | Python                    | 3.14+      | Application runtime                        |
| **API Framework**     | FastAPI + Granian/Uvicorn | 0.136.0+   | REST API, auth middleware                  |
| **Message Queue**     | RabbitMQ                  | 3.12+      | Task buffering, DLX (Dead Letter Exchange) |
| **Primary DB**        | PostgreSQL                | 17         | Tasks, users, audit logs                   |
| **Session Store**     | PostgreSQL                | 7          | Opaque session tokens, pub/sub              |
| **Encryption**        | bcrypt                    | 5.0.0+     | Password hashing                           |
| **Metrics**           | Prometheus                | latest     | Time-series metrics collection             |
| **Visualization**     | Grafana                   | latest     | Dashboards, alerts, real-time insights     |
| **Orchestration**     | Docker Compose            | 3.8        | Local development & testing                |

---

## API Endpoints

### Authentication Endpoints

| Method | Endpoint            | Purpose                                        | Auth |
|--------|---------------------|------------------------------------------------|------|
| `POST` | `/v1/auth/register` | Register new user (username + password hash)   | ❌    |
| `POST` | `/v1/auth/login`    | Authenticate user, return opaque session token | ❌    |
| `POST` | `/v1/auth/logout`   | Invalidate current session token               | ✅    |
| `POST` | `/v1/auth/refresh`  | Refresh session token (extends 7 days)         | ✅    |
| `GET`  | `/v1/auth/me`       | Get current user profile                       | ✅    |

### HTTP Request Management

| Method   | Endpoint                 | Purpose                                   | Auth |
|----------|--------------------------|-------------------------------------------|------|
| `POST`   | `/v1/requests/`          | Create new HTTP request task              | ✅    |
| `GET`    | `/v1/requests/`          | List user's tasks (paginated, skip/limit) | ✅    |
| `GET`    | `/v1/requests/{task_id}` | Get task details by ID                    | ✅    |
| `PUT`    | `/v1/requests/{task_id}` | Update task (only pending tasks)          | ✅    |
| `DELETE` | `/v1/requests/{task_id}` | Cancel task (only pending tasks)          | ✅    |

### Monitoring

| Method | Endpoint      | Purpose                             | Auth |
|--------|---------------|-------------------------------------|------|
| `GET`  | `/v1/metrics` | Export metrics in Prometheus format | ❌    |

---

## Key Features

| Feature                   | Status | Implementation                                                     |
|---------------------------|--------|--------------------------------------------------------------------|
| ✅ Async HTTP execution    | Done   | FastAPI + RabbitMQ – non‑blocking request handling                 |
| ✅ Reliable task queuing   | Done   | Dead Letter Queue, exponential retry (5s → 40s), graceful shutdown |
| ✅ Instant auth revocation | Done   | Opaque session tokens  (no JWT blind spots)                |
| ✅ Metrics & monitoring    | Done   | Prometheus export at `/v1/metrics`, Grafana dashboards             |
| ✅ Secure authentication   | Done   | bcrypt password hashing                                            |
| ✅ User management         | Done   | Register, login, logout, token refresh, profile endpoints          |
| ✅ Task CRUD operations    | Done   | Create, read, update, cancel HTTP request tasks                    |
| ⏳ Worker implementation   | WIP    | External worker service for task execution (planned: Go/Rust)      |
| ✅ Rate limiting           | Done   | Sliding window algorithm (infrastructure ready in Redis)           |

---

## Quick Start

### Prerequisites

- Python 3.14+
- PostgreSQL 17+
- Redis 7+
- RabbitMQ 3.12+
- Docker & Docker Compose (optional, for full stack)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/0ralo/smart-http-requester.git
cd smart-http-requester
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -e .
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your database/Redis/RabbitMQ configuration
```

5. **Run database migrations**
```bash
psql -U dev -d development -f migrations/0001_initialization.sql
psql -U dev -d development -f migrations/0002_token_and_roles.sql
psql -U dev -d development -f migrations/0003_task_notify_trigger.sql
```

6. **Start the server**
```bash
python -m uvicorn application:app --reload
```

The API will be available at `http://localhost:8000`
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Metrics Endpoint**: http://localhost:8000/v1/metrics

---

## Docker Deployment

### Full Stack (API + All Services)

```bash
docker-compose -f docker-compose.yml up -d
```

This starts:
- **FastAPI**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **RabbitMQ Admin**: http://localhost:15672 (guest/guest)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

---

## Monitoring

### Prometheus & Grafana

When running the full stack (`docker-compose.yml`):

- **Prometheus UI**: http://localhost:9090
  - View metrics: http://localhost:9090/graph
  - Query examples: `http_requests_total`, `tasks_in_queue`, `http_request_duration_seconds`

- **Grafana Dashboards**: http://localhost:3000
  - Default credentials: `admin` / `admin`
  - Prometheus is pre-configured as data source
  - Import dashboards or create custom ones

### Available Metrics

**HTTP Metrics:**
- `http_requests_total` – Counter by method, endpoint, status
- `http_request_duration_seconds` – Request latency distribution
- `http_request_size_bytes` – Request payload sizes
- `http_response_size_bytes` – Response payload sizes
- `http_requests_in_progress` – Active request gauge

**Task Metrics:**
- `tasks_created_total` – Counter of submitted tasks
- `tasks_completed_total` – Counter by completion status
- `tasks_in_queue` – Current queue depth gauge

**Auth Metrics:**
- `auth_attempts_total` – Counter by operation (register/login) and outcome

For detailed metrics documentation, see [PROMETHEUS_METRICS.md](PROMETHEUS_METRICS.md).

---

## Authentication Strategy

### Why Opaque Tokens Instead of JWT?

This project uses **opaque sessions** for authentication because:

✅ **Instant revocation** – Logout takes effect immediately (no 5-15 minute delay)  
✅ **Single token format** – No refresh token complexity  
✅ **Infrastructure reuse** – Redis already in the stack for caching

**JWT Trade‑offs:**
- Requires long expiry for good UX (exposes revocation window)
- Hybrid approach (JWT + Redis blacklist) adds complexity
- No real benefit for this use case where auth service is always available

### Token Lifecycle

1. **Register**: `POST /v1/auth/register` → UUID token
2. **Login**: `POST /v1/auth/login` → existing or new session token
3. **Refresh**: `POST /v1/auth/refresh` → extends expiry by 7 days
4. **Logout**: `POST /v1/auth/logout` → token immediately deleted
5. **Revocation**: Admins can invalidate tokens instantly (no delay)

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest tests/test_auth.py -v

# Run async tests
pytest -v --asyncio-mode=auto
```

Key test files:
- `tests/test_auth.py` – Authentication endpoints
- `tests/test_requests.py` – HTTP request management
- `tests/test_metrics.py` – Prometheus metrics collection

---

## Project Structure

```
smart-http-requester/
├── api/v1/                     # API routes
│   ├── auth.py                 # Auth endpoints
│   ├── requests.py             # HTTP request endpoints
│   └── metrics.py              # Prometheus export
├── core/                        # Business logic
│   ├── auth.py                 # Auth domain logic
│   └── task.py                 # Task execution logic
├── domain/                      # Data models & exceptions
│   ├── auth.py                 # Auth domain entities
│   └── tasks.py                # Task domain entities
├── repository/                  # Database access layer
│   ├── auth.py                 # Auth queries
│   └── task.py                 # Task queries
├── schemas/                     # Pydantic request/response models
│   ├── auth.py                 # Auth schemas
│   └── task.py                 # Task schemas
├── services/                    # External integrations
│   ├── database.py             # PostgreSQL connection pool
│   ├── redis.py                # Redis client & pub/sub
│   ├── rabbitmq.py             # RabbitMQ message queue
│   ├── metrics.py              # Prometheus metric definitions
│   └── pg_poller.py            # PostgreSQL LISTEN/NOTIFY
├── middleware/                  # HTTP middleware
│   ├── auth.py                 # Token validation
│   └── metrics.py              # Request metrics collection
├── migrations/                  # Database migrations
├── docker/                      # Docker configuration files
├── application.py              # FastAPI app initialization
├── config.py                   # Environment configuration
└── README.md                   # This file
```

---

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Format & lint

```bash
# Black code formatting
black .

# Ruff linting
ruff check . --fix
```

### Generate OpenAPI schema

```bash
curl http://localhost:8000/api/openapi.json > schema.json
```

---

## Performance Characteristics

### Throughput
- **Single instance**: ~500-1000 req/s (depends on task complexity)
- **Horizontal scaling**: Add more API instances behind load balancer

### Latency
- **Task creation**: < 50ms
- **Task retrieval**: < 10ms
- **Status notification**: < 100ms (API query)  

### Resource Usage
- **Memory**: ~150MB (minimal, stateless)
- **Connections**: 
  - 1 PostgreSQL connection pool (min 5, max 20)
  - 1 Redis connection
  - 1 RabbitMQ connection

---

## License

MIT License – See LICENSE file for details

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Support

For issues, questions, or feature requests, please open an issue on GitHub.