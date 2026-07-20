### ADR-006: Observability with Prometheus and Grafana

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

The system consists of multiple services (API, multiple workers, RabbitMQ, Redis, PostgreSQL). Without observability, it is impossible to:

- Understand system behavior under load
- Detect performance degradation early
- Debug failures across distributed services
- Track business metrics (tasks created, tasks failed, retry rates)

The system must expose metrics that can be collected, stored, and visualized.

**Problem:**

Choose an observability stack that:

- Works with our existing Docker Compose deployment
- Does not require external SaaS services
- Is lightweight enough for local development
- Align with commonly adopted monitoring practices in containerized environments

**Decision:**

Use **Prometheus** (metrics collection + storage) and **Grafana** (visualization + dashboards). Prometheus follows a **pull model** — it scrapes metrics from service endpoints at regular intervals.

**Why Prometheus?**

- **Pull model** — services expose metrics via HTTP endpoints; Prometheus scrapes them. This avoids configuration drift (services don't need to know where to push).
- **Multi-dimensional data model** — metrics can have labels (`status="500"`, `method="POST"`), enabling rich queries.
- **Built-in alerting** — Prometheus AlertManager can send alerts based on metric thresholds.
- **Wide ecosystem** — many services (RabbitMQ, PostgreSQL, Redis) have pre-built Prometheus exporters.

**Why Grafana?**

- **Rich visualizations** — dashboards with time-series graphs, heatmaps, tables
- **Multi-data-source** — can also query PostgreSQL if needed
- **Alerting** — complementary to Prometheus
- **Used in production** — industry standard

**Alternatives Considered:**

| Alternative                                                    | Why Rejected                                                                                                                                  |
|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **OpenTelemetry + Jaeger**                                     | Focuses on tracing, not metrics. Good for distributed tracing, but our current use case needs metrics first. Could be added later as ADR-007. |
| **ELK Stack (Elasticsearch, Logstash, Kibana)**                | Better for log aggregation than metrics. Overkill for a pet project (requires more memory and resources).                                     |
| **Cloud-native solutions (Datadog, New Relic, Grafana Cloud)** | Excellent tools, but violate the "self-contained, docker-compose" requirement. Also introduce cost and vendor lock-in.                        |
| **StatsD + Graphite**                                          | Older pull model; less flexible than Prometheus.                                                                                              |

**Trade-offs:**

| Pros                                                                                | Cons                                                                                                                           |
|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| ✅ Pull model avoids services knowing about monitoring infrastructure                | ❌ Need to expose `/metrics` endpoints from each service (adds code complexity)                                                 |
| ✅ Rich ecosystem of exporters for Redis, RabbitMQ, PostgreSQL, and our own services | ❌ Prometheus uses disk storage (must manage retention)                                                                         |
| ✅ Industry standard — shows knowledge of production monitoring                      | ❌ Requires additional containers (Prometheus, Grafana) in `docker-compose.yml`                                                 |
| ✅ Grafana dashboards can be version-controlled as JSON files                        | ❌ Not designed for long-term storage (we don't need years of history for a pet project)                                        |
| ✅ Alerting built-in (via AlertManager)                                              | ❌ Pull model means metrics are scraped at intervals, not real-time (but sub-second granularity is sufficient for this project) |

**Metrics to Expose:**

| Service               | Metrics                                                                                                               |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------|
| **API**               | Request count per endpoint, latency (histogram), error rate, authenticated users, tasks created rate, rate limit hits |
| **Workers (Go/Rust)** | Tasks consumed rate, tasks completed, tasks failed, HTTP request latency, retries triggered, queue depth              |
| **RabbitMQ**          | Queue length, message rates, consumer count, DLX messages                                                             |
| **PostgreSQL**        | Connection pool usage, query latency, active queries                                                                  |
| **Redis**             | Memory usage, hit rate, command latency                                                                               |

**Consequences:**

- **Positive:** Production-ready observability, industry-standard tools, rich dashboards, ability to detect issues early
- **Negative:** Additional containers to run; need to instrument code with Prometheus client libraries; disk storage for metrics; learning curve for PromQL queries

**References:**

- Prometheus Overview: https://prometheus.io/docs/introduction/overview/
- Grafana: https://grafana.com/oss/grafana/
- RabbitMQ Prometheus Plugin: https://www.rabbitmq.com/docs/prometheus
- Redis Prometheus Exporter: https://github.com/oliver006/redis_exporter
- PostgreSQL Prometheus Exporter: https://github.com/prometheus-community/postgres_exporter