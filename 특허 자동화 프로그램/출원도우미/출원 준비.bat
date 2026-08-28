@echo off
rem ASCII only. Korean text here breaks cmd parsing after chcp 65001.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8

where python >nul 2>nul
if errorlevel 1 (set PY=py) else (set PY=python)

%PY% -m patentkit --version >nul 2>nul
if errorlevel 1 %PY% -m pip install --quiet patentkit

%PY% "%~dp0출원도우미.py" 준비 . --열기

echo.
pause
