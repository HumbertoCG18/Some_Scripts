# Instalador da Biblioteca Astral (sem dependências, sem admin).
# Copia o .exe para a pasta do usuário e cria atalhos (Área de Trabalho + Menu Iniciar).
# Parâmetros existem só para teste; o uso normal é sem argumentos.
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\Biblioteca Astral"),
    [string]$DesktopDir = ([Environment]::GetFolderPath("Desktop")),
    [string]$StartMenuDir = (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"),
    [switch]$NoRegistry
)
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot

$exeName = "Biblioteca Astral.exe"
$srcExe = Join-Path $src $exeName
if (-not (Test-Path $srcExe)) {
    Write-Host "ERRO: '$exeName' não encontrado ao lado deste script." -ForegroundColor Red
    exit 1
}

Write-Host "Instalando em: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $srcExe (Join-Path $InstallDir $exeName) -Force
$srcIco = Join-Path $src "book.ico"
if (Test-Path $srcIco) { Copy-Item $srcIco (Join-Path $InstallDir "book.ico") -Force }

$exe = Join-Path $InstallDir $exeName
$ico = Join-Path $InstallDir "book.ico"
if (-not (Test-Path $ico)) { $ico = $exe }  # usa o ícone embutido no exe

function New-Shortcut($path) {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath = $exe
    $lnk.WorkingDirectory = $InstallDir
    $lnk.IconLocation = $ico
    $lnk.Description = "Downloader da Biblioteca Astral"
    $lnk.Save()
}

New-Item -ItemType Directory -Force -Path $DesktopDir | Out-Null
New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
New-Shortcut (Join-Path $DesktopDir "Biblioteca Astral.lnk")
New-Shortcut (Join-Path $StartMenuDir "Biblioteca Astral.lnk")

if (-not $NoRegistry) {
    # Aparece em "Aplicativos instalados" / "Adicionar ou remover programas".
    $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\BibliotecaAstral"
    New-Item -Path $key -Force | Out-Null
    Set-ItemProperty $key DisplayName "Biblioteca Astral"
    Set-ItemProperty $key DisplayIcon $ico
    Set-ItemProperty $key DisplayVersion "1.0"
    Set-ItemProperty $key Publisher "Biblioteca Astral"
    Set-ItemProperty $key InstallLocation $InstallDir
    Set-ItemProperty $key UninstallString "powershell -NoProfile -ExecutionPolicy Bypass -File `"$InstallDir\uninstall.ps1`""
    Copy-Item (Join-Path $src "uninstall.ps1") (Join-Path $InstallDir "uninstall.ps1") -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Instalado! Atalho criado na Área de Trabalho." -ForegroundColor Green
Write-Host "Os livros serão salvos em: Documentos\Biblioteca Astral"
