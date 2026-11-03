$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectDir '.local\processes.json'
if (Test-Path -LiteralPath $pidFile) {
    foreach ($saved in (Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json)) {
        $process = Get-Process -Id $saved.id -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.started_ticks) {
            & taskkill.exe /PID $saved.id /T /F | Out-Null
        }
    }
    Remove-Item -LiteralPath $pidFile
}
Write-Host 'Serviços do Ateliê Verde encerrados.'
