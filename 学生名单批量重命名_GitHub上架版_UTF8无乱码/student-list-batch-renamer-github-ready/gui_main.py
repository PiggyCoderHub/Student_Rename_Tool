# -*- coding: utf-8 -*-
"""
实验报告收缴管理系统 - 可视化界面版
"""

import os
import sys
import io

# Windows编码兼容
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime

from student_db import StudentDB
from docx_reader import BatchDocxReader, DocxReader
from excel_importer import SmartExcelImporter


# ===== 中文数字转换 =====
CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

def int_to_chinese(num: int) -> str:
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


class ScrollableFrame(tk.Frame):
    """可滚动的Frame"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, bg='#f5f5f5', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#f5f5f5')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 鼠标滚轮支持
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))


class StudentManagerGUI:
    """学生信息管理界面"""
    
    def __init__(self, parent, db, app):
        self.parent = parent
        self.db = db
        self.app = app
        self.selected_students = set()
        self.setup_ui()
        self.load_classes()
    
    def setup_ui(self):
        # 主框架
        self.frame = tk.Frame(self.parent, bg='#f0f0f0')
        
        # 顶部标题
        title_frame = tk.Frame(self.frame, bg='#2c3e50', pady=15)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="学生信息管理", font=('Microsoft YaHei', 18, 'bold'), 
                fg='white', bg='#2c3e50').pack()
        
        # 工具栏
        toolbar = tk.Frame(self.frame, bg='#ecf0f1', pady=10)
        toolbar.pack(fill='x')
        
        buttons = [
            ("添加班级", self.add_class),
            ("添加学生", self.add_student),
            ("Excel导入", self.import_excel),
            ("删除选中", self.delete_selected),
            ("分配班级", self.assign_class),
            ("导出Excel", self.export_excel),
            ("刷新", self.load_classes),
        ]
        
        for text, cmd in buttons:
            tk.Button(toolbar, text=text, command=cmd, width=10,
                    bg='#3498db', fg='white', relief='flat',
                    cursor='hand2', font=('Microsoft YaHei', 10)).pack(side='left', padx=5)
        
        # 学生列表区域
        list_frame = tk.Frame(self.frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 表头
        header_frame = tk.Frame(list_frame, bg='#34495e')
        header_frame.pack(fill='x')
        
        headers = [('选择', 5), ('学号', 18), ('姓名', 10), ('班级', 15), ('电话', 15), ('操作', 10)]
        for text, width in headers:
            tk.Label(header_frame, text=text, width=width, font=('Microsoft YaHei', 10, 'bold'),
                    fg='white', bg='#34495e', anchor='w', padx=5, pady=8).pack(side='left')
        
        # 可滚动学生列表
        self.list_container = ScrollableFrame(list_frame)
        self.list_container.pack(fill='both', expand=True)
        
        # 状态栏
        self.status_label = tk.Label(self.frame, text="就绪", font=('Microsoft YaHei', 9),
                                     bg='#ecf0f1', anchor='w', padx=10, pady=5)
        self.status_label.pack(fill='x', side='bottom')
    
    def load_classes(self):
        """加载班级到下拉框"""
        classes = self.db.get_all_classes()
        self.class_list = [c['class_name'] for c in classes]
    
    def refresh_student_list(self, class_filter=None):
        """刷新学生列表"""
        # 清空现有列表
        for widget in self.list_container.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.selected_students.clear()
        
        # 获取学生数据
        if class_filter:
            students = self.db.get_students_by_class(class_filter)
        else:
            students = self.db.get_all_students()
        
        # 显示学生
        for i, student in enumerate(students):
            bg = 'white' if i % 2 == 0 else '#f8f9fa'
            row_frame = tk.Frame(self.list_container.scrollable_frame, bg=bg)
            row_frame.pack(fill='x', pady=0.5)
            
            var = tk.BooleanVar(value=False)
            
            def toggle(sid=student['student_id'], v=var):
                if v.get():
                    self.selected_students.add(sid)
                else:
                    self.selected_students.discard(sid)
            
            cb = tk.Checkbutton(row_frame, variable=var, command=toggle, bg=bg)
            cb.pack(side='left', padx=5)
            
            tk.Label(row_frame, text=student['student_id'], width=18, anchor='w', 
                    bg=bg, font=('Consolas', 9)).pack(side='left')
            tk.Label(row_frame, text=student['name'], width=10, anchor='w', 
                    bg=bg, font=('Microsoft YaHei', 9)).pack(side='left')
            tk.Label(row_frame, text=student.get('class_name', '-'), width=15, anchor='w', 
                    bg=bg, font=('Microsoft YaHei', 9)).pack(side='left')
            tk.Label(row_frame, text=student.get('phone', '-'), width=15, anchor='w', 
                    bg=bg, font=('Microsoft YaHei', 9)).pack(side='left')
            
            # 操作按钮
            btn_frame = tk.Frame(row_frame, bg=bg)
            btn_frame.pack(side='left')
            
            tk.Button(btn_frame, text="编辑", width=5, command=lambda s=student: self.edit_student(s),
                     bg='#27ae60', fg='white', relief='flat', cursor='hand2').pack(side='left', padx=2)
            tk.Button(btn_frame, text="删除", width=5, command=lambda s=student: self.delete_student(s),
                     bg='#e74c3c', fg='white', relief='flat', cursor='hand2').pack(side='left', padx=2)
        
        self.status_label.config(text=f"共 {len(students)} 名学生，已选中 {len(self.selected_students)} 名")
    
    def add_class(self):
        """添加班级"""
        win = tk.Toplevel(self.parent)
        win.title("添加班级")
        win.geometry("400x250")
        win.resizable(False, False)
        win.transient(self.parent)
        win.grab_set()
        
        tk.Label(win, text="添加班级", font=('Microsoft YaHei', 14, 'bold')).pack(pady=15)
        
        tk.Label(win, text="班级名称:").place(x=50, y=60)
        name_entry = tk.Entry(win, width=25, font=('Microsoft YaHei', 10))
        name_entry.place(x=130, y=60)
        
        tk.Label(win, text="年级:").place(x=50, y=100)
        grade_entry = tk.Entry(win, width=25, font=('Microsoft YaHei', 10))
        grade_entry.place(x=130, y=100)
        
        tk.Label(win, text="专业:").place(x=50, y=140)
        major_entry = tk.Entry(win, width=25, font=('Microsoft YaHei', 10))
        major_entry.place(x=130, y=140)
        
        def save():
            class_name = name_entry.get().strip()
            if not class_name:
                messagebox.showwarning("提示", "班级名称不能为空")
                return
            
            grade = grade_entry.get().strip()
            major = major_entry.get().strip()
            
            ok, msg = self.db.add_class(class_name, grade, major)
            if ok:
                messagebox.showinfo("成功", msg)
                self.load_classes()
                win.destroy()
            else:
                messagebox.showerror("错误", msg)
        
        tk.Button(win, text="保存", command=save, width=10, bg='#3498db', fg='white',
                 relief='flat', cursor='hand2').place(x=100, y=190)
        tk.Button(win, text="取消", command=win.destroy, width=10, bg='#95a5a6', fg='white',
                 relief='flat', cursor='hand2').place(x=210, y=190)
    
    def add_student(self):
        """添加学生"""
        win = tk.Toplevel(self.parent)
        win.title("添加学生")
        win.geometry("450x350")
        win.resizable(False, False)
        win.transient(self.parent)
        win.grab_set()
        
        tk.Label(win, text="添加学生", font=('Microsoft YaHei', 14, 'bold')).pack(pady=15)
        
        fields = [("学号:", 50, 50), ("姓名:", 50, 90), ("电话:", 50, 130), ("邮箱:", 50, 170)]
        entries = {}
        
        for label, x, y in fields:
            tk.Label(win, text=label, font=('Microsoft YaHei', 10)).place(x=x, y=y)
            entries[label] = tk.Entry(win, width=28, font=('Microsoft YaHei', 10))
            entries[label].place(x=100, y=y)
        
        tk.Label(win, text="班级:", font=('Microsoft YaHei', 10)).place(x=50, y=210)
        class_combo = ttk.Combobox(win, values=self.class_list, width=26, state='readonly')
        class_combo.place(x=100, y=210)
        
        def save():
            student_id = entries["学号:"].get().strip()
            name = entries["姓名:"].get().strip()
            
            if not student_id or not name:
                messagebox.showwarning("提示", "学号和姓名不能为空")
                return
            
            phone = entries["电话:"].get().strip()
            email = entries["邮箱:"].get().strip()
            class_name = class_combo.get().strip()
            
            ok, msg = self.db.add_student(student_id, name, class_name, phone, email)
            if ok:
                messagebox.showinfo("成功", msg)
                self.refresh_student_list()
                win.destroy()
            else:
                messagebox.showerror("错误", msg)
        
        tk.Button(win, text="保存", command=save, width=10, bg='#3498db', fg='white',
                 relief='flat', cursor='hand2').place(x=100, y=290)
        tk.Button(win, text="取消", command=win.destroy, width=10, bg='#95a5a6', fg='white',
                 relief='flat', cursor='hand2').place(x=230, y=290)
    
    def import_excel(self):
        """从Excel/CSV导入学生 - 修复版"""
        filepath = filedialog.askopenfilename(
            title="选择学生名单文件",
            filetypes=[("学生名单", "*.xlsx *.xlsm *.csv"), ("Excel文件", "*.xlsx *.xlsm"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        importer = SmartExcelImporter(filepath)
        ok, msg = importer.load_file()
        if not ok:
            messagebox.showerror("导入失败", msg)
            return

        valid, messages = importer.validate_data()
        students = importer.get_students()
        if not students:
            detail = "\n".join(messages[:8]) if messages else "请检查文件中是否包含学号和姓名两列。"
            messagebox.showerror("导入失败", f"没有找到有效学生数据。\n\n{detail}")
            return

        win = tk.Toplevel(self.parent)
        win.title("导入学生名单")
        win.geometry("420x220")
        win.resizable(False, False)
        win.transient(self.parent)
        win.grab_set()

        tk.Label(win, text=f"已识别 {len(students)} 名学生", font=('Microsoft YaHei', 12, 'bold')).pack(pady=(18, 8))
        tk.Label(win, text="导入到班级：", font=('Microsoft YaHei', 10)).pack()

        values = ["按表格班级/不指定"] + self.class_list
        class_combo = ttk.Combobox(win, values=values, width=30, state='readonly')
        class_combo.pack(pady=8)
        class_combo.current(0)

        preview = importer.preview_data(max_rows=3).splitlines()
        tk.Label(win, text="\n".join(preview[-3:]), justify='left', fg='gray').pack(pady=5)

        def do_import():
            chosen = class_combo.get()
            class_name = None if chosen == "按表格班级/不指定" else chosen
            success, failed, errors = importer.import_to_db(self.db, class_name)
            detail = ""
            if errors:
                detail = "\n\n部分问题：\n" + "\n".join(errors[:6])
            messagebox.showinfo("导入完成", f"成功/更新: {success}\n失败: {failed}{detail}")
            self.load_classes()
            self.refresh_student_list()
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="确认导入", command=do_import, width=12, bg='#27ae60', fg='white',
                 relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=8)
        tk.Button(btn_frame, text="取消", command=win.destroy, width=10, bg='#95a5a6', fg='white',
                 relief='flat', cursor='hand2').pack(side=tk.LEFT, padx=8)

    def edit_student(self, student):
        """编辑学生"""
        win = tk.Toplevel(self.parent)
        win.title("编辑学生")
        win.geometry("450x350")
        win.resizable(False, False)
        win.transient(self.parent)
        win.grab_set()
        
        tk.Label(win, text=f"编辑 - {student['name']}", font=('Microsoft YaHei', 14, 'bold')).pack(pady=15)
        
        tk.Label(win, text=f"学号: {student['student_id']}", font=('Microsoft YaHei', 10)).place(x=50, y=50)
        
        tk.Label(win, text="姓名:").place(x=50, y=85)
        name_entry = tk.Entry(win, width=28, font=('Microsoft YaHei', 10))
        name_entry.insert(0, student['name'])
        name_entry.place(x=100, y=85)
        
        tk.Label(win, text="电话:").place(x=50, y=125)
        phone_entry = tk.Entry(win, width=28, font=('Microsoft YaHei', 10))
        phone_entry.insert(0, student.get('phone', ''))
        phone_entry.place(x=100, y=125)
        
        tk.Label(win, text="邮箱:").place(x=50, y=165)
        email_entry = tk.Entry(win, width=28, font=('Microsoft YaHei', 10))
        email_entry.insert(0, student.get('email', ''))
        email_entry.place(x=100, y=165)
        
        tk.Label(win, text="班级:").place(x=50, y=205)
        class_combo = ttk.Combobox(win, values=[''] + self.class_list, width=26, state='readonly')
        class_combo.set(student.get('class_name', ''))
        class_combo.place(x=100, y=205)
        
        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("提示", "姓名不能为空")
                return
            
            class_name = class_combo.get().strip()
            class_id = None if not class_name else class_name
            
            ok, msg = self.db.update_student(student['student_id'], name=name, 
                                            phone=phone_entry.get().strip(),
                                            email=email_entry.get().strip(),
                                            class_name=class_id)
            if ok:
                messagebox.showinfo("成功", msg)
                self.refresh_student_list()
                win.destroy()
            else:
                messagebox.showerror("错误", msg)
        
        tk.Button(win, text="保存", command=save, width=10, bg='#3498db', fg='white',
                 relief='flat', cursor='hand2').place(x=100, y=280)
        tk.Button(win, text="取消", command=win.destroy, width=10, bg='#95a5a6', fg='white',
                 relief='flat', cursor='hand2').place(x=230, y=280)
    
    def delete_student(self, student):
        """删除学生"""
        if messagebox.askyesno("确认", f"确定删除学生 {student['name']} ({student['student_id']})？"):
            ok, msg = self.db.delete_student(student_id=student['student_id'])
            if ok:
                messagebox.showinfo("成功", msg)
                self.refresh_student_list()
            else:
                messagebox.showerror("错误", msg)
    
    def delete_selected(self):
        """删除选中学生"""
        if not self.selected_students:
            messagebox.showinfo("提示", "请先选择要删除的学生")
            return
        
        if messagebox.askyesno("确认", f"确定删除选中的 {len(self.selected_students)} 名学生？"):
            deleted, errors = self.db.delete_students_batch(list(self.selected_students))
            messagebox.showinfo("完成", f"已删除 {deleted} 名学生")
            self.refresh_student_list()
    
    def assign_class(self):
        """分配班级"""
        if not self.selected_students:
            messagebox.showinfo("提示", "请先选择要分配班级的学生")
            return
        
        if not self.class_list:
            messagebox.showinfo("提示", "请先添加班级")
            return
        
        win = tk.Toplevel(self.parent)
        win.title("分配班级")
        win.geometry("300x150")
        win.resizable(False, False)
        win.transient(self.parent)
        win.grab_set()
        
        tk.Label(win, text=f"将 {len(self.selected_students)} 名学生分配到:", 
                font=('Microsoft YaHei', 11)).pack(pady=15)
        
        class_combo = ttk.Combobox(win, values=self.class_list, width=25, state='readonly')
        class_combo.pack(pady=10)
        if self.class_list:
            class_combo.current(0)
        
        def do_assign():
            class_name = class_combo.get()
            updated, errors = self.db.assign_class_batch(list(self.selected_students), class_name)
            messagebox.showinfo("完成", f"已分配 {updated} 名学生到 {class_name}")
            self.refresh_student_list()
            win.destroy()
        
        tk.Button(win, text="分配", command=do_assign, width=10, bg='#27ae60', fg='white',
                 relief='flat', cursor='hand2').pack(pady=5)
    
    def export_excel(self):
        """导出Excel"""
        filepath = filedialog.asksaveasfilename(title="保存Excel文件", 
                                                defaultextension=".xlsx",
                                                filetypes=[("Excel文件", "*.xlsx")])
        if not filepath:
            return
        
        ok, msg = self.db.export_to_excel(filepath)
        if ok:
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("错误", msg)
    
    def show(self):
        self.frame.pack(fill='both', expand=True)
        self.refresh_student_list()
    
    def hide(self):
        self.frame.pack_forget()


class RenamerGUI:
    """文件重命名界面"""
    
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.setup_ui()
        self.load_classes()
    
    def setup_ui(self):
        self.frame = tk.Frame(self.parent, bg='#f0f0f0')
        
        # 标题
        title_frame = tk.Frame(self.frame, bg='#2c3e50', pady=15)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="实验报告批量重命名", font=('Microsoft YaHei', 18, 'bold'),
                fg='white', bg='#2c3e50').pack()
        
        # 配置区域
        config_frame = tk.LabelFrame(self.frame, text=" 配置 ", font=('Microsoft YaHei', 11),
                                     bg='#f0f0f0', padx=20, pady=15)
        config_frame.pack(fill='x', padx=20, pady=15)
        
        # 班级选择
        row1 = tk.Frame(config_frame, bg='#f0f0f0')
        row1.pack(fill='x', pady=5)
        tk.Label(row1, text="班级:", font=('Microsoft YaHei', 10), bg='#f0f0f0').pack(side='left')
        self.class_combo = ttk.Combobox(row1, values=[], width=25, state='readonly')
        self.class_combo.pack(side='left', padx=10)
        
        # 文件夹选择
        row2 = tk.Frame(config_frame, bg='#f0f0f0')
        row2.pack(fill='x', pady=5)
        tk.Label(row2, text="文件夹:", font=('Microsoft YaHei', 10), bg='#f0f0f0').pack(side='left')
        self.folder_entry = tk.Entry(row2, width=35, font=('Microsoft YaHei', 10))
        self.folder_entry.pack(side='left', padx=10)
        tk.Button(row2, text="浏览...", command=self.browse_folder, bg='#3498db', fg='white',
                 relief='flat', cursor='hand2').pack(side='left')
        
        # 命名格式预览
        preview_frame = tk.LabelFrame(self.frame, text=" 命名格式预览 ", font=('Microsoft YaHei', 11),
                                     bg='#f0f0f0', padx=20, pady=10)
        preview_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Label(preview_frame, text="格式: 学号 + 姓名 + 实验报告 + 序号",
                font=('Microsoft YaHei', 10), bg='#f0f0f0', fg='#2c3e50').pack()
        tk.Label(preview_frame, text="示例: 202509160101曹柯实验报告一.docx",
                font=('Consolas', 10), bg='#f0f0f0', fg='#7f8c8d').pack()
        
        # 操作按钮
        btn_frame = tk.Frame(self.frame, bg='#f0f0f0')
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="开始重命名", command=self.start_rename, width=15, height=2,
                 bg='#27ae60', fg='white', relief='flat', cursor='hand2',
                 font=('Microsoft YaHei', 12, 'bold')).pack(side='left', padx=10)
        tk.Button(btn_frame, text="预览结果", command=self.preview, width=15, height=2,
                 bg='#3498db', fg='white', relief='flat', cursor='hand2',
                 font=('Microsoft YaHei', 12, 'bold')).pack(side='left', padx=10)
        
        # 结果显示区
        result_frame = tk.LabelFrame(self.frame, text=" 处理结果 ", font=('Microsoft YaHei', 11),
                                     bg='#f0f0f0', padx=10, pady=10)
        result_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        
        self.result_text = tk.Text(result_frame, width=70, height=15, font=('Consolas', 10),
                                   bg='#2c3e50', fg='#ecf0f1', relief='flat')
        self.result_text.pack(fill='both', expand=True)
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.result_text.config(yscrollcommand=scrollbar.set)
    
    def load_classes(self):
        classes = self.db.get_all_classes()
        self.class_list = [''] + [c['class_name'] for c in classes]
        self.class_combo['values'] = self.class_list
        if self.class_list:
            self.class_combo.current(0)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="选择实验报告文件夹")
        if folder:
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
    
    def preview(self):
        """预览重命名结果"""
        folder = self.folder_entry.get().strip()
        class_name = self.class_combo.get().strip()
        
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请选择有效的文件夹")
            return
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert(tk.END, f"[预览模式]\n")
        self.result_text.insert(tk.END, f"文件夹: {folder}\n")
        self.result_text.insert(tk.END, f"班级: {class_name or '不限'}\n\n")
        
        # 获取学生信息
        students = self.db.get_students_by_class(class_name) if class_name else []
        student_map = {s['student_id']: s for s in students}
        name_map = {s['name']: s for s in students}
        
        # 扫描文件
        files = list(Path(folder).glob("*.docx")) + list(Path(folder).glob("*.doc"))
        
        if not files:
            self.result_text.insert(tk.END, "文件夹中没有找到docx文件\n")
            return
        
        self.result_text.insert(tk.END, f"找到 {len(files)} 个文件:\n")
        self.result_text.insert(tk.END, "-" * 60 + "\n")
        
        idx = 1
        for f in files:
            reader = DocxReader(str(f))
            info = reader.extract_all_info()
            
            student_id = info.get('student_id')
            name = info.get('name')
            
            # 尝试匹配
            matched = student_map.get(student_id) if student_id else None
            if not matched and name:
                matched = name_map.get(name)
            
            if matched:
                sid = matched['student_id']
                nm = matched['name']
            else:
                sid = student_id or '未知'
                nm = name or '未知'
            
            new_name = f"{sid}{nm}实验报告{int_to_chinese(idx)}.docx"
            self.result_text.insert(tk.END, f"  {f.name}\n")
            self.result_text.insert(tk.END, f"  -> {new_name}\n\n")
            idx += 1
    
    def start_rename(self):
        """开始重命名"""
        folder = self.folder_entry.get().strip()
        class_name = self.class_combo.get().strip()
        
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("提示", "请选择有效的文件夹")
            return
        
        if not messagebox.askyesno("确认", "确定要重命名这些文件吗？"):
            return
        
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert(tk.END, "[正在处理...]\n\n")
        
        # 获取学生信息
        students = self.db.get_students_by_class(class_name) if class_name else []
        student_map = {s['student_id']: s for s in students}
        name_map = {s['name']: s for s in students}
        
        # 扫描并处理文件
        files = list(Path(folder).glob("*.docx")) + list(Path(folder).glob("*.doc"))
        
        success, skipped, errors = 0, 0, 0
        idx = 1
        
        for f in files:
            reader = DocxReader(str(f))
            info = reader.extract_all_info()
            
            student_id = info.get('student_id')
            name = info.get('name')
            
            # 匹配
            matched = student_map.get(student_id) if student_id else None
            if not matched and name:
                matched = name_map.get(name)
            
            if matched:
                sid = matched['student_id']
                nm = matched['name']
            else:
                sid = student_id or '未知'
                nm = name or '未知'
            
            new_name = f"{sid}{nm}实验报告{int_to_chinese(idx)}{f.suffix}"
            new_path = f.parent / new_name
            
            # 处理冲突
            if new_path.exists() and new_path != f:
                base = new_path.stem
                counter = 1
                while new_path.exists():
                    new_name = f"{base}_{counter}{f.suffix}"
                    new_path = f.parent / new_name
                    counter += 1
            
            try:
                if new_path != f:
                    import shutil
                    shutil.move(str(f), str(new_path))
                    self.result_text.insert(tk.END, f"[OK] {f.name}\n")
                    self.result_text.insert(tk.END, f"    -> {new_path.name}\n\n")
                    success += 1
                else:
                    skipped += 1
                idx += 1
            except Exception as e:
                errors += 1
                self.result_text.insert(tk.END, f"[X] {f.name}: {str(e)}\n")
        
        self.result_text.insert(tk.END, "-" * 60 + "\n")
        self.result_text.insert(tk.END, f"完成: 成功 {success}, 跳过 {skipped}, 失败 {errors}\n")
        
        messagebox.showinfo("完成", f"处理完成！\n成功: {success}\n跳过: {skipped}\n失败: {errors}")
    
    def show(self):
        self.frame.pack(fill='both', expand=True)
        self.load_classes()
    
    def hide(self):
        self.frame.pack_forget()


class MainApp:
    """主程序"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("实验报告收缴管理系统 v2")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)
        
        # 初始化数据库
        self.db = StudentDB()
        
        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 创建主容器
        self.main_container = tk.Frame(self.root, bg='#f0f0f0')
        self.main_container.pack(fill='both', expand=True)
        
        # 创建各个界面
        self.student_manager = StudentManagerGUI(self.main_container, self.db, self)
        self.renamer = RenamerGUI(self.main_container, self.db)
        
        # 显示学生管理界面
        self.show_student_manager()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def show_student_manager(self):
        self.renamer.hide()
        self.student_manager.show()
        self.update_title("学生信息管理")
    
    def show_renamer(self):
        self.student_manager.hide()
        self.renamer.show()
        self.update_title("批量重命名")
    
    def update_title(self, subtitle=""):
        title = "实验报告收缴管理系统 v2"
        if subtitle:
            title = f"{title} - {subtitle}"
        self.root.title(title)
    
    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self.db.close()
            self.root.destroy()
    
    def run(self):
        self.root.mainloop()


def main():
    app = MainApp()
    app.run()


if __name__ == "__main__":
    main()
