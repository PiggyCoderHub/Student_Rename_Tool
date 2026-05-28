# GitHub 上架步骤

## 方法一：网页上传

1. 登录 GitHub。
2. 新建仓库，例如：`student-list-batch-renamer`。
3. 不要勾选自动生成 README，因为本项目已经有 `README.md`。
4. 把本项目根目录下的全部文件上传到仓库。
5. 提交后检查首页 README 是否正常显示中文。
6. 打开 Actions，确认自动检查通过。

## 方法二：命令行上传

在本项目根目录打开终端：

```bash
git init
git add .
git commit -m "Initial release: student list batch renamer"
git branch -M main
git remote add origin https://github.com/你的用户名/student-list-batch-renamer.git
git push -u origin main
```

## 发布 Release

1. 进入 GitHub 仓库。
2. 点击 Releases。
3. 点击 Draft a new release。
4. Tag 填写：`v1.0.0`。
5. Title 填写：`学生名单批量重命名工具 v1.0.0`。
6. Release notes 可以参考 `CHANGELOG.md`。
7. 上传打包好的 ZIP 文件。
8. 点击 Publish release。

## 上架后检查清单

- README 首页中文正常。
- `docs/` 文档中文正常。
- `启动程序.bat` 内容中文正常。
- Actions 检查通过。
- 仓库中没有 `students.db`。
- 仓库中没有 `__pycache__`。
- 仓库中没有运行日志。
