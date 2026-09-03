# Auto-Installer for Antigravity Resilience Toolkit
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     INSTALLING ANTIGRAVITY RESILIENCE TOOLKIT        " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$targetDir = "$env:LOCALAPPDATA\agy\bin"
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
}

$sourceDir = $PSScriptRoot

# Copy Account Manager files
Copy-Item "$sourceDir\account_manager\agy_account.py" -Destination $targetDir -Force
Copy-Item "$sourceDir\account_manager\agy-account.cmd" -Destination $targetDir -Force
Copy-Item "$sourceDir\account_manager\agya.cmd" -Destination $targetDir -Force

# Copy Fallback Runners
Copy-Item "$sourceDir\fallback_runners\agy-fallback.ps1" -Destination $targetDir -Force
Copy-Item "$sourceDir\fallback_runners\agy-fallback.cmd" -Destination $targetDir -Force

# Set Execution Policy
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue
} catch {}

Write-Host "`n[OK] Installation successful!" -ForegroundColor Green
Write-Host "Files copied to: $targetDir" -ForegroundColor Gray
Write-Host "`nAvailable Commands:" -ForegroundColor Yellow
Write-Host "  agy-account list         - List all registered Google accounts"
Write-Host "  agy-account add <name>   - Add & login a new Google account"
Write-Host "  agy-account switch <name>- Switch active Google account"
Write-Host "  agya -c                  - Auto-fallback to next account & resume session"
Write-Host "  agya -p <prompt>         - Run AGY prompt with automatic quota fallback"
Write-Host "=======================================================`n" -ForegroundColor Cyan
