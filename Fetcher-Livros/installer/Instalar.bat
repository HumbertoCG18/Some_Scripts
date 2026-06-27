@echo off
chcp 65001 >nul
title Instalar Biblioteca Astral
echo Instalando a Biblioteca Astral...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
