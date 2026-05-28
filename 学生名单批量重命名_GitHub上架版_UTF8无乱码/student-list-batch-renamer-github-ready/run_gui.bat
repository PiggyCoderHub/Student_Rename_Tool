@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Student List Rename Tool
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
python start_gui.py
pause
endlocal
