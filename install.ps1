# Auto-Installer for Antigravity Resilience Toolkit & Web UI
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     INSTALLING ANTIGRAVITY RESILIENCE TOOLKIT        " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$targetBinDir = "$env:LOCALAPPDATA\agy\bin"
$targetWebDir = "$env:LOCALAPPDATA\agy\webui"
$targetSkillDir = "$env:USERPROFILE\.gemini\config\skills\agy-resilience"

if (-not (Test-Path $targetBinDir)) { New-Item -ItemType Directory -Force -Path $targetBinDir | Out-Null }
if (-not (Test-Path "$targetWebDir\uploads")) { New-Item -ItemType Directory -Force -Path "$targetWebDir\uploads" | Out-Null }
if (-not (Test-Path "$targetWebDir\templates")) { New-Item -ItemType Directory -Force -Path "$targetWebDir\templates" | Out-Null }
if (-not (Test-Path $targetSkillDir)) { New-Item -ItemType Directory -Force -Path $targetSkillDir | Out-Null }

$sourceDir = $PSScriptRoot

# 1. Copy Account Manager & Launchers
Write-Host "[*] Installing CLI binaries & wrappers..." -ForegroundColor Yellow
Copy-Item "$sourceDir\account_manager\agy_account.py" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agy-account.cmd" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agya.cmd" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\account_manager\agya-web.cmd" -Destination $targetBinDir -Force
if (Test-Path "$sourceDir\account_manager\py.cmd") {
    Copy-Item "$sourceDir\account_manager\py.cmd" -Destination $targetBinDir -Force
}

# 2. Copy Fallback Runners
Copy-Item "$sourceDir\fallback_runners\agy-fallback.ps1" -Destination $targetBinDir -Force
Copy-Item "$sourceDir\fallback_runners\agy-fallback.cmd" -Destination $targetBinDir -Force

# 3. Copy Web UI Files
Write-Host "[*] Installing Web UI assets..." -ForegroundColor Yellow
Copy-Item "$sourceDir\webui\server.py" -Destination $targetWebDir -Force
Copy-Item "$sourceDir\webui\templates\index.html" -Destination "$targetWebDir\templates\index.html" -Force

# 4. Install AGY Skill (Antigravity Native Skill Integration)
if (Test-Path "$sourceDir\skills\agy-resilience\SKILL.md") {
    Write-Host "[*] Registering AGY Skill (agy-resilience)..." -ForegroundColor Yellow
    Copy-Item "$sourceDir\skills\agy-resilience\SKILL.md" -Destination "$targetSkillDir\SKILL.md" -Force
}

# 5. Check and Install Python dependencies (Flask)
Write-Host "[*] Checking Python environment & dependencies..." -ForegroundColor Yellow
$pyExe = "python"
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd -or $pyCmd.Source -like "*WindowsApps*") {
    $foundPy = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    if (Test-Path $foundPy) { $pyExe = $foundPy }
}
try {
    & $pyExe -c "import flask" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[*] Installing Flask for Web UI..." -ForegroundColor Yellow
        & $pyExe -m pip install flask --quiet
    }
} catch {}

# 6. Create Desktop Shortcut
$desktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$desktopLauncher = "$desktopPath\Antigravity Web UI.cmd"
Set-Content -Path $desktopLauncher -Value "@echo off`r`nstart `"`" `"$targetBinDir\agya-web.cmd`"" -Force

# 7. Set Execution Policy
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue
} catch {}

# 8. Ensure PATH contains agy\bin
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$targetBinDir*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$targetBinDir;$userPath", "User")
}

Write-Host "`n[OK] Installation & AGY CLI Integration successful!" -ForegroundColor Green
Write-Host "CLI Binaries  : $targetBinDir" -ForegroundColor Gray
Write-Host "Web UI Server : $targetWebDir" -ForegroundColor Gray
Write-Host "AGY Skill     : $targetSkillDir\SKILL.md" -ForegroundColor Gray
Write-Host "Desktop Icon  : $desktopLauncher" -ForegroundColor Gray
Write-Host "`nAvailable Commands in Terminal / CMD:" -ForegroundColor Yellow
Write-Host "  agya web                  - Launch Web UI with Vision in browser"
Write-Host "  agy-account list          - List all registered Google accounts"
Write-Host "  agy-account add <name>    - Add & login a new Google account"
Write-Host "  agy-account switch <name> - Switch active Google account"
Write-Host "  agya -c                   - Auto-fallback to next account & resume session"
Write-Host "  agya -p <prompt>          - Run AGY prompt with automatic quota fallback"
Write-Host "  agy-fallback check        - Health check quotas across models"
Write-Host "=======================================================`n" -ForegroundColor Cyan
