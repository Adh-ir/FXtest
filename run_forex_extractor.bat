@echo off
cd /d "%~dp0"
echo Installing dependencies...
pip install -r code\requirements.txt
python code\main.py
pause
