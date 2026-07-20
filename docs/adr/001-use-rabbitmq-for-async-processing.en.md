# ADR-001: Use RabbitMQ for Asynchronous Processing

**Status:** *Accepted* (2026-07-20)

**Context:**  
The system accepts HTTP requests to schedule tasks. These tasks involve making outbound HTTP calls to external services. Performing these calls synchronously within the API request/response cycle would introduce high latency, block the API gateway, and make the system fragile under load. We need a reliable, persistent message broker to decouple request acceptance from task execution.

**Decision:**  
Use **RabbitMQ** as the message broker for all task distribution.

**Rationale:**
- **TTL & Dead Letter Exchange (DLX):** RabbitMQ natively supports message TTL and DLX, which perfectly enables our exponential retry strategy without requiring additional infrastructure (like a separate scheduler).
- **Smart Routing:** RabbitMQ's exchange types (direct, topic, fanout) give flexibility for future extensions (e.g., priority queues, different worker pools for different task types).
- **Maturity & Stability:** It's battle-tested in production environments and supports persistent messages (durable queues) to prevent data loss between API and workers.
- **Simplicity:** Python's `pika` and Go/Rust clients are well-documented and easy to implement, lowering the learning curve for a pet project.

**Alternatives Considered:**
- **Apache Kafka:** Provides high throughput and event streaming but adds unnecessary complexity for simple task distribution. No built-in TTL/DLX for retries; would require custom implementation.
- **Redis Streams:** Faster but less reliable for persistence; lacks advanced routing and dead-letter capabilities out-of-the-box.
- **AWS SQS:** Vendor lock-in; we want to keep the project self-contained and deployable with Docker Compose.

**Consequences:**
- **Positive:** Reliable decoupling, built-in retry mechanism, easy to scale workers horizontally.
- **Negative:** Adds operational overhead (managing RabbitMQ cluster). Requires careful configuration of queues, exchanges, and bindings to avoid message loss.

---

# ADR-001: Verwendung von RabbitMQ für die asynchrone Verarbeitung (DE)

**Status:** *Akzeptiert* (2026-07-20)

**Kontext:**  
Das System akzeptiert HTTP-Anfragen zur Planung von Aufgaben, die ausgehende HTTP-Aufrufe an externe Dienste beinhalten. Eine synchrone Ausführung würde die API blockieren und die Latenz erhöhen. Benötigt wird ein zuverlässiger, persistenter Message-Broker zur Entkopplung.

**Entscheidung:**  
Einsatz von **RabbitMQ** als Message-Broker für die Aufgabenverteilung.

**Begründung:**
- **TTL & DLX:** Native Unterstützung für Message-TTL und Dead-Letter-Exchanges, ideal für unsere exponentielle Wiederholungsstrategie.
- **Flexibles Routing:** Verschiedene Exchange-Typen erlauben zukünftige Erweiterungen (z.B. Prioritätswarteschlangen).
- **Bewährtheit:** Produktionserprobt, unterstützt persistente Nachrichten gegen Datenverlust.
- **Einfache Integration:** Verfügbare Clients für Python, Go und Rust.

**Alternativen:**
- **Apache Kafka:** Zu komplex für einfache Aufgabenverteilung; keine eingebaute TTL/DLX.
- **Redis Streams:** Weniger zuverlässig bei Persistenz; fehlende Dead-Letter-Funktionen.
- **AWS SQS:** Vendor-Lock-in; Wunsch nach Docker-Compose-Deployment.

**Konsequenzen:**
- **Positiv:** Entkopplung, eingebaute Wiederholungen, horizontale Skalierbarkeit.
- **Negativ:** Zusätzlicher Betriebsaufwand, sorgfältige Konfiguration erforderlich.

---

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