@echo off
:: Tat QuickEdit Mode de CMD khong bi dung khi click chuot
reg add "HKEY_CURRENT_USER\Console" /v QuickEdit /t REG_DWORD /d 0 /f >nul 2>&1

:loop
echo ============================================
echo  Starting bot... (Press Ctrl+C to stop)
echo  QuickEdit Mode: DISABLED
echo ============================================
cd /d "%~dp0"
python main.py
echo Script exited with code %ERRORLEVEL%
echo Restarting in 5 seconds...
timeout /t 5
goto loop
