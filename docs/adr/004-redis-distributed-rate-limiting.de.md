# ADR-004: Verwendung von Redis für verteiltes Rate Limiting

---

**Status:** *Akzeptiert* (2026-07-20)

---

**Kontext:**

Die API akzeptiert HTTP-Anfragen von potenziell vielen Benutzern. Ohne Rate Limiting könnte ein einzelner Benutzer (oder ein böswilliger Akteur) das System mit Task-Erstellungsanfragen überfluten, was zu Folgendem führen würde:

- Erschöpfung des PostgreSQL-Verbindungspools
- Überlauf der RabbitMQ-Queue
- Ressourcenmangel für legitime Benutzer
- Verschlechterte Leistung und potenzielle Denial-of-Service-Angriffe

Der Rate Limiter muss über mehrere API-Instanzen hinweg funktionieren, wenn horizontal skaliert wird. Er muss auch schnell genug sein, um keinen signifikanten Overhead pro Anfrage hinzuzufügen.

**Problem:**

Implementierung eines Rate-Limiting-Mechanismus, der:

- **Verteilt** ist — über mehrere API-Replikate hinweg funktioniert
- **Schnell** ist — Sub-Millisekunde pro Anfrage
- **Genau** ist — keine Bursts an Grenzen (im Gegensatz zum Fixed Window)
- **Konfigurierbar** ist — benutzerspezifische Limits mit flexiblen Fenstergrößen

**Entscheidung:**

Implementierung von Rate Limiting mit **Redis** und einem **atomaren Lua-Skript**, das den **Sliding-Window**-Algorithmus mit einem konfigurierbaren Koeffizienten implementiert.

**Warum Sliding Window?**

| Algorithmus        | Beschreibung                                                                     | Vorteile                         | Nachteile                                                                      | Warum nicht hier?                                          |
|--------------------|----------------------------------------------------------------------------------|----------------------------------|--------------------------------------------------------------------------------|------------------------------------------------------------|
| **Fixed Window**   | Zählt Anfragen in festen Zeitfenstern (z.B. 60 Sekunden)                         | Einfach, geringer Speicherbedarf | Bursts an Fenstergrenzen (59. und 61. Sekunde können beide durchkommen)        | ❌ Ungenau für strenge Limits                               |
| **Token Bucket**   | Token werden mit fester Rate hinzugefügt; jede Anfrage verbraucht einen Token    | Glättet Bursts, weit verbreitet  | Erlaubt Bursts bis zur Bucket-Größe; komplex atomar in Redis zu implementieren | ❌ Erlaubt Bursts, wir wollen striktes Sliding Window       |
| **Leaky Bucket**   | Anfragen werden in einer Warteschlange gepuffert und mit fester Rate verarbeitet | Glättet Verkehr vollständig      | Kann Verzögerungen einführen; weniger genau für Rate Limiting von Anfragen     | ❌ Führt Latenz ein; für Netzwerkverkehrsformung konzipiert |
| **Sliding Window** | Verfolgt genaue Anfrage-Zeitstempel in einem Fenster                             | Genau, keine Grenz-Bursts        | Höherer Speicherbedarf (speichert Zeitstempel pro Benutzer)                    | ✅ Beste Genauigkeit für unseren Anwendungsfall             |

**Betrachtete Alternativen:**

| Alternative                                                    | Warum abgelehnt                                                                                                                                   |
|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| **In-Memory-Rate-Limiting (z.B. `slowapi` Python-Bibliothek)** | Funktioniert nicht mit mehreren API-Replikaten; Zustand ist instanzbezogen.                                                                       |
| **Rate Limiting über nginx/API-Gateway**                       | Weniger flexibel; schwierig, dynamische benutzerspezifische Limits oder Sliding Window mit benutzerdefinierten Geschäftsregeln zu implementieren. |
| **PostgreSQL-Zeilenbasierte Zähler**                           | Zu langsam für hochfrequente Anfragen (Festplatten-E/A); fügt der Hauptdatenbank unnötige Last hinzu.                                             |
| **Redis mit SETEX und INCR (Fixed Window)**                    | Einfacher, leidet aber unter Grenz-Bursts.                                                                                                        |

**Abwägungen:**

| Vorteile                                                                          | Nachteile                                                                                                                             |
|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| ✅ Sub-Millisekunden-Latenz — Redis ist In-Memory                                  | ❌ Fügt Redis als weitere Abhängigkeit hinzu (muss in `docker-compose.yml` sein)                                                       |
| ✅ Atomare Lua-Skripte verhindern Race-Conditions zwischen gleichzeitigen Anfragen | ❌ Lua-Skript-Komplexität — muss sorgfältig geschrieben werden, um Leistungsverschlechterung zu vermeiden                              |
| ✅ Verteilter Zustand — konsistente Limits über alle API-Replikate                 | ❌ Redis wird zur kritischen Abhängigkeit — wenn Redis ausfällt, schlägt Rate Limiting offen oder geschlossen fehl (sorgfältig wählen) |
| ✅ Sliding-Window-Genauigkeit — keine Bursts an Grenzen                            | ❌ Höherer Speicherbedarf als Fixed Window (speichert Zeitstempel pro Benutzer)                                                        |
| ✅ Branchenstandard-Muster — zeigt Wissen über gängige Infrastruktur               | ❌ Erfordert zusätzliche Überwachung (Redis-Speicher, CPU)                                                                             |
| ✅ Konfigurierbarer Koeffizient — ermöglicht Anpassung der Strenge                 | ❌ Multi-Key-Lua-Skripte können Redis blockieren, wenn sie komplex sind                                                                |

**Konsequenzen:**

- **Positiv:** Schnell, verteilt, genaues Sliding Window, branchenbewährte Lösung, atomare Operationen
- **Negativ:** Fügt Redis als Abhängigkeit hinzu; Lua-Skript-Komplexität; höherer Speicherbedarf als Fixed Window; Redis wird zur kritischen Infrastruktur

**Referenzen:**

- Redis Lua Scripting: https://redis.io/docs/latest/develop/programmability/eval-intro/
- Rate Limiting Algorithms: https://bytebytego.com/courses/system-design-interview/design-a-rate-limiter