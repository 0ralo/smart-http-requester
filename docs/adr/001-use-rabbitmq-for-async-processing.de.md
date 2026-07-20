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
