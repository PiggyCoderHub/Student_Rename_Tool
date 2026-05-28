@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Debug Start - Student List Rename Tool
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
python start_gui.py 1>run_output.log 2>run_error.log
pause
endlocal
