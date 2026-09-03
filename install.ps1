# Auto-Installer for Antigravity Resilience Toolkit & Web UI
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     INSTALLING ANTIGRAVITY RESILIENCE TOOLKIT        " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$targetBinDir = "$env:LOCALAPPDATA\agy\bin"
$targetWebDir = "$env:LOCALAPPDATA\agy\webui"

if (-not (Test-Path $targetBinDir)) { New-Item -ItemType Directory -Force -Path $targetBinDir | Out-Null }
if (-not (Test-Path "$targetWebDir\uploads")) { New-Item -ItemType Directory -Force -Path "$targetWebDir\uploads" | Out-Null }
if (-not (Test-Path "$targetWebDir\templates")) { New-Item -ItemType Directory -Force -Path "$targetWebDir\templates" | Out-Null }

$sourceDir = $PSScriptRoot

# Copy Account Manager & Launchers
Copy-Item "$sourceDir\account_manager\agy_account.py" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agy-account.cmd" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agya.cmd" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agya-web.cmd" -Destination $targetBinDir -Force

# Copy Fallback Runners
Copy-Item "$sourceDir\fallback_runners\agy-fallback.ps1" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\fallback_runners\agy-fallback.cmd" -Destination $targetBinDir -Force

# Copy Web UI Files
Copy-Item "$sourceDir\webui\server.py" -Destination $targetWebDir -Force
Copy-Item "$sourceDir\webui\templates\index.html" -Destination "$targetWebDir\templates\index.html" -Force

# Create Desktop Shortcut
$desktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$desktopLauncher = "$desktopPath\Antigravity Web UI.cmd"
Set-Content -Path $desktopLauncher -Value "@echo off`r`nstart `"`" `"$targetBinDir\agya-web.cmd`"" -Force

# Set Execution Policy
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue
} catch {}

Write-Host "`n[OK] Installation successful!" -ForegroundColor Green
Write-Host "CLI Binaries : $targetBinDir" -ForegroundColor Gray
Write-Host "Web UI Server: $targetWebDir" -ForegroundColor Gray
Write-Host "Desktop Icon : $desktopLauncher" -ForegroundColor Gray
Write-Host "`nAvailable Commands:" -ForegroundColor Yellow
Write-Host "  agya web                 - Launch Web UI with Image Vision in browser"
Write-Host "  agy-account list         - List all registered Google accounts"
Write-Host "  agy-account add <name>   - Add & login a new Google account"
Write-Host "  agy-account switch <name>- Switch active Google account"
Write-Host "  agya -c                  - Auto-fallback to next account & resume session"
Write-Host "  agya -p <prompt>         - Run AGY prompt with automatic quota fallback"
Write-Host "=======================================================`n" -ForegroundColor Cyan
