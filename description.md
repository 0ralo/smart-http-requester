## Privacy Notice

### IP Address (Rate Limiting)
- IP address is collected automatically from every API request
- Used **exclusively** for rate limiting via sliding window algorithm
- Stored **temporarily in Redis (in-memory)**
- Retained for a **maximum of 2 minutes**, then automatically and permanently deleted
- **NOT persisted** to any database or disk
- **NOT included** in any logs
- **NOT exposed** to Prometheus metrics or any monitoring/statistics system
- Prometheus collects only aggregated metrics (request counts, latency, status codes) - **no individual identification possible**
- **NOT shared** with any third parties

### Authentication Data (Login / Password)
- Login (username/email) and password are stored in a relational database
- Passwords are **hashed and salted** (bcrypt/Argon2)
- **Plain-text passwords are never stored**
- Retained for a **maximum of 30 days (1 month)** from registration or last login
- After 30 days, account data is **automatically deleted**
- This data is used **exclusively** for demonstrating authentication mechanisms in this pet project
- **NOT used** for analytics, marketing, or any other purposes
- **NOT shared** with any third parties

### Legal Basis (GDPR)
- **IP Address:** Legitimate Interest (Art. 6(1)(f) GDPR) - service stability, abuse prevention, fair usage
- **Authentication Data:** Consent (Art. 6(1)(a) GDPR) - provided during registration

### Summary

| Data Type | Storage | Retention | Purpose | Shared? |
|-----------|---------|-----------|---------|---------|
| IP Address | Redis (in-memory) | 2 minutes | Rate limiting | No |
| Login/Password | Database (hashed) | 30 days | Authentication demo | No |

## Datenschutzhinweis

### IP-Adresse (Rate Limiting)
- IP-Adresse wird automatisch bei jeder API-Anfrage erhoben
- **Ausschließlich** für Rate Limiting mittels Sliding-Window-Algorithmus
- **Temporär im Arbeitsspeicher (Redis)** gespeichert
- Aufbewahrung für **maximal 2 Minuten**, dann automatische und endgültige Löschung
- **Nicht** in Datenbank oder auf Festplatte persistiert
- **Nicht** in Logs enthalten
- **Nicht** in Prometheus-Metriken oder Monitoring-Systemen enthalten
- Prometheus erfasst nur aggregierte Metriken - **keine individuelle Identifizierung möglich**
- **Nicht** an Dritte weitergegeben

### Authentifizierungsdaten (Login / Passwort)
- Login (Benutzername/E-Mail) und Passwort werden in relationaler Datenbank gespeichert
- Passwörter werden **gehasht und mit Salt versehen** (bcrypt/Argon2)
- **Klartext-Passwörter werden niemals gespeichert**
- Aufbewahrung für **maximal 30 Tage (1 Monat)** ab Registrierung oder letztem Login
- Nach 30 Tagen werden Kontodaten **automatisch gelöscht**
- Daten werden **ausschließlich** zur Demonstration von Authentifizierungsmechanismen in diesem Pet-Projekt genutzt
- **Nicht** für Analytics, Marketing oder andere Zwecke verwendet
- **Nicht** an Dritte weitergegeben

### Rechtsgrundlage (DSGVO)
- **IP-Adresse:** Berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO) - Stabilität, Missbrauchsschutz, faire Nutzung
- **Authentifizierungsdaten:** Einwilligung (Art. 6 Abs. 1 lit. a DSGVO) - bei Registrierung erteilt

### Zusammenfassung

| Datentyp | Speicherung | Aufbewahrung | Zweck | Geteilt? |
|----------|-------------|--------------|-------|----------|
| IP-Adresse | Redis (In-Memory) | 2 Minuten | Rate Limiting | Nein |
| Login/Passwort | Datenbank (gehasht) | 30 Tage | Authentifizierungs-Demo | Nein |