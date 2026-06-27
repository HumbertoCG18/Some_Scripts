@echo off
chcp 65001>nul
title Instalar Biblioteca Astral
echo Instalando a Biblioteca Astral...
echo.
set "BA_SELF=%~f0"
set "BA_ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[IO.File]::ReadAllText($env:BA_SELF,[Text.Encoding]::UTF8); $m='#PS'+'CODE'; $i=$b.IndexOf($m); iex $b.Substring($i+$m.Length)"
echo.
pause
exit /b
#PSCODE
$ErrorActionPreference = 'Stop'
$Root = $env:BA_ROOT
$exeName = 'Biblioteca Astral.exe'

# Procura o exe ao lado do instalador (ou em dist\, caso rode do repositório).
$srcExe = Join-Path $Root $exeName
if (-not (Test-Path $srcExe)) {
    $alt = Join-Path $Root 'dist\Biblioteca Astral.exe'
    if (Test-Path $alt) { $srcExe = $alt }
}
if (-not (Test-Path $srcExe)) {
    Write-Host "ERRO: '$exeName' não está nesta pasta." -ForegroundColor Red
    Write-Host "Deixe o Instalar.bat na mesma pasta que o '$exeName'." -ForegroundColor Yellow
    exit 1
}

$dest = Join-Path $env:LOCALAPPDATA 'Programs\Biblioteca Astral'
Write-Host "Instalando em: $dest"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item $srcExe (Join-Path $dest $exeName) -Force
$exe = Join-Path $dest $exeName

# Atalhos (Área de Trabalho + Menu Iniciar) — ícone vem do próprio exe.
$ws = New-Object -ComObject WScript.Shell
function MkLnk($p) {
    $l = $ws.CreateShortcut($p)
    $l.TargetPath = $exe
    $l.WorkingDirectory = $dest
    $l.IconLocation = "$exe,0"
    $l.Description = 'Downloader da Biblioteca Astral'
    $l.Save()
}
$desk = [Environment]::GetFolderPath('Desktop')
$sm = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
MkLnk (Join-Path $desk 'Biblioteca Astral.lnk')
MkLnk (Join-Path $sm 'Biblioteca Astral.lnk')

# Registro: aparece em "Adicionar ou remover programas".
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\BibliotecaAstral'
New-Item -Path $key -Force | Out-Null
Set-ItemProperty $key DisplayName 'Biblioteca Astral'
Set-ItemProperty $key DisplayIcon "$exe,0"
Set-ItemProperty $key DisplayVersion '1.0'
Set-ItemProperty $key Publisher 'Biblioteca Astral'
Set-ItemProperty $key InstallLocation $dest
$q = [char]34
$u = "Remove-Item '$dest' -Recurse -Force -EA SilentlyContinue; " +
     "Remove-Item '$desk\Biblioteca Astral.lnk' -Force -EA SilentlyContinue; " +
     "Remove-Item '$sm\Biblioteca Astral.lnk' -Force -EA SilentlyContinue; " +
     "Remove-Item '$key' -Recurse -Force -EA SilentlyContinue"
Set-ItemProperty $key UninstallString ("powershell -NoProfile -ExecutionPolicy Bypass -Command $q$u$q")

Write-Host ''
Write-Host 'Instalado! Atalho "Biblioteca Astral" criado na Área de Trabalho.' -ForegroundColor Green
Write-Host 'Os livros serão salvos em: Documentos\Biblioteca Astral'
