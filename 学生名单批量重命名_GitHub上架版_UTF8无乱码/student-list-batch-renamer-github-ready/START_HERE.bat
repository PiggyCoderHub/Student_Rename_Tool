@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Student List Rename Tool
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3.8+ and enable Add Python to PATH.
    pause
    exit /b 1
)

python start_gui.py
if errorlevel 1 (
    echo.
    echo Start failed. Please check run_error.log or run run_gui_debug.bat.
    pause
)
endlocal
