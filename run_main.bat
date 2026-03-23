@echo off
:loop
echo Starting script...
cd /d "%~dp0"
python main.py
echo Script exited with code %ERRORLEVEL%
echo Restarting in 5 seconds...
timeout /t 5 /nobreak
goto loop