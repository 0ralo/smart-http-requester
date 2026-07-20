# ADR-005: Implementierung von Wiederholungen mit RabbitMQ Dead-Letter-Exchanges und TTL (DE)

**Status:** *Akzeptiert* (2026-07-20)

**Kontext:**  
HTTP-Tasks können aufgrund temporärer Probleme fehlschlagen. Das System muss Wiederholungen mit **exponentiellem Backoff** (1s, 2s, 4s, 8s, 16s, 32s, 64s) durchführen. Worker dürfen während der Wartezeit nicht blockiert werden.

**Entscheidung:**  
Wiederholungen mit **RabbitMQ Dead-Letter-Exchanges (DLX) und TTL pro Queue**. Eine Kette von Verzögerungs-Queues (`delay-1s` bis `delay-64s`) wird erstellt. Nach Ablauf des TTL werden Nachrichten per Dead-Letter an die Haupt-Work-Queue weitergeleitet.

**Begründung:**
- **Keine Worker-Blockierung:** Worker bestätigen fehlgeschlagene Nachrichten sofort und veröffentlichen sie in die Verzögerungs-Queue.
- **Keine "Head-of-Line"-Blockierung:** Pro-Queue-TTL verhindert, dass eine lang verzögerte Nachricht vorne in der Queue kürzere Verzögerungen blockiert (Problem bei per-Message-TTL).
- **Native RabbitMQ:** Kein externes Plugin erforderlich (einfaches `docker-compose`).
- **Durability:** Verzögerungs-Queues können dauerhaft sein, sodass Wiederholungen einen Broker-Neustart überstehen.

**Alternativen:**
- **Per-Message-TTL:** Verursacht "Head-of-Line"-Blockierung.
- **Delayed-Message-Plugin:** Sauberer, aber zusätzliche Installation – widerspricht der Einfachheit.
- **Worker-seitiges `time.sleep()`:** Blockiert Goroutines/Threads und reduziert die Parallelität.

**Konsequenzen:**
- **Positiv:** Worker bleiben ausgelastet, präziser exponentieller Backoff, keine Head-of-Line-Blockierung, keine Plugins.
- **Negativ:** Erfordert 7 vordefinierte Verzögerungs-Queues (mehr Konfiguration). Maximale Verzögerung ist auf 64s begrenzt.
