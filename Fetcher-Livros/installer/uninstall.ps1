# Desinstalador da Biblioteca Astral. NÃO apaga os livros baixados (Documentos\Biblioteca Astral).
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Programs\Biblioteca Astral"),
    [string]$DesktopDir = ([Environment]::GetFolderPath("Desktop")),
    [string]$StartMenuDir = (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs")
)
$ErrorActionPreference = "SilentlyContinue"

Remove-Item (Join-Path $DesktopDir "Biblioteca Astral.lnk") -Force
Remove-Item (Join-Path $StartMenuDir "Biblioteca Astral.lnk") -Force
Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\BibliotecaAstral" -Recurse -Force

# Remove a pasta de instalação (o exe pode estar em uso se aberto pelo próprio uninstall;
# por isso agenda remoção caso falhe).
try {
    Remove-Item $InstallDir -Recurse -Force -ErrorAction Stop
} catch {
    Start-Process cmd -ArgumentList "/c timeout /t 2 >nul & rmdir /s /q `"$InstallDir`"" -WindowStyle Hidden
}

Write-Host "Biblioteca Astral removida. (Seus livros em Documentos\Biblioteca Astral foram mantidos.)" -ForegroundColor Green
