# -*- coding: utf-8 -*-
"""
学生信息数据库管理模块 - 修复增强版
功能：班级/学生增删改查、批量导入、导出、数据持久化。

修复重点：
1. 自动创建 data/students.db；
2. 学号唯一，避免名单反复导入产生重复记录；
3. 批量导入时同学号自动更新，不再因为重复学号导致“上传不上去”；
4. 支持名单中的班级列自动创建并分配班级。
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class StudentDB:
    """学生信息数据库管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            project_dir = Path(__file__).parent
            data_dir = project_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "students.db"

        self.db_path = str(db_path)
        self.conn = None
        self._connect()
        self._init_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL UNIQUE,
                grade TEXT,
                major TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                remark TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                class_id INTEGER,
                phone TEXT,
                email TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                remark TEXT,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                class_name TEXT,
                record_count INTEGER,
                imported_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_class_id ON students(class_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_id ON students(student_id)")
        self.conn.commit()
        self._dedupe_students()
        self._ensure_unique_student_index()

    def _dedupe_students(self):
        """清理旧版本数据库中可能已经存在的重复学号。保留最后一条。"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT student_id, MAX(id) AS keep_id, COUNT(*) AS cnt
            FROM students
            GROUP BY student_id
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        for row in duplicates:
            cursor.execute(
                "DELETE FROM students WHERE student_id = ? AND id <> ?",
                (row['student_id'], row['keep_id'])
            )
        self.conn.commit()

    def _ensure_unique_student_index(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_student_id_unique ON students(student_id)")
            self.conn.commit()
        except sqlite3.IntegrityError:
            self._dedupe_students()
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_student_id_unique ON students(student_id)")
            self.conn.commit()

    @staticmethod
    def _clean_text(value) -> str:
        if value is None:
            return ''
        text = str(value).strip()
        if text.endswith('.0') and text[:-2].isdigit():
            text = text[:-2]
        return text

    def _get_or_create_class_id(self, class_name: str = None, grade: str = None, major: str = None) -> Optional[int]:
        if not class_name:
            return None
        class_name = str(class_name).strip()
        if not class_name:
            return None
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM classes WHERE class_name = ?", (class_name,))
        row = cursor.fetchone()
        if row:
            return row['id']
        cursor.execute(
            "INSERT INTO classes (class_name, grade, major) VALUES (?, ?, ?)",
            (class_name, grade, major)
        )
        self.conn.commit()
        return cursor.lastrowid

    # ===== 班级操作 =====

    def add_class(self, class_name: str, grade: str = None, major: str = None, remark: str = None) -> Tuple[bool, str]:
        class_name = self._clean_text(class_name)
        if not class_name:
            return False, "班级名称不能为空"
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO classes (class_name, grade, major, remark) VALUES (?, ?, ?, ?)",
                (class_name, grade, major, remark)
            )
            self.conn.commit()
            return True, f"班级 '{class_name}' 添加成功"
        except sqlite3.IntegrityError:
            return False, f"班级 '{class_name}' 已存在"

    def delete_class(self, class_name: str) -> Tuple[bool, str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM classes WHERE class_name = ?", (class_name,))
        row = cursor.fetchone()
        if not row:
            return False, f"班级 '{class_name}' 不存在"

        class_id = row['id']
        cursor.execute("DELETE FROM students WHERE class_id = ?", (class_id,))
        cursor.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        self.conn.commit()
        return True, f"班级 '{class_name}' 及相关学生已删除"

    def get_all_classes(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, COUNT(s.id) AS student_count
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id
            GROUP BY c.id
            ORDER BY c.class_name
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_class_by_name(self, class_name: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM classes WHERE class_name = ?", (class_name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # ===== 学生操作 =====

    def add_student(self, student_id: str, name: str, class_name: str = None,
                    phone: str = None, email: str = None, remark: str = None) -> Tuple[bool, str]:
        student_id = self._clean_text(student_id)
        name = self._clean_text(name)
        if not student_id or not name:
            return False, "学号和姓名不能为空"

        try:
            cursor = self.conn.cursor()
            class_id = self._get_or_create_class_id(class_name)
            cursor.execute("""
                INSERT INTO students (student_id, name, class_id, phone, email, remark)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, name, class_id, phone or None, email or None, remark or None))
            self.conn.commit()
            return True, f"学生 '{name}' (学号: {student_id}) 添加成功"
        except sqlite3.IntegrityError:
            return False, f"学号 '{student_id}' 已存在"
        except Exception as e:
            return False, f"添加失败: {e}"

    def upsert_student(self, student: Dict, default_class_name: str = None) -> Tuple[bool, str]:
        """新增或更新学生。批量导入使用该方法。"""
        student_id = self._clean_text(student.get('student_id'))
        name = self._clean_text(student.get('name'))
        if not student_id or not name:
            return False, f"学号或姓名不能为空: {student}"

        # 用户在导入窗口指定班级时优先使用指定班级；否则使用表格中的班级列。
        class_name = default_class_name or self._clean_text(student.get('class_name'))
        class_id = self._get_or_create_class_id(class_name)
        phone = self._clean_text(student.get('phone')) or None
        email = self._clean_text(student.get('email')) or None
        remark = self._clean_text(student.get('remark')) or None

        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id FROM students WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE students
                    SET name = ?, class_id = ?, phone = ?, email = ?, remark = ?
                    WHERE student_id = ?
                """, (name, class_id, phone, email, remark, student_id))
                self.conn.commit()
                return True, f"已更新：{student_id} {name}"

            cursor.execute("""
                INSERT INTO students (student_id, name, class_id, phone, email, remark)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, name, class_id, phone, email, remark))
            self.conn.commit()
            return True, f"已新增：{student_id} {name}"
        except Exception as e:
            self.conn.rollback()
            return False, f"{student_id} {name}: {e}"

    def add_student_batch(self, students: List[Dict], class_name: str = None) -> Tuple[int, int, List[str]]:
        """批量添加/更新学生。返回：成功数、失败数、错误信息。"""
        success_count = 0
        error_messages: List[str] = []

        # 同一个名单内重复学号时以后出现的数据为准。
        deduped: Dict[str, Dict] = {}
        no_id_rows: List[Dict] = []
        for stu in students:
            sid = self._clean_text(stu.get('student_id'))
            if sid:
                deduped[sid] = stu
            else:
                no_id_rows.append(stu)

        final_students = list(deduped.values()) + no_id_rows
        for student in final_students:
            ok, msg = self.upsert_student(student, class_name)
            if ok:
                success_count += 1
            else:
                error_messages.append(msg)

        return success_count, len(final_students) - success_count, error_messages

    def delete_student(self, student_id: str = None, name: str = None) -> Tuple[bool, str]:
        cursor = self.conn.cursor()

        if student_id:
            cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        elif name:
            cursor.execute("DELETE FROM students WHERE name = ?", (name,))
        else:
            return False, "请提供学号或姓名"

        if cursor.rowcount == 0:
            return False, "未找到该学生"

        self.conn.commit()
        return True, "学生已删除"

    def delete_students_batch(self, student_ids: List[str]) -> Tuple[int, List[str]]:
        deleted = 0
        errors = []
        cursor = self.conn.cursor()
        for sid in student_ids:
            cursor.execute("DELETE FROM students WHERE student_id = ?", (sid,))
            if cursor.rowcount > 0:
                deleted += 1
            else:
                errors.append(f"学号 '{sid}' 不存在")
        self.conn.commit()
        return deleted, errors

    def update_student(self, student_id: str, **kwargs) -> Tuple[bool, str]:
        allowed_fields = ['name', 'class_id', 'phone', 'email', 'remark']

        if 'class_name' in kwargs:
            class_name = kwargs.get('class_name')
            kwargs['class_id'] = self._get_or_create_class_id(class_name) if class_name else None
            del kwargs['class_name']

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False, "没有需要更新的字段"

        cursor = self.conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [student_id]
        cursor.execute(f"UPDATE students SET {set_clause} WHERE student_id = ?", values)

        if cursor.rowcount == 0:
            return False, f"学号 '{student_id}' 不存在"

        self.conn.commit()
        return True, f"学号 '{student_id}' 信息已更新"

    def assign_class_batch(self, student_ids: List[str], class_name: str) -> Tuple[int, List[str]]:
        class_id = self._get_or_create_class_id(class_name)
        if not class_id:
            return 0, ["班级名称不能为空"]

        cursor = self.conn.cursor()
        updated = 0
        errors = []
        for sid in student_ids:
            cursor.execute("UPDATE students SET class_id = ? WHERE student_id = ?", (class_id, sid))
            if cursor.rowcount > 0:
                updated += 1
            else:
                errors.append(f"学号 '{sid}' 不存在")
        self.conn.commit()
        return updated, errors

    def remove_class_batch(self, student_ids: List[str]) -> Tuple[int, List[str]]:
        cursor = self.conn.cursor()
        updated = 0
        errors = []
        for sid in student_ids:
            cursor.execute("UPDATE students SET class_id = NULL WHERE student_id = ?", (sid,))
            if cursor.rowcount > 0:
                updated += 1
            else:
                errors.append(f"学号 '{sid}' 不存在")
        self.conn.commit()
        return updated, errors

    def search_student(self, keyword: str = None, class_name: str = None) -> List[Dict]:
        cursor = self.conn.cursor()
        query = """
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE 1=1
        """
        params = []

        if keyword:
            query += " AND (s.student_id LIKE ? OR s.name LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if class_name:
            query += " AND c.class_name = ?"
            params.append(class_name)

        query += " ORDER BY s.student_id"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_student_by_id(self, student_id: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.student_id = ?
        """, (student_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_students_by_class(self, class_name: str) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE c.class_name = ?
            ORDER BY s.student_id
        """, (class_name,))
        return [dict(row) for row in cursor.fetchall()]

    def get_students_without_class(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.class_id IS NULL
            ORDER BY s.student_id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_students(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, c.class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            ORDER BY c.class_name, s.student_id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM classes")
        class_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) AS count FROM students")
        student_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) AS count FROM students WHERE class_id IS NULL")
        no_class_count = cursor.fetchone()['count']
        cursor.execute("""
            SELECT c.class_name, COUNT(s.id) AS count
            FROM classes c
            LEFT JOIN students s ON c.id = s.class_id
            GROUP BY c.id
            ORDER BY c.class_name
        """)
        class_stats = [dict(row) for row in cursor.fetchall()]
        return {
            'total_classes': class_count,
            'total_students': student_count,
            'no_class_students': no_class_count,
            'class_stats': class_stats
        }

    def export_to_excel(self, filepath: str, class_name: str = None) -> Tuple[bool, str]:
        try:
            students = self.get_students_by_class(class_name) if class_name else self.get_all_students()
            if not students:
                return False, "没有学生数据可导出"

            try:
                from openpyxl import Workbook
            except Exception:
                return False, "缺少 openpyxl 依赖，请先运行：pip install openpyxl"

            wb = Workbook()
            ws = wb.active
            ws.title = "学生信息"
            headers = ['学号', '姓名', '班级', '电话', '邮箱', '备注']
            ws.append(headers)
            for s in students:
                ws.append([
                    s.get('student_id', ''), s.get('name', ''), s.get('class_name', '') or '',
                    s.get('phone', '') or '', s.get('email', '') or '', s.get('remark', '') or ''
                ])
            for col, width in zip('ABCDEF', [18, 14, 24, 16, 24, 28]):
                ws.column_dimensions[col].width = width
            wb.save(filepath)
            return True, f"成功导出 {len(students)} 条学生信息到 {filepath}"
        except Exception as e:
            return False, f"导出失败: {e}"

    def close(self):
        if self.conn:
            self.conn.close()


# 兼容旧代码中可能直接 import db 的写法
db = StudentDB()


if __name__ == "__main__":
    print("=== 学生信息数据库测试 ===")
    print(f"数据库路径: {db.db_path}")
    stats = db.get_stats()
    print(f"统计: {stats['total_classes']}个班级, {stats['total_students']}名学生")
