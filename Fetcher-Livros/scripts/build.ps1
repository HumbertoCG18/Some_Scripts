# Reconstrói o executável e monta a pasta release/ pronta para distribuir.
# Requisitos (só para quem compila): python, pip install pyinstaller pillow requests
# Rode da raiz ou de qualquer lugar: .\scripts\build.ps1
param([switch]$SkipIcon)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent   # raiz do repo (scripts/..)
Set-Location $root

if (-not $SkipIcon) { python scripts\make_icon.py }

python -m PyInstaller --noconfirm --onefile --windowed `
    --icon assets\book.ico --name "Biblioteca Astral" `
    --paths src --add-data "assets\book.ico;." src\main.py

# Coloca o exe na raiz, ao lado de Instalar.bat / Desinstalar.bat (versionado).
Copy-Item ".\dist\Biblioteca Astral.exe" $root -Force

Write-Host ""
Write-Host "Pronto. Exe atualizado na raiz do repositório." -ForegroundColor Green
Write-Host "Distribua: 'Biblioteca Astral.exe' + 'Instalar.bat' + 'Desinstalar.bat'."
Write-Host "O usuário final dá dois cliques em 'Instalar.bat'."
