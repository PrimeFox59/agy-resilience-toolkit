# hermes-sync-daemon.ps1
# Distributed Memory Watcher & Mirroring Daemon (MC18 <-> VPS <-> DEV20)

param (
    [int]$PollIntervalSeconds = 30
)

$LocalDir = $env:USERPROFILE
$KeyCandidates = @(
    (Join-Path $LocalDir ".ssh\primeprojectx16.pem"),
    "D:\0 Pre Deploy\vps\primeprojectx16.pem",
    (Join-Path $LocalDir "Documents\VPS\primeprojectx16.pem"),
    (Join-Path $LocalDir ".vps-10g-gateway\primeprojectx16.pem")
)
$KeyPath = $KeyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $KeyPath) { $KeyPath = Join-Path $LocalDir ".ssh\primeprojectx16.pem" }
$RemoteUser = "Prime-Projectx"
$RemoteHost = "103.31.205.218"
$RemoteDir = "/home/Prime-Projectx"
$Files = @("USER.md", "MEMORY.md", "AGENTS.md")
$LogFile = Join-Path $LocalDir "scripts\hermes-sync.log"

function Write-Log ($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Output $line
    $line | Out-File -FilePath $LogFile -Append -Encoding utf8
}

Write-Log "=========================================================="
Write-Log "Hermes Distributed Memory Mirroring Daemon Started"
Write-Log "Node: $env:COMPUTERNAME ($LocalDir) -> Hub: $RemoteUser@$RemoteHost"
Write-Log "=========================================================="

$knownHashes = @{}

# Helper: Get local file hash
function Get-LocalHash ($filename) {
    $path = Join-Path $LocalDir $filename
    if (Test-Path $path) {
        return (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLower()
    }
    return $null
}

# Helper: Get remote hashes in one SSH command
function Get-RemoteHashes {
    try {
        $paths = ($Files | ForEach-Object { "$RemoteDir/$_" }) -join " "
        $out = ssh -i $KeyPath -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=no ${RemoteUser}@${RemoteHost} sha256sum $paths 2>$null
        if (-not $out) { return $null }

        $hashes = @{}
        foreach ($line in $out) {
            $parts = $line.Trim() -split "\s+"
            if ($parts.Count -ge 2) {
                $hash = $parts[0].ToLower()
                $name = Split-Path $parts[1] -Leaf
                $hashes[$name] = $hash
            }
        }
        return $hashes
    } catch {
        return $null
    }
}

# Initial synchronization baseline
$remote = Get-RemoteHashes
foreach ($f in $Files) {
    $localHash = Get-LocalHash $f
    if ($remote -and $remote.ContainsKey($f)) {
        $rHash = $remote[$f]
        if ($localHash -and $rHash -and $localHash -ne $rHash) {
            # Local and remote differ on startup, remote is SSOT
            Write-Log "[INIT-PULL] Syncing $f from VPS..."
            scp -i $KeyPath -o BatchMode=yes -o StrictHostKeyChecking=no "${RemoteUser}@${RemoteHost}:${RemoteDir}/$f" (Join-Path $LocalDir $f) 2>$null
            $knownHashes[$f] = $rHash
        } else {
            $knownHashes[$f] = if ($localHash) { $localHash } else { $rHash }
        }
    } else {
        $knownHashes[$f] = $localHash
    }
}
Write-Log "[INIT] Baseline established. Monitoring every $PollIntervalSeconds seconds..."

# Main continuous sync loop
while ($true) {
    try {
        # 1. Check if local files modified
        foreach ($f in $Files) {
            $localHash = Get-LocalHash $f
            if ($localHash -and $knownHashes.ContainsKey($f) -and $localHash -ne $knownHashes[$f]) {
                Write-Log "[LOCAL-CHANGE] $f modified locally. Pushing to VPS..."
                $localFile = Join-Path $LocalDir $f
                scp -i $KeyPath -o BatchMode=yes -o StrictHostKeyChecking=no $localFile "${RemoteUser}@${RemoteHost}:${RemoteDir}/$f" 2>$null
                $knownHashes[$f] = $localHash
                Write-Log "[PUSH-OK] Mirrored $f -> VPS ($($localHash.Substring(0, 8)))"
            }
        }

        # 2. Check if remote files modified by peer nodes
        $remote = Get-RemoteHashes
        if ($remote) {
            foreach ($f in $Files) {
                if ($remote.ContainsKey($f)) {
                    $rHash = $remote[$f]
                    $localHash = Get-LocalHash $f
                    if ($rHash -ne $knownHashes[$f] -and $rHash -ne $localHash) {
                        Write-Log "[REMOTE-CHANGE] $f updated on VPS by peer node. Pulling..."
                        scp -i $KeyPath -o BatchMode=yes -o StrictHostKeyChecking=no "${RemoteUser}@${RemoteHost}:${RemoteDir}/$f" (Join-Path $LocalDir $f) 2>$null
                        $knownHashes[$f] = $rHash
                        Write-Log "[PULL-OK] Updated local $f from VPS ($($rHash.Substring(0, 8)))"
                    } elseif ($rHash -eq $localHash) {
                        $knownHashes[$f] = $localHash
                    }
                }
            }
        }
    } catch {
        Write-Log "[WARN] Loop exception: $_"
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
