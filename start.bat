@echo off
chcp 65001 >nul 2>&1
cd /d %~dp0
set PYTHONPATH=%cd%\Dravion_backend
set GOOGLE_APPLICATION_CREDENTIALS=%cd%\gcloud-key.json
set PYTHONIOENCODING=utf-8
color 0B
title DRAVION v.9

echo.
echo   [38;5;244m──────────────────────────────────────────────────[0m
echo   [38;5;51m[1m  Initializing DRAVION v.9...[0m
echo   [38;5;244m──────────────────────────────────────────────────[0m
echo.

:: Start Ollama server in background (local brain)
start "DRAVION-OLLAMA" /min cmd /c "ollama serve 2>nul"
timeout /t 1 /nobreak >nul
echo   [38;5;244m├─[0m [38;5;48m[OK][0m [38;5;117mOllama server started[0m

:: Launch Core System
echo   [38;5;244m└─[0m [38;5;48m[OK][0m [38;5;117mLaunching Cortex...[0m
echo.

poetry run python Dravion_backend\main.py
pause
