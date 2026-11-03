param([switch]$Install, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Crie o ambiente Python: py -3.12 -m venv .venv. Depois rode este script com -Install.'
}
Push-Location $projectDir
try {
    if ($Install) {
        & $pythonPath -m pip install -r backend\requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências Python.' }
        & npm.cmd --prefix frontend ci
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências Node.' }
    }
    $stateDir = Join-Path $projectDir '.local'
    New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
    $statePath = Join-Path $stateDir 'processes.json'
    if (Test-Path -LiteralPath $statePath) {
        $runningCount = 0
        foreach ($saved in (Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json)) {
            $running = Get-Process -Id $saved.id -ErrorAction SilentlyContinue
            if ($running -and $running.StartTime.ToUniversalTime().Ticks.ToString() -eq $saved.started_ticks) {
                $runningCount++
            }
        }
        if ($runningCount -eq 2) {
            Write-Host 'Ateliê Verde já está em execução. Acesse http://127.0.0.1:5173.'
            if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' }
            return
        }
        & (Join-Path $PSScriptRoot 'parar.ps1')
    }
    foreach ($port in @(8015,5173)) {
        $socket = [System.Net.Sockets.TcpClient]::new()
        try {
            $socket.Connect('127.0.0.1',$port)
            throw "A porta $port já está ocupada por um serviço não registrado. Encerre esse serviço antes de iniciar o Ateliê Verde."
        } catch [System.Net.Sockets.SocketException] {
            # A porta está livre.
        } finally { $socket.Dispose() }
    }
    $env:SEED_DEMO = 'true'
    $env:APP_ENV = 'development'
    # Explicit environment overrides .env; the older local JSON is only a fallback.
    $assistantStartupJson = & $pythonPath -c "import sys,os,json;sys.path.insert(0,'backend');from app.assistant_settings import load;load();print(json.dumps({key:os.getenv(key,'') for key in ['RAFINHA_PROVIDER','RAFINHA_OLLAMA_MODEL','RAFINHA_OLLAMA_URL']}))"
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao carregar a configuração do Rafinha.' }
    $assistantStartup = $assistantStartupJson | ConvertFrom-Json
    foreach ($assistantKey in @('RAFINHA_PROVIDER','RAFINHA_OLLAMA_MODEL','RAFINHA_OLLAMA_URL')) {
        $assistantValue = $assistantStartup.PSObject.Properties[$assistantKey].Value
        if ($assistantValue) { [Environment]::SetEnvironmentVariable($assistantKey, [string]$assistantValue, 'Process') }
    }
    $rafinhaConfigPath = Join-Path $stateDir 'rafinha-provider.json'
    if (Test-Path -LiteralPath $rafinhaConfigPath) {
        $rafinhaConfig = Get-Content -LiteralPath $rafinhaConfigPath -Raw | ConvertFrom-Json
        if (-not $env:RAFINHA_OLLAMA_MODEL) { $env:RAFINHA_OLLAMA_MODEL = [string]$rafinhaConfig.model }
        if (-not $env:RAFINHA_OLLAMA_URL) { $env:RAFINHA_OLLAMA_URL = [string]$rafinhaConfig.url }
        if (-not $env:RAFINHA_PROVIDER) { $env:RAFINHA_PROVIDER = 'auto' }
    }
    & $pythonPath -m alembic -c backend\alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas migrações. Confira a documentação antes de alterar um banco existente.' }
    $processes = @()
    $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8015') -WorkingDirectory $projectDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDir 'api.log') -RedirectStandardError (Join-Path $stateDir 'api-error.log')
    $processes += $apiProcess.Id
    $nodePath = (Get-Command node.exe).Source
    $webProcess = Start-Process -FilePath $nodePath -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory (Join-Path $projectDir 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDir 'web.log') -RedirectStandardError (Join-Path $stateDir 'web-error.log')
    $processes += $webProcess.Id
    @($apiProcess,$webProcess) | ForEach-Object { @{id=$_.Id;started_ticks=$_.StartTime.ToUniversalTime().Ticks.ToString()} } | ConvertTo-Json | Set-Content -LiteralPath $statePath
    $ready = $false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        $apiProcess.Refresh()
        $webProcess.Refresh()
        if ($apiProcess.HasExited -or $webProcess.HasExited) { throw 'Um serviço não iniciou. Consulte .local\*-error.log.' }
        try { Invoke-WebRequest 'http://127.0.0.1:8015/api/health' -UseBasicParsing -TimeoutSec 1 | Out-Null; Invoke-WebRequest 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 1 | Out-Null; $ready=$true; break } catch {}
    }
    if (-not $ready) { throw 'Os serviços não responderam a tempo. Consulte os logs.' }
    Write-Host 'Ateliê Verde: http://127.0.0.1:5173 · API: http://127.0.0.1:8015/docs'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173' }
} catch {
    if ($processes) { foreach ($processId in $processes) { & taskkill.exe /PID $processId /T /F 2>$null | Out-Null } }
    throw
} finally { Pop-Location }
