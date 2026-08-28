@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Patent Kit Uninstaller
set "HOME_DIR=%LOCALAPPDATA%\Programs\PatentKit"
set "VENVPY=%HOME_DIR%\venv\Scripts\python.exe"

if not exist "%VENVPY%" (
  echo.
  echo   Not installed. 설치돼 있지 않습니다.
  echo.
  pause
  exit /b 0
)

"%VENVPY%" -m patentkit uninstall
echo.
echo   Removing program files...
cd /d "%LOCALAPPDATA%"
rmdir /s /q "%HOME_DIR%" 2>nul
if exist "%HOME_DIR%" (
  timeout /t 2 /nobreak >nul
  rmdir /s /q "%HOME_DIR%" 2>nul
)
if exist "%HOME_DIR%" (
  echo   일부 파일이 남았습니다. 창을 모두 닫고 다시 실행해 주세요.
) else (
  echo   Done. 제거를 마쳤습니다.
)
echo.
pause
