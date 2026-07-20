# ADR-002: Trennung von API und Workern in unabhängige Dienste (DE)

**Status:** *Akzeptiert* (2026-07-20)

**Kontext:**  
Zwei unterschiedliche Verantwortlichkeiten: (1) Annahme von Anfragen (API), (2) Ausführung von HTTP-Tasks (Worker). Unterschiedliche Leistungsanforderungen.

**Entscheidung:**  
Python-FastAPI als eigenständiger Webservice; Go- und Rust-Worker als separate, unabhängige Container.

**Begründung:**
- **Performance:** Python langsamer bei paralleler Ausführung; Go/Rust optimal für viele parallele HTTP-Requests.
- **Unabhängiges Skalieren:** API basierend auf Anfragen, Worker basierend auf Queue-Tiefe skalierbar.
- **Technologie-Demonstration:** Beherrschung mehrerer Sprachen (Python+Go+Rust) und Microservices-Design.
- **Fehlerisolation:** Abstürze im Worker beeinflussen die API nicht.

**Alternativen:**
- **Monolith (nur Python):** GIL-Einschränkungen, schlechtere CPU-Auslastung, keine unabhängige Skalierung.
- **Nur Python-Worker:** Versteckt Kenntnisse über kompilierte Sprachen.

**Konsequenzen:**
- **Positiv:** Optimale Ressourcennutzung, unabhängige Deployments, Polyglot-Architektur.
- **Negativ:** Höhere Betriebskomplexität (mehr Container, Kommunikation über RabbitMQ).