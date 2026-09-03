@echo off
if /i "%~1"=="web" goto LAUNCH_WEB
if /i "%~1"=="ui" goto LAUNCH_WEB

set "PY_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%PY_CMD%" "%LOCALAPPDATA%\agy\bin\agy_account.py" %*
exit /b %ERRORLEVEL%

:LAUNCH_WEB
shift
call "%LOCALAPPDATA%\agy\bin\agya-web.cmd"
exit /b 0
