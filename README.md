# Carrera Hybrid Challenge Discord Bot

Ein Discord Bot, der automatisch Leaderboards für Carrera Hybrid Challenges verwaltet. Der Bot analysiert Screenshots von Rennergebnissen und aktualisiert ein Leaderboard in einem angehefteten Discord-Post.

## Features

- **Automatische Screenshot-Analyse** mit OCR
- **Intelligente Fahrer-Zuordnung** basierend auf App-Namen und Discord-Benutzern
- **Thread-sichere Leaderboard-Updates** 
- **Automatisches Challenge-Ende** basierend auf Channel-Namen und deutscher Lokalzeit
- **Admin-Commands** für Channel-Management
- **Persistente Datenspeicherung** pro Channel
- **Docker-Support** für einfaches Deployment

## Voraussetzungen

- Python 3.11+
- Discord Bot Token
- Tesseract OCR
- Docker (optional)

## Installation

### Lokale Installation

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd carrera-hybrid-bot
   ```

2. **Python Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Tesseract OCR installieren:**
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng
   ```
   
   **macOS:**
   ```bash
   brew install tesseract tesseract-lang
   ```
   
   **Windows:**
   - Tesseract von [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) herunterladen
   - Installationspfad zu PATH hinzufügen

4. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   # .env Datei mit Bot Token bearbeiten
   ```

5. **Bot starten:**
   ```bash
   python main.py
   ```

### Docker Installation

1. **Docker Image bauen:**
   ```bash
   docker build -t carrera-hybrid-bot .
   ```

2. **Container starten:**
   ```bash
   docker run -d \
     --name carrera-bot \
     -e DISCORD_BOT_TOKEN=your_token_here \
     -v $(pwd)/data:/app/data \
     carrera-hybrid-bot
   ```

### Docker Compose (Empfohlen)

1. **docker-compose.yml erstellen:**
   ```yaml
   version: '3.8'
   services:
     carrera-bot:
       build: .
       environment:
         - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
       volumes:
         - ./data:/app/data
         - ./logs:/app/logs
       restart: unless-stopped
   ```

2. **Starten:**
   ```bash
   docker-compose up -d
   ```

## Bot Setup in Discord

### 1. Discord Application erstellen

1. Gehe zu [Discord Developer Portal](https://discord.com/developers/applications)
2. Klicke auf "New Application"
3. Gib einen Namen ein und erstelle die Application

### 2. Bot erstellen

1. Gehe zum "Bot" Tab
2. Klicke auf "Add Bot"
3. Kopiere den Bot Token
4. Aktiviere alle "Privileged Gateway Intents"

### 3. Bot zu Server hinzufügen

1. Gehe zum "OAuth2" > "URL Generator" Tab
2. Wähle Scopes: `bot`
3. Wähle Bot Permissions:
   - Read Messages
   - Send Messages
   - Manage Messages
   - Read Message History
   - Attach Files
   - Use Slash Commands
4. Nutze die generierte URL um den Bot einzuladen

### 4. Bot Berechtigungen

Der Bot benötigt folgende Berechtigungen in den Challenge-Channels:
- **Nachrichten lesen**
- **Nachrichten senden** 
- **Nachrichten verwalten** (für Leaderboard-Updates)
- **Nachrichtenverlauf lesen**
- **Dateien anhängen** (für Debugging)

## Nutzung

### Admin Commands

**Bot zu Channel hinzufügen:**
```
!add_challenge <channel_id> <leaderboard_post_id>
```

**Bot von Channel entfernen:**
```
!remove_challenge <channel_id>
```

**Hilfe anzeigen:**
```
!help_challenge
```

### Challenge Setup

1. **Channel erstellen** mit Namen im Format `challenge-name-DD-MM-YY`
   - Beispiel: `time-attack-23-07-25`
   - Das Datum bestimmt wann die Challenge automatisch endet (19:00 deutscher Zeit)

2. **Leaderboard Post erstellen** und anheften:
   ```
   Stand: 23.07.25 um 18:46
   ```

3. **Bot aktivieren** mit Admin-Command:
   ```
   !add_challenge 123456789012345678 987654321098765432
   ```

### Screenshots posten

1. **Carrera Hybrid App Screenshot** in den Challenge-Channel posten
2. Bot erkennt automatisch:
   - Fahrernamen aus der "RACER" Spalte
   - Zeiten aus der "ZEIT" Spalte (MM:SS.mmm Format)
3. **Leaderboard wird automatisch aktualisiert**
4. **Bestätigung** durch ✅ Reaktion

### Fahrer-Zuordnung

- **Primär:** Fahrername aus der App
- **Anzeige:** 
  - `Fahrername` (wenn gleich Discord-Name)
  - `Fahrername (Discord-Name)` (wenn unterschiedlich)
- **Bei mehreren Fahrern:** Nur bereits bekannte Fahrer werden verarbeitet

### Challenge-Ende

- **Automatisch um 19:00 deutscher Zeit** am Datum im Channel-Namen
- Header wechselt von "Stand: ..." zu "Endstand"
- **Keine weiteren Updates** nach Challenge-Ende

## Konfiguration

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `DISCORD_BOT_TOKEN` | Discord Bot Token | **Erforderlich** |
| `LOG_LEVEL` | Logging Level | `INFO` |
| `TESSERACT_CMD` | Tesseract Pfad | Auto-detect |

### Datenspeicherung

- **Channel-Konfiguration:** `channel_<channel_id>.json`
- **Logs:** `bot.log`
- **Temp-Dateien:** Automatisch bereinigt

Beispiel Channel-Konfiguration:
```json
{
  "channel_id": 123456789012345678,
  "leaderboard_post_id": 987654321098765432,
  "driver_mappings": {
    "CYSTIX": "user123",
    "LEGENDE": "Hermann"
  },
  "is_active": true
}
```

## Leaderboard Format

```
Stand: 23.07.25 um 18:46
🥇 | 01:13.839 | 25 Punkte | CYSTIX
🥈 | 01:13.913 | 22 Punkte | LEGENDE (Hermann)
🥉 | 01:14.446 | 20 Punkte | WHITE DRAGON
4. | 01:14.531 | 18 Punkte | DTFREAK
5. | 01:15.123 | 16 Punkte | SPEEDKING
```

### Punkte-System

| Position | Punkte |
|----------|--------|
| 1. | 25 |
| 2. | 22 |
| 3. | 20 |
| 4. | 18 |
| 5. | 16 |
| 6. | 14 |
| 7. | 12 |
| 8. | 10 |
| 9. | 8 |
| 10. | 6 |
| 11. | 4 |
| 12. | 2 |
| 13.+ | 1 |

## Troubleshooting

### Häufige Probleme

**Bot reagiert nicht auf Screenshots:**
- Bot-Berechtigungen prüfen
- Channel-Konfiguration mit `!add_challenge` überprüfen
- Log-Dateien auf Fehler prüfen

**OCR erkennt keine Texte:**
- Screenshot-Qualität verbessern
- Tesseract Installation prüfen
- Deutsche Sprachpakete installiert?

**Leaderboard wird nicht aktualisiert:**
- Challenge noch aktiv? (vor 19:00 Uhr)
- Bot hat Berechtigung Post zu bearbeiten?
- Post-ID korrekt?

**Challenge endet nicht automatisch:**
- Channel-Name endet auf DD-MM-YY?
- Bot läuft kontinuierlich?
- Zeitzone korrekt (Europa/Berlin)?

### Debug-Modus

Für detaillierte Logs:
```bash
export LOG_LEVEL=DEBUG
python main.py
```

### Logs prüfen

```bash
# Aktuelle Logs
tail -f bot.log

# Fehler filtern
grep ERROR bot.log

# OCR-Ergebnisse
grep "OCR Ergebnis" bot.log
```

## Entwicklung

### Code-Struktur

```
├── main.py              # Hauptbot-Code
├── requirements.txt     # Python Dependencies
├── Dockerfile          # Container Build
├── .env.example        # Umgebungsvariablen Template
├── README.md           # Diese Datei
├── channel_*.json      # Channel-Konfigurationen
└── bot.log            # Log-Datei
```

### Wichtige Funktionen

- `extract_race_results()` - OCR und Datenextraktion
- `update_leaderboard()` - Thread-sichere Leaderboard-Updates
- `check_challenge_end()` - Periodische Challenge-Ende-Prüfung
- `parse_leaderboard()` - Aktuelles Leaderboard parsen
- `format_leaderboard()` - Leaderboard formatieren

### Testing

Für lokale Tests:
```bash
# Test-Screenshot verarbeiten
python -c "
from main import extract_race_results
results = extract_race_results('test_screenshot.png')
print(results)
"
```

## Sicherheit

- **Non-root Docker User** für Container-Sicherheit
- **Admin-Permissions** erforderlich für Bot-Commands
- **Input-Validierung** für alle OCR-Ergebnisse
- **Thread-Locks** für Race-Condition-Prevention

## Lizenz

MIT License - siehe LICENSE Datei für Details.

## Support

Bei Problemen oder Fragen:
1. **Logs prüfen** (`bot.log`)
2. **GitHub Issues** erstellen
3. **Discord-Berechtigungen** überprüfen
4. **Tesseract-Installation** testen

## Changelog

### v1.0.0
- Initiale Version
- OCR-basierte Screenshot-Analyse
- Automatisches Leaderboard-Management
- Docker-Support
- Thread-sichere Updates
- Automatisches Challenge-Ende
   