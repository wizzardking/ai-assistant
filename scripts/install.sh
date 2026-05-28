#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
AUTOSTART_DIR="${HOME}/.config/autostart"

echo "==> AI Assistant Installation"
echo "Projekt: ${PROJECT_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 nicht gefunden. Bitte installieren: sudo apt install python3 python3-venv"
  exit 1
fi

echo "==> System-Abhängigkeiten prüfen..."
MISSING=()
for pkg in python3-venv libsecret-1-0; do
  if ! dpkg -s "$pkg" >/dev/null 2>&1; then
    MISSING+=("$pkg")
  fi
done

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "Fehlende Pakete: ${MISSING[*]}"
  echo "Installiere mit: sudo apt install ${MISSING[*]}"
fi

echo "==> Virtuelle Umgebung erstellen..."
if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "==> Python-Abhängigkeiten installieren..."
pip install --upgrade pip
pip install -e "${PROJECT_DIR}"

echo "==> Autostart einrichten..."
mkdir -p "${AUTOSTART_DIR}"
DESKTOP_FILE="${AUTOSTART_DIR}/ai-assistant.desktop"
sed "s|Exec=.*|Exec=${VENV_DIR}/bin/ai-assistant|" \
  "${PROJECT_DIR}/data/ai-assistant.desktop" > "${DESKTOP_FILE}"

echo "==> Fertig!"
echo "Manuell starten: ${VENV_DIR}/bin/ai-assistant"
echo "Hotkey: Ctrl+Shift+Leertaste"
echo "Konfiguration: ~/.config/ai-assistant/config.json"
echo "Autostart: ${DESKTOP_FILE}"
