# -*- coding: utf-8 -*-
"""
Excel/CSV学生名单导入模块 - 修复增强版
功能：自动识别学生名单中的学号、姓名、班级、电话、邮箱等字段，并导入数据库。

修复重点：
1. 支持有表头、无表头、表头不在第一行的名单；
2. 修复 Excel 把学号读成数字、浮点数、科学计数法后无法导入的问题；
3. 支持 .xlsx/.xlsm/.csv，.xls 给出明确提示；
4. 支持按表格中的班级列自动创建/分配班级；
5. 不再强依赖 pandas，减少“程序跑不起来”的概率。
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover - GUI中会给出提示
    load_workbook = None


class SmartExcelImporter:
    """智能学生名单导入器"""

    STUDENT_ID_KEYWORDS = [
        '学号', '学生学号', '学籍号', '编号', '序号编号', 'student_id', 'studentid',
        'student no', 'studentno', 'student number', 'no.', 'id'
    ]
    NAME_KEYWORDS = ['姓名', '学生姓名', '名字', '姓名全称', 'name', 'student_name', 'student name']
    CLASS_KEYWORDS = ['班级', '班别', '行政班', '教学班', 'class', 'class_name', '班级名称']
    PHONE_KEYWORDS = ['电话', '手机', '手机号', '联系电话', '联系方式', 'phone', 'tel', 'mobile']
    EMAIL_KEYWORDS = ['邮箱', '电子邮箱', '电子邮件', 'email', 'mail', 'e-mail']
    REMARK_KEYWORDS = ['备注', '说明', 'remark', 'note']

    def __init__(self, excel_path: str):
        self.excel_path = Path(excel_path)
        self.workbook = None
        self.raw_data: List[List[Any]] = []
        self.header_row: int = 0          # 1-based；0表示无表头
        self.data_start_row: int = 1      # 1-based；实际数据起始行
        self.column_map: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    # ==================== 文件读取 ====================

    def load_file(self) -> Tuple[bool, str]:
        """加载文件并读取原始数据"""
        self.errors = []
        self.warnings = []
        self.raw_data = []
        self.column_map = {}
        self.header_row = 0
        self.data_start_row = 1

        if not self.excel_path.exists():
            return False, f"文件不存在: {self.excel_path}"

        suffix = self.excel_path.suffix.lower()
        try:
            if suffix in ('.xlsx', '.xlsm'):
                if load_workbook is None:
                    return False, "缺少 openpyxl 依赖，请先运行：pip install openpyxl"
                self.workbook = load_workbook(self.excel_path, data_only=True, read_only=False)
                ok = self._read_sheet_data()
                if not ok:
                    return False, '; '.join(self.errors) if self.errors else '读取Excel失败'
                return True, f"成功加载工作簿，共 {len(self.workbook.sheetnames)} 个工作表"

            if suffix == '.csv':
                ok = self._read_csv_data()
                if not ok:
                    return False, '; '.join(self.errors) if self.errors else '读取CSV失败'
                return True, "成功加载CSV文件"

            if suffix == '.xls':
                ok = self._read_xls_data()
                if not ok:
                    return False, '; '.join(self.errors) if self.errors else '读取XLS失败'
                return True, "成功加载XLS文件"

            return False, "文件格式不支持，请选择 .xlsx、.xlsm、.xls 或 .csv 文件"
        except Exception as e:
            return False, f"加载失败: {e}"

    def _read_xls_data(self) -> bool:
        """读取旧版 .xls 文件；需要 xlrd。"""
        try:
            import xlrd
        except Exception:
            self.errors.append("当前环境缺少 xlrd，无法读取 .xls。请先运行 install_dependencies.bat，或用 Excel/WPS 将名单另存为 .xlsx 后再导入。")
            return False
        try:
            book = xlrd.open_workbook(str(self.excel_path))
            if book.nsheets == 0:
                self.errors.append("工作簿为空")
                return False
            sheet = book.sheet_by_index(0)
            self.raw_data = []
            for r in range(sheet.nrows):
                row_data = []
                for c in range(sheet.ncols):
                    row_data.append(sheet.cell_value(r, c))
                while row_data and self._is_blank(row_data[-1]):
                    row_data.pop()
                self.raw_data.append(row_data)
            while self.raw_data and all(self._is_blank(v) for v in self.raw_data[0]):
                self.raw_data.pop(0)
            while self.raw_data and all(self._is_blank(v) for v in self.raw_data[-1]):
                self.raw_data.pop()
            if not self.raw_data:
                self.errors.append("工作表为空或无有效数据")
                return False
            self._analyze_table_structure()
            return True
        except Exception as e:
            self.errors.append(f"读取XLS失败: {e}")
            return False

    def _read_csv_data(self) -> bool:
        """读取CSV文件，兼容常见编码"""
        for enc in ('utf-8-sig', 'gbk', 'gb18030', 'utf-8'):
            try:
                with open(self.excel_path, 'r', encoding=enc, newline='') as f:
                    reader = csv.reader(f)
                    self.raw_data = [row for row in reader]
                self._analyze_table_structure()
                return True
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.errors.append(f"读取CSV失败: {e}")
                return False
        self.errors.append("CSV编码无法识别，请另存为 UTF-8 或 GBK 编码后重试")
        return False

    def _read_sheet_data(self) -> bool:
        """读取工作表数据。load_file 已读取过 CSV 时，重复调用该方法会直接返回 True。"""
        if self.workbook is None and self.raw_data:
            return True
        try:
            sheet = self.workbook.active

            merged_cells = {}
            for merged_range in sheet.merged_cells.ranges:
                min_col, min_row, max_col, max_row = merged_range.bounds
                value = sheet.cell(min_row, min_col).value
                for row in range(min_row, max_row + 1):
                    for col in range(min_col, max_col + 1):
                        merged_cells[(row, col)] = value

            self.raw_data = []
            for row_idx in range(1, sheet.max_row + 1):
                row_data = []
                for col_idx in range(1, sheet.max_column + 1):
                    cell_value = sheet.cell(row_idx, col_idx).value
                    if (row_idx, col_idx) in merged_cells:
                        cell_value = merged_cells[(row_idx, col_idx)]
                    row_data.append(cell_value)
                # 去掉行尾空列，避免空列干扰识别
                while row_data and self._is_blank(row_data[-1]):
                    row_data.pop()
                self.raw_data.append(row_data)

            # 去掉前后空行
            while self.raw_data and all(self._is_blank(v) for v in self.raw_data[0]):
                self.raw_data.pop(0)
            while self.raw_data and all(self._is_blank(v) for v in self.raw_data[-1]):
                self.raw_data.pop()

            self._analyze_table_structure()
            return True
        except Exception as e:
            self.errors.append(f"读取数据失败: {e}")
            return False

    # 兼容旧代码：main.py/gui_main.py 仍会调用这个内部方法
    def _read_sheet_data_legacy(self) -> bool:
        return self._read_sheet_data()

    # ==================== 结构识别 ====================

    @staticmethod
    def _is_blank(value: Any) -> bool:
        return value is None or str(value).strip() == ''

    @staticmethod
    def _cell_to_text(value: Any) -> str:
        """把单元格值转成适合匹配的文本，避免 20230101.0 这类问题"""
        if value is None:
            return ''
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            # 尽量避免科学计数法；但已被Excel四舍五入的超长数字无法完全恢复
            return format(value, 'f').rstrip('0').rstrip('.')
        return str(value).strip()

    @staticmethod
    def _norm_header(value: Any) -> str:
        text = SmartExcelImporter._cell_to_text(value).strip().lower()
        text = re.sub(r'[\s_\-—:：/\\（）()\[\]【】]+', '', text)
        return text

    def _keyword_match(self, value: Any, keywords: List[str]) -> bool:
        text = self._norm_header(value)
        if not text:
            return False
        for kw in keywords:
            kw_norm = self._norm_header(kw)
            if kw_norm and (text == kw_norm or kw_norm in text):
                return True
        return False

    def _parse_column(self, value: Any) -> Optional[str]:
        if self._keyword_match(value, self.STUDENT_ID_KEYWORDS):
            return 'student_id'
        if self._keyword_match(value, self.NAME_KEYWORDS):
            return 'name'
        if self._keyword_match(value, self.CLASS_KEYWORDS):
            return 'class_name'
        if self._keyword_match(value, self.PHONE_KEYWORDS):
            return 'phone'
        if self._keyword_match(value, self.EMAIL_KEYWORDS):
            return 'email'
        if self._keyword_match(value, self.REMARK_KEYWORDS):
            return 'remark'
        return None

    def _find_header_row_by_keywords(self) -> int:
        """返回1-based表头行；没找到返回0"""
        max_scan = min(30, len(self.raw_data))
        for idx in range(max_scan):
            row = self.raw_data[idx]
            parsed = [self._parse_column(v) for v in row]
            score = 0
            if 'student_id' in parsed:
                score += 2
            if 'name' in parsed:
                score += 2
            if 'class_name' in parsed:
                score += 1
            if score >= 3 or ('student_id' in parsed and 'name' in parsed):
                return idx + 1
        return 0

    def _is_student_id(self, value: Any) -> bool:
        sid = self._normalize_student_id(value, warn=False)
        return sid is not None

    def _is_name(self, value: Any) -> bool:
        text = self._cell_to_text(value).strip()
        if not text:
            return False
        # 排除明显表头、电话、邮箱、纯数字
        if self._parse_column(text) is not None:
            return False
        if re.fullmatch(r'\d+', text):
            return False
        if '@' in text:
            return False
        if re.fullmatch(r'1\d{10}', text):
            return False
        if re.fullmatch(r'[\u4e00-\u9fa5·•]{2,8}', text):
            return True
        if re.fullmatch(r'[A-Za-z][A-Za-z .\-]{1,40}', text):
            return True
        return False

    def _infer_columns_by_data(self, start_idx: int = 0) -> Dict[str, int]:
        """无表头或表头不规范时，根据数据特征推断列"""
        column_map: Dict[str, int] = {}
        sample_rows = [r for r in self.raw_data[start_idx:start_idx + 30] if any(not self._is_blank(v) for v in r)]
        if not sample_rows:
            return column_map

        max_cols = max(len(r) for r in sample_rows)
        scores = {i: {'student_id': 0, 'name': 0, 'phone': 0, 'email': 0, 'class_name': 0} for i in range(max_cols)}

        for row in sample_rows:
            for col_idx in range(max_cols):
                value = row[col_idx] if col_idx < len(row) else None
                text = self._cell_to_text(value).strip()
                if not text:
                    continue
                if self._is_student_id(text):
                    scores[col_idx]['student_id'] += 3
                if self._is_name(text):
                    scores[col_idx]['name'] += 2
                if re.fullmatch(r'1\d{10}', re.sub(r'\D', '', text)):
                    scores[col_idx]['phone'] += 1
                if '@' in text and '.' in text:
                    scores[col_idx]['email'] += 2
                if '班' in text and not self._is_name(text):
                    scores[col_idx]['class_name'] += 1

        # 选择分数最高的学号列和姓名列，且不能同列
        sid_col = max(scores, key=lambda c: scores[c]['student_id'])
        if scores[sid_col]['student_id'] > 0:
            column_map['student_id'] = sid_col

        name_candidates = sorted(scores, key=lambda c: scores[c]['name'], reverse=True)
        for c in name_candidates:
            if scores[c]['name'] > 0 and c != column_map.get('student_id'):
                column_map['name'] = c
                break

        for field in ('class_name', 'phone', 'email'):
            candidates = sorted(scores, key=lambda c: scores[c][field], reverse=True)
            for c in candidates:
                if scores[c][field] > 0 and c not in column_map.values():
                    column_map[field] = c
                    break

        if 'student_id' in column_map and 'name' in column_map and self.header_row == 0:
            self.warnings.append("未找到标准表头，已按数据特征自动识别学号列和姓名列")

        return column_map

    def _smart_detect_columns(self, header_row: List[Any], first_data_row: List[Any] = None) -> Dict[str, int]:
        """兼容旧接口：优先按表头识别，不足时按数据推断"""
        column_map: Dict[str, int] = {}
        for col_idx, value in enumerate(header_row):
            col_type = self._parse_column(value)
            if col_type and col_type not in column_map:
                column_map[col_type] = col_idx

        if 'student_id' not in column_map or 'name' not in column_map:
            inferred = self._infer_columns_by_data(self.data_start_row - 1)
            for k, v in inferred.items():
                column_map.setdefault(k, v)
        return column_map

    def _analyze_table_structure(self) -> None:
        if not self.raw_data:
            self.errors.append("文件中没有数据")
            return

        self.header_row = self._find_header_row_by_keywords()
        if self.header_row:
            self.data_start_row = self.header_row + 1
            header = self.raw_data[self.header_row - 1]
            first_data = self.raw_data[self.data_start_row - 1] if len(self.raw_data) >= self.data_start_row else []
            self.column_map = self._smart_detect_columns(header, first_data)
        else:
            # 无表头：从第一行非空数据开始推断列
            self.data_start_row = 1
            self.column_map = self._infer_columns_by_data(0)

        if 'student_id' not in self.column_map or 'name' not in self.column_map:
            self.errors.append("无法识别学号列和姓名列。请保证名单至少包含两列：学号、姓名。")

    # ==================== 数据清洗/导出 ====================

    def _normalize_student_id(self, value: Any, warn: bool = True) -> Optional[str]:
        if value is None:
            return None
        text = self._cell_to_text(value)
        text = text.replace('，', ',').strip()
        text = re.sub(r'\.0$', '', text)
        text = re.sub(r'[\s\-\u3000]', '', text)

        # 对类似 2.02509160101E+11 的字符串尽量恢复
        sci_match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)[eE]\+?(\d+)', text)
        if sci_match:
            try:
                text = format(float(text), '.0f')
            except Exception:
                pass

        digits = re.sub(r'\D', '', text)
        if not digits:
            return None

        # 常见学号位数：8-18位。过短通常不是学号。
        if len(digits) < 6:
            if warn:
                self.warnings.append(f"学号过短: {text}")
            return None
        if len(digits) > 20:
            if warn:
                self.warnings.append(f"学号过长，已保留数字部分: {digits}")
        return digits

    def _normalize_name(self, value: Any) -> str:
        text = self._cell_to_text(value).strip()
        text = re.sub(r'\s+', '', text) if re.search(r'[\u4e00-\u9fa5]', text) else re.sub(r'\s+', ' ', text)
        return text

    def _row_get(self, row: List[Any], field: str) -> Any:
        col = self.column_map.get(field)
        if col is None or col >= len(row):
            return None
        return row[col]

    def get_students(self) -> List[Dict]:
        """获取清洗后的学生列表"""
        if not self.raw_data or not self.column_map:
            return []

        students: List[Dict] = []
        start_idx = max(self.data_start_row - 1, 0)

        for row_idx in range(start_idx, len(self.raw_data)):
            row = self.raw_data[row_idx]
            if all(self._is_blank(v) for v in row):
                continue

            sid = self._normalize_student_id(self._row_get(row, 'student_id'))
            name = self._normalize_name(self._row_get(row, 'name'))

            # 跳过误读到的表头行
            if self._parse_column(sid) or self._parse_column(name):
                continue

            if not sid or not name:
                self.warnings.append(f"第{row_idx + 1}行缺少学号或姓名，已跳过")
                continue

            student = {
                'student_id': sid,
                'name': name,
                '_row_num': row_idx + 1,
            }

            for field in ('class_name', 'phone', 'email', 'remark'):
                val = self._row_get(row, field)
                text = self._cell_to_text(val).strip()
                if text and text != '-':
                    student[field] = text

            students.append(student)

        return students

    def validate_data(self) -> Tuple[bool, List[str]]:
        students = self.get_students()
        messages: List[str] = []

        if not students:
            messages.append("没有找到有效的学生数据")
            if self.errors:
                messages.extend(self.errors)
            self.errors = messages
            return False, messages

        seen = {}
        for s in students:
            sid = s['student_id']
            seen.setdefault(sid, []).append(s['name'])
        duplicates = {sid: names for sid, names in seen.items() if len(names) > 1}
        if duplicates:
            messages.append(f"名单内部发现重复学号 {len(duplicates)} 个，导入时将以最后一次出现的数据为准")
            for sid, names in list(duplicates.items())[:5]:
                messages.append(f"  {sid}: {', '.join(names)}")

        length_stats: Dict[int, int] = {}
        for s in students:
            length_stats[len(s['student_id'])] = length_stats.get(len(s['student_id']), 0) + 1
        if length_stats:
            info = ', '.join(f"{k}位:{v}人" for k, v in sorted(length_stats.items()))
            messages.append(f"学号长度分布: {info}")

        if self.warnings:
            messages.extend(self.warnings[:8])

        self.errors = messages
        return True, messages

    def import_to_db(self, db, class_name: str = None) -> Tuple[int, int, List[str]]:
        students = self.get_students()
        if not students:
            return 0, 0, self.errors if self.errors else ["没有可导入的学生数据"]
        success, failed, errors = db.add_student_batch(students, class_name)
        # 记录导入历史，不影响主流程
        try:
            cursor = db.conn.cursor()
            cursor.execute(
                "INSERT INTO import_history (filename, class_name, record_count) VALUES (?, ?, ?)",
                (self.excel_path.name, class_name or '按表格/未指定', success)
            )
            db.conn.commit()
        except Exception:
            pass
        return success, failed, errors + self.warnings[:5]

    def preview_data(self, max_rows: int = 15) -> str:
        if not self.raw_data:
            return "未加载数据"
        result = ["=" * 60]
        if self.header_row:
            result.append(f"数据预览：表头位于第 {self.header_row} 行，数据从第 {self.data_start_row} 行开始")
        else:
            result.append(f"数据预览：未发现标准表头，数据从第 {self.data_start_row} 行开始")
        result.append("=" * 60)

        if self.column_map:
            names = {
                'student_id': '学号', 'name': '姓名', 'class_name': '班级',
                'phone': '电话', 'email': '邮箱', 'remark': '备注'
            }
            fields = [f"{names.get(k, k)}=第{v + 1}列" for k, v in sorted(self.column_map.items(), key=lambda x: x[1])]
            result.append("识别字段：" + '，'.join(fields))
        else:
            result.append("未识别到有效字段")

        students = self.get_students()
        result.append(f"有效学生数：{len(students)}")
        for i, s in enumerate(students[:max_rows], 1):
            class_part = f" | {s.get('class_name')}" if s.get('class_name') else ''
            result.append(f"  {i}. {s['student_id']} | {s['name']}{class_part}")
        if len(students) > max_rows:
            result.append(f"  ... 还有 {len(students) - max_rows} 条未显示")
        return '\n'.join(result)

    def get_column_info(self) -> Dict:
        return {
            'header_row': self.header_row,
            'data_start_row': self.data_start_row,
            'total_rows': len(self.raw_data),
            'detected_columns': self.column_map,
            'data_rows': max(0, len(self.raw_data) - (self.data_start_row - 1)),
            'warnings': self.warnings,
            'errors': self.errors,
        }


def import_from_excel(excel_path: str, db, class_name: str = None) -> Tuple[int, int, List[str]]:
    """便捷函数：从名单文件导入学生"""
    importer = SmartExcelImporter(excel_path)
    ok, msg = importer.load_file()
    if not ok:
        return 0, 0, [msg]
    importer.validate_data()
    return importer.import_to_db(db, class_name)


if __name__ == "__main__":
    print("=== 学生名单导入模块 ===")
    print("支持：.xlsx/.xlsm/.csv；.xls 请另存为 .xlsx 后导入。")
