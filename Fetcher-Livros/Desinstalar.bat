@echo off
chcp 65001>nul
title Desinstalar Biblioteca Astral
echo Removendo a Biblioteca Astral...
echo.
set "BA_SELF=%~f0"
set "BA_ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[IO.File]::ReadAllText($env:BA_SELF,[Text.Encoding]::UTF8); $m='#PS'+'CODE'; $i=$b.IndexOf($m); iex $b.Substring($i+$m.Length)"
echo.
pause
exit /b
#PSCODE
$ErrorActionPreference = 'SilentlyContinue'
$Root = $env:BA_ROOT.TrimEnd('\')
$dest = Join-Path $env:LOCALAPPDATA 'Programs\Biblioteca Astral'
$desk = [Environment]::GetFolderPath('Desktop')
$sm = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'

# Instalação + atalhos + registro
Remove-Item (Join-Path $desk 'Biblioteca Astral.lnk') -Force
Remove-Item (Join-Path $sm 'Biblioteca Astral.lnk') -Force
Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\BibliotecaAstral' -Recurse -Force
Remove-Item $dest -Recurse -Force

# Artefatos de compilação que possam ter sobrado na pasta do projeto
Remove-Item (Join-Path $Root 'Biblioteca Astral.exe') -Force
Remove-Item (Join-Path $Root 'build') -Recurse -Force
Remove-Item (Join-Path $Root 'dist') -Recurse -Force
Remove-Item (Join-Path $Root '*.spec') -Force

Write-Host 'Biblioteca Astral removida.' -ForegroundColor Green
Write-Host 'Seus livros em Documentos\Biblioteca Astral foram mantidos.'
