@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 学生名单批量重命名工具
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if errorlevel 1 (
    echo 未检测到 Python。
    echo 请先安装 Python 3.8 或以上版本，并勾选 Add Python to PATH。
    pause
    exit /b 1
)

python start_gui.py
if errorlevel 1 (
    echo.
    echo 程序启动失败，请查看 run_error.log。
    echo 如果日志文件不存在，请双击 调试启动.bat。
    pause
)
endlocal
