@echo off
set "PY_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%PY_CMD%" "%LOCALAPPDATA%\agy\bin\agy_account.py" %*
