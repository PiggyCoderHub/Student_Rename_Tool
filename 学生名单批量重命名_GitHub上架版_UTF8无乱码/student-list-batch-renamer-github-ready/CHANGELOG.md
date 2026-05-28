# 更新日志

## GitHub 上架版

基于“中文版 v6 无乱码版”整理。

### 新增

- 新增 `README.md`，用于 GitHub 首页展示。
- 新增 `.gitignore`，避免上传本地数据库、日志和缓存文件。
- 新增 `.gitattributes` 和 `.editorconfig`，统一换行与编码策略。
- 新增 `LICENSE`、`CONTRIBUTING.md`、`docs/使用手册.md`。
- 新增 `docs/编码与中文乱码处理说明.md`。
- 新增 `docs/GitHub上架步骤.md`。
- 新增 GitHub Issue 模板。
- 新增 GitHub Actions 编码检查与 Python 语法检查。

### 修复

- 清理 `__pycache__`、`.pyc`、本地 `students.db`。
- 中文 BAT 脚本改为 UTF-8 BOM，并设置 `chcp 65001`。
- CSV 模板使用 UTF-8 BOM，降低 Excel 中文乱码概率。
- ZIP 文件名使用 UTF-8 标志，避免中文文件名解压乱码。

### 保留

- 学生名单导入预览勾选。
- 全选、全不选、反选。
- 同学号更新。
- 自动识别学号、姓名、班级列。
- 重名文件自动追加序号。
