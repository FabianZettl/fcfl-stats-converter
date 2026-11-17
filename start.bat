@echo off
cd /d "%~dp0"
py flconv\server.py %*
if errorlevel 1 python flconv\server.py %*
