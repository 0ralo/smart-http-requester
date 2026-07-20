# ADR-003: Unterstützung mehrerer Worker-Implementierungen (Go und Rust)

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

Das System definiert einen klaren Messaging-Vertrag zwischen API und Workern:

- Nachrichtenformat: `{ "task_uuid": "550e8400-e29b-41d4-a716-446655440000" }`
- Kommunikationsprotokoll: AMQP 0-9-1 (RabbitMQ)
- Task-Ausführungslogik: UUID konsumieren → Aus PostgreSQL abrufen → HTTP-Anfrage ausführen → Status aktualisieren → Wiederholungen behandeln

Der Messaging-Vertrag ist unabhängig von einer bestimmten Programmiersprache. Jeder Client, der AMQP sprechen und das Nachrichtenformat verstehen kann, kann ein Worker sein.

**Problem:**

Wir haben die Möglichkeit, Worker in mehreren Sprachen zu implementieren. Sollen wir eine einzige Worker-Implementierung pflegen oder mehrere Sprachimplementierungen unterstützen?

**Entscheidung:**

Implementierung von **zwei separaten Worker-Diensten**: einem in **Go** und einem in **Rust**. Beide sind funktional identisch, konsumieren aus derselben RabbitMQ-Queue und können gleichzeitig laufen.

**Betrachtete Alternativen:**

| Alternative                                                                    | Warum abgelehnt                                                                                                                               |
|--------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| **Einzelne Implementierung (nur Go)**                                          | Vereinfacht die Wartung, validiert aber nicht, dass das Messaging-Protokoll wirklich sprachunabhängig ist.                                    |
| **Einzelne Implementierung (nur Rust)**                                        | Rust hat eine steilere Lernkurve und längere Kompilierzeiten, was die Entwicklung verlangsamen kann. Zeigt nicht die Protokollunabhängigkeit. |
| **Einzelne Implementierung mit beiden Sprachen aber über eine Shared Library** | Vermischt Bedenken; der ganze Punkt ist zu zeigen, dass das Protokoll selbst ausreichend ist, nicht Code zwischen Sprachen zu teilen.         |

**Abwägungen:**

| Vorteile                                                                                                                            | Nachteile                                                                                          |
|-------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| ✅ Validiert, dass der Messaging-Vertrag wirklich sprachunabhängig ist                                                               | ❌ Verdoppelt den Wartungsaufwand (zwei Codebasen, zwei Abhängigkeitssätze)                         |
| ✅ Ermöglicht Performance-Benchmarking zwischen Go und Rust unter identischen Workloads                                              | ❌ Muss sicherstellen, dass beide Implementierungen Nachrichtenformate identisch behandeln          |
| ✅ Reduziert den Bus-Faktor — wenn eine Sprache aus der Mode kommt, bleibt die andere nutzbar                                        | ❌ Erhöht die CI/CD-Komplexität (beide Images müssen gebaut werden)                                 |
| ✅ Ermöglicht Experimente — neue Funktionen können in einer Implementierung getestet werden, bevor sie in die andere portiert werden | ❌ Potenzial für subtile Bugs, wenn eine Implementierung das Nachrichtenformat falsch interpretiert |
| ✅ Zeigt, dass Worker lose über das Messaging-Protokoll gekoppelt sind, nicht über Code-Sharing                                      | ❌ Entwickler benötigen Kenntnisse in beiden Sprachen, um Änderungen zu überprüfen                  |

**Konsequenzen:**

- **Positiv:** Validiert Protokoll-Agnostizismus, ermöglicht Performance-Benchmarking, reduziert Bus-Faktor, ermöglicht Experimente
- **Negativ:** Verdoppelt den Wartungsaufwand, erfordert sorgfältige Koordination von Nachrichtenformatänderungen, erhöht die CI/CD-Komplexität

**Referenzen:**

- AMQP 0-9-1 Specification: https://github.com/rabbitmq/amqp-0.9.1-spec
- Go RabbitMQ Client: https://github.com/rabbitmq/amqp091-go
- Rust RabbitMQ Client: https://crates.io/crates/lapin