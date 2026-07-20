### ADR-004: Use Redis for Distributed Rate Limiting

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

The API accepts HTTP requests from potentially many users. Without rate limiting, a single user (or a malicious actor) could flood the system with task creation requests, causing:

- PostgreSQL connection pool exhaustion
- RabbitMQ queue overflow
- Resource starvation for legitimate users
- Degraded performance and potential denial-of-service

The rate limiter must work across multiple API instances if scaled horizontally. It must also be fast enough to not add significant overhead to each request.

**Problem:**

Implement a rate limiting mechanism that is:

- **Distributed** — works across multiple API replicas
- **Fast** — sub-millisecond per request
- **Accurate** — no burst at boundaries (unlike fixed window)
- **Configurable** — per-user limits with flexible window sizes

**Decision:**

Implement rate limiting using **Redis** with an **atomic Lua script** implementing the **Sliding Window** algorithm with a configurable coefficient.

**Why Sliding Window?**

| Algorithm          | Description                                               | Pros                         | Cons                                                                      | Why Not Here                                               |
|--------------------|-----------------------------------------------------------|------------------------------|---------------------------------------------------------------------------|------------------------------------------------------------|
| **Fixed Window**   | Count requests in fixed time windows (e.g., 60 seconds)   | Simple, low memory           | Burst at window boundaries (59th and 61st second can both pass)           | ❌ Inaccurate for strict limits                             |
| **Token Bucket**   | Tokens added at fixed rate; each request consumes a token | Smooths bursts, widely used  | Allows bursts up to bucket size; complex to implement atomically in Redis | ❌ Allows bursts, we want strict sliding window             |
| **Leaky Bucket**   | Requests queued and processed at fixed rate               | Smooths traffic completely   | Can introduce delays; less accurate for rate limiting of requests         | ❌ Introduces latency; designed for network traffic shaping |
| **Sliding Window** | Tracks exact request timestamps in a window               | Accurate, no boundary bursts | Higher memory usage (stores timestamps per user)                          | ✅ Best accuracy for our use case                           |

**Alternatives Considered:**

| Alternative                                                  | Why Rejected                                                                                                |
|--------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| **In-memory rate limiting (e.g., `slowapi` Python library)** | Does not work with multiple API replicas; state is per-instance.                                            |
| **Rate limiting via nginx/API Gateway**                      | Less flexible; difficult to implement dynamic per-user limits or sliding window with custom business rules. |
| **PostgreSQL row-level counters**                            | Too slow for high-frequency requests (disk I/O); adds unnecessary load to the main database.                |
| **Redis with SETEX and INCR (Fixed Window)**                 | Simpler, but suffers from boundary bursts.                                                                  |

**Trade-offs:**

| Pros                                                                          | Cons                                                                                                            |
|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| ✅ Sub-millisecond latency — Redis is in-memory                                | ❌ Adds Redis as another dependency (must be in `docker-compose.yml`)                                            |
| ✅ Atomic Lua scripts prevent race conditions between concurrent requests      | ❌ Lua script complexity — must be carefully written to avoid performance degradation                            |
| ✅ Distributed state — consistent limits across all API replicas               | ❌ Redis becomes a critical dependency — if Redis is down, rate limiting fails open or closed (choose carefully) |
| ✅ Sliding window accuracy — no burst at boundaries                            | ❌ Higher memory usage than fixed window (stores timestamps per user)                                            |
| ✅ Industry-standard pattern — demonstrates knowledge of common infrastructure | ❌ Requires additional monitoring (Redis memory, CPU)                                                            |
| ✅ Configurable coefficient — allows tuning strictness                         | ❌ Multi-key Lua scripts may block Redis if complex                                                              |

**Consequences:**

- **Positive:** Fast, distributed, accurate sliding window, industry-proven solution, atomic operations
- **Negative:** Adds Redis as a dependency; Lua script complexity; higher memory usage than fixed window; Redis becomes critical infrastructure

**References:**

- Redis Lua Scripting: https://redis.io/docs/latest/develop/programmability/eval-intro/
- Rate Limiting Algorithms: https://bytebytego.com/courses/system-design-interview/design-a-rate-limiter