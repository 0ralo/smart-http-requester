# ADR-002: Separate API and Workers into Independent Services

**Status:** *Accepted* (2026-07-20)

**Context:**  
We have two distinct responsibilities: (1) accepting and validating user requests (API), and (2) executing HTTP tasks (workers). These have different performance characteristics, scaling requirements, and resource profiles.

**Decision:**  
Deploy the **Python FastAPI application** as a standalone web service, and deploy **Go and Rust workers** as separate, independent services (containers).

**Rationale:**
- **Performance Optimization:** Python is I/O-bound and slower for CPU-intensive concurrent execution. Go and Rust excel at high-concurrency network I/O, making them ideal for workers that perform many parallel HTTP requests.
- **Independent Scaling:** The API can scale separately from workers based on incoming request rates; workers can scale based on queue depth (number of pending tasks in RabbitMQ).
- **Technology Showcase:** This architecture demonstrates proficiency in multiple languages (Python + Go + Rust) and microservices design, which is attractive to future employers.
- **Failure Isolation:** A crash or slowdown in workers does not affect API availability (and vice versa).

**Alternatives Considered:**
- **Monolith (Single Python App):** Simpler but would suffer from GIL limitations, poor CPU utilization for concurrent requests, and inability to scale components independently.
- **All workers in Python only:** Hides knowledge of compiled languages; less impressive for a portfolio.

**Consequences:**
- **Positive:** Optimal resource usage, independent deployments, showcase of polyglot architecture.
- **Negative:** Increased operational complexity (more containers to orchestrate, inter-service communication via RabbitMQ requires careful message design).