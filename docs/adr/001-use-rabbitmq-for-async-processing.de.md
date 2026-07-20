# ADR-001: Verwendung von RabbitMQ für die asynchrone Verarbeitung

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

Das System akzeptiert HTTP-Anfragen von Benutzern, um ausgehende HTTP-Aufrufe an Drittanbieterdienste zu planen. Diese Aufrufe können je nach Antwortverhalten des Zieldienstes und den Netzwerkbedingungen zwischen wenigen Millisekunden und mehreren Minuten dauern. Die Aufrechterhaltung der HTTP-Verbindung zwischen Client und API während der gesamten Dauer würde:

- **Den Durchsatz reduzieren** — jede Verbindung verbraucht Ressourcen auf dem API-Server
- **Clients Fehlern aussetzen** — jeder Timeout oder Fehler im Zieldienst würde als 5xx-Fehler für den Aufrufer sichtbar
- **Die Wiederholungslogik erschweren** — Clients müssten ihre eigenen Wiederholungsmechanismen implementieren

Darüber hinaus wird erwartet, dass das System Bursts von Task-Erstellungen verarbeiten kann (z.B. Benutzer, die Hunderte von Tasks gleichzeitig planen), während es eine vorhersehbare Leistung beibehält.

**Problem:**

Wir benötigen einen Mechanismus, um die Anfrageannahme von der Task-Ausführung zu entkoppeln, der ermöglicht:

- Sofortige Bestätigung an Clients, dass ihr Task angenommen wurde
- Unabhängige Skalierung der API- und Ausführungsschichten
- Zuverlässige Zustellung von Tasks, selbst wenn Worker vorübergehend nicht verfügbar sind
- Eingebaute Unterstützung für Wiederholungen mit Verzögerungen

**Entscheidung:**

Verwendung von **RabbitMQ** als Message-Broker für die gesamte Aufgabenverteilung zwischen API und Workern.

**Betrachtete Alternativen:**

| Alternative                                | Warum abgelehnt                                                                                                                                                                                                                                                                                                                                   |
|--------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Apache Kafka**                           | Bietet viel höheren Durchsatz (Millionen Nachrichten/Sekunde), ist jedoch für Event-Streaming konzipiert, nicht für Aufgabenverteilung. Kein eingebautes TTL oder Dead Letter Exchange für Wiederholungen. Würde die Implementierung der Wiederholungslogik im Consumer erfordern, was die Worker verkompliziert. Für diesen Maßstab übertrieben. |
| **Redis Streams**                          | Schneller und einfacher für einfaches Queueing, aber es fehlen garantierte Persistenzmechanismen (Daten können bei Neustart verloren gehen). Kein nativer Wiederholungsmechanismus oder DLX. Die Verwendung würde den Aufbau eines separaten Scheduler-Dienstes erfordern, was die Systemkomplexität erhöht.                                      |
| **AWS SQS**                                | Vollständig verwaltet, führt jedoch zu Vendor-Lock-in. Das Projekt muss für die Portfolio-Präsentation mit `docker-compose` bereitstellbar bleiben.                                                                                                                                                                                               |
| **In-Memory-Queue (Python `queue.Queue`)** | Funktioniert nur innerhalb eines einzelnen Prozesses. Unterstützt keine verteilten Worker, Persistenz oder horizontale Skalierung.                                                                                                                                                                                                                |

**Abwägungen:**

| Vorteile                                                                                                    | Nachteile                                                                                                  |
|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| ✅ Natürlicher Gegendruck — wenn Worker langsam sind, stauen sich Nachrichten in Queues und schützen die API | ❌ Broker wird zur kritischen Infrastruktur — wenn RabbitMQ ausfällt, können keine Tasks verarbeitet werden |
| ✅ Unabhängige Bereitstellungen — API und Worker können ohne Koordination separat bereitgestellt werden      | ❌ Mindestens-einmal-Zustellung — Worker müssen Idempotenz behandeln (doppelte Verarbeitung)                |
| ✅ Horizontale Skalierung — beliebig viele Worker können aus derselben Queue konsumieren                     | ❌ Nachrichtenreihenfolge ist bei mehreren Consumern nicht garantiert                                       |
| ✅ Wiederholungsunterstützung über DLX ohne worker-seitige Timer                                             | ❌ Zusätzliche Betriebskomplexität (Überwachung von Queues, Verwaltung von Exchanges)                       |
| ✅ Durable Queues — Nachrichten überleben Broker-Neustarts                                                   | ❌ Fügt eine weitere Komponente zu `docker-compose.yml` hinzu (Overhead für lokale Entwicklung)             |

**Nicht-Ziele:**

- RabbitMQ ist **nicht** für die langfristige Ereignisspeicherung vorgesehen (Nachrichten werden nach Bestätigung gelöscht)
- RabbitMQ wird **nicht** als Analytics-Pipeline oder Event-Sourcing-Log verwendet
- Event-Replay liegt außerhalb des Projektumfangs (wir müssen keine historischen Tasks erneut verarbeiten)
- Wir optimieren nicht für maximalen Durchsatz (Tausende von Nachrichten pro Sekunde sind ausreichend)

**Konsequenzen:**

- **Positiv:** Zuverlässige Entkopplung, eingebauter Wiederholungsmechanismus über DLX, einfache horizontale Skalierung der Worker, natürlicher Gegendruck
- **Negativ:** Mindestens-einmal-Zustellung bedeutet, dass Worker idempotent sein müssen; Broker wird zum Single Point of Failure; zusätzliche Überwachung erforderlich

**Referenzen:**

- RabbitMQ Dead Letter Exchanges: https://www.rabbitmq.com/docs/dlx
- RabbitMQ Reliability Guide: https://www.rabbitmq.com/docs/reliability