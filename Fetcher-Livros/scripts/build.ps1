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

$rel = Join-Path $root "release"
Remove-Item $rel -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $rel | Out-Null
Copy-Item ".\dist\Biblioteca Astral.exe" $rel
Copy-Item ".\assets\book.ico" $rel
Copy-Item ".\installer\*" $rel -Force

Write-Host ""
Write-Host "Pronto. Distribua a pasta: $rel" -ForegroundColor Green
Write-Host "O usuário final dá dois cliques em 'Instalar.bat'."
