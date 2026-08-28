@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Patent Kit Installer
cd /d "%~dp0"

set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY call :FindPython
if not defined PY goto :AskInstall
goto :Run

:FindPython
for %%D in (Python313 Python312 Python311 Python310) do (
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\%%D\python.exe" set PY="%LOCALAPPDATA%\Programs\Python\%%D\python.exe"
  if not defined PY if exist "%ProgramFiles%\%%D\python.exe" set PY="%ProgramFiles%\%%D\python.exe"
)
if not defined PY for /f "delims=" %%V in ('python -c "import sys;print(sys.version_info.major)" 2^>nul') do if "%%V"=="3" set "PY=python"
exit /b 0

:AskInstall
echo.
echo   Python is required and was not found on this PC.
echo   파이썬이 필요한데 이 컴퓨터에 없습니다.
echo.
echo   Install it now with winget? (no admin rights needed)
echo   지금 설치할까요? (관리자 권한 없이 사용자 계정에만 설치됩니다)
echo.
set "ANS="
set /p "ANS=  Y = install / N = quit  >  "
if /I not "%ANS%"=="Y" goto :Bye
echo.
echo   Installing Python. This takes a few minutes.
winget install --id Python.Python.3.12 --source winget --scope user --silent --accept-package-agreements --accept-source-agreements
call :FindPython
if not defined PY (
  echo.
  echo   Python is still not found. Install it manually from
  echo   https://www.python.org/downloads/  then run this file again.
  echo   파이썬을 직접 설치한 뒤 이 파일을 다시 실행해 주세요.
  echo.
  pause
  exit /b 2
)

:Run
%PY% "%~dp0bootstrap.py"
echo.
pause
exit /b 0

:Bye
echo.
echo   Cancelled. 설치를 그만둡니다.
echo.
pause
exit /b 1
