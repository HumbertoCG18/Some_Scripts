@echo off
chcp 65001>nul
title Instalar Biblioteca Astral
echo ============================================
echo   Instalador da Biblioteca Astral
echo   (instala Python e dependencias se faltar,
echo    compila o programa e cria o atalho)
echo ============================================
echo.
set "BA_SELF=%~f0"
set "BA_ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b=[IO.File]::ReadAllText($env:BA_SELF,[Text.Encoding]::UTF8); $m='#PS'+'CODE'; $i=$b.IndexOf($m); iex $b.Substring($i+$m.Length)"
echo.
pause
exit /b
#PSCODE
$ErrorActionPreference = 'Stop'
$Root = $env:BA_ROOT.TrimEnd('\')

function Find-Python {
    $g = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($g) { try { $v = & $g.Source --version 2>&1; if ("$v" -match 'Python 3') { return $g.Source } } catch {} }
    $g = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($g) { try { $p = & $g.Source -3 -c "import sys;print(sys.executable)" 2>&1; if ($p -and (Test-Path $p)) { return $p } } catch {} }
    $c = @()
    $c += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue
    $c += Get-ChildItem "$env:ProgramFiles\Python3*\python.exe" -ErrorAction SilentlyContinue
    $c += Get-ChildItem "$env:ProgramFiles(x86)\Python3*\python.exe" -ErrorAction SilentlyContinue
    if ($c) { return $c[0].FullName }
    return $null
}

# 1) Garante Python -------------------------------------------------------
$py = Find-Python
if (-not $py) {
    Write-Host "Python não encontrado. Instalando via winget (pode demorar)..." -ForegroundColor Yellow
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        Write-Host "ERRO: winget indisponível. Instale o Python manualmente em python.org e rode de novo." -ForegroundColor Red
        exit 1
    }
    winget install -e --id Python.Python.3.12 --scope user `
        --accept-package-agreements --accept-source-agreements --silent
    $py = Find-Python
    if (-not $py) {
        Write-Host "Python instalado, mas não localizado. Feche e abra este instalador de novo." -ForegroundColor Red
        exit 1
    }
}
$pydir = Split-Path $py
$env:PATH = "$pydir;$pydir\Scripts;$env:PATH"
Write-Host "Python: $py" -ForegroundColor Green

# 2) Dependências (projeto + compilador) ----------------------------------
Write-Host "Instalando dependências..." -ForegroundColor Cyan
& $py -m pip install --upgrade pip --quiet
& $py -m pip install --quiet pyinstaller
$req = Join-Path $Root 'requirements.txt'
if (Test-Path $req) { & $py -m pip install --quiet -r $req } else { & $py -m pip install --quiet requests }

# 3) Compila o .exe -------------------------------------------------------
Write-Host "Compilando o programa (PyInstaller)..." -ForegroundColor Cyan
& (Join-Path $Root 'scripts\build.ps1') -SkipIcon
$exeName = 'Biblioteca Astral.exe'
$srcExe = Join-Path $Root $exeName
if (-not (Test-Path $srcExe)) {
    Write-Host "ERRO: a compilação não gerou o '$exeName'." -ForegroundColor Red
    exit 1
}

# 4) Instala (copia + atalhos + registro) ---------------------------------
$dest = Join-Path $env:LOCALAPPDATA 'Programs\Biblioteca Astral'
Write-Host "Instalando em: $dest" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item $srcExe (Join-Path $dest $exeName) -Force
$exe = Join-Path $dest $exeName

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

# 5) Limpa intermediários da compilação -----------------------------------
Remove-Item (Join-Path $Root 'build') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Root 'dist') -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $srcExe -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Root '*.spec') -Force -ErrorAction SilentlyContinue

Write-Host ''
Write-Host 'Instalado! Atalho "Biblioteca Astral" criado na Área de Trabalho.' -ForegroundColor Green
Write-Host 'Os livros serão salvos em: Documentos\Biblioteca Astral'
