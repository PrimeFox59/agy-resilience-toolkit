$ErrorActionPreference = "Continue"
$logFile = "C:\Users\PRIMA\scripts\sync.log"
"Starting Hermes Memory Sync at $(Get-Date)" | Out-File -FilePath $logFile -Append

& "C:\Program Files\nodejs\node.exe" "C:\Users\PRIMA\scripts\hermes-memory-sync.js" *>> $logFile
