### ADR-001: Use RabbitMQ for Asynchronous Processing

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

The system accepts HTTP requests from users to schedule outbound HTTP calls to third-party services. These calls may take anywhere from a few milliseconds to several minutes, depending on the target service's responsiveness and network conditions. Holding the HTTP connection open between the client and our API for the entire duration would:

- **Reduce throughput** — each connection consumes resources on the API server
- **Expose clients to failures** — any timeout or error in the target service would become a 5xx error visible to the caller
- **Complicate retry logic** — clients would need to implement their own retry mechanisms

Additionally, the system is expected to handle bursts of task creation (e.g., users scheduling hundreds of tasks simultaneously) while maintaining predictable performance.

**Problem:**

We need a mechanism to decouple request acceptance from task execution, enabling:

- Immediate acknowledgment to clients that their task has been accepted
- Independent scaling of API and execution layers
- Reliable delivery of tasks even if workers are temporarily unavailable
- Built-in support for retries with delays

**Decision:**

Use **RabbitMQ** as the message broker for all task distribution between API and workers.

**Alternatives Considered:**

| Alternative                                | Why Rejected                                                                                                                                                                                                                                                                            |
|--------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Apache Kafka**                           | Provides much higher throughput (millions of messages/sec) but is designed for event streaming, not task distribution. No built-in TTL or Dead Letter Exchange for retries. Would require implementing retry logic in the consumer, which complicates workers. Overkill for this scale. |
| **Redis Streams**                          | Faster and simpler for basic queueing, but lacks persistent storage guarantees (data can be lost on restart). No native retry mechanism or DLX. Using it would require building a separate scheduler service, increasing system complexity.                                             |
| **AWS SQS**                                | Fully managed, but introduces vendor lock-in. The project must remain deployable with `docker-compose` for portfolio demonstration.                                                                                                                                                     |
| **In-memory queue (Python `queue.Queue`)** | Only works within a single process. Does not support distributed workers, persistence, or horizontal scaling.                                                                                                                                                                           |

**Trade-offs:**

| Pros                                                                                         | Cons                                                                                      |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| ✅ Natural backpressure — if workers are slow, messages pile up in queues, protecting the API | ❌ Broker becomes critical infrastructure — if RabbitMQ is down, no tasks can be processed |
| ✅ Independent deployments — API and workers can be deployed separately without coordination  | ❌ At-least-once delivery — workers must handle idempotency (duplicate processing)         |
| ✅ Horizontal scaling — any number of workers can consume from the same queue                 | ❌ Message ordering is not guaranteed between multiple consumers                           |
| ✅ Retry support via DLX without requiring worker-side timers                                 | ❌ Additional operational complexity (monitoring queues, managing exchanges)               |
| ✅ Durable queues — messages survive broker restarts                                          | ❌ Adds another component to `docker-compose.yml` (overhead for local development)         |

**Non-goals:**

- RabbitMQ is **not** intended for long-term event storage (messages are deleted after acknowledgment)
- RabbitMQ is **not** used as an analytics pipeline or event sourcing log
- Event replay is outside the project scope (we don't need to reprocess historical tasks)
- We are not optimizing for maximum throughput (thousands of messages per second is sufficient)

**Consequences:**

- **Positive:** Reliable decoupling, built-in retry mechanism via DLX, easy to scale workers horizontally, natural backpressure
- **Negative:** At-least-once delivery means workers must be idempotent; broker becomes single point of failure; additional monitoring required

**References:**

- RabbitMQ Dead Letter Exchanges: https://www.rabbitmq.com/docs/dlx
- RabbitMQ Reliability Guide: https://www.rabbitmq.com/docs/reliability