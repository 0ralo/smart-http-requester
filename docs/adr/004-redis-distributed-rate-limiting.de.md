# ADR-004: Verwendung von Redis für verteiltes Rate Limiting (DE)

**Status:** *Akzeptiert* (2026-07-20)

**Kontext:**  
API akzeptiert Anfragen vieler Benutzer. Ohne Rate Limiting könnte ein einzelner Benutzer das System überfluten. Der Limiter muss über mehrere API-Instanzen hinweg funktionieren.

**Entscheidung:**  
Rate Limiting mit **Redis** und einem **atomaren Lua-Skript**, das den **Sliding-Window-Algorithmus** mit konfigurierbarem Koeffizienten implementiert.

**Begründung:**
- **Performance:** Redis ist extrem schnell (Sub-Millisekunde) – ideal für pro-Anfrage-Prüfungen.
- **Atomarität:** Lua-Skripte verhindern Race-Conditions.
- **Verteilt:** Redis als zentraler Zustandsspeicher gewährleistet Konsistenz über API-Replikate.
- **Standard:** Redis ist Branchenstandard für Caching und Rate Limiting.
- **Sliding Window:** Genauer als Fixed Window; Koeffizient ermöglicht Anpassung der Strenge.

**Alternativen:**
- **In-Memory (z.B. `slowapi`):** Nicht verteilt; Zustand geht bei Neustart verloren.
- **Nginx/API-Gateway:** Weniger flexibel, keine dynamischen Benutzergrenzen.
- **PostgreSQL-Zähler:** Zu langsam für hohe Anfragefrequenzen.

**Konsequenzen:**
- **Positiv:** Schnell, verteilt, akkurates Sliding Window, bewährte Lösung.
- **Negativ:** Zusätzliche Abhängigkeit (Redis); sorgfältige Lua-Skript-Entwicklung erforderlich.
