<#
.SYNOPSIS
    Installiert den AI-Assistant-Autostart unter Windows.

.DESCRIPTION
    Legt eine Verknüpfung im Windows-Autostart-Ordner an, die beim Login
    `ai-assistant-autostart.ps1` ausführt.

.PARAMETER RepoPath
    Pfad zum geklonten Repository.

.PARAMETER VenvPython
    Pfad zur pythonw.exe innerhalb des venv (kein Konsolenfenster).
#>

param(
    [string]$RepoPath = "C:\Code\ai-assistant",
    [string]$VenvPython = "C:\Code\ai-assistant\.venv\Scripts\pythonw.exe"
)

$startupDir = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir 'AI Assistant.lnk'
$wrapperScript = Join-Path $RepoPath 'scripts\ai-assistant-autostart.ps1'

if (-not (Test-Path $wrapperScript)) {
    Write-Host "Wrapper-Skript nicht gefunden: $wrapperScript" -ForegroundColor Red
    exit 1
}

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = (Get-Command powershell.exe).Source
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$wrapperScript`" -RepoPath `"$RepoPath`" -VenvPython `"$VenvPython`""
$shortcut.WorkingDirectory = $RepoPath
$shortcut.IconLocation = (Join-Path $RepoPath 'assets\icons\chat.svg')
$shortcut.Description = 'AI Assistant – Radial Overlay'
$shortcut.Save()

Write-Host "Autostart-Verknüpfung erstellt: $shortcutPath" -ForegroundColor Green
Write-Host "Beim nächsten Login startet die App automatisch." -ForegroundColor Green
