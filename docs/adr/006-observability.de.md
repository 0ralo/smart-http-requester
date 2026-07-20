# ADR-006: Observability mit Prometheus und Grafana

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

Das System besteht aus mehreren Diensten (API, mehrere Worker, RabbitMQ, Redis, PostgreSQL). Ohne Observability ist es unmöglich:

- Das Systemverhalten unter Last zu verstehen
- Leistungsverschlechterungen frühzeitig zu erkennen
- Fehler über verteilte Dienste hinweg zu debuggen
- Geschäftsmetriken zu verfolgen (erstellte Tasks, fehlgeschlagene Tasks, Wiederholungsraten)

Das System muss Metriken exponieren, die gesammelt, gespeichert und visualisiert werden können.

**Problem:**

Auswahl eines Observability-Stacks, der:

- Mit unserer bestehenden Docker-Compose-Bereitstellung funktioniert
- Keine externen SaaS-Dienste erfordert
- Leicht genug für die lokale Entwicklung ist
- Mit allgemein üblichen Überwachungspraktiken in containerisierten Umgebungen übereinstimmt

**Entscheidung:**

Verwendung von **Prometheus** (Metriksammlung + -speicherung) und **Grafana** (Visualisierung + Dashboards). Prometheus folgt einem **Pull-Modell** — es sammelt Metriken in regelmäßigen Abständen von Dienst-Endpunkten.

**Warum Prometheus?**

- **Pull-Modell** — Dienste exponieren Metriken über HTTP-Endpunkte; Prometheus sammelt sie. Dies vermeidet Konfigurationsabweichungen (Dienste müssen nicht wissen, wohin sie pushen müssen).
- **Multidimensionales Datenmodell** — Metriken können Labels haben (`status="500"`, `method="POST"`), was reichhaltige Abfragen ermöglicht.
- **Eingebaute Alarmierung** — Prometheus AlertManager kann Alarme basierend auf Metrikschwellenwerten senden.
- **Großes Ökosystem** — viele Dienste (RabbitMQ, PostgreSQL, Redis) haben vorgefertigte Prometheus-Exporter.

**Warum Grafana?**

- **Reichhaltige Visualisierungen** — Dashboards mit Zeitreihendiagrammen, Heatmaps, Tabellen
- **Multi-Data-Source** — kann bei Bedarf auch PostgreSQL abfragen
- **Alarmierung** — ergänzend zu Prometheus
- **In der Produktion verwendet** — Branchenstandard

**Betrachtete Alternativen:**

| Alternative                                                   | Warum abgelehnt                                                                                                                                                                     |
|---------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **OpenTelemetry + Jaeger**                                    | Fokussiert auf Tracing, nicht auf Metriken. Gut für verteiltes Tracing, aber unser aktueller Anwendungsfall benötigt zuerst Metriken. Könnte später als ADR-007 hinzugefügt werden. |
| **ELK Stack (Elasticsearch, Logstash, Kibana)**               | Besser für Log-Aggregation als für Metriken. Übertrieben für ein Pet-Projekt (erfordert mehr Speicher und Ressourcen).                                                              |
| **Cloud-native Lösungen (Datadog, New Relic, Grafana Cloud)** | Hervorragende Werkzeuge, verletzen aber die "selbstständig, docker-compose"-Anforderung. Führen auch zu Kosten und Vendor-Lock-in.                                                  |
| **StatsD + Graphite**                                         | Älteres Pull-Modell; weniger flexibel als Prometheus.                                                                                                                               |

**Abwägungen:**

| Vorteile                                                                                           | Nachteile                                                                                                                                                    |
|----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ✅ Pull-Modell vermeidet, dass Dienste von der Überwachungsinfrastruktur wissen müssen              | ❌ Muss `/metrics`-Endpunkte von jedem Dienst exponieren (fügt Code-Komplexität hinzu)                                                                        |
| ✅ Reichhaltiges Ökosystem von Exporters für Redis, RabbitMQ, PostgreSQL und unsere eigenen Dienste | ❌ Prometheus verwendet Festplattenspeicher (Aufbewahrung muss verwaltet werden)                                                                              |
| ✅ Branchenstandard — zeigt Wissen über produktionsreife Überwachung                                | ❌ Erfordert zusätzliche Container (Prometheus, Grafana) in `docker-compose.yml`                                                                              |
| ✅ Grafana-Dashboards können als JSON-Dateien versioniert werden                                    | ❌ Nicht für langfristige Speicherung ausgelegt (wir brauchen für ein Pet-Projekt keine Jahre an Historie)                                                    |
| ✅ Eingebaute Alarmierung (über AlertManager)                                                       | ❌ Pull-Modell bedeutet, dass Metriken in Intervallen gesammelt werden, nicht in Echtzeit (aber Sub-Sekunden-Granularität ist für dieses Projekt ausreichend) |

**Zu exponierende Metriken:**

| Dienst               | Metriken                                                                                                                          |
|----------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| **API**              | Anfragenanzahl pro Endpunkt, Latenz (Histogramm), Fehlerrate, authentifizierte Benutzer, Task-Erstellungsrate, Rate-Limit-Treffer |
| **Worker (Go/Rust)** | Konsumierte Tasks-Rate, abgeschlossene Tasks, fehlgeschlagene Tasks, HTTP-Anfragenlatenz, ausgelöste Wiederholungen, Queue-Tiefe  |
| **RabbitMQ**         | Queuelänge, Nachrichtenraten, Consumer-Anzahl, DLX-Nachrichten                                                                    |
| **PostgreSQL**       | Verbindungspool-Nutzung, Abfragelatenz, aktive Abfragen                                                                           |
| **Redis**            | Speichernutzung, Trefferquote, Befehls-Latenz                                                                                     |

**Konsequenzen:**

- **Positiv:** Produktionsreife Observability, Branchenstandard-Werkzeuge, reichhaltige Dashboards, Möglichkeit, Probleme frühzeitig zu erkennen
- **Negativ:** Zusätzliche Container zu betreiben; Code mit Prometheus-Client-Bibliotheken instrumentieren; Festplattenspeicher für Metriken; Lernkurve für PromQL-Abfragen

**Referenzen:**

- Prometheus Overview: https://prometheus.io/docs/introduction/overview/
- Grafana: https://grafana.com/oss/grafana/
- RabbitMQ Prometheus Plugin: https://www.rabbitmq.com/docs/prometheus
- Redis Prometheus Exporter: https://github.com/oliver006/redis_exporter
- PostgreSQL Prometheus Exporter: https://github.com/prometheus-community/postgres_exporter