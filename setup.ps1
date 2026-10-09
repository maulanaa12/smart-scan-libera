$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
}
& '.venv\Scripts\python.exe' -m pip install --no-cache-dir -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Instalasi paket gagal' }
New-Item -ItemType Directory -Force -Path 'models' | Out-Null
$modelPath = Join-Path $PSScriptRoot 'models\hand_landmarker.task'
if (-not (Test-Path -LiteralPath $modelPath)) {
    $partialPath = "$modelPath.download"
    try {
        Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task' -OutFile $partialPath
        if ((Get-Item -LiteralPath $partialPath).Length -lt 1000000) { throw 'Unduhan model tidak lengkap' }
        Move-Item -LiteralPath $partialPath -Destination $modelPath
    } finally {
        if (Test-Path -LiteralPath $partialPath) { Remove-Item -LiteralPath $partialPath }
    }
}
Write-Host 'Selesai. Jalankan run_smart_scan.bat --dry-run untuk menguji tanpa memotret.'
