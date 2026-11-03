param([switch]$InstallBuildDependencies, [switch]$SkipSmoke)
$ErrorActionPreference = 'Stop'
$projectDir = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$pythonPath = Join-Path $projectDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Crie o ambiente virtual e instale backend/requirements.txt antes do build.' }
if ($env:OS -ne 'Windows_NT') { throw 'Gere o executável Windows em uma instalação Windows.' }
Push-Location $projectDir
try {
    if ($InstallBuildDependencies) {
        & $pythonPath -m pip install -r backend\requirements-build.txt
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências de build.' }
    }
    & $pythonPath -c "import PyInstaller; assert PyInstaller.__version__ == '6.22.3', 'Instale backend/requirements-build.txt'"
    if ($LASTEXITCODE -ne 0) { throw 'Instale as dependências de build com -InstallBuildDependencies.' }
    & npm.cmd --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw 'O build do frontend falhou. Nenhum release foi gerado.' }
    & $pythonPath scripts\verificar_release.py --source-only
    if ($LASTEXITCODE -ne 0) { throw 'Verificação de segurança rejeitou os arquivos de entrada.' }
    $buildTag = Get-Date -Format 'yyyyMMdd-HHmmss'
    $releaseRoot = Join-Path $projectDir "release\windows\$buildTag"
    $buildRoot = Join-Path $projectDir "build\pyinstaller\$buildTag"
    # Fresh directories only: builds never remove or replace an existing release.
    if ((Test-Path -LiteralPath $releaseRoot) -or (Test-Path -LiteralPath $buildRoot)) { throw 'O diretório de build já existe. Execute novamente para gerar uma saída nova.' }
    & $pythonPath -m PyInstaller --noconfirm --distpath $releaseRoot --workpath $buildRoot packaging\AtelieVerde.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller não concluiu. O diretório não é um release aprovado.' }
    $appFolder = Join-Path $releaseRoot 'AtelieVerde'
    @'
@echo off
start "" "%~dp0AtelieVerde.exe" --stop
'@ | Set-Content -LiteralPath (Join-Path $appFolder 'EncerrarAtelieVerde.cmd') -Encoding ascii
    @'
Ateliê Verde — portal local Windows

Extraia toda esta pasta e abra AtelieVerde.exe. Mantenha _internal junto do executável.
O portal abre no navegador e atende somente em 127.0.0.1.
Use EncerrarAtelieVerde.cmd para parar o servidor local.

Banco, uploads, logs e cofre ficam em %LOCALAPPDATA%\AtelieVerde.
A distribuição contém dados demonstrativos públicos, gerados no primeiro início.
Contas da demonstração: admin@atelieverde.local (Leandro) / cliente@atelieverde.local (Rafael).
Senha pública da demonstração: AtelieVerde@2026.

O Rafinha usa uma conta ChatGPT autorizada pelo administrador desta instalação.
Entre em Administrador > Configurações > Inteligência Artificial > Continuar com ChatGPT.
Sem login, o catálogo continua disponível; nenhuma conta do desenvolvedor é utilizada.
O cofre do executável fica em RafinhaPublic, separado da conexão de desenvolvimento.
Ollama, Tavily e APIs pagas não são usados pelo fluxo de conversa desta versão.
Nenhuma credencial do desenvolvedor acompanha o pacote.

Esta é uma demonstração local; não a exponha como um serviço público usando as contas demonstrativas.
O executável não possui assinatura digital; o Windows pode solicitar confirmação de origem.
'@ | Set-Content -LiteralPath (Join-Path $appFolder 'LEIA-ME.txt') -Encoding utf8
    & $pythonPath scripts\verificar_release.py $appFolder --seal
    if ($LASTEXITCODE -ne 0) { throw 'Verificação de segurança rejeitou o artefato. Não distribua esta saída.' }
    if (-not $SkipSmoke) {
        & $pythonPath scripts\testar_exe_seguro.py $appFolder
        if ($LASTEXITCODE -ne 0) { throw 'O teste do executável falhou. Não distribua esta saída.' }
    }
    & $pythonPath scripts\verificar_release.py $appFolder
    if ($LASTEXITCODE -ne 0) { throw 'Os arquivos do pacote mudaram após a verificação.' }
    $zipPath = Join-Path $releaseRoot 'AtelieVerde-Windows.zip'
    Compress-Archive -LiteralPath $appFolder -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Executável seguro: $(Join-Path $appFolder 'AtelieVerde.exe')"
    Write-Host "Distribuição: $zipPath"
} finally { Pop-Location }
