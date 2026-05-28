# -*- coding: utf-8 -*-
"""
实验报告收缴管理系统 - 主程序 v2 (Windows兼容版)
功能：批量重命名学生实验报告文件
"""

import os
import sys
import shutil
import io
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Set

# Windows编码兼容
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from student_db import StudentDB
from docx_reader import BatchDocxReader, DocxReader
from excel_importer import SmartExcelImporter


# ===== 中文数字转换 =====
CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
CN_DIGIT = ['', '十', '百', '千']

def int_to_chinese(num: int) -> str:
    """整数转中文数字"""
    if num <= 0:
        return '零'
    if num <= 10:
        return CN_NUM[num]
    if num < 20:
        return '十' + (CN_NUM[num - 10] if num > 10 else '')
    if num < 100:
        tens = num // 10
        ones = num % 10
        return CN_NUM[tens] + '十' + (CN_NUM[ones] if ones else '')
    return str(num)


class ExperimentReportRenamer:
    """实验报告重命名器 - 增强版"""

    def __init__(self, db: StudentDB):
        self.db = db
        self.stats = {'success': 0, 'skipped': 0, 'errors': 0, 'renamed': []}

    def _generate_name(self, student_id: str, name: str, index: int, extension: str) -> str:
        """生成新文件名
        格式: 学号姓名实验报告x
        示例: 202509160101曹柯实验报告一
        """
        name_part = name if name else "未知"
        num_part = int_to_chinese(index)
        return f"{student_id}{name_part}实验报告{num_part}{extension}"

    def rename_single_file(self, filepath: str, target_info: dict = None, index: int = 1) -> Tuple[bool, str]:
        """重名单个文件"""
        try:
            old_path = Path(filepath)
            if not old_path.exists():
                return False, "文件不存在"

            extension = old_path.suffix

            student_id = "未知"
            name = "未知"

            if target_info:
                if target_info.get('student_id'):
                    student_id = target_info['student_id']
                if target_info.get('name'):
                    name = target_info['name']

            new_name = self._generate_name(student_id, name, index, extension)
            new_path = old_path.parent / new_name

            # 处理冲突
            if new_path.exists() and new_path != old_path:
                base = new_path.stem
                counter = 1
                while new_path.exists():
                    new_name = f"{base}_{counter}{extension}"
                    new_path = old_path.parent / new_name
                    counter += 1

            # 执行重命名
            if new_path != old_path:
                shutil.move(str(old_path), str(new_path))
                self.stats['success'] += 1
                self.stats['renamed'].append((old_path.name, new_path.name))
                return True, f"{old_path.name} -> {new_path.name}"
            else:
                self.stats['skipped'] += 1
                return True, "文件名相同，跳过"

        except Exception as e:
            self.stats['errors'] += 1
            return False, f"错误: {str(e)}"

    def batch_rename(self, folder_path: str, class_name: str = None) -> dict:
        """批量处理文件夹中的文件"""
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"文件夹不存在: {folder_path}")

        files = list(folder.glob("*.docx")) + list(folder.glob("*.doc"))
        if not files:
            return {'message': '文件夹中没有docx文件'}

        print(f"\n>>> 找到 {len(files)} 个文件\n")

        # 获取该班级的学生信息
        students = self.db.get_students_by_class(class_name) if class_name else []
        student_map = {s['student_id']: s for s in students}
        name_map = {s['name']: s for s in students}

        # 提取每个文件的信息
        file_infos = []
        for f in files:
            reader = DocxReader(str(f))
            info = reader.extract_all_info()
            info['filepath'] = str(f)
            info['original_name'] = f.name

            # 尝试匹配数据库
            matched = None
            if info.get('student_id'):
                matched = student_map.get(info['student_id'])
            if not matched and info.get('name'):
                matched = name_map.get(info['name'])

            info['matched_student'] = matched
            file_infos.append(info)

        # 显示匹配结果
        matched_count = sum(1 for fi in file_infos if fi['matched_student'])
        print(f"[OK] 数据库匹配: {matched_count} 个")
        print(f"[--] 从文件内容提取: {len(file_infos) - matched_count} 个\n")

        # 显示未匹配文件
        unmatched = [fi for fi in file_infos if not fi['matched_student']]
        if unmatched:
            print("未匹配的文件:")
            for i, fi in enumerate(unmatched[:10], 1):
                print(f"  {i}. {fi['original_name']}")
                if fi.get('student_id'):
                    print(f"     学号: {fi['student_id']}")
                if fi.get('name'):
                    print(f"     姓名: {fi['name']}")
            if len(unmatched) > 10:
                print(f"  ... 还有 {len(unmatched) - 10} 个")

        # 开始重命名
        print("\n" + "=" * 50)
        print("开始重命名...")
        print("=" * 50 + "\n")

        renamed_index = 1
        for fi in file_infos:
            if fi['matched_student']:
                student = fi['matched_student']
                target_info = {
                    'student_id': student['student_id'],
                    'name': student['name']
                }
            else:
                target_info = {
                    'student_id': fi.get('student_id', '未知'),
                    'name': fi.get('name', '未知')
                }

            ok, msg = self.rename_single_file(fi['filepath'], target_info, renamed_index)
            if ok:
                print(f"[OK] {msg}")
                if "->" in msg:
                    renamed_index += 1
            else:
                print(f"[X] {fi['original_name']}: {msg}")

        # 统计结果
        print("\n" + "=" * 50)
        print(f"[OK] 重命名成功: {self.stats['success']}")
        print(f"[-] 跳过: {self.stats['skipped']}")
        print(f"[X] 失败: {self.stats['errors']}")
        print("=" * 50)

        return self.stats


class MenuSystem:
    """菜单系统 - 增强版"""

    def __init__(self):
        self.db = StudentDB()
        self.renamer = ExperimentReportRenamer(self.db)
        self.selected_students: Set[str] = set()  # 勾选的学生学号

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title: str):
        print("\n" + "=" * 55)
        print(f"  * {title}")
        print("=" * 55)

    def wait_enter(self):
        input("\n按回车继续...")

    # ===== 学生信息管理 =====

    def manage_students(self):
        """学生信息管理"""
        while True:
            self.clear_screen()
            self.print_header("学生信息管理")

            stats = self.db.get_stats()
            print(f"\n[STAT] 当前数据: {stats['total_classes']} 个班级, {stats['total_students']} 名学生")
            print(f"       未分配班级: {stats['no_class_students']} 名")

            print("\n  1. 查看所有班级")
            print("  2. 添加班级")
            print("  3. 删除班级")
            print("  4. 查看班级学生")
            print("  5. 添加学生（单个）")
            print("  6. 批量添加学生")
            print("  7. 修改学生信息")
            print("  8. 批量删除学生 [NEW]")
            print("  9. 批量分配班级 [NEW]")
            print("  10. 搜索学生")
            print("  11. 导出学生信息")
            print("  12. 查看未分配班级的学生")
            print("\n  0. 返回上级菜单")

            choice = input("\n请选择: ").strip()

            if choice == '1':
                self.view_classes()
            elif choice == '2':
                self.add_class()
            elif choice == '3':
                self.delete_class()
            elif choice == '4':
                self.view_class_students()
            elif choice == '5':
                self.add_student()
            elif choice == '6':
                self.batch_add_students()
            elif choice == '7':
                self.update_student()
            elif choice == '8':
                self.batch_delete_students()
            elif choice == '9':
                self.batch_assign_class()
            elif choice == '10':
                self.search_students()
            elif choice == '11':
                self.export_students()
            elif choice == '12':
                self.view_students_without_class()
            elif choice == '0':
                break

    def view_classes(self):
        self.clear_screen()
        self.print_header("班级列表")

        classes = self.db.get_all_classes()
        if not classes:
            print("\n暂无班级，请先添加班级")
        else:
            print(f"\n{'序号':<4} {'班级名称':<25} {'年级':<8} {'人数':<6}")
            print("-" * 50)
            for i, c in enumerate(classes, 1):
                print(f"{i:<4} {c['class_name']:<25} {c.get('grade', '-'):<8} {c['student_count']:<6}")

        self.wait_enter()

    def add_class(self):
        self.clear_screen()
        self.print_header("添加班级")

        class_name = input("班级名称: ").strip()
        if not class_name:
            print("班级名称不能为空")
            self.wait_enter()
            return

        grade = input("年级 (如2023): ").strip()
        major = input("专业: ").strip()

        ok, msg = self.db.add_class(class_name, grade, major)
        print(f"\n{'[OK] ' + msg if ok else '[X] ' + msg}")
        self.wait_enter()

    def delete_class(self):
        self.clear_screen()
        self.print_header("删除班级")

        classes = self.db.get_all_classes()
        if not classes:
            print("暂无班级")
            self.wait_enter()
            return

        print("\n班级列表:")
        for i, c in enumerate(classes, 1):
            print(f"  {i}. {c['class_name']} ({c['student_count']}人)")

        choice = input("\n请输入班级序号或名称: ").strip()
        class_name = None

        if choice.isdigit() and 1 <= int(choice) <= len(classes):
            class_name = classes[int(choice) - 1]['class_name']
        else:
            class_name = choice

        confirm = input(f"确认删除班级 '{class_name}' 及其所有学生？(y/N): ").strip().lower()
        if confirm == 'y':
            ok, msg = self.db.delete_class(class_name)
            print(f"\n{'[OK] ' + msg if ok else '[X] ' + msg}")

        self.wait_enter()

    def view_class_students(self):
        self.clear_screen()
        self.print_header("班级学生列表")

        classes = self.db.get_all_classes()
        if not classes:
            print("暂无班级")
            self.wait_enter()
            return

        print("\n班级列表:")
        for i, c in enumerate(classes, 1):
            print(f"  {i}. {c['class_name']}")

        choice = input("\n请选择班级: ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(classes):
            return

        class_name = classes[int(choice) - 1]['class_name']
        students = self.db.get_students_by_class(class_name)

        print(f"\n{class_name} - {len(students)} 名学生")
        print(f"\n{'学号':<15} {'姓名':<10} {'电话':<15}")
        print("-" * 50)
        for s in students:
            print(f"{s['student_id']:<15} {s['name']:<10} {s.get('phone', '-'):<15}")

        self.wait_enter()

    def add_student(self):
        self.clear_screen()
        self.print_header("添加学生（单个）")

        student_id = input("学号: ").strip()
        name = input("姓名: ").strip()

        if not student_id or not name:
            print("\n学号和姓名不能为空")
            self.wait_enter()
            return

        # 选择班级
        classes = self.db.get_all_classes()
        class_name = None
        if classes:
            print("\n班级列表:")
            for i, c in enumerate(classes, 1):
                print(f"  {i}. {c['class_name']}")
            choice = input("选择班级 (直接回车跳过): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(classes):
                class_name = classes[int(choice) - 1]['class_name']

        phone = input("电话: ").strip()
        email = input("邮箱: ").strip()

        ok, msg = self.db.add_student(student_id, name, class_name, phone, email)
        print(f"\n{'[OK] ' + msg if ok else '[X] ' + msg}")
        self.wait_enter()

    def batch_add_students(self):
        self.clear_screen()
        self.print_header("批量添加学生")

        print("\n选择导入方式:")
        print("  1. 从Excel文件导入 [推荐]")
        print("  2. 手动输入列表")
        print("  0. 返回")

        choice = input("\n请选择: ").strip()

        if choice == '1':
            self.import_from_excel()
        elif choice == '2':
            self.manual_batch_add()
        elif choice == '0':
            return

    def import_from_excel(self):
        self.clear_screen()
        self.print_header("从Excel导入学生")

        filepath = input("请输入Excel文件路径: ").strip().strip('"')
        if not os.path.exists(filepath):
            print("文件不存在")
            self.wait_enter()
            return

        # 选择班级
        classes = self.db.get_all_classes()
        class_name = None
        if classes:
            print("\n班级列表:")
            for i, c in enumerate(classes, 1):
                print(f"  {i}. {c['class_name']}")
            print("  0. 不指定班级（按表格中的班级分配）")
            choice = input("\n选择导入到的班级: ").strip()
            if choice.isdigit():
                if int(choice) >= 1 and int(choice) <= len(classes):
                    class_name = classes[int(choice) - 1]['class_name']

        # 导入
        importer = SmartExcelImporter(filepath)
        ok, msg = importer.load_file()
        if not ok:
            print(f"\n[X] {msg}")
            self.wait_enter()
            return

        importer._read_sheet_data()

        print(f"\n[OK] {msg}")
        print(importer.preview_data())

        col_info = importer.get_column_info()
        if col_info['detected_columns']:
            print(f"\n[INFO] 识别到的字段: {', '.join(col_info['detected_columns'].keys())}")

        valid, errors = importer.validate_data()
        if errors:
            print("\n[WARNING] 验证信息:")
            for e in errors[:5]:
                print(f"  - {e}")

        confirm = input("\n确认导入？(y/N): ").strip().lower()
        if confirm == 'y':
            success, failed, err_list = importer.import_to_db(self.db, class_name)
            print(f"\n导入完成: 成功 {success}, 失败 {failed}")
            if err_list:
                print("部分错误:")
                for e in err_list[:5]:
                    print(f"  - {e}")

        self.wait_enter()

    def manual_batch_add(self):
        self.clear_screen()
        self.print_header("手动批量添加学生")

        print("\n输入格式: 学号,姓名,电话,邮箱 (用逗号分隔)")
        print("每行一条，输入空行结束")
        print("示例: 202301010001,张三,13800000001,test@example.com\n")

        students = []
        while True:
            line = input().strip()
            if not line:
                break

            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                students.append({
                    'student_id': parts[0],
                    'name': parts[1],
                    'phone': parts[2] if len(parts) > 2 else None,
                    'email': parts[3] if len(parts) > 3 else None
                })
            else:
                print(f"格式错误: {line}")

        if not students:
            print("没有输入数据")
            self.wait_enter()
            return

        # 选择班级
        classes = self.db.get_all_classes()
        class_name = None
        if classes:
            print("\n班级列表:")
            for i, c in enumerate(classes, 1):
                print(f"  {i}. {c['class_name']}")
            choice = input("\n选择班级 (直接回车跳过): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(classes):
                class_name = classes[int(choice) - 1]['class_name']

        confirm = input(f"\n确认导入 {len(students)} 名学生？(y/N): ").strip().lower()
        if confirm == 'y':
            success, failed, errors = self.db.add_student_batch(students, class_name)
            print(f"\n导入完成: 成功 {success}, 失败 {failed}")
            if errors:
                for e in errors[:5]:
                    print(f"  - {e}")

        self.wait_enter()

    def update_student(self):
        self.clear_screen()
        self.print_header("修改学生信息")

        student_id = input("请输入要修改的学号: ").strip()
        student = self.db.get_student_by_id(student_id)

        if not student:
            print(f"\n[X] 学号 '{student_id}' 不存在")
            self.wait_enter()
            return

        print(f"\n当前信息:")
        print(f"  学号: {student['student_id']}")
        print(f"  姓名: {student['name']}")
        print(f"  班级: {student.get('class_name', '未分配')}")
        print(f"  电话: {student.get('phone', '-')}")
        print(f"  邮箱: {student.get('email', '-')}")
        print(f"  备注: {student.get('remark', '-')}")

        print("\n直接回车保持原值，输入新值修改:")

        name = input(f"姓名 [{student['name']}]: ").strip()
        phone = input(f"电话 [{student.get('phone', '-')}]: ").strip()
        email = input(f"邮箱 [{student.get('email', '-')}]: ").strip()
        remark = input(f"备注 [{student.get('remark', '-')}]: ").strip()

        # 班级选择
        classes = self.db.get_all_classes()
        print("\n班级选择:")
        print("  0. 不分配班级")
        for i, c in enumerate(classes, 1):
            marker = " <- 当前" if c['class_name'] == student.get('class_name') else ""
            print(f"  {i}. {c['class_name']}{marker}")
        class_choice = input("选择班级: ").strip()

        updates = {'remark': remark} if remark else {}
        if name:
            updates['name'] = name
        if phone:
            updates['phone'] = phone
        if email:
            updates['email'] = email

        if class_choice.isdigit():
            if class_choice == '0':
                updates['class_id'] = None
            elif 1 <= int(class_choice) <= len(classes):
                updates['class_id'] = classes[int(class_choice) - 1]['class_name']

        if updates:
            ok, msg = self.db.update_student(student_id, **updates)
            print(f"\n{'[OK] ' + msg if ok else '[X] ' + msg}")
        else:
            print("\n未做任何修改")

        self.wait_enter()

    def batch_delete_students(self):
        """批量删除学生 - 带勾选功能"""
        self.clear_screen()
        self.print_header("批量删除学生")

        # 获取所有学生
        all_students = self.db.get_all_students()
        if not all_students:
            print("暂无学生数据")
            self.wait_enter()
            return

        # 显示学生列表，带序号
        page_size = 20
        page = 0

        while True:
            self.clear_screen()
            self.print_header("批量删除学生")

            start = page * page_size
            end = min(start + page_size, len(all_students))
            page_students = all_students[start:end]

            print(f"\n共 {len(all_students)} 名学生，已选择 {len(self.selected_students)} 名")
            total_pages = max(1, (len(all_students) - 1) // page_size + 1)
            print(f"页码: {page + 1}/{total_pages}\n")
            print(f"{'选择':<6} {'学号':<15} {'姓名':<10} {'班级':<20}")
            print("-" * 55)

            for i, s in enumerate(page_students):
                idx = start + i + 1
                checked = "[*]" if s['student_id'] in self.selected_students else "[ ]"
                print(f"{checked} {idx:<3} {s['student_id']:<15} {s['name']:<10} {s.get('class_name', '未分配'):<20}")

            print("\n操作:")
            print("  输入序号选择/取消选择 (如: 1,3,5 或 1-5)")
            print("  A - 全选本页")
            print("  N - 取消本页全选")
            print("  C - 取消全部选择")
            print("  D - 确认删除所选")
            print("  P - 上一页")
            print("  S - 下一页")
            print("  0. 返回")

            choice = input("\n请选择: ").strip().upper()

            if choice == '0':
                break
            elif choice == 'A':
                for s in page_students:
                    self.selected_students.add(s['student_id'])
            elif choice == 'N':
                for s in page_students:
                    self.selected_students.discard(s['student_id'])
            elif choice == 'C':
                self.selected_students.clear()
            elif choice == 'D':
                if not self.selected_students:
                    print("请先选择要删除的学生")
                    input()
                    continue
                print(f"\n确认删除 {len(self.selected_students)} 名学生？(y/N): ")
                confirm = input().strip().lower()
                if confirm == 'y':
                    deleted, errors = self.db.delete_students_batch(list(self.selected_students))
                    print(f"\n[OK] 已删除 {deleted} 名学生")
                    self.selected_students.clear()
                    # 刷新列表
                    all_students = self.db.get_all_students()
                    page = 0
                    input()
            elif choice == 'P':
                page = max(0, page - 1)
            elif choice == 'S':
                if page < total_pages - 1:
                    page += 1
            elif choice and not choice.isalpha():
                # 处理序号选择
                try:
                    if '-' in choice:
                        start_idx, end_idx = choice.split('-')
                        for idx in range(int(start_idx), int(end_idx) + 1):
                            if 1 <= idx <= len(all_students):
                                sid = all_students[idx - 1]['student_id']
                                if sid in self.selected_students:
                                    self.selected_students.discard(sid)
                                else:
                                    self.selected_students.add(sid)
                    else:
                        for idx_str in choice.split(','):
                            idx = int(idx_str.strip())
                            if 1 <= idx <= len(all_students):
                                sid = all_students[idx - 1]['student_id']
                                if sid in self.selected_students:
                                    self.selected_students.discard(sid)
                                else:
                                    self.selected_students.add(sid)
                except:
                    pass

    def batch_assign_class(self):
        """批量分配班级"""
        self.clear_screen()
        self.print_header("批量分配班级")

        # 获取未分配班级的学生
        no_class = self.db.get_students_without_class()
        all_students = self.db.get_all_students()

        print(f"\n选择要分配班级的学生:")
        print(f"  1. 未分配班级的学生 ({len(no_class)}人)")
        print("  2. 所有学生")

        choice = input("\n请选择 (1/2): ").strip()

        if choice == '1':
            target_students = no_class
        else:
            target_students = all_students

        # 显示可选学生
        page_size = 20
        page = 0
        self.selected_students.clear()

        while True:
            self.clear_screen()
            self.print_header("批量分配班级")

            start = page * page_size
            end = min(start + page_size, len(target_students))
            page_students = target_students[start:end]
            total_pages = max(1, (len(target_students) - 1) // page_size + 1)

            print(f"\n共 {len(target_students)} 名学生，已选择 {len(self.selected_students)} 名")
            print(f"页码: {page + 1}/{total_pages}\n")
            print(f"{'选择':<6} {'学号':<15} {'姓名':<10} {'当前班级':<20}")
            print("-" * 55)

            for i, s in enumerate(page_students):
                idx = start + i + 1
                checked = "[*]" if s['student_id'] in self.selected_students else "[ ]"
                print(f"{checked} {idx:<3} {s['student_id']:<15} {s['name']:<10} {s.get('class_name', '未分配'):<20}")

            print("\n操作:")
            print("  输入序号选择")
            print("  A - 全选本页")
            print("  C - 取消选择")
            print("  X - 确认选择")
            print("  P/N - 上一页/下一页")
            print("  0. 返回")

            cmd = input("\n请选择: ").strip().upper()

            if cmd == '0':
                break
            elif cmd == 'A':
                for s in page_students:
                    self.selected_students.add(s['student_id'])
            elif cmd == 'C':
                self.selected_students.clear()
            elif cmd == 'X':
                if not self.selected_students:
                    print("请先选择学生")
                    input()
                    continue

                # 选择目标班级
                classes = self.db.get_all_classes()
                if not classes:
                    print("暂无班级，请先添加班级")
                    input()
                    continue

                print("\n目标班级:")
                for i, c in enumerate(classes, 1):
                    print(f"  {i}. {c['class_name']} ({c['student_count']}人)")

                class_choice = input("\n选择班级: ").strip()
                if class_choice.isdigit() and 1 <= int(class_choice) <= len(classes):
                    target_class = classes[int(class_choice) - 1]['class_name']
                    updated, errors = self.db.assign_class_batch(list(self.selected_students), target_class)
                    print(f"\n[OK] 已将 {updated} 名学生分配到 '{target_class}'")
                    if errors:
                        for e in errors[:3]:
                            print(f"  - {e}")

                    self.selected_students.clear()
                    # 刷新
                    no_class = self.db.get_students_without_class()
                    target_students = no_class if choice == '1' else self.db.get_all_students()
                    page = 0
                input()

            elif cmd == 'P':
                page = max(0, page - 1)
            elif cmd == 'S':
                if page < total_pages - 1:
                    page += 1
            else:
                try:
                    for idx_str in cmd.split(','):
                        idx = int(idx_str.strip())
                        if 1 <= idx <= len(target_students):
                            sid = target_students[idx - 1]['student_id']
                            if sid in self.selected_students:
                                self.selected_students.discard(sid)
                            else:
                                self.selected_students.add(sid)
                except:
                    pass

    def view_students_without_class(self):
        """查看未分配班级的学生"""
        self.clear_screen()
        self.print_header("未分配班级的学生")

        students = self.db.get_students_without_class()

        if not students:
            print("\n所有学生都已分配班级")
        else:
            print(f"\n共 {len(students)} 名学生未分配班级:\n")
            print(f"{'学号':<15} {'姓名':<10} {'电话':<15}")
            print("-" * 45)
            for s in students:
                print(f"{s['student_id']:<15} {s['name']:<10} {s.get('phone', '-'):<15}")

            print("\n提示: 可使用 '批量分配班级' 功能快速分配")

        self.wait_enter()

    def search_students(self):
        self.clear_screen()
        self.print_header("搜索学生")

        keyword = input("输入学号或姓名搜索: ").strip()
        if not keyword:
            return

        students = self.db.search_student(keyword=keyword)

        if not students:
            print("\n未找到匹配的学生")
        else:
            print(f"\n找到 {len(students)} 个结果:")
            print(f"\n{'学号':<15} {'姓名':<10} {'班级':<20}")
            print("-" * 50)
            for s in students:
                print(f"{s['student_id']:<15} {s['name']:<10} {s.get('class_name', '-'):<20}")

        self.wait_enter()

    def export_students(self):
        self.clear_screen()
        self.print_header("导出学生信息")

        classes = self.db.get_all_classes()
        class_name = None

        if classes:
            print("\n班级列表:")
            for i, c in enumerate(classes, 1):
                print(f"  {i}. {c['class_name']}")
            print("  0. 导出全部")
            choice = input("\n选择班级: ").strip()
            if choice.isdigit():
                if int(choice) == 0:
                    class_name = None
                elif 1 <= int(choice) <= len(classes):
                    class_name = classes[int(choice) - 1]['class_name']

        default_name = f"学生信息_{datetime.now().strftime('%Y%m%d')}.xlsx"
        filepath = input(f"\n保存路径 [{default_name}]: ").strip()
        if not filepath:
            filepath = default_name

        ok, msg = self.db.export_to_excel(filepath, class_name)
        print(f"\n{'[OK] ' + msg if ok else '[X] ' + msg}")
        self.wait_enter()

    # ===== 文件重命名 =====

    def rename_reports(self):
        self.clear_screen()
        self.print_header("实验报告批量重命名")

        classes = self.db.get_all_classes()
        if not classes:
            print("\n[X] 暂无班级信息，请先添加班级和学生")
            self.wait_enter()
            return

        print("\n班级列表:")
        for i, c in enumerate(classes, 1):
            print(f"  {i}. {c['class_name']} ({c['student_count']}人)")
        print("  0. 不限定班级")

        choice = input("\n选择班级: ").strip()
        class_name = None
        if choice.isdigit() and 1 <= int(choice) <= len(classes):
            class_name = classes[int(choice) - 1]['class_name']

        folder = input("\n请输入实验报告文件夹路径: ").strip().strip('"')
        if not os.path.isdir(folder):
            print("[X] 文件夹不存在")
            self.wait_enter()
            return

        print(f"\n[FOLDER] 目标文件夹: {folder}")
        if class_name:
            print(f"[CLASS] 班级: {class_name}")
        print("\n命名格式: 学号姓名实验报告序号")
        print("示例: 202509160101曹柯实验报告一.docx")

        confirm = input("\n确认开始处理？(y/N): ").strip().lower()
        if confirm != 'y':
            return

        self.renamer = ExperimentReportRenamer(self.db)
        try:
            self.renamer.batch_rename(folder, class_name)
        except Exception as e:
            print(f"\n[X] 处理出错: {str(e)}")

        self.wait_enter()

    # ===== 主菜单 =====

    def run(self):
        while True:
            self.clear_screen()
            self.print_header("实验报告收缴管理系统 v2")

            stats = self.db.get_stats()
            print(f"\n  [STAT] 数据统计: {stats['total_classes']} 个班级, {stats['total_students']} 名学生")
            if stats['no_class_students'] > 0:
                print(f"           (其中 {stats['no_class_students']} 名未分配班级)")

            print("\n  1. 学生信息管理 (增删改查/批量操作)")
            print("  2. 批量重命名实验报告")
            print("  3. 搜索学生")
            print("\n  0. 退出")

            choice = input("\n请选择: ").strip()

            if choice == '1':
                self.manage_students()
            elif choice == '2':
                self.rename_reports()
            elif choice == '3':
                self.search_students()
            elif choice == '0':
                print("\nBYE!")
                self.db.close()
                break


def main():
    try:
        menu = MenuSystem()
        menu.run()
    except KeyboardInterrupt:
        print("\n\nBYE!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] 程序异常: {str(e)}")
        input()
        sys.exit(1)


if __name__ == "__main__":
    main()
