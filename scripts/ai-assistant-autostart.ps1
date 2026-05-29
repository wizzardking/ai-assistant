<#
.SYNOPSIS
    Autostart-Wrapper für den AI Assistant unter Windows.

.DESCRIPTION
    - Startet die App nicht doppelt.
    - Auf den Branches master/main wird "git pull --ff-only" versucht, sodass
      der Autostart immer die aktuelle stabile Version verwendet.
    - Auf jedem anderen Branch (z.B. Feature-Branch) bleibt der lokale
      Stand unangetastet.
    - Loggt nach %LOCALAPPDATA%\ai-assistant\app.log.

.NOTES
    Pfade unten ggf. an die eigene Installation anpassen.
#>

param(
    [string]$RepoPath = "C:\Code\ai-assistant",
    [string]$VenvPython = "C:\Code\ai-assistant\.venv\Scripts\pythonw.exe"
)

$ErrorActionPreference = 'Continue'

$LogDir = Join-Path $env:LOCALAPPDATA 'ai-assistant'
$LogFile = Join-Path $LogDir 'app.log'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    "[autostart $stamp] $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
}

# Doppelstart vermeiden: prüfe, ob bereits ein Python-Prozess die App ausführt.
$running = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'ai_assistant\.main' }
if ($running) {
    Write-Log "AI Assistant läuft bereits (PID $($running[0].ProcessId)) – Start übersprungen."
    exit 0
}

if (-not (Test-Path $RepoPath)) {
    Write-Log "Repo-Pfad nicht gefunden: $RepoPath"
    exit 1
}
if (-not (Test-Path $VenvPython)) {
    Write-Log "Python (venv) nicht gefunden: $VenvPython"
    exit 1
}

Push-Location $RepoPath
try {
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) { $branch = 'unknown' }

    if ($branch -in @('master', 'main')) {
        $dirty = $false
        git diff --quiet
        if ($LASTEXITCODE -ne 0) { $dirty = $true }
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) { $dirty = $true }

        if (-not $dirty) {
            Write-Log "Branch=$branch – versuche git pull --ff-only"
            $pullResult = git pull --ff-only --quiet 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Log "git pull fehlgeschlagen: $pullResult"
            }
        } else {
            Write-Log "Branch=$branch hat uncommittete Änderungen – kein Pull."
        }
    } else {
        Write-Log "Branch=$branch – kein automatischer Pull (Entwicklungs-Branch)."
    }

    Write-Log "Starte AI Assistant ($VenvPython)"
    # Start-Process, damit das Skript zurückkehrt; pythonw verhindert Konsole.
    Start-Process -FilePath $VenvPython `
        -ArgumentList @('-m', 'ai_assistant.main') `
        -WorkingDirectory $RepoPath `
        -WindowStyle Hidden `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $LogFile
} finally {
    Pop-Location
}
