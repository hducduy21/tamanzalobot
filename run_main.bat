@echo off
:loop
echo Starting script...
cd /d C:\Users\Administrator\Desktop\botpython - Copy\botpython - Copy\botpython - Copy
start /B python main.py
timeout /t 1800 /nobreak
taskkill /f /im python.exe
echo Script stopped. Restarting...
timeout /t 5 /nobreak
goto loop