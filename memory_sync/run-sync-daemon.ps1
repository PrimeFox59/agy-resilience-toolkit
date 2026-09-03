$ErrorActionPreference = "Continue"
$userDir = $env:USERPROFILE
$logFile = "$userDir\scripts\sync.log"
"Starting Hermes Memory Sync at $(Get-Date)" | Out-File -FilePath $logFile -Append

& "node" "$userDir\scripts\hermes-memory-sync.js" *>> $logFile
