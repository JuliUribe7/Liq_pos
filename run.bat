@echo off
cd /d "%~dp0"
venv\Scripts\python.exe login_gui.py
if errorlevel 1 pause
