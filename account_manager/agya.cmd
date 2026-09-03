@echo off
if /i "%~1"=="web" goto LAUNCH_WEB
if /i "%~1"=="ui" goto LAUNCH_WEB
py -3 "C:\Users\PRIMA\AppData\Local\agy\bin\agy_account.py" %*
exit /b %ERRORLEVEL%

:LAUNCH_WEB
shift
call "C:\Users\PRIMA\AppData\Local\agy\bin\agya-web.cmd"
exit /b 0
