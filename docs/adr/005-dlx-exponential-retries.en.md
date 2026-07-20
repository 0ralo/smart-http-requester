### ADR-005: Implement Retries Using RabbitMQ Dead-Letter Exchanges and TTL

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

HTTP tasks may fail due to transient issues:

- Target service returns 5xx errors (server overload, temporary unavailability)
- Network timeouts (DNS resolution, connection establishment, read/write timeouts)
- Rate limiting from the target service (429 Too Many Requests)

The system must retry failed tasks up to `max_attempts` (specified by the user) with **exponential backoff** (1s, 2s, 4s, 8s, 16s, 32s, 64s) to avoid overwhelming the target service during recovery.

The retry mechanism must not block workers during the waiting period. Workers should remain free to process other tasks.

**Problem:**

Implement an exponential backoff retry mechanism that:

- Does not block workers during waiting periods
- Ensures tasks are retried after precise delays
- Does not suffer from head-of-line blocking (where one delayed message blocks others)
- Survives worker restarts (durability)

**Decision:**

Implement retries using **RabbitMQ Dead Letter Exchanges (DLX) with per-queue TTL**. Create a chain of delay queues:

```
delay-1s → delay-2s → delay-4s → delay-8s → delay-16s → delay-32s → delay-64s
```

Each queue has a TTL equal to its delay. After TTL expires, messages are automatically dead-lettered to the next queue in the chain. The final queue dead-letters back to the main work queue.

**Alternatives Considered:**

| Alternative                                                        | Why Rejected                                                                                                                                                                                                                   |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Worker-side `time.sleep()` / `tokio::sleep()` / `time.After()`** | Blocks the worker goroutine/thread. If a worker sleeps for 64s, it cannot process any other tasks during that time. Reduces concurrency and wastes resources.                                                                  |
| **Per-message TTL (single delay queue)**                           | Simpler to configure (single queue with per-message TTL). However, messages expire only from the front of the queue — a message with 64s TTL at the front blocks messages behind it with shorter TTLs (head-of-line blocking). |
| **RabbitMQ Delayed Message Plugin**                                | Native support for delayed messages. However, requires installing a plugin (additional step for `docker-compose` setup). Overkill for a pet project.                                                                           |
| **External scheduler (e.g., Celery with Redis Beat)**              | Adds significant complexity. Requires separate scheduler process and state management.                                                                                                                                         |
| **PostgreSQL polling + scheduled tasks**                           | Heavy load on PostgreSQL (constant polling). Distributed locking required to prevent duplicate execution.                                                                                                                      |

**Trade-offs:**

| Pros                                                                                                      | Cons                                                                                           |
|-----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| ✅ Workers do not block — they immediately acknowledge failed messages and publish to delay queues         | ❌ Requires creating 7 predefined delay queues (operational setup)                              |
| ✅ No head-of-line blocking — each delay has its own queue, so short delays are not blocked by long delays | ❌ Maximum delay is fixed at 64s (cannot exceed without adding more queues)                     |
| ✅ No external plugins required — uses only native RabbitMQ features                                       | ❌ Messages move through multiple queues, adding overhead (each hop is a publish+consume cycle) |
| ✅ Durable queues — pending retries survive broker restarts                                                | ❌ Fixed delay steps (1,2,4,8,...) — cannot support custom delays per task                      |
| ✅ Natural separation of concerns — worker only handles execution, RabbitMQ handles timing                 | ❌ More complex to monitor (need to check multiple delay queues for backlogs)                   |
| ✅ Exponential backoff is built into the queue chain                                                       | ❌ If a delay queue is deleted accidentally, retries are lost                                   |

**Why not worker-side sleep?**

Worker-side sleeping is simpler to implement but fundamentally flawed for a concurrent system:

```
while attempts < max_attempts:
    if execute_task() == success:
        break
    time.sleep(backoff[attempts])  # Worker is blocked here
    attempts++
```

In Go, a sleeping goroutine still consumes memory (stack) and cannot process other tasks. In Rust, `tokio::sleep()` can yield the runtime, but the task is still occupying the executor. With 100 workers each sleeping for 64s, we waste potential processing capacity of 100 * 64s = 6400 seconds of work.

**Consequences:**

- **Positive:** Workers stay busy, precise exponential backoff, no head-of-line blocking, no external plugins, durable retries
- **Negative:** Requires 7 predefined delay queues, maximum delay fixed at 64s, more complex to monitor, messages hop through multiple queues

**References:**

- RabbitMQ Dead Letter Exchanges: https://www.rabbitmq.com/docs/dlx
- RabbitMQ TTL: https://www.rabbitmq.com/docs/ttl
- Head-of-line blocking explained: https://en.wikipedia.org/wiki/Head-of-line_blocking