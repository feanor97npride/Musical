@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Falta o ambiente .venv. Veja o guia & pause & exit /b 1)
".venv\Scripts\python.exe" -m web.launcher
pause
