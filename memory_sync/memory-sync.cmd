@echo off
setlocal
set "SCRIPT_DIR=%LOCALAPPDATA%\agy\memory_sync"
if not exist "%SCRIPT_DIR%\sync-once.ps1" (
    if exist "%USERPROFILE%\scripts\sync-once.ps1" (
        set "SCRIPT_DIR=%USERPROFILE%\scripts"
    ) else if exist "%USERPROFILE%\agy-resilience-toolkit\memory_sync\sync-once.ps1" (
        set "SCRIPT_DIR=%USERPROFILE%\agy-resilience-toolkit\memory_sync"
    )
)

if /i "%~1"=="pull" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\sync-once.ps1" -Action pull
    exit /b %ERRORLEVEL%
)
if /i "%~1"=="push" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\sync-once.ps1" -Action push
    exit /b %ERRORLEVEL%
)
if /i "%~1"=="status" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\sync-once.ps1" -Action status
    exit /b %ERRORLEVEL%
)
if /i "%~1"=="daemon" goto START_DAEMON
if /i "%~1"=="start" goto START_DAEMON
if /i "%~1"=="stop" (
    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes-memory-sync.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    echo [OK] Hermes Memory Sync Daemon stopped.
    exit /b 0
)

echo =======================================================
echo          HERMES DISTRIBUTED MEMORY SYNC (VPS HUB)      
echo =======================================================
echo   memory-sync pull    - Ambil memory terbaru dari VPS Hub
echo   memory-sync push    - Kirim memory lokal ke VPS Hub
echo   memory-sync status  - Bandingkan status hash memory lokal vs VPS
echo   memory-sync start   - Jalankan background auto-sync daemon
echo   memory-sync stop    - Hentikan background auto-sync daemon
echo =======================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\sync-once.ps1" -Action status
exit /b 0

:START_DAEMON
wscript "%SCRIPT_DIR%\start-sync.vbs"
echo [OK] Hermes Memory Sync Daemon started in background.
exit /b 0
