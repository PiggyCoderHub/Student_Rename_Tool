# -*- coding: utf-8 -*-
"""中文启动器：把启动错误写入 run_error.log，避免窗口一闪而过。"""
from __future__ import annotations

import os
import sys
import subprocess
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_PATH = BASE_DIR / "run_error.log"
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def write_log(title: str, detail: str) -> None:
    LOG_PATH.write_text(f"{title}\n\n{detail}\n", encoding="utf-8-sig", errors="replace")


def show_error(title: str, message: str) -> None:
    write_log(title, message)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message + f"\n\n详细日志位置：{LOG_PATH}")
        root.destroy()
    except Exception:
        print(title)
        print(message)
        print(f"详细日志位置：{LOG_PATH}")


def ensure_dependencies() -> bool:
    missing = []
    checks = [("openpyxl", "openpyxl"), ("docx", "python-docx"), ("xlrd", "xlrd")]
    for module_name, package_name in checks:
        try:
            __import__(module_name)
        except Exception:
            missing.append(package_name)
    if not missing:
        return True

    print("缺少依赖：" + ", ".join(missing))
    print("正在尝试根据 requirements.txt 自动安装依赖……")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(BASE_DIR / "requirements.txt")]
        subprocess.check_call(cmd)
    except Exception:
        detail = traceback.format_exc()
        show_error(
            "依赖安装失败",
            "程序需要的 Python 依赖没有安装，自动安装也失败了。\n"
            "请先双击“安装依赖.bat”，再双击“启动程序.bat”。\n"
            "如果仍然失败，请把 run_error.log 发给我。\n\n" + detail,
        )
        return False

    for module_name, package_name in checks:
        try:
            __import__(module_name)
        except Exception:
            show_error("依赖仍然缺失", f"依赖包仍然无法使用：{package_name}")
            return False
    return True


def main() -> int:
    try:
        if not ensure_dependencies():
            return 1
        from gui_app import App
        app = App()
        app.run()
        return 0
    except Exception:
        detail = traceback.format_exc()
        show_error("程序启动失败", detail)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
