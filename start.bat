@echo off
cd /d "%~dp0"
start "AI Agents" cmd /k ".venv\Scripts\python.exe main.py"
start "Dashboard" cmd /k ".venv\Scripts\python.exe dashboard.py"
