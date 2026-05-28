# AI Assistant für Linux Mint Cinnamon

Radialer AI-Assistent für markierten Text. Öffne das Funktions-Rad per **Ctrl+Shift+Leertaste**, wähle ein Modul und erhalte das Ergebnis in der Zwischenablage.

## Funktionen

- Globales Hotkey-Overlay unabhängig von der aktiven App
- Radiales Icon-Menü um die Mausposition
- **Übersetzer** mit Unter-Aktionen Deutsch / Englisch
- **Einstellungen** für OpenAI API-Key, Modellwahl und Prompts
- Visuelles Feedback (Loading / Fertig / Fehler) am Mauszeiger
- Erweiterbare Modul-Architektur

## Voraussetzungen

- Linux Mint Cinnamon mit **X11**
- Python 3.11+
- System-Pakete:

```bash
sudo apt install python3 python3-venv libsecret-1-0
```

## Installation

```bash
cd /home/robin/Dokumente/Coding/ai-assistant
chmod +x scripts/install.sh
./scripts/install.sh
```

## Erste Schritte

1. Assistent starten (oder nach Autostart neu anmelden)
2. **Ctrl+Shift+Leertaste** drücken → Radialmenü erscheint
3. **Einstellungen** öffnen und OpenAI API-Key hinterlegen
4. Text markieren → Hotkey → **Übersetzer** → **EN** oder **DE**

Erneutes Drücken von **Ctrl+Shift+Leertaste** schließt das Rad ohne Aktion.

## Konfiguration

| Pfad | Inhalt |
|------|--------|
| `~/.config/ai-assistant/config.json` | Hotkey, Modellwahl, Prompts |
| Keyring (`ai-assistant/openai-api-key`) | OpenAI API-Key |

Verfügbare Modelle (Standard): `gpt-5.5`, `gpt-5.4-nano`

## Neues Modul hinzufügen

1. Datei in `ai_assistant/modules/` anlegen (siehe `translator.py`)
2. Modul in `ai_assistant/modules/registry.py` registrieren
3. Assistent neu starten

## Manueller Start

```bash
/home/robin/Dokumente/Coding/ai-assistant/.venv/bin/ai-assistant
```

## Troubleshooting

- **Kein Text ausgewählt**: Text zuerst markieren, dann Hotkey drücken
- **Hotkey reagiert nicht**: prüfen ob der Prozess läuft; Konflikt mit anderen Shortcuts
- **API-Fehler**: Key und Modell-ID in den Einstellungen prüfen
- **Wayland**: v1 unterstützt nur X11

## Lizenz

MIT (Projekt lokal)
