@echo off
rem ASCII only. Korean in this file breaks cmd parsing after chcp 65001.
rem Korean paths and options are resolved by run.py instead.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PATENTKIT_OPEN=1

where python >nul 2>nul
if errorlevel 1 (py run.py) else (python run.py)

echo.
pause
