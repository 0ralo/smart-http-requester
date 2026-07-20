# ADR-004: Use Redis for Distributed Rate Limiting

**Status:** *Accepted* (2026-07-20)

**Context:**
The API accepts HTTP requests from potentially many users. Without rate limiting, a single user could flood the system with task creation requests, causing resource exhaustion and degrading service quality for others. The rate limiter must work across multiple API instances (if scaled horizontally).

**Decision:**
Implement rate limiting using **Redis** with an **atomic Lua script** implementing the **Sliding Window** algorithm with a configurable coefficient.

**Rationale:**
- **Performance:** Redis is in-memory and extremely fast (sub-millisecond latency), ideal for per-request rate checks without adding significant overhead.
- **Atomicity:** Lua scripts in Redis execute atomically, preventing race conditions where two concurrent requests could both pass the limit check.
- **Distributed:** Redis acts as a central state store, so rate limits are consistent across all API replicas (unlike in-memory limits per instance).
- **Industry Standard:** Redis is widely used for rate limiting and caching, demonstrating knowledge of common infrastructure patterns.
- **Sliding Window Accuracy:** More precise than Fixed Window (no burst at boundaries); the coefficient allows tuning strictness.

**Alternatives Considered:**
- **In-memory rate limiting (e.g., `slowapi` or `django-ratelimit`):** Does not work with multiple API replicas; state is lost on restart.
- **Rate limiting via nginx/API Gateway:** Less flexible; difficult to implement dynamic per-user limits or sliding window with Lua.
- **PostgreSQL row-level counters:** Too slow for high-frequency requests; adds unnecessary load to the main database.

**Consequences:**
- **Positive:** Fast, distributed, accurate sliding window, industry-proven solution.
- **Negative:** Adds Redis as another dependency (must be included in `docker-compose.yml`). Requires careful Lua script design to avoid performance pitfalls.