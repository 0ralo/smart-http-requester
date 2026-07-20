### ADR-002: Separate API and Workers into Independent Services

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

The system has two distinct responsibilities with fundamentally different operational characteristics:

1. **API Layer** (Python FastAPI):
   - Handles HTTP requests from users
   - Performs authentication (JWT generation/validation)
   - Validates task definitions (URL, headers, body format)
   - Writes task records to PostgreSQL
   - Publishes task IDs to RabbitMQ
   - Has short-lived, low-CPU operations

2. **Worker Layer** (Go and Rust):
   - Consumes task IDs from RabbitMQ
   - Makes outbound HTTP calls to external services
   - Implements retry logic with exponential backoff
   - Updates task status in PostgreSQL
   - May perform high-concurrency network I/O
   - May be CPU-bound when processing many parallel requests

These layers have different scaling requirements:

- API scales based on incoming request rate (number of users)
- Worker scales based on queue depth (number of pending tasks)

**Problem:**

Should these two responsibilities be deployed as a single service or as separate, independent services?

**Decision:**

Deploy the Python FastAPI application as a standalone web service, and deploy Go and Rust workers as separate, independent services (containers).

**Alternatives Considered:**

| Alternative                                                 | Why Rejected                                                                                                                                                                                                                        |
|-------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Monolith (single Python service)**                        | Simpler to develop, but suffers from Python's GIL (Global Interpreter Lock) — parallel HTTP requests from workers would block API threads. Cannot scale components independently. If workers cause high CPU load, API also suffers. |
| **All workers in Python only**                              | Python's `asyncio` can handle I/O concurrency, but CPU-bound operations and high parallelism are still limited by GIL. Hides the fact that workers are language-agnostic.                                                           |
| **API + workers in same container but different processes** | Works but complicates resource allocation. Cannot independently scale API vs workers. If container restarts (e.g., due to worker crash), API also restarts.                                                                         |

**Trade-offs:**

| Pros                                                                                             | Cons                                                                                        |
|--------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| ✅ Optimal resource usage — API can be small (2-4 replicas), workers can be many (10-20 replicas) | ❌ Increased operational complexity — more containers to orchestrate in `docker-compose.yml` |
| ✅ Independent scaling — API and workers scale based on different metrics                         | ❌ Inter-service communication via RabbitMQ requires careful message design                  |
| ✅ Failure isolation — a crash in workers does not affect API availability                        | ❌ More complex logging (need correlation IDs across services)                               |
| ✅ Technology flexibility — workers can be rewritten in any language without affecting API        | ❌ Additional network latency (message from API → RabbitMQ → worker)                         |
| ✅ Independent deployment — can deploy new worker version without restarting API                  | ❌ Requires managing two separate Dockerfiles/CI pipelines                                   |

**Consequences:**

- **Positive:** Optimal resource usage, independent scaling, failure isolation, technology flexibility, independent deployments
- **Negative:** Increased operational complexity, inter-service communication requires careful design, additional monitoring needed for multiple services

**References:**

- Microservices vs Monolith: https://martinfowler.com/articles/microservices.html
- Python GIL limitations: https://realpython.com/python-gil/