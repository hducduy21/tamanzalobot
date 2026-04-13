@echo off
title Zalo Bot - Keep Alive
cd /d "%~dp0"
chcp 65001 >nul
echo Starting Zalo Bot with Keep Alive...
echo.
echo Rules:
echo   - 06:00 - 00:00: restart if no message for 60 minutes
echo   - 00:00 - 05:00: restart if no message for 180 minutes
echo   - 06:00 daily: auto restart every morning
echo.
python keep_alive.py
pause