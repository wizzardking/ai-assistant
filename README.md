# AI Assistant (Linux & Windows)

Radialer AI-Assistent für markierten Text. Öffne das Funktions-Rad per Hotkey,
wähle ein Modul und erhalte das Ergebnis in der Zwischenablage oder in einem
dedizierten Fenster (Bildgenerierung, Chat, Zusammenfassen, Erklären, ...).

## Funktionen

- Globales Hotkey-Overlay unabhängig von der aktiven App
- Radiales Icon-Menü um die Mausposition
- **Übersetzer** mit Sprachen- und Tonauswahl
- **Umschreiben** und **Antwort verfassen** mit verschiedenen Tönen
- **Zusammenfassen** und **Erklären** in dedizierten Fenstern
- **Bildgenerierung** mit Größen- und Qualitätsauswahl
- **Chat** mit persistentem Verlauf, mehreren Konversationen, Markdown-Rendering
- Cursor-folgender Lade-Indikator mit „AI"-Beschriftung
- Erweiterbare Modul-Architektur

## Plattformen

- **Linux** (X11, getestet auf Linux Mint Cinnamon)
- **Windows 10/11**
- macOS (experimentell, ungetestet)

---

## Installation – Linux

### Voraussetzungen

```bash
sudo apt install python3 python3-venv libsecret-1-0 xclip
```

### Installation

```bash
cd /pfad/zum/repo
chmod +x scripts/install.sh
./scripts/install.sh
```

oder manuell:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Autostart (Linux)

```bash
mkdir -p ~/bin
cp scripts/ai-assistant-autostart.sh ~/bin/
chmod +x ~/bin/ai-assistant-autostart.sh

cat > ~/.config/autostart/ai-assistant.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=AI Assistant
Exec=/home/<dein-user>/bin/ai-assistant-autostart.sh
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
EOF
```

Der Wrapper zieht auf `master` automatisch neue Commits (`git pull --ff-only`) und
startet die App. Auf Feature-Branches wird kein Pull versucht.

---

## Installation – Windows

### Voraussetzungen

- **Python 3.11+** – installieren von [python.org](https://www.python.org/downloads/) oder via `winget install Python.Python.3.12`
- **Git** – `winget install Git.Git`
- (Optional) Logitech Options+ / G Hub deaktivieren oder so konfigurieren, dass extra
  Maus-Buttons als „Generic Mouse Button" durchgereicht werden, falls du Maus-Hotkeys
  nutzen möchtest

### Setup

```powershell
git clone <repo-url> C:\Code\ai-assistant
cd C:\Code\ai-assistant
py -m venv .venv
.\.venv\Scripts\pip install -e .
```

### Erster Start (manuell, mit Konsole für Logs)

```powershell
.\.venv\Scripts\python.exe -m ai_assistant.main
```

oder geräuschlos im Hintergrund:

```powershell
.\.venv\Scripts\pythonw.exe -m ai_assistant.main
```

Dann das Funktions-Rad mit dem Default-Hotkey **Ctrl+Shift+Alt+Leertaste** öffnen.

### Autostart (Windows)

Lege eine Verknüpfung im Windows-Autostart-Ordner an, die das mitgelieferte
Wrapper-Skript ausführt:

```powershell
# Setzt eine Verknüpfung im Autostart-Ordner mit dem Wrapper-Skript.
.\scripts\install-windows-autostart.ps1 `
    -RepoPath "C:\Code\ai-assistant" `
    -VenvPython "C:\Code\ai-assistant\.venv\Scripts\pythonw.exe"
```

Der Wrapper (`scripts\ai-assistant-autostart.ps1`) verhält sich identisch zum
Linux-Wrapper:

- Doppelstart wird verhindert
- Auf den Branches `master`/`main` wird automatisch `git pull --ff-only` versucht
- Auf jedem anderen Branch bleibt der lokale Stand unangetastet
- Logs landen in `%LOCALAPPDATA%\ai-assistant\app.log`

---

## Erste Schritte

1. App starten (oder nach Login auf Autostart vertrauen)
2. Hotkey drücken → Radialmenü erscheint
3. **Einstellungen** öffnen und OpenAI API-Key hinterlegen
4. Text markieren → Hotkey → Modul auswählen

Erneutes Drücken des Hotkeys oder Klick außerhalb schließt das Rad.

## Konfiguration

| Wo | Inhalt |
|----|--------|
| Linux: `~/.config/ai-assistant/config.json` | Hotkeys, Modellwahl, Prompts |
| Windows: `%APPDATA%\ai-assistant\config.json` | Hotkeys, Modellwahl, Prompts |
| OS-Keyring (`ai-assistant/openai-api-key`) | OpenAI API-Key |
| Linux: `~/.config/ai-assistant/chats.json` | Persistente Chat-Historie |
| Windows: `%APPDATA%\ai-assistant\chats.json` | Persistente Chat-Historie |

Default-Hotkey:

- Linux: `mouse:button11` (Funktionstaste der MX Master 4 / Side-Button), zusätzlich `<ctrl>+<shift>+<cmd>+<space>`
- Windows: `<ctrl>+<shift>+<alt>+<space>`

Mehrere Hotkeys können parallel konfiguriert werden.

## Hotkey-Syntax

```
<ctrl>+<shift>+<space>      # Tastenkombination (pynput-Stil)
mouse:button11              # Maus-Button
mouse:back / mouse:x1       # Standard-Side-Buttons
combo:shift+ctrl+space      # VK-basierte Kombination (Linux: X11-Keysyms,
                            # Windows: Win32 VK-Codes)
```

## Neues Modul hinzufügen

1. Datei in `ai_assistant/modules/` anlegen (siehe `translator.py`)
2. Modul in `ai_assistant/modules/registry.py` registrieren
3. Assistent neu starten

## Architektur

```
ai_assistant/
├── main.py                    # Einstiegspunkt
├── app_controller.py          # Zentrale UI-/Modul-Orchestrierung
├── config.py                  # Konfiguration (platformdirs)
├── secrets.py                 # OS-Keyring + File-Fallback
├── clipboard.py               # ClipboardManager (delegiert an Backend)
├── hotkey.py                  # Globaler Hotkey-Listener (pynput)
├── chat_store.py              # Persistente Chat-Historie
├── platform_support/          # Plattform-Backends
│   ├── linux.py               #   xclip + LD_LIBRARY_PATH
│   ├── windows.py             #   Qt + optional pyperclip
│   └── macos.py               #   pbcopy/pbpaste
├── modules/                   # Funktionsmodule
└── ui/                        # PyQt6 Dialoge & Overlays
```

## Troubleshooting

### Linux

- **Kein Text ausgewählt**: zuerst markieren, dann Hotkey drücken
- **Hotkey reagiert nicht**: Prozess prüfen (`pgrep -f ai_assistant.main`); Konflikt mit anderen Shortcuts
- **xclip fehlt**: `sudo apt install xclip` (oder die mitgelieferte Local-Lib unter `.local-lib/`)
- **Wayland**: nicht unterstützt, X11-Session verwenden

### Windows

- **Hotkey reagiert nicht**: prüfen, ob `pythonw.exe` läuft (`tasklist /FI "imagename eq pythonw.exe"`)
- **Maus-Button-Hotkey**: viele Maus-Treiber (Logi Options+, G Hub) fangen Extra-Buttons ab. Tipp: in den Treiber-Einstellungen den Button auf „Generic Button" stellen, oder einen Tasten-Hotkey wählen
- **Konsolen-Fenster geht kurz auf**: `python.exe` durch `pythonw.exe` ersetzen
- **Logs**: `%LOCALAPPDATA%\ai-assistant\app.log`

## Lizenz

MIT
