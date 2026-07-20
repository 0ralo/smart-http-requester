# ADR-002: Trennung von API und Workern in unabhängige Dienste

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

Das System hat zwei unterschiedliche Verantwortlichkeiten mit grundlegend verschiedenen betrieblichen Eigenschaften:

1. **API-Schicht** (Python FastAPI):
   - Verarbeitet HTTP-Anfragen von Benutzern
   - Führt Authentifizierung durch (JWT-Erzeugung/Validierung)
   - Validiert Task-Definitionen (URL, Header, Body-Format)
   - Schreibt Task-Datensätze in PostgreSQL
   - Veröffentlicht Task-IDs an RabbitMQ
   - Kurzlebige, CPU-arme Operationen

2. **Worker-Schicht** (Go und Rust):
   - Konsumiert Task-IDs von RabbitMQ
   - Führt ausgehende HTTP-Aufrufe an externe Dienste durch
   - Implementiert Wiederholungslogik mit exponentiellem Backoff
   - Aktualisiert Task-Status in PostgreSQL
   - Kann hochkonkurrente Netzwerk-E/A durchführen
   - Kann bei der Verarbeitung vieler paralleler Anfragen CPU-gebunden sein

Diese Schichten haben unterschiedliche Skalierungsanforderungen:

- API skaliert basierend auf der eingehenden Anfragenrate (Anzahl der Benutzer)
- Worker skaliert basierend auf der Queue-Tiefe (Anzahl der ausstehenden Tasks)

**Problem:**

Sollen diese beiden Verantwortlichkeiten als einzelner Dienst oder als separate, unabhängige Dienste bereitgestellt werden?

**Entscheidung:**

Die Python FastAPI-Anwendung als eigenständigen Webservice bereitstellen und die Go- und Rust-Worker als separate, unabhängige Dienste (Container) bereitstellen.

**Betrachtete Alternativen:**

| Alternative                                                       | Warum abgelehnt                                                                                                                                                                                                                                                  |
|-------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Monolith (einzelner Python-Dienst)**                            | Einfacher zu entwickeln, leidet jedoch unter Pythons GIL (Global Interpreter Lock) — parallele HTTP-Anfragen von Workern würden API-Threads blockieren. Kann Komponenten nicht unabhängig skalieren. Wenn Worker hohe CPU-Last verursachen, leidet auch die API. |
| **Alle Worker nur in Python**                                     | Pythons `asyncio` kann E/A-Konkurrenz bewältigen, aber CPU-gebundene Operationen und hohe Parallelität sind durch die GIL immer noch begrenzt. Verbirgt, dass Worker sprachunabhängig sind.                                                                      |
| **API + Worker im selben Container aber verschiedenen Prozessen** | Funktioniert, erschwert jedoch die Ressourcenzuteilung. Kann API vs. Worker nicht unabhängig skalieren. Wenn der Container neu startet (z.B. durch Worker-Absturz), startet auch die API neu.                                                                    |

**Abwägungen:**

| Vorteile                                                                                                       | Nachteile                                                                               |
|----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| ✅ Optimale Ressourcennutzung — API kann klein sein (2-4 Replikate), Worker können viele sein (10-20 Replikate) | ❌ Erhöhte Betriebskomplexität — mehr Container in `docker-compose.yml` zu orchestrieren |
| ✅ Unabhängige Skalierung — API und Worker skalieren basierend auf unterschiedlichen Metriken                   | ❌ Dienst-zu-Dienst-Kommunikation über RabbitMQ erfordert sorgfältiges Nachrichtendesign |
| ✅ Fehlerisolation — ein Absturz in Workern beeinflusst die API-Verfügbarkeit nicht                             | ❌ Komplexeres Logging (benötigt Korrelations-IDs über Dienste hinweg)                   |
| ✅ Technologieflexibilität — Worker können in jeder Sprache umgeschrieben werden, ohne die API zu beeinflussen  | ❌ Zusätzliche Netzwerklatenz (Nachricht von API → RabbitMQ → Worker)                    |
| ✅ Unabhängige Bereitstellung — neue Workerversion kann ohne API-Neustart bereitgestellt werden                 | ❌ Erfordert die Verwaltung von zwei separaten Dockerfiles/CI-Pipelines                  |

**Konsequenzen:**

- **Positiv:** Optimale Ressourcennutzung, unabhängige Skalierung, Fehlerisolation, Technologieflexibilität, unabhängige Bereitstellungen
- **Negativ:** Erhöhte Betriebskomplexität, Kommunikation zwischen Diensten erfordert sorgfältiges Design, zusätzliche Überwachung für mehrere Dienste erforderlich

**Referenzen:**

- Microservices vs Monolith: https://martinfowler.com/articles/microservices.html
- Python GIL Limitations: https://realpython.com/python-gil/