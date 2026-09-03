<#
.SYNOPSIS
    Antigravity CLI (AGY) Auto-Fallback & Quota Resilience Manager
    Otomatis mendeteksi limit kuota dan beralih ke model alternatif (Gemini / Claude / Pro / GPT)
.DESCRIPTION
    Menyediakan eksekusi cerdas untuk Antigravity CLI:
    - agya / agy-fallback           : Luncurkan sesi interaktif dengan model terbaik yang kuotanya siap
    - agya -c / agy-fallback -c     : Lanjutkan sesi terakhir yang terputus dengan model alternatif
    - agya check                    : Cek status kuota semua model (Gemini 3.8, Claude, Gemini 3.7, Pro)
    - agya -p "..." / agya run ...  : Jalankan perintah dengan auto-retry fallback jika kuota habis
#>

$Arguments = $args

$AGY_EXE = "$env:LOCALAPPDATA\agy\bin\agy.exe"
if (-not (Test-Path $AGY_EXE)) {
    $found = Get-Command agy.exe -ErrorAction SilentlyContinue
    if ($found) { $AGY_EXE = $found.Source }
}

# Rantai prioritas model fallback
$MODEL_CHAIN = @(
    "gemini-3.8-flash-high",
    "claude-sonnet-4-6",
    "gemini-3.7-flash-high",
    "gemini-3.1-pro-high",
    "gpt-oss-120b-medium"
)

# Indikator error kuota habis
$QUOTA_ERROR_PATTERNS = @(
    "Individual quota reached",
    "quota reached",
    "Please upgrade your subscription",
    "rate limit exceeded",
    "Resource has been exhausted",
    "429 Too Many Requests"
)

function Test-ModelQuota([string]$model) {
    try {
        # Eksekusi probe langsung via CLI print mode
        $output = (& $AGY_EXE -p "Jawab singkat: OK" --model $model 2>&1 | Out-String)
        $exitCode = $LASTEXITCODE

        foreach ($p in $QUOTA_ERROR_PATTERNS) {
            if ($output -like "*$p*") {
                return $false
            }
        }
        return ($exitCode -eq 0 -and $output.Trim().Length -gt 0)
    }
    catch {
        return $false
    }
}

function Show-QuotaStatus() {
    Write-Host "`n=======================================================" -ForegroundColor Cyan
    Write-Host "     ANTIGRAVITY CLI (AGY) MODEL QUOTA HEALTH CHECK   " -ForegroundColor Cyan
    Write-Host "=======================================================" -ForegroundColor Cyan
    
    foreach ($m in $MODEL_CHAIN) {
        Write-Host -NoNewline "Checking [$m] ... " -ForegroundColor Gray
        $isOk = Test-ModelQuota -model $m
        if ($isOk) {
            Write-Host "READY (Active & Quota Available)" -ForegroundColor Green
        } else {
            Write-Host "EXHAUSTED / LIMITED" -ForegroundColor Red
        }
    }
    Write-Host "-------------------------------------------------------`n" -ForegroundColor Cyan
}

function Find-FirstAvailableModel() {
    Write-Host "[AGY-FALLBACK] Memindai model dengan kuota aktif..." -ForegroundColor Yellow
    foreach ($m in $MODEL_CHAIN) {
        Write-Host -NoNewline "  - Menguji $m ... " -ForegroundColor Gray
        if (Test-ModelQuota -model $m) {
            Write-Host "TERSEDIA!" -ForegroundColor Green
            return $m
        } else {
            Write-Host "LIMIT / TIDAK AKTIF" -ForegroundColor Red
        }
    }
    Write-Host "[AGY-FALLBACK] Semua model habis atau offline. Menggunakan default $($MODEL_CHAIN[0])." -ForegroundColor DarkYellow
    return $MODEL_CHAIN[0]
}

# ----------------- ROUTING LOGIC -----------------

if ($null -eq $Arguments -or $Arguments.Length -eq 0) {
    # Tanpa argumen: Cari model yang siap lalu mulai interactive session
    $bestModel = Find-FirstAvailableModel
    Write-Host "`n[AGY-FALLBACK] Memulai sesi interaktif dengan model: $bestModel`n" -ForegroundColor Cyan
    & $AGY_EXE --model $bestModel
    exit $LASTEXITCODE
}

$firstArg = $Arguments[0].ToLower()

if ($firstArg -eq "check" -or $firstArg -eq "status") {
    Show-QuotaStatus
    exit 0
}

if ($firstArg -eq "-c" -or $firstArg -eq "--continue" -or $firstArg -eq "continue" -or $firstArg -eq "resume") {
    # Melanjutkan sesi sebelumnya yang terputus dengan model yang kuotanya siap
    Write-Host "`n[AGY-FALLBACK] Mendeteksi sesi terakhir yang terputus karena kuota..." -ForegroundColor Yellow
    $bestModel = Find-FirstAvailableModel
    Write-Host "[AGY-FALLBACK] Melanjutkan sesi sebelumnya dengan model: $bestModel`n" -ForegroundColor Green
    & $AGY_EXE -c --model $bestModel
    exit $LASTEXITCODE
}

# Mode eksekusi dengan auto-retry fallback
# Contoh: agya -p "buat script backup"
$targetArgs = @($Arguments)
Write-Host "[AGY-FALLBACK] Menjalankan tugas AGY dengan perlindungan auto-fallback..." -ForegroundColor Cyan

$attempt = 0
$success = $false

foreach ($currentModel in $MODEL_CHAIN) {
    $attempt++
    Write-Host "`n[AGY-FALLBACK] [Percobaan $attempt] Mencoba model: $currentModel" -ForegroundColor Gray
    
    # Rekonstruksi argumen dengan model aktif
    $execArgs = @()
    $hasModel = $false
    for ($i = 0; $i -lt $targetArgs.Length; $i++) {
        if ($targetArgs[$i] -eq "--model" -or $targetArgs[$i] -eq "-m") {
            $hasModel = $true
            $execArgs += $targetArgs[$i]
            $execArgs += $currentModel
            $i++
        } else {
            $execArgs += $targetArgs[$i]
        }
    }
    if (-not $hasModel) {
        $execArgs += "--model"
        $execArgs += $currentModel
    }

    $out = (& $AGY_EXE @execArgs 2>&1 | Out-String)
    $code = $LASTEXITCODE

    $isQuota = $false
    foreach ($p in $QUOTA_ERROR_PATTERNS) {
        if ($out -like "*$p*") {
            $isQuota = $true
            break
        }
    }

    if ($isQuota) {
        Write-Host "[!] KUOTA HABIS pada model: $currentModel" -ForegroundColor Red
        Write-Host "    Pesan: Individual quota reached. Otomatis fallback ke model berikutnya..." -ForegroundColor Yellow
        # Beralih ke mode continue untuk menjaga konteks
        if (-not ($targetArgs -contains "-c" -or $targetArgs -contains "--continue")) {
            $targetArgs = @("-c") + $targetArgs
        }
        continue
    } else {
        Write-Host $out
        $success = $true
        exit $code
    }
}

if (-not $success) {
    Write-Host "`n[AGY-FALLBACK] Semua model dalam rantai fallback telah mencapai batas kuota." -ForegroundColor Red
    exit 1
}
