@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Install Dependencies
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3.8+ and enable Add Python to PATH.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Dependencies installed. Run START_HERE.bat or 启动程序.bat.
pause
endlocal
