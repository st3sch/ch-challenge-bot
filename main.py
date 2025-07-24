import discord
from discord.ext import commands, tasks
import pytesseract
from PIL import Image
import re
import json
import os
import asyncio
from datetime import datetime, time
import pytz
from typing import Dict, List, Optional, Tuple
import logging
from io import BytesIO
import threading

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Globale Variablen
update_locks = {}  # Channel-spezifische Locks für Thread-Sicherheit
GERMAN_TZ = pytz.timezone('Europe/Berlin')
CHALLENGE_END_TIME = time(19, 0)  # 19:00 Uhr

class ChannelConfig:
    """Konfiguration für einen Channel"""
    def __init__(self, channel_id: int, leaderboard_post_id: int):
        self.channel_id = channel_id
        self.leaderboard_post_id = leaderboard_post_id
        self.driver_mappings = {}  # fahrername -> discord_username
        self.is_active = True

    def to_dict(self):
        return {
            'channel_id': self.channel_id,
            'leaderboard_post_id': self.leaderboard_post_id,
            'driver_mappings': self.driver_mappings,
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data):
        config = cls(data['channel_id'], data['leaderboard_post_id'])
        config.driver_mappings = data.get('driver_mappings', {})
        config.is_active = data.get('is_active', True)
        return config

def load_channel_config(channel_id: int) -> Optional[ChannelConfig]:
    """Lädt die Konfiguration für einen Channel"""
    config_file = f'channel_{channel_id}.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ChannelConfig.from_dict(data)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Konfiguration für Channel {channel_id}: {e}")
    return None

def save_channel_config(config: ChannelConfig):
    """Speichert die Konfiguration für einen Channel"""
    config_file = f'channel_{config.channel_id}.json'
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Konfiguration für Channel {config.channel_id} gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Konfiguration für Channel {config.channel_id}: {e}")

def remove_channel_config(channel_id: int):
    """Entfernt die Konfiguration für einen Channel"""
    config_file = f'channel_{channel_id}.json'
    try:
        if os.path.exists(config_file):
            os.remove(config_file)
            logger.info(f"Konfiguration für Channel {channel_id} entfernt")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen der Konfiguration für Channel {channel_id}: {e}")

def extract_date_from_channel_name(channel_name: str) -> Optional[datetime]:
    """Extrahiert das Datum aus dem Channel-Namen (Format: DD-MM-YY)"""
    pattern = r'(\d{2}-\d{2}-\d{2})$'
    match = re.search(pattern, channel_name)
    if match:
        date_str = match.group(1)
        try:
            # Parse DD-MM-YY Format
            date_obj = datetime.strptime(date_str, '%d-%m-%y')
            return GERMAN_TZ.localize(date_obj.replace(
                hour=CHALLENGE_END_TIME.hour,
                minute=CHALLENGE_END_TIME.minute
            ))
        except ValueError:
            logger.error(f"Ungültiges Datumsformat in Channel-Name: {date_str}")
    return None

def is_challenge_active(channel_name: str) -> bool:
    """Prüft, ob eine Challenge noch aktiv ist"""
    end_time = extract_date_from_channel_name(channel_name)
    if end_time:
        now = datetime.now(GERMAN_TZ)
        return now < end_time
    return True  # Falls kein Datum erkannt wird, als aktiv betrachten

def extract_race_results(image_path: str) -> List[Tuple[str, str]]:
    """Extrahiert Rennergebnisse aus einem Screenshot"""
    try:
        image = Image.open(image_path)
        
        # OCR Konfiguration für bessere Erkennung
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÄÖÜäöüß:.| '
        
        # Text extrahieren
        text = pytesseract.image_to_string(image, config=custom_config, lang='deu+eng')
        logger.info(f"OCR Ergebnis: {text}")
        
        results = []
        lines = text.strip().split('\n')
        
        for line in lines:
            # Suche nach Zeit-Pattern (MM:SS.mmm)
            time_pattern = r'(\d{1,2}:\d{2}\.\d{3})'
            time_match = re.search(time_pattern, line)
            
            if time_match:
                race_time = time_match.group(1)
                
                # Suche nach Fahrername (vor der Zeit)
                parts = line.split()
                driver_name = None
                
                for i, part in enumerate(parts):
                    if time_pattern in part:
                        # Fahrername sollte vor der Zeit stehen
                        if i > 0:
                            driver_name = ' '.join(parts[:i]).strip()
                        break
                
                if driver_name and validate_time_format(race_time):
                    results.append((driver_name, race_time))
                    logger.info(f"Extrahiert: {driver_name} - {race_time}")
        
        return results
    
    except Exception as e:
        logger.error(f"Fehler bei der OCR-Verarbeitung: {e}")
        return []

def validate_time_format(time_str: str) -> bool:
    """Validiert das Zeitformat MM:SS.mmm"""
    pattern = r'^\d{1,2}:\d{2}\.\d{3}$'
    return bool(re.match(pattern, time_str))

def time_to_milliseconds(time_str: str) -> int:
    """Konvertiert MM:SS.mmm zu Millisekunden für Vergleiche"""
    try:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds_parts = parts[1].split('.')
        seconds = int(seconds_parts[0])
        milliseconds = int(seconds_parts[1])
        
        total_ms = minutes * 60 * 1000 + seconds * 1000 + milliseconds
        return total_ms
    except:
        return float('inf')

async def update_leaderboard(channel: discord.TextChannel, config: ChannelConfig, new_results: List[Tuple[str, str, str]]):
    """Aktualisiert das Leaderboard mit neuen Ergebnissen"""
    
    # Thread-Lock für diesen Channel
    if channel.id not in update_locks:
        update_locks[channel.id] = asyncio.Lock()
    
    async with update_locks[channel.id]:
        try:
            # Leaderboard Post abrufen
            leaderboard_post = await channel.fetch_message(config.leaderboard_post_id)
            
            # Prüfen ob Challenge noch aktiv ist
            if not is_challenge_active(channel.name):
                logger.info(f"Challenge in Channel {channel.name} ist beendet, keine Updates")
                return
            
            # Aktuelles Leaderboard parsen
            current_content = leaderboard_post.content
            leaderboard_entries = parse_leaderboard(current_content)
            
            # Neue Ergebnisse verarbeiten
            updated = False
            for driver_name, discord_user, race_time in new_results:
                # Eindeutigen Identifier erstellen
                identifier = f"{driver_name}_{discord_user}" if discord_user else driver_name
                
                # Prüfen ob bereits im Leaderboard
                existing_entry = None
                for entry in leaderboard_entries:
                    if entry['identifier'] == identifier:
                        existing_entry = entry
                        break
                
                new_time_ms = time_to_milliseconds(race_time)
                
                if existing_entry:
                    # Nur bessere Zeit übernehmen
                    existing_time_ms = time_to_milliseconds(existing_entry['time'])
                    if new_time_ms < existing_time_ms:
                        existing_entry['time'] = race_time
                        updated = True
                        logger.info(f"Zeit verbessert für {driver_name}: {race_time}")
                else:
                    # Neuen Eintrag hinzufügen
                    display_name = f"{driver_name} ({discord_user})" if discord_user and driver_name.lower() != discord_user.lower() else driver_name
                    leaderboard_entries.append({
                        'identifier': identifier,
                        'display_name': display_name,
                        'time': race_time,
                        'time_ms': new_time_ms
                    })
                    updated = True
                    logger.info(f"Neuer Eintrag: {driver_name} - {race_time}")
            
            if updated:
                # Leaderboard sortieren
                leaderboard_entries.sort(key=lambda x: x['time_ms'])
                
                # Neuen Leaderboard-Content erstellen
                new_content = format_leaderboard(leaderboard_entries)
                
                # Post aktualisieren
                await leaderboard_post.edit(content=new_content)
                logger.info(f"Leaderboard in Channel {channel.name} aktualisiert")
        
        except discord.NotFound:
            logger.error(f"Leaderboard Post {config.leaderboard_post_id} nicht gefunden")
        except discord.Forbidden:
            logger.error(f"Keine Berechtigung zum Bearbeiten des Posts in Channel {channel.name}")
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Leaderboards: {e}")

def parse_leaderboard(content: str) -> List[Dict]:
    """Parst den aktuellen Leaderboard-Inhalt"""
    entries = []
    lines = content.split('\n')
    
    for line in lines:
        # Suche nach Leaderboard-Einträgen (🥇, 🥈, 🥉, oder Nummer.)
        entry_pattern = r'(?:🥇|🥈|🥉|\d+\.)\s*\|\s*(\d{1,2}:\d{2}\.\d{3})\s*\|\s*\d+\s*Punkte\s*\|\s*(.+)'
        match = re.search(entry_pattern, line)
        
        if match:
            race_time = match.group(1)
            display_name = match.group(2).strip()
            
            # Identifier aus Display Name extrahieren
            if '(' in display_name and ')' in display_name:
                # Format: "FAHRERNAME (Discord-User)"
                parts = display_name.split('(')
                driver_name = parts[0].strip()
                discord_user = parts[1].rstrip(')').strip()
                identifier = f"{driver_name}_{discord_user}"
            else:
                # Nur Fahrername
                identifier = display_name
            
            entries.append({
                'identifier': identifier,
                'display_name': display_name,
                'time': race_time,
                'time_ms': time_to_milliseconds(race_time)
            })
    
    return entries

def format_leaderboard(entries: List[Dict]) -> str:
    """Formatiert das Leaderboard für die Anzeige"""
    now = datetime.now(GERMAN_TZ)
    timestamp = now.strftime("%d.%m.%y um %H:%M")
    
    content = f"Stand: {timestamp}\n"
    
    medals = ['🥇', '🥈', '🥉']
    points = [25, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 1]
    
    for i, entry in enumerate(entries):
        if i < 3:
            symbol = medals[i]
        else:
            symbol = f"{i + 1}."
        
        entry_points = points[i] if i < len(points) else 1
        content += f"{symbol} | {entry['time']} | {entry_points} Punkte | {entry['display_name']}\n"
    
    return content

@bot.event
async def on_ready():
    """Bot ist bereit"""
    logger.info(f'{bot.user} ist online!')
    check_challenge_end.start()

@bot.event
async def on_message(message):
    """Verarbeitet eingehende Nachrichten"""
    if message.author == bot.user:
        return
    
    # Commands verarbeiten
    await bot.process_commands(message)
    
    # Prüfen ob Nachricht Bilder enthält
    if message.attachments:
        config = load_channel_config(message.channel.id)
        if config and config.is_active:
            await process_images(message, config)

async def process_images(message, config: ChannelConfig):
    """Verarbeitet Bilder in einer Nachricht"""
    for attachment in message.attachments:
        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                # Bild herunterladen
                image_data = await attachment.read()
                image_path = f"temp_{attachment.filename}"
                
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                
                # Rennergebnisse extrahieren
                race_results = extract_race_results(image_path)
                
                # Aufräumen
                os.remove(image_path)
                
                if race_results:
                    # Fahrer-Zuordnung
                    processed_results = []
                    existing_drivers = list(config.driver_mappings.keys())
                    
                    # Filtern basierend auf vorhandenen Fahrern
                    if existing_drivers:
                        for driver_name, race_time in race_results:
                            # Case-insensitive Suche nach vorhandenen Fahrern
                            found_driver = None
                            for existing in existing_drivers:
                                if existing.lower() == driver_name.lower():
                                    found_driver = existing
                                    break
                            
                            if found_driver:
                                discord_user = config.driver_mappings[found_driver]
                                processed_results.append((found_driver, discord_user, race_time))
                    else:
                        # Keine vorhandenen Fahrer, alle verarbeiten
                        for driver_name, race_time in race_results:
                            # Discord-Username aus Nachricht ableiten
                            discord_user = message.author.display_name
                            config.driver_mappings[driver_name] = discord_user
                            processed_results.append((driver_name, discord_user, race_time))
                    
                    if processed_results:
                        # Konfiguration speichern
                        save_channel_config(config)
                        
                        # Leaderboard aktualisieren
                        await update_leaderboard(message.channel, config, processed_results)
                        
                        # Bestätigung senden
                        await message.add_reaction('✅')
                
            except Exception as e:
                logger.error(f"Fehler beim Verarbeiten des Bildes {attachment.filename}: {e}")

@bot.command(name='add_challenge')
@commands.has_permissions(administrator=True)
async def add_challenge(ctx, channel_id: int, leaderboard_post_id: int):
    """Fügt einen Bot zu einem Challenge-Channel hinzu"""
    try:
        # Channel und Post validieren
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send(f"Channel mit ID {channel_id} nicht gefunden.")
            return
        
        try:
            post = await channel.fetch_message(leaderboard_post_id)
        except discord.NotFound:
            await ctx.send(f"Post mit ID {leaderboard_post_id} nicht gefunden.")
            return
        
        # Konfiguration erstellen
        config = ChannelConfig(channel_id, leaderboard_post_id)
        save_channel_config(config)
        
        await ctx.send(f"Bot erfolgreich zu Channel {channel.mention} hinzugefügt!")
        logger.info(f"Bot zu Channel {channel_id} hinzugefügt")
        
    except Exception as e:
        await ctx.send(f"Fehler beim Hinzufügen: {e}")
        logger.error(f"Fehler beim Hinzufügen zu Channel {channel_id}: {e}")

@bot.command(name='remove_challenge')
@commands.has_permissions(administrator=True)
async def remove_challenge(ctx, channel_id: int):
    """Entfernt den Bot von einem Challenge-Channel"""
    try:
        config = load_channel_config(channel_id)
        if not config:
            await ctx.send(f"Bot ist nicht in Channel {channel_id} aktiv.")
            return
        
        # Konfiguration entfernen
        remove_channel_config(channel_id)
        
        channel = bot.get_channel(channel_id)
        channel_name = channel.mention if channel else f"Channel {channel_id}"
        
        await ctx.send(f"Bot erfolgreich von {channel_name} entfernt!")
        logger.info(f"Bot von Channel {channel_id} entfernt")
        
    except Exception as e:
        await ctx.send(f"Fehler beim Entfernen: {e}")
        logger.error(f"Fehler beim Entfernen von Channel {channel_id}: {e}")

@tasks.loop(minutes=5)
async def check_challenge_end():
    """Prüft periodisch auf Challenge-Ende"""
    try:
        # Alle Channel-Konfigurationen durchgehen
        for filename in os.listdir('.'):
            if filename.startswith('channel_') and filename.endswith('.json'):
                channel_id = int(filename.replace('channel_', '').replace('.json', ''))
                config = load_channel_config(channel_id)
                
                if config and config.is_active:
                    channel = bot.get_channel(channel_id)
                    if channel and not is_challenge_active(channel.name):
                        await end_challenge(channel, config)
    
    except Exception as e:
        logger.error(f"Fehler bei der Challenge-Ende-Prüfung: {e}")

async def end_challenge(channel: discord.TextChannel, config: ChannelConfig):
    """Beendet eine Challenge"""
    try:
        leaderboard_post = await channel.fetch_message(config.leaderboard_post_id)
        current_content = leaderboard_post.content
        
        # Header zu "Endstand" ändern
        lines = current_content.split('\n')
        if lines:
            lines[0] = "Endstand"
            new_content = '\n'.join(lines)
            await leaderboard_post.edit(content=new_content)
        
        # Konfiguration als inaktiv markieren
        config.is_active = False
        save_channel_config(config)
        
        logger.info(f"Challenge in Channel {channel.name} beendet")
        
    except Exception as e:
        logger.error(f"Fehler beim Beenden der Challenge in Channel {channel.name}: {e}")

@bot.command(name='help_challenge')
async def help_challenge(ctx):
    """Zeigt Hilfe-Informationen"""
    help_text = """
**Carrera Hybrid Challenge Bot - Hilfe**

**Admin-Commands:**
• `!add_challenge <channel_id> <leaderboard_post_id>` - Bot zu Channel hinzufügen
• `!remove_challenge <channel_id>` - Bot von Channel entfernen

**Nutzung:**
1. Poste Screenshots der Carrera Hybrid App Rennergebnisse
2. Bot erkennt automatisch Fahrernamen und Zeiten
3. Leaderboard wird automatisch aktualisiert
4. Challenge endet automatisch um 19:00 deutscher Zeit (basierend auf Channel-Name)

**Hinweise:**
• Channel-Name muss auf DD-MM-YY enden für automatisches Challenge-Ende
• Nur bessere Zeiten werden übernommen
• Bei mehreren Fahrern im Screenshot werden nur bekannte Fahrer verarbeitet
    """
    
    await ctx.send(help_text)

if __name__ == '__main__':
    # Bot Token aus Umgebungsvariable
    bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN Umgebungsvariable nicht gesetzt!")
        exit(1)
    
    bot.run(bot_token)