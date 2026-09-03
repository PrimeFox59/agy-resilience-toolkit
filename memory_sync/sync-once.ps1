# Hermes Memory Manual / On-Demand Sync
param (
    [ValidateSet("push", "pull", "status")]
    [string]$Action = "push"
)

$LocalDir = $env:USERPROFILE
$RemoteUser = "Prime-Projectx"
$RemoteHost = "103.31.205.218"
$RemoteDir = "/home/Prime-Projectx"
$KeyCandidates = @(
    (Join-Path $LocalDir ".ssh\primeprojectx16.pem"),
    "D:\0 Pre Deploy\vps\primeprojectx16.pem",
    (Join-Path $LocalDir "Documents\VPS\primeprojectx16.pem"),
    (Join-Path $LocalDir ".vps-10g-gateway\primeprojectx16.pem")
)
$KeyPath = $KeyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $KeyPath) { $KeyPath = Join-Path $LocalDir ".ssh\primeprojectx16.pem" }
$Files = @("USER.md", "MEMORY.md", "AGENTS.md")

Write-Host "=== Hermes Memory Sync ($Action) ===" -ForegroundColor Cyan
Write-Host "Local Node: $env:COMPUTERNAME ($LocalDir)"
Write-Host "Central Hub: $RemoteUser@$RemoteHost"

if ($Action -eq "push") {
    foreach ($f in $Files) {
        $localFile = Join-Path $LocalDir $f
        if (Test-Path $localFile) {
            Write-Host "Pushing $f -> VPS..." -NoNewline
            scp -i $KeyPath -o StrictHostKeyChecking=no $localFile "${RemoteUser}@${RemoteHost}:${RemoteDir}/$f" | Out-Null
            Write-Host " [OK]" -ForegroundColor Green
        }
    }
    # Sync .agents directory
    $agentsDir = Join-Path $LocalDir ".agents"
    if (Test-Path $agentsDir) {
        Write-Host "Pushing .agents/ -> VPS..." -NoNewline
        scp -i $KeyPath -r -o StrictHostKeyChecking=no $agentsDir "${RemoteUser}@${RemoteHost}:${RemoteDir}/" | Out-Null
        Write-Host " [OK]" -ForegroundColor Green
    }
} elseif ($Action -eq "pull") {
    foreach ($f in $Files) {
        $localFile = Join-Path $LocalDir $f
        Write-Host "Pulling $f <- VPS..." -NoNewline
        scp -i $KeyPath -o StrictHostKeyChecking=no "${RemoteUser}@${RemoteHost}:${RemoteDir}/$f" $localFile | Out-Null
        Write-Host " [OK]" -ForegroundColor Green
    }
} elseif ($Action -eq "status") {
    Write-Host "`n--- SHA256 Comparison ---" -ForegroundColor Yellow
    foreach ($f in $Files) {
        $localFile = Join-Path $LocalDir $f
        $localHash = if (Test-Path $localFile) { (Get-FileHash -Algorithm SHA256 $localFile).Hash.Substring(0, 12) } else { "MISSING" }
        Write-Host "$f local: $localHash"
    }
    ssh -i $KeyPath -o StrictHostKeyChecking=no "${RemoteUser}@${RemoteHost}" "sha256sum ${RemoteDir}/USER.md ${RemoteDir}/MEMORY.md ${RemoteDir}/AGENTS.md"
}

Write-Host "Sync operation complete.`n" -ForegroundColor Green
