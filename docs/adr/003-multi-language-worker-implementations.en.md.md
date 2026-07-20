# ADR-003: Support Multiple Worker Implementations (Go and Rust)

**Status:** *Accepted* (2026-07-20)

**Context:**  
The system requires workers to consume tasks from RabbitMQ, perform HTTP requests, and handle retries. We have the opportunity to implement the same worker logic in different programming languages to demonstrate versatility.

**Decision:**  
Implement **two separate worker services**: one in **Go** and one in **Rust**. Both are functionally identical and can run simultaneously, competing for tasks from the same RabbitMQ queue.

**Rationale:**
- **Skill Demonstration:** Shows employers competency in both a mainstream compiled language (Go) and a modern systems language with memory safety guarantees (Rust).
- **Performance Comparison:** The project can serve as a benchmark to compare performance (latency, memory usage, CPU) between Go and Rust workers under load.
- **Resilience & Redundancy:** If one worker implementation has a bug or crashes, the other language worker can continue processing tasks.
- **Easy Integration:** Both languages have mature RabbitMQ client libraries (Go: `amqp091-go`, Rust: `lapin` or `amqprs`).

**Alternatives Considered:**
- **Single Implementation (Go only):** Simpler but less impressive; fails to showcase Rust skills.
- **Single Implementation (Rust only):** Would hide Go experience; Rust has a steeper learning curve for future maintainers.

**Consequences:**
- **Positive:** Demonstrates polyglot development, redundancy, benchmarking opportunities.
- **Negative:** Doubles maintenance effort (two codebases to update); must ensure both respect the same protocol (message format, UUID handling).
