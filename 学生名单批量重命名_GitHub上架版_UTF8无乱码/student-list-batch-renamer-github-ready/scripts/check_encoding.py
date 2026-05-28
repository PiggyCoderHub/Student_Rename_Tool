# -*- coding: utf-8 -*-
"""检查仓库文本文件是否可按 UTF-8 解码。"""
from __future__ import annotations

from pathlib import Path
import sys

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".csv", ".bat", ".cmd", ".yml", ".yaml", ".toml", ".gitignore", ".gitattributes"
}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "env", "build", "dist"}
SKIP_SUFFIXES = {".xlsx", ".xlsm", ".xls", ".db", ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".rar", ".7z"}


def should_check(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if path.name in {".gitignore", ".gitattributes"}:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failed = []
    for path in root.rglob("*"):
        if not path.is_file() or not should_check(path):
            continue
        try:
            path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            failed.append((path.relative_to(root), str(exc)))
    if failed:
        print("以下文件不是 UTF-8，可能导致 GitHub 中文乱码：")
        for file, err in failed:
            print(f"- {file}: {err}")
        return 1
    print("编码检查通过：文本文件均可按 UTF-8 解码。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
