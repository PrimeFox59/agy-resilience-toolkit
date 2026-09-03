@echo off
title Antigravity Web UI Server
echo =======================================================
echo        STARTING GOOGLE ANTIGRAVITY WEB UI               
echo =======================================================
echo  [*] Opening browser: http://127.0.0.1:4567
echo  [*] Multi-Account & Vision Attachment: READY
echo =======================================================
set "PY_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
start "" "http://127.0.0.1:4567"
"%PY_CMD%" "%LOCALAPPDATA%\agy\webui\server.py" 4567
