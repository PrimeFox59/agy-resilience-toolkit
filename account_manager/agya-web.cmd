@echo off
title Antigravity Web UI Server
echo =======================================================
echo        STARTING GOOGLE ANTIGRAVITY WEB UI               
echo =======================================================
echo  [*] Target URL : http://127.0.0.1:4567
echo  [*] Status     : Active with Vision & Multi-Account
echo =======================================================

netstat -ano | findstr /R /C:":4567 " | findstr /I "LISTENING" >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo  [*] Server is already running. Opening browser...
    start "" "http://127.0.0.1:4567"
    timeout /t 2 >nul
    exit /b 0
)

set "PY_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
start "" "http://127.0.0.1:4567"
"%PY_CMD%" "%LOCALAPPDATA%\agy\webui\server.py" 4567
