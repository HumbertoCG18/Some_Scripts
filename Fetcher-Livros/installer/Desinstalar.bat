@echo off
chcp 65001 >nul
title Desinstalar Biblioteca Astral
echo Removendo a Biblioteca Astral...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
echo.
pause
