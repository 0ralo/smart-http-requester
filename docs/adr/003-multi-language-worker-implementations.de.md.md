# ADR-003: Unterstützung mehrerer Worker-Implementierungen (Go und Rust) (DE)

**Status:** *Akzeptiert* (2026-07-20)

**Kontext:**  
Worker konsumieren Tasks von RabbitMQ, führen HTTP-Requests aus und behandeln Wiederholungen. Möglichkeit, dieselbe Logik in verschiedenen Sprachen zu implementieren.

**Entscheidung:**  
Zwei separate Worker-Dienste: einer in **Go**, einer in **Rust**. Funktionell identisch, laufen parallel und konkurrieren um Tasks aus derselben Queue.

**Begründung:**
- **Kompetenz-Demonstration:** Beherrschung von Go und Rust gegenüber Arbeitgebern.
- **Performance-Vergleich:** Benchmarking zwischen Go und Rust möglich.
- **Redundanz:** Wenn ein Worker abstürzt, kann der andere übernehmen.
- **Bibliotheken:** Ausgereifte RabbitMQ-Clients für beide Sprachen verfügbar.

**Alternativen:**
- **Nur Go:** Einfacher, aber weniger beeindruckend; Rust-Kenntnisse nicht sichtbar.
- **Nur Rust:** Versteckt Go-Erfahrung; steilere Lernkurve.

**Konsequenzen:**
- **Positiv:** Polyglot-Entwicklung, Redundanz, Benchmarking-Möglichkeiten.
- **Negativ:** Doppelter Wartungsaufwand, einheitliches Nachrichtenformat erforderlich.
