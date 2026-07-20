### ADR-003: Support Multiple Worker Implementations (Go and Rust)

---

**Status:** *Accepted* (2026-07-20)

---

**Context:**

The system defines a clear messaging contract between the API and workers:

- Message format: `{ "task_uuid": "550e8400-e29b-41d4-a716-446655440000" }`
- Communication protocol: AMQP 0-9-1 (RabbitMQ)
- Task execution logic: Consume UUID → Fetch from PostgreSQL → Execute HTTP request → Update status → Handle retries

The messaging contract is independent of any specific programming language. Any client that can speak AMQP and understand the message format can be a worker.

**Problem:**

We have the opportunity to implement workers in multiple languages. Should we maintain a single worker implementation, or support multiple language implementations?

**Decision:**

Implement **two separate worker services**: one in **Go** and one in **Rust**. Both are functionally identical, consume from the same RabbitMQ queue, and can run simultaneously.

**Alternatives Considered:**

| Alternative                                                            | Why Rejected                                                                                                                        |
|------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **Single implementation (Go only)**                                    | Simplifies maintenance but does not validate that the messaging protocol is truly language-agnostic.                                |
| **Single implementation (Rust only)**                                  | Rust has a steeper learning curve and longer compile times, which may slow development. Does not demonstrate protocol independence. |
| **Single implementation with both languages but via a shared library** | Mixes concerns; the whole point is to show that the protocol itself is sufficient, not to share code between languages.             |

**Trade-offs:**

| Pros                                                                                                     | Cons                                                                               |
|----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| ✅ Validates that the messaging contract is truly language-agnostic                                       | ❌ Doubles maintenance effort (two codebases, two dependency sets)                  |
| ✅ Enables performance benchmarking between Go and Rust under identical workloads                         | ❌ Must ensure both implementations handle message formats identically              |
| ✅ Reduces bus factor — if one language falls out of favor, the other remains viable                      | ❌ Increases CI/CD complexity (build both images)                                   |
| ✅ Allows experimentation — can test new features in one implementation before porting to another         | ❌ Potential for subtle bugs if one implementation misinterprets the message format |
| ✅ Demonstrates that workers are loosely coupled through the messaging protocol, not through code sharing | ❌ Developers need familiarity with both languages to review changes                |
**Consequences:**

- **Positive:** Validates protocol agnosticism, enables performance benchmarking, reduces bus factor, allows experimentation
- **Negative:** Doubles maintenance effort, requires careful coordination of message format changes, increases CI/CD complexity

**References:**

- AMQP 0-9-1 Specification: https://github.com/rabbitmq/amqp-0.9.1-spec
- Go RabbitMQ Client: https://github.com/rabbitmq/amqp091-go
- Rust RabbitMQ Client: https://crates.io/crates/lapin