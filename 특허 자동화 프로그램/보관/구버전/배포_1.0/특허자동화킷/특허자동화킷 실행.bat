@echo off
rem ASCII only. Korean text here breaks cmd parsing after chcp 65001.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

where python >nul 2>nul
if errorlevel 1 (py "%~dp0gui.py") else (python "%~dp0gui.py")

echo.
echo [ended] If Python is missing, install it from python.org
pause
