# ADR-005: Implement Retries Using RabbitMQ Dead-Letter Exchanges and TTL

**Status:** *Accepted* (2026-07-20)

**Context:**  
HTTP tasks may fail due to transient issues (network timeouts, external service downtime). The system must retry failed tasks up to `max_attempts` with **exponential backoff** (1s, 2s, 4s, 8s, 16s, 32s, 64s). The retry mechanism must not block workers during the waiting period.

**Decision:**  
Implement retries using **RabbitMQ Dead Letter Exchanges (DLX) with per-queue TTL**. Create a chain of delay queues (`delay-1s`, `delay-2s`, `delay-4s`, ..., `delay-64s`). Each queue has a TTL equal to its delay. After TTL expires, messages are dead-lettered to the main work queue.

**Rationale:**
- **No Worker Blocking:** Workers immediately acknowledge failed messages and publish them to the appropriate delay queue. Workers remain free to process other tasks while waiting.
- **Strict Order Independence:** Using per-queue TTL avoids the "head-of-line blocking" issue where a single long-delay message at the front of a queue blocks all shorter-delay messages behind it (common with per-message TTL).
- **Native RabbitMQ:** Does not require external plugins (like `rabbitmq-delayed-message-plugin`), keeping the `docker-compose` setup simple and portable.
- **Durability:** Delay queues can be made durable, so pending retries survive broker restarts.

**Alternatives Considered:**
- **Per-Message TTL:** Simplifies configuration but causes head-of-line blocking (messages expire only from the front of the queue, so a short TTL message behind a long TTL message waits).
- **Delayed Message Plugin:** Cleaner but requires extra installation; violates "keep it simple for a pet project".
- **Worker-side `time.sleep()`:** Blocks worker goroutines/threads, reducing concurrency and wasting resources.

**Consequences:**
- **Positive:** Workers stay busy, precise exponential backoff, no head-of-line blocking, no external plugins.
- **Negative:** Requires creating 7 predefined delay queues (more operational setup). Maximum delay is fixed at 64s (cannot exceed without adding more queues).
