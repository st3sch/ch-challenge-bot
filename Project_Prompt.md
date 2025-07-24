# Discord Bot für Carrera Hybrid Challenge - Entwicklungsauftrag

## Projektübersicht
Erstelle einen Discord Bot, der automatisch Leaderboards für eine Carrera Hybrid Challenge verwaltet. Der Bot analysiert Screenshots von Rennergebnissen aus der Carrera Hybrid App und aktualisiert ein Leaderboard in einem angehefteten Discord-Post.

## Funktionale Anforderungen

### 1. Screenshot-Analyse
**Eingabe:** Screenshots der Carrera Hybrid App mit Rennergebnissen

**Zu extrahierende Daten:**
- Fahrername (aus der "RACER" Spalte)
- Gesamtzeit (aus der "ZEIT" Spalte im Format MM:SS.mmm)

**Besonderheiten:**
- Normalerweise erscheint nur ein Fahrzeug pro Screenshot
- Können mehrere Fahrer enthalten sein (siehe Verarbeitungslogik unten)
- Nicht alle Bilder sind Rennergebnisse (diese ignorieren)

### 2. Fahrer-Zuordnung
**Primäre Identifikation:** Fahrername aus der App ist der Hauptidentifier

**Namensanzeige-Logik:**
- Falls Fahrername ≠ Discord-Username (case-insensitive Vergleich): 
  - Format: `Fahrername (Discord-Username)`
- Falls Fahrername = Discord-Username (case-insensitive): 
  - Format: `Fahrername`

**Eindeutige Identifikation:** Die Kombination aus Fahrername + Discord-Username (falls vorhanden) bildet den eindeutigen Identifier für Leaderboard-Updates

**Mehrere Fahrer im Screenshot:**
- Falls bereits Fahrer im Leaderboard vorhanden sind: Nur diese verarbeiten
- Falls keine der Fahrer im Screenshot bereits im Leaderboard stehen: Alle Fahrer verarbeiten

### 3. Leaderboard-Verwaltung
**Lokation:** Angehefteter Post am Anfang des Discord-Threads

### 4. Challenge-Management

**Admin-Commands:**
- `!add_challenge <channel_id> <leaderboard_post_id>` - Bot zu einem Channel hinzufügen
- `!remove_challenge <channel_id>` - Bot von einem Channel abmelden

**Datenpersistierung:**
- Jeder Channel erhält eine eigene JSON-Datei: `channel_<channel_id>.json`
- Speichert Fahrer-Zuordnungen (Fahrername → Discord-Username)
- Beim Abmelden wird die entsprechende JSON-Datei gelöscht

**Automatisches Challenge-Ende:**
- Bot erkennt Challenge-Ende am Channel-Titel
- Channel-Titel endet immer auf Datum im Format `DD-MM-YY`
- Challenge läuft bis 19:00 Uhr Lokalzeit Deutschland am angegebenen Datum
- Nach 19:00 Uhr wird automatisch "Endstand" gesetzt und Leaderboard gesperrt

**Challenge-Status-Erkennung:**
- Aktive Challenge: Header "Stand: DD.MM.YY um HH:MM" → Updates erlaubt
- Beendete Challenge: Header "Endstand" → Leaderboard gesperrt

**Format:** Nummerierte Liste, sortiert nach schnellster Zeit (aufsteigend)

**Timestamp-Update:** Bei jeder Änderung wird Datum/Uhrzeit im Header aktualisiert

**Aktualisierungslogik:**
- Nur bei aktiven Challenges (Status != "Endstand")
- Neue Zeit einfügen an korrekter Position
- Alle nachfolgenden Einträge nach unten verschieben
- Nummerierung automatisch anpassen
- Bei existierendem Fahrer: Nur bessere Zeiten übernehmen, schlechtere verwerfen
- Namensanzeige: Fahrername (Discord-Username) wenn unterschiedlich, sonst nur Fahrername
- Concurrency-Handling: Thread-sichere Verarbeitung für gleichzeitige Post-Einreichungen

### 4. Leaderboard-Format
**Challenge-Status:**
- Aktive Challenge: Header zeigt "Stand: [Datum] um [Uhrzeit]" (Leaderboard kann aktualisiert werden)
- Beendete Challenge: Header zeigt "Endstand" (Leaderboard ist gesperrt, keine Updates mehr)

**Beispiel-Format:**
```
Stand: 21.07.25 um 18:46
🥇 | 01:13.839 | 25 Punkte | CYSTIX
🥈 | 01:13.913 | 22 Punkte | LEGENDE (Hermann)
🥉 | 01:14.446 | 20 Punkte | WHITE DRAGON
4. | 01:14.531 | 18 Punkte | DTFREAK
...
```

## Technische Anforderungen

### 1. Discord Integration
- Discord.py Bibliothek verwenden
- Bot reagiert auf Bilder in konfigurierten Channels
- Kann angeheftete Posts bearbeiten
- Admin-Commands für Channel-Management
- Fehlerbehandlung für fehlende Berechtigungen

### 2. Datenpersistierung
- JSON-Dateien pro Channel: `channel_<channel_id>.json`
- Speichert Fahrer-Zuordnungen und Channel-Konfiguration
- Automatisches Löschen der JSON-Datei beim Abmelden
- Backup-Mechanismus für kritische Daten

### 3. Zeitmanagement
- Automatische Challenge-Ende-Erkennung
- Channel-Titel-Parsing für Datum-Extraktion (DD-MM-YY Format)
- Deutsche Lokalzeit (Europe/Berlin) für 19:00 Uhr Deadline
- Periodische Prüfung auf Challenge-Ende

### 4. Bildverarbeitung
- OCR für Text-Extraktion aus Screenshots
- Robuste Erkennung der Tabellen-Struktur
- Fehlerbehandlung für unleserliche/ungültige Bilder

### 5. Datenvalidierung
- Zeit-Format validieren (MM:SS.mmm)
- Fahrernamen bereinigen
- Duplikat-Erkennung basierend auf eindeutigem Identifier
- Challenge-Status prüfen (aktiv vs. beendet)
- Race-Condition Prevention für gleichzeitige Updates

### 6. Deployment
- Docker Container Setup
- Dockerfile erstellen
- Environment Variables für Bot-Token
- Persistente Datenspeicherung (falls nötig)

## Implementierungsdetails

### Benötigte Dependencies
- discord.py
- Pillow (PIL) für Bildverarbeitung
- pytesseract für OCR
- pytz für Zeitzonen-Handling (deutsche Lokalzeit)
- Weitere OCR-Bibliotheken nach Bedarf

### Bot-Berechtigungen
- Read Messages
- Send Messages
- Manage Messages (für Post-Updates)
- Read Message History
- Attach Files (für Debugging)
- Administrator-Berechtigungen für Commands (falls erforderlich)

### Konfiguration
- Bot Token als Umgebungsvariable
- Admin-Commands für Channel-Management
- Automatische Datenpersistierung pro Channel

### Logging und Debugging
- Ausführliche Logs für OCR-Ergebnisse
- Error-Handling für API-Limits
- Debug-Modus für Entwicklung

## Zusätzliche Überlegungen

### Challenge-Management
- Automatische Challenge-Ende-Erkennung basierend auf Channel-Titel und deutscher Lokalzeit
- Admin-Commands für Channel-Verwaltung
- JSON-basierte Datenpersistierung pro Channel
- Automatische Timestamp-Aktualisierung bei Änderungen

### Robustheit
- Retry-Mechanismen für Discord API-Calls
- Graceful degradation bei OCR-Fehlern
- Rate-Limiting beachten
- Mutex/Lock für Leaderboard-Updates (Race-Condition Prevention)
- Transaktionale Updates für Datenkonsistenz

### Skalierbarkeit
- Mehrere Leaderboards/Channels unterstützen
- Backup/Restore Funktionalität

### User Experience
- Bestätigungsnachrichten nach erfolgreicher Verarbeitung
- Fehlermeldungen bei ungültigen Screenshots
- Help-Command mit Anleitung

## Erwartetes Verhalten

1. **User postet Screenshot** → Bot analysiert Bild automatisch
2. **Challenge-Status-Prüfung** → Nur aktive Challenges werden bearbeitet
3. **Gültiges Rennergebnis erkannt** → Leaderboard wird aktualisiert mit neuem Timestamp
4. **Ungültiges Bild** → Stille Ignorierung (kein Spam)
5. **Bessere Zeit** → Alte Zeit wird ersetzt, Position aktualisiert
6. **Schlechtere Zeit** → Neue Zeit wird verworfen
7. **Neue Fahrer** → Werden an entsprechender Position eingefügt
8. **Beendete Challenge** → Keine Updates mehr, Bot ignoriert Screenshots
9. **Gleichzeitige Posts** → Thread-sichere Verarbeitung verhindert Datenverlust
10. **Mehrere Fahrer im Screenshot** → Nur bereits im Leaderboard vorhandene Fahrer verarbeiten, falls keiner vorhanden alle verarbeiten
11. **Challenge-Ende** → Automatisch um 19:00 Uhr deutscher Zeit basierend auf Channel-Titel-Datum
12. **Admin-Commands** → `!add_challenge` und `!remove_challenge` für Channel-Management

## Deliverables

1. Vollständiger Python-Code für den Discord Bot
2. Dockerfile für Container-Deployment
3. requirements.txt mit allen Dependencies
4. README.md mit Setup-Anleitung
5. Beispiel .env Datei für Konfiguration

Erstelle einen funktionsfähigen, robusten Discord Bot, der diese Anforderungen erfüllt und in einer Docker-Umgebung lauffähig ist.