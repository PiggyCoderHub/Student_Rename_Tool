# 贡献说明

欢迎提交 Issue 或 Pull Request。为避免中文乱码和运行环境问题，提交代码前请遵守以下规则。

## 编码要求

- Python、Markdown 使用 UTF-8。
- CSV 模板建议使用 UTF-8 BOM。
- BAT 文件建议使用 UTF-8 BOM，并在开头保留 `chcp 65001 >nul`。
- 不要把中文文件保存为 ANSI/GBK 后再提交到 GitHub。

## 提交前检查

建议运行：

```bash
python scripts/check_encoding.py
python -m compileall .
```

## 不要提交的文件

以下文件不应提交：

- `data/students.db`
- `run_error.log`
- `run_output.log`
- `__pycache__/`
- `.pyc` 文件
- 本地压缩包

这些内容已写入 `.gitignore`。

## Issue 建议

反馈问题时请尽量提供：

- Windows 版本
- Python 版本
- 是否运行过 `安装依赖.bat`
- 错误截图
- `run_error.log` 内容
- 使用的学生名单格式
