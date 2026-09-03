@echo off
title Antigravity Web UI Server
echo =======================================================
echo        STARTING GOOGLE ANTIGRAVITY WEB UI               
echo =======================================================
echo  [*] Opening browser: http://127.0.0.1:4567
echo  [*] Multi-Account & Vision Attachment: READY
echo =======================================================
start "" "http://127.0.0.1:4567"
py -3 "C:\Users\PRIMA\AppData\Local\agy\webui\server.py" 4567
