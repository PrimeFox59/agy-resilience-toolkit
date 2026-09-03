@echo off
set "REAL_PY=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "REAL_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%REAL_PY%" %*
