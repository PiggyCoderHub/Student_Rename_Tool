@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 调试启动 - 学生名单批量重命名工具
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo 正在调试启动，错误信息会写入 run_error.log。
echo.
python start_gui.py 1>run_output.log 2>run_error.log

echo.
echo 调试结束。
echo 如果程序没有打开，请把 run_error.log 发给维护者。
pause
endlocal
