# Background Heartbeat Pull Daemon
$LocalDir = $env:USERPROFILE
$ScriptPath = Join-Path $LocalDir "scripts\sync-once.ps1"

while ($true) {
    try {
        & powershell -ExecutionPolicy Bypass -File $ScriptPath -Action pull | Out-Null
    } catch {
        # Silent retry
    }
    Start-Sleep -Seconds 60
}
