@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 安装运行依赖
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if errorlevel 1 (
    echo 未检测到 Python。
    echo 请先安装 Python 3.8 或以上版本，并勾选 Add Python to PATH。
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo 依赖安装完成。如果没有红色错误信息，请双击 启动程序.bat。
pause
endlocal
