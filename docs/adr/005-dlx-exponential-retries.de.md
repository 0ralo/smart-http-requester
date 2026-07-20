# ADR-005: Implementierung von Wiederholungen mit RabbitMQ Dead-Letter-Exchanges und TTL

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

HTTP-Tasks können aufgrund vorübergehender Probleme fehlschlagen:

- Zieldienst gibt 5xx-Fehler zurück (Serverüberlastung, vorübergehende Nichtverfügbarkeit)
- Netzwerk-Timeouts (DNS-Auflösung, Verbindungsaufbau, Lese-/Schreib-Timeouts)
- Rate Limiting durch den Zieldienst (429 Too Many Requests)

Das System muss fehlgeschlagene Tasks bis zu `max_attempts` (vom Benutzer angegeben) mit **exponentiellem Backoff** (1s, 2s, 4s, 8s, 16s, 32s, 64s) wiederholen, um den Zieldienst während der Erholung nicht zu überlasten.

Der Wiederholungsmechanismus darf Worker während der Wartezeit nicht blockieren. Worker sollen weiterhin andere Tasks verarbeiten können.

**Problem:**

Implementierung eines exponentiellen Backoff-Wiederholungsmechanismus, der:

- Worker während der Wartezeit nicht blockiert
- Sicherstellt, dass Tasks nach präzisen Verzögerungen wiederholt werden
- Nicht unter Head-of-Line-Blocking leidet (wobei eine verzögerte Nachricht andere blockiert)
- Worker-Neustarts übersteht (Durability)

**Entscheidung:**

Implementierung von Wiederholungen mit **RabbitMQ Dead Letter Exchanges (DLX) mit TTL pro Queue**. Erstellung einer Kette von Verzögerungs-Queues:

```
delay-1s → delay-2s → delay-4s → delay-8s → delay-16s → delay-32s → delay-64s
```

Jede Queue hat ein TTL, das ihrer Verzögerung entspricht. Nach Ablauf des TTL werden Nachrichten automatisch an die nächste Queue in der Kette weitergeleitet (Dead-Letter). Die letzte Queue leitet per Dead-Letter zurück zur Haupt-Work-Queue.

**Betrachtete Alternativen:**

| Alternative                                                            | Warum abgelehnt                                                                                                                                                                                                                         |
|------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Worker-seitiges `time.sleep()` / `tokio::sleep()` / `time.After()`** | Blockiert den Worker-Goroutine/Thread. Wenn ein Worker 64s schläft, kann er während dieser Zeit keine anderen Tasks verarbeiten. Reduziert die Parallelität und verschwendet Ressourcen.                                                |
| **Per-Message-TTL (einzelne Verzögerungs-Queue)**                      | Einfacher zu konfigurieren (einzelne Queue mit per-Message-TTL). Jedoch verfallen Nachrichten nur vom Anfang der Queue — eine Nachricht mit 64s TTL am Anfang blockiert Nachrichten dahinter mit kürzeren TTLs (Head-of-Line-Blocking). |
| **RabbitMQ Delayed Message Plugin**                                    | Native Unterstützung für verzögerte Nachrichten. Erfordert jedoch die Installation eines Plugins (zusätzlicher Schritt für `docker-compose`-Setup). Übertrieben für ein Pet-Projekt.                                                    |
| **Externer Scheduler (z.B. Celery mit Redis Beat)**                    | Fügt erhebliche Komplexität hinzu. Erfordert separaten Scheduler-Prozess und Zustandsverwaltung.                                                                                                                                        |
| **PostgreSQL-Polling + geplante Tasks**                                | Hohe Last auf PostgreSQL (ständiges Polling). Verteiltes Locking erforderlich, um doppelte Ausführung zu verhindern.                                                                                                                    |

**Abwägungen:**

| Vorteile                                                                                                                                            | Nachteile                                                                                                               |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| ✅ Worker blockieren nicht — sie bestätigen fehlgeschlagene Nachrichten sofort und veröffentlichen sie in Verzögerungs-Queues                        | ❌ Erfordert die Erstellung von 7 vordefinierten Verzögerungs-Queues (betrieblicher Aufwand)                             |
| ✅ Kein Head-of-Line-Blocking — jede Verzögerung hat ihre eigene Queue, so dass kurze Verzögerungen nicht durch lange Verzögerungen blockiert werden | ❌ Maximale Verzögerung ist auf 64s festgelegt (kann ohne Hinzufügen weiterer Queues nicht überschritten werden)         |
| ✅ Keine externen Plugins erforderlich — verwendet nur native RabbitMQ-Funktionen                                                                    | ❌ Nachrichten durchlaufen mehrere Queues, was Overhead hinzufügt (jeder Hop ist ein Veröffentlichen+Konsumieren-Zyklus) |
| ✅ Durable Queues — ausstehende Wiederholungen überleben Broker-Neustarts                                                                            | ❌ Feste Verzögerungsschritte (1,2,4,8,...) — keine benutzerdefinierten Verzögerungen pro Task möglich                   |
| ✅ Natürliche Trennung der Verantwortlichkeiten — Worker kümmert sich nur um Ausführung, RabbitMQ um Timing                                          | ❌ Komplexere Überwachung (mehrere Verzögerungs-Queues auf Rückstände prüfen)                                            |
| ✅ Exponentieller Backoff ist in die Queue-Kette eingebaut                                                                                           | ❌ Wenn eine Verzögerungs-Queue versehentlich gelöscht wird, sind Wiederholungen verloren                                |

**Warum nicht worker-seitiges Sleep?**

Worker-seitiges Sleep ist einfacher zu implementieren, aber grundlegend fehlerhaft für ein konkurrentes System:

```
while attempts < max_attempts:
    if execute_task() == success:
        break
    time.sleep(backoff[attempts])  # Worker ist hier blockiert
    attempts++
```

In Go verbraucht ein schlafender Goroutine immer noch Speicher (Stack) und kann keine anderen Tasks verarbeiten. In Rust kann `tokio::sleep()` die Runtime abgeben, aber die Task belegt immer noch den Executor. Mit 100 Workern, die jeweils 64s schlafen, verschwenden wir potenzielle Verarbeitungskapazität von 100 * 64s = 6400 Sekunden Arbeit.

**Konsequenzen:**

- **Positiv:** Worker bleiben ausgelastet, präziser exponentieller Backoff, kein Head-of-Line-Blocking, keine externen Plugins, dauerhafte Wiederholungen
- **Negativ:** Erfordert 7 vordefinierte Verzögerungs-Queues, maximale Verzögerung auf 64s begrenzt, komplexere Überwachung, Nachrichten durchlaufen mehrere Queues

**Referenzen:**

- RabbitMQ Dead Letter Exchanges: https://www.rabbitmq.com/docs/dlx
- RabbitMQ TTL: https://www.rabbitmq.com/docs/ttl
- Head-of-line blocking explained: https://en.wikipedia.org/wiki/Head-of-line_blocking