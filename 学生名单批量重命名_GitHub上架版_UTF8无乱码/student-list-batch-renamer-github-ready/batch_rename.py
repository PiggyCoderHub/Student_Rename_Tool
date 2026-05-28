# -*- coding: utf-8 -*-
"""
文件夹批量重命名工具 - 主程序
功能：按规则批量重命名文件夹内的文件
作者：AI Assistant
"""

import os
import sys
import shutil
from pathlib import Path
from config import RENAME_RULES, CONFLICT_STRATEGY, LOG_LEVEL


class BatchRenamer:
    """批量重命名处理器"""

    def __init__(self, folder_path: str, rules: dict):
        self.folder_path = Path(folder_path)
        self.rules = rules
        self.stats = {'success': 0, 'skipped': 0, 'errors': 0}
        self.logs = []

    def _log(self, level: str, message: str):
        """日志记录"""
        if hasattr(LOG_LEVEL, level):
            return
        self.logs.append(f"[{level}] {message}")
        print(f"[{level}] {message}")

    def _apply_rules(self, original_name: str, index: int) -> str:
        """应用重命名规则"""
        # 获取文件扩展名
        name = Path(original_name).stem
        ext = Path(original_name).suffix if self.rules.get('keep_extension', True) else ''

        # 应用字符替换
        for old, new in self.rules.get('replace_chars', {}).items():
            name = name.replace(old, new)

        # 构建新名称
        number = str(index).zfill(self.rules.get('number_width', 3))
        prefix = self.rules.get('prefix', '')
        suffix = self.rules.get('suffix', '')

        new_name = f"{prefix}{number}{suffix}{ext}"
        return new_name

    def _resolve_conflict(self, new_path: Path) -> Path:
        """处理文件名冲突"""
        if not new_path.exists():
            return new_path

        strategy = CONFLICT_STRATEGY

        if strategy == 'skip':
            self._log('INFO', f"跳过已存在的文件: {new_path.name}")
            return None

        elif strategy == 'overwrite':
            self._log('WARNING', f"覆盖已存在文件: {new_path.name}")
            return new_path

        else:  # add_suffix (默认)
            stem = new_path.stem
            ext = new_path.suffix
            counter = 1
            while new_path.exists():
                new_path = new_path.parent / f"{stem}_{counter}{ext}"
                counter += 1
            return new_path

    def _rename_file(self, old_path: Path, new_name: str) -> bool:
        """重名单个文件"""
        try:
            new_path = self.folder_path / new_name
            new_path = self._resolve_conflict(new_path)

            if new_path is None:
                self.stats['skipped'] += 1
                return False

            shutil.move(str(old_path), str(new_path))
            self._log('INFO', f"[成功] {old_path.name} -> {new_path.name}")
            self.stats['success'] += 1
            return True

        except PermissionError:
            self._log('ERROR', f"权限不足，无法重命名: {old_path.name}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            self._log('ERROR', f"重命名失败 [{old_path.name}]: {str(e)}")
            self.stats['errors'] += 1
            return False

    def run(self) -> dict:
        """执行批量重命名"""
        # 验证文件夹
        if not self.folder_path.exists():
            raise FileNotFoundError(f"目标文件夹不存在: {self.folder_path}")

        if not self.folder_path.is_dir():
            raise NotADirectoryError(f"路径不是文件夹: {self.folder_path}")

        # 获取文件列表
        files = [f for f in self.folder_path.iterdir() if f.is_file()]

        if not files:
            print("[提示] 文件夹中没有文件")
            return self.stats

        print(f"\n目标文件夹: {self.folder_path}")
        print(f"找到 {len(files)} 个文件，开始重命名...\n")

        # 按文件名排序以保证顺序一致
        files.sort(key=lambda x: x.name)

        # 逐个重命名
        index = self.rules.get('start_number', 1)
        for file_path in files:
            new_name = self._apply_rules(file_path.name, index)
            if new_name != file_path.name:
                self._rename_file(file_path, new_name)
            else:
                self._log('INFO', f"跳过无变化文件: {file_path.name}")
                self.stats['skipped'] += 1
            index += 1

        # 输出统计
        print(f"\n{'='*40}")
        print(f"[成功] 重命名成功: {self.stats['success']}")
        print(f"[跳过] 跳过/无变化: {self.stats['skipped']}")
        print(f"[失败] 处理失败: {self.stats['errors']}")
        print(f"{'='*40}\n")

        return self.stats


def get_user_input() -> tuple:
    """获取用户输入"""
    print("=" * 40)
    print("     文件夹批量重命名工具")
    print("=" * 40)

    # 获取文件夹路径
    while True:
        folder = input("\n请输入目标文件夹路径: ").strip().strip('"')
        if folder.lower() == 'q':
            print("已退出")
            sys.exit(0)

        if os.path.isdir(folder):
            break
        print(f"[失败] 路径不存在或不是文件夹，请重新输入（或输入 q 退出）")

    # 确认使用默认配置
    use_default = input("是否使用默认配置？(Y/n): ").strip().lower()

    return folder, (use_default != 'n')


def main():
    """主入口"""
    try:
        folder, use_default = get_user_input()

        if use_default:
            rules = RENAME_RULES
            print("[成功] 使用默认配置")
        else:
            # 自定义配置（简化版）
            rules = {
                'prefix': input("前缀（留空直接回车）: "),
                'suffix': input("后缀（留空直接回车）: "),
                'start_number': int(input("起始序号（默认1）: ") or "1"),
                'number_width': int(input("序号位数（默认3）: ") or "3"),
                'replace_chars': {' ': '_'},
                'keep_extension': True,
            }

        # 执行重命名
        renamer = BatchRenamer(folder, rules)
        renamer.run()

        # 继续或退出
        again = input("是否继续处理其他文件夹？(y/N): ").strip().lower()
        if again == 'y':
            main()
        else:
            print("感谢使用！")

    except KeyboardInterrupt:
        print("\n\n[提示] 已取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n[失败] 程序异常: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
