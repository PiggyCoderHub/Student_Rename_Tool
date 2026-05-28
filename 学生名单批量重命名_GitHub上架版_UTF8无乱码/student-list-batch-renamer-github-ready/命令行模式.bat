@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 命令行模式 - 学生名单批量重命名工具
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

python main.py
pause
endlocal
