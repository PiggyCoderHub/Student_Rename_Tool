#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
班级学生管理与文件重命名工具 - 分模块设计
直接双击“启动程序.bat”运行
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import re
import shutil
import io


# Windows console encoding compatibility. GUI text uses UTF-8 source strings; console output is only for debugging.
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 颜色配置
DARK_BLUE = "#1a365d"
MID_BLUE = "#2c5282"
LIGHT_BLUE = "#4299e1"
WHITE = "#ffffff"
LIGHT_GRAY = "#f7fafc"
BORDER = "#e2e8f0"
GREEN = "#008000"  # 匹配成功颜色
RED = "#FF0000"    # 未匹配颜色

# ==================== 主应用类 ====================
class App:
    def __init__(self):
        self.root = tk.Tk()
        # 统一使用中文字体，减少界面文字显示成方块或乱码的情况
        try:
            from tkinter import font
            for font_name in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
                try:
                    font.nametofont(font_name).configure(family="Microsoft YaHei")
                except Exception:
                    pass
            self.root.option_add("*Font", "{Microsoft YaHei} 10")
        except Exception:
            pass
        self.root.title("班级学生管理与文件重命名工具")
        self.root.geometry("1000x700")
        self.root.configure(bg=DARK_BLUE)
        
        # 设置窗口最小尺寸
        self.root.minsize(800, 600)
        
        from student_db import StudentDB
        self.db = StudentDB()
        
        self.setup_ui()
        
    def setup_ui(self):
        # 标题
        title_frame = tk.Frame(self.root, bg=DARK_BLUE, height=50)
        title_frame.pack(fill=tk.X, padx=20, pady=(15, 10))
        tk.Label(title_frame, text="班级学生管理与文件重命名工具", 
                font=("Microsoft YaHei", 18, "bold"), 
                fg=WHITE, bg=DARK_BLUE).pack(side=tk.LEFT)
        
        # 底部状态栏
        self.status_label = tk.Label(self.root, text="就绪", 
                                     font=("Microsoft YaHei", 9),
                                     bg=DARK_BLUE, fg=WHITE, anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        # 创建笔记本（分页面）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # 创建三个页面
        self.page1 = ClassManagePage(self.notebook, self.db, self)
        self.page2 = StudentManagePage(self.notebook, self.db, self)
        self.page3 = FileRenamePage(self.notebook, self.db, self)
        
        self.notebook.add(self.page1.frame, text="班级管理")
        self.notebook.add(self.page2.frame, text="学生管理")
        self.notebook.add(self.page3.frame, text="文件重命名")
        
        # 绑定全局鼠标滚轮事件，支持页面内滚动
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    
    def _on_mousewheel(self, event):
        """全局鼠标滚轮事件处理"""
        # 获取当前活动页面
        current = self.notebook.select()
        if not current:
            return
        
        # 查找对应的页面对象
        for page in [self.page1, self.page2, self.page3]:
            if str(page.frame) == current:
                if hasattr(page, 'canvas'):
                    page.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                break
    
    def _on_tab_changed(self, event):
        """页面切换时更新滚动区域"""
        current = self.notebook.select()
        for page in [self.page1, self.page2, self.page3]:
            if hasattr(page, 'canvas') and hasattr(page, 'scrollable_frame'):
                if str(page.frame) == current:
                    page.canvas.configure(scrollregion=page.canvas.bbox("all"))
                    break
        
    def status(self, msg):
        self.status_label.config(text=msg)
    
    def run(self):
        self.root.mainloop()

# ==================== 班级管理页面 ====================
class ClassManagePage:
    def __init__(self, parent, db, app):
        self.db = db
        self.app = app
        self.frame = tk.Frame(parent, bg=LIGHT_GRAY)
        
        # 创建滚动画布
        self.canvas = tk.Canvas(self.frame, bg=LIGHT_GRAY, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=LIGHT_GRAY)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 顶部操作区
        top_frame = tk.Frame(self.scrollable_frame, bg=WHITE, padx=20, pady=15)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="班级名称:", font=("Microsoft YaHei", 11),
                bg=WHITE, fg=DARK_BLUE).pack(side=tk.LEFT)
        
        self.name_entry = tk.Entry(top_frame, width=25, font=("Microsoft YaHei", 11))
        self.name_entry.pack(side=tk.LEFT, padx=10)
        
        tk.Button(top_frame, text="添加班级", command=self.add_class,
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=15, pady=5,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="刷新列表", command=self.refresh,
                 bg="gray", fg=WHITE, relief=tk.FLAT, padx=15, pady=5,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=5)
        
        # 班级列表区
        list_container = tk.Frame(self.scrollable_frame, bg=WHITE)
        list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 表头
        header = tk.Frame(list_container, bg=MID_BLUE)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="序号", width=8, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=1)
        tk.Label(header, text="班级名称", width=30, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=1)
        tk.Label(header, text="学生人数", width=15, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=1)
        tk.Label(header, text="创建时间", width=20, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=1)
        tk.Label(header, text="操作", width=20, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=1)
        
        # 列表内容
        self.list_frame = tk.Frame(list_container, bg=WHITE)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.refresh()
        
    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        classes = self.db.get_all_classes()
        
        if not classes:
            tk.Label(self.list_frame, text="暂无班级，请添加", 
                    bg=WHITE, fg="gray", font=("Microsoft YaHei", 10)).pack(pady=30)
            return
        
        for i, cls in enumerate(classes):
            row = tk.Frame(self.list_frame, bg=WHITE if i % 2 == 0 else LIGHT_GRAY)
            row.pack(fill=tk.X)
            
            tk.Label(row, text=str(i+1), width=8, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=1)
            tk.Label(row, text=cls["class_name"], width=30, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=1)
            tk.Label(row, text=str(cls.get("student_count", 0)), width=15, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=1)
            tk.Label(row, text=cls.get("created_at", "")[:19] if cls.get("created_at") else "",
                    width=20, bg=row.cget("bg"), font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=1)
            
            btn_frame = tk.Frame(row, bg=row.cget("bg"))
            btn_frame.pack(side=tk.LEFT, padx=1)
            
            tk.Button(btn_frame, text="编辑", command=lambda c=cls: self.edit_class(c),
                     bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=10,
                     font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="删除", command=lambda c=cls: self.delete_class(c),
                     bg="#e53e3e", fg=WHITE, relief=tk.FLAT, padx=10,
                     font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
    
    def add_class(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入班级名称")
            return
        
        success, msg = self.db.add_class(name)
        if success:
            self.name_entry.delete(0, tk.END)
            self.refresh()
            self.app.status(f"班级 '{name}' 添加成功")
        else:
            messagebox.showerror("错误", msg)
    
    def edit_class(self, cls):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("编辑班级")
        dialog.geometry("300x120")
        dialog.configure(bg=WHITE)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="班级名称:", font=("Microsoft YaHei", 10),
                bg=WHITE).pack(pady=(20, 5))
        
        name_var = tk.StringVar(value=cls["class_name"])
        tk.Entry(dialog, textvariable=name_var, width=25,
                font=("Microsoft YaHei", 10)).pack(pady=5)
        
        def save():
            new_name = name_var.get().strip()
            if new_name and new_name != cls["class_name"]:
                cursor = self.db.conn.cursor()
                cursor.execute("UPDATE classes SET class_name = ? WHERE id = ?",
                             (new_name, cls["id"]))
                self.db.conn.commit()
                self.refresh()
                self.app.page2.refresh()
            dialog.destroy()
        
        tk.Button(dialog, text="保存", command=save, bg=MID_BLUE, fg=WHITE,
                 relief=tk.FLAT, padx=20, font=("Microsoft YaHei", 10)).pack(pady=10)
    
    def delete_class(self, cls):
        if messagebox.askyesno("确认", f"确定删除班级「{cls['class_name']}」？"):
            success, msg = self.db.delete_class(cls["class_name"])
            if success:
                self.refresh()
                self.app.page2.refresh()
                self.app.status("班级已删除")

# ==================== 学生管理页面 ====================
class StudentManagePage:
    def __init__(self, parent, db, app):
        self.db = db
        self.app = app
        self.selected_students = set()
        self.current_class = None
        self.all_student_ids = []
        self.frame = tk.Frame(parent, bg=LIGHT_GRAY)
        
        # 创建滚动画布
        self.canvas = tk.Canvas(self.frame, bg=LIGHT_GRAY, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=LIGHT_GRAY)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 顶部筛选区
        filter_frame = tk.Frame(self.scrollable_frame, bg=WHITE, padx=20, pady=10)
        filter_frame.pack(fill=tk.X)
        
        tk.Label(filter_frame, text="筛选班级:", font=("Microsoft YaHei", 10),
                bg=WHITE, fg=DARK_BLUE).pack(side=tk.LEFT)
        
        self.class_var = tk.StringVar()
        self.class_combo = ttk.Combobox(filter_frame, textvariable=self.class_var, 
                                        state="readonly", width=20, font=("Microsoft YaHei", 10))
        self.class_combo.pack(side=tk.LEFT, padx=10)
        self.class_combo.bind("<<ComboboxSelected>>", self.on_class_changed)
        
        tk.Button(filter_frame, text="添加学生", command=self.add_student,
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=15, pady=3,
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=20)
        
        tk.Button(filter_frame, text="删除选中", command=self.delete_selected,
                 bg="#e53e3e", fg=WHITE, relief=tk.FLAT, padx=15, pady=3,
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(filter_frame, text="分配班级", command=self.assign_class,
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=15, pady=3,
                 font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(filter_frame, text="全选", command=self.select_all,
                bg="gray", fg=WHITE, relief=tk.FLAT, padx=12, pady=3,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(20, 5))
        
        tk.Button(filter_frame, text="取消", command=self.deselect_all,
                bg="gray", fg=WHITE, relief=tk.FLAT, padx=12, pady=3,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        
        # 批量从Excel导入按钮（绿色醒目按钮）
        tk.Button(filter_frame, text="批量从Excel导入", command=self.import_from_excel,
                bg="#38a169", fg=WHITE, relief=tk.FLAT, padx=15, pady=3,
                font=("Microsoft YaHei", 9, "bold")).pack(side=tk.LEFT, padx=(30, 5))
        
        # 列表区
        list_container = tk.Frame(self.scrollable_frame, bg=WHITE)
        list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 表头
        header = tk.Frame(list_container, bg=MID_BLUE)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="", width=3, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Label(header, text="学号", width=18, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Label(header, text="姓名", width=12, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Label(header, text="班级", width=20, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Label(header, text="操作", width=18, bg=MID_BLUE, fg=WHITE,
                font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        
        # 列表内容
        self.list_frame = tk.Frame(list_container, bg=WHITE)
        self.list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.load_classes()
        self.refresh()
        
    def load_classes(self):
        classes = self.db.get_all_classes()
        class_list = ["全部学生"] + [c["class_name"] for c in classes]
        self.class_combo["values"] = class_list
        if class_list:
            self.class_combo.current(0)
    
    def on_class_changed(self, event=None):
        selected = self.class_var.get()
        self.current_class = None if selected == "全部学生" else selected
        self.refresh()
    
    def refresh(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        self.selected_students = set()
        self.all_student_ids = []
        
        if self.current_class:
            students = self.db.get_students_by_class(self.current_class)
        else:
            students = self.db.get_all_students()
        
        if not students:
            tk.Label(self.list_frame, text="暂无学生，请添加或切换班级筛选",
                    bg=WHITE, fg="gray", font=("Microsoft YaHei", 10)).pack(pady=30)
            return
        
        for i, stu in enumerate(students):
            self.all_student_ids.append(stu["student_id"])
            row = tk.Frame(self.list_frame, bg=WHITE if i % 2 == 0 else LIGHT_GRAY)
            row.pack(fill=tk.X)
            
            var = tk.BooleanVar()
            cb = tk.Checkbutton(row, variable=var, bg=row.cget("bg"),
                               command=lambda s=stu, v=var: self.toggle_student(s, v))
            cb.pack(side=tk.LEFT, padx=5)
            
            tk.Label(row, text=stu["student_id"], width=18, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
            tk.Label(row, text=stu["name"], width=12, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
            class_name = stu.get("class_name") or "未分配"
            tk.Label(row, text=class_name, width=20, bg=row.cget("bg"),
                    font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
            
            btn_frame = tk.Frame(row, bg=row.cget("bg"))
            btn_frame.pack(side=tk.LEFT)
            
            tk.Button(btn_frame, text="编辑", command=lambda s=stu: self.edit_student(s),
                     bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=8,
                     font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="删除", command=lambda s=stu: self.delete_student(s),
                     bg="#e53e3e", fg=WHITE, relief=tk.FLAT, padx=8,
                     font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
    
    def toggle_student(self, stu, var):
        if var.get():
            self.selected_students.add(stu["student_id"])
        else:
            self.selected_students.discard(stu["student_id"])
    
    def select_all(self):
        for widget in self.list_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Checkbutton):
                    child.select()
        self.selected_students = set(self.all_student_ids)
    
    def deselect_all(self):
        for widget in self.list_frame.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Checkbutton):
                    child.deselect()
        self.selected_students = set()
    
    def add_student(self):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("添加学生")
        dialog.geometry("400x280")
        dialog.configure(bg=WHITE)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        # 居中
        dialog.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 400) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 280) // 2
        dialog.geometry(f"400x280+{x}+{y}")
        
        fields = [("学号:", 30), ("姓名:", 90), ("班级:", 150)]
        entries = {}
        
        for text, y_pos in fields:
            tk.Label(dialog, text=text, font=("Microsoft YaHei", 10),
                    bg=WHITE).place(x=60, y=y_pos)
            entries[text] = tk.Entry(dialog, width=22, font=("Microsoft YaHei", 10))
            entries[text].place(x=130, y=y_pos)
        
        tk.Label(dialog, text="班级:", font=("Microsoft YaHei", 10),
                bg=WHITE).place(x=60, y=150)
        
        class_var = tk.StringVar()
        class_combo = ttk.Combobox(dialog, textvariable=class_var, 
                                   state="readonly", width=20, font=("Microsoft YaHei", 10))
        class_combo.place(x=130, y=150)
        
        classes = self.db.get_all_classes()
        class_combo["values"] = ["不分配"] + [c["class_name"] for c in classes]
        class_combo.current(0)
        
        def save():
            student_id = entries["学号:"].get().strip()
            name = entries["姓名:"].get().strip()
            class_name = class_var.get()
            
            if not student_id or not name:
                messagebox.showwarning("提示", "请填写学号和姓名")
                return
            
            class_param = None if class_name == "不分配" else class_name
            success, msg = self.db.add_student(student_id, name, class_param)
            
            if success:
                self.refresh()
                dialog.destroy()
                self.app.status(f"已添加学生: {name}")
            else:
                messagebox.showerror("错误", msg)
        
        tk.Button(dialog, text="保存", command=save, bg=MID_BLUE, fg=WHITE,
                 relief=tk.FLAT, padx=25, font=("Microsoft YaHei", 10)).place(x=150, y=200)
    
    def edit_student(self, stu):
        dialog = tk.Toplevel(self.app.root)
        dialog.title("编辑学生")
        dialog.geometry("400x280")
        dialog.configure(bg=WHITE)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 400) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 280) // 2
        dialog.geometry(f"400x280+{x}+{y}")
        
        # 提前保存原始数据
        original_student_id = stu["student_id"]
        original_name = stu["name"]
        original_id = stu["id"]  # 数据库唯一ID，用于精确定位
        
        # 创建 Entry 组件并存储为对话框属性
        id_entry = tk.Entry(dialog, width=22, font=("Microsoft YaHei", 10))
        name_entry = tk.Entry(dialog, width=22, font=("Microsoft YaHei", 10))
        
        tk.Label(dialog, text="学号:", font=("Microsoft YaHei", 10), bg=WHITE).place(x=60, y=30)
        id_entry.place(x=130, y=30)
        tk.Label(dialog, text="姓名:", font=("Microsoft YaHei", 10), bg=WHITE).place(x=60, y=90)
        name_entry.place(x=130, y=90)
        
        # 填充原始值
        id_entry.insert(0, original_student_id)
        name_entry.insert(0, original_name)
        
        tk.Label(dialog, text="班级:", font=("Microsoft YaHei", 10), bg=WHITE).place(x=60, y=150)
        
        class_var = tk.StringVar()
        class_combo = ttk.Combobox(dialog, textvariable=class_var, 
                                   state="readonly", width=20, font=("Microsoft YaHei", 10))
        class_combo.place(x=130, y=150)
        
        classes = self.db.get_all_classes()
        class_combo["values"] = ["不分配"] + [c["class_name"] for c in classes]
        class_combo.set(stu.get("class_name") or "不分配")
        
        def save():
            # 使用局部变量捕获当前值
            new_id = id_entry.get().strip()
            new_name = name_entry.get().strip()
            class_name = class_var.get()
            
            if not new_id or not new_name:
                messagebox.showwarning("提示", "请填写学号和姓名")
                return
            
            # 更新数据库，使用数据库唯一ID精确定位
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT id FROM classes WHERE class_name = ?", (class_name,))
            row = cursor.fetchone()
            class_id = row["id"] if row else None
            
            cursor.execute("""UPDATE students SET student_id = ?, name = ?, class_id = ? 
                            WHERE id = ?""",
                          (new_id, new_name, class_id, original_id))
            self.db.conn.commit()
            
            self.refresh()
            dialog.destroy()
            self.app.status("学生信息已更新")
        
        tk.Button(dialog, text="保存", command=save, bg=MID_BLUE, fg=WHITE,
                 relief=tk.FLAT, padx=25, font=("Microsoft YaHei", 10)).place(x=150, y=200)
    
    def delete_student(self, stu):
        if messagebox.askyesno("确认", f"确定删除学生「{stu['name']}」？"):
            success, msg = self.db.delete_student(stu["student_id"])
            if success:
                self.refresh()
                self.app.status("学生已删除")
    
    def delete_selected(self):
        if not self.selected_students:
            messagebox.showwarning("提示", "请勾选要删除的学生")
            return
        
        if messagebox.askyesno("确认", f"确定删除选中的 {len(self.selected_students)} 名学生？"):
            deleted, errors = self.db.delete_students_batch(list(self.selected_students))
            self.selected_students = set()
            self.refresh()
            self.app.status(f"已删除 {deleted} 名学生")
    
    def assign_class(self):
        if not self.selected_students:
            messagebox.showwarning("提示", "请勾选要分配班级的学生")
            return
        
        dialog = tk.Toplevel(self.app.root)
        dialog.title("分配班级")
        dialog.geometry("300x150")
        dialog.configure(bg=WHITE)
        dialog.transient(self.app.root)
        dialog.grab_set()
        
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - 300) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - 150) // 2
        dialog.geometry(f"300x150+{x}+{y}")
        
        tk.Label(dialog, text=f"为 {len(self.selected_students)} 名学生分配班级:",
                font=("Microsoft YaHei", 10), bg=WHITE).pack(pady=15)
        
        class_var = tk.StringVar()
        class_combo = ttk.Combobox(dialog, textvariable=class_var, 
                                   state="readonly", width=20, font=("Microsoft YaHei", 10))
        class_combo.pack(pady=10)
        
        classes = self.db.get_all_classes()
        class_combo["values"] = [c["class_name"] for c in classes]
        if classes:
            class_combo.current(0)
        
        def save():
            class_name = class_var.get()
            if class_name:
                updated, errors = self.db.assign_class_batch(list(self.selected_students), class_name)
                self.selected_students = set()
                self.refresh()
                dialog.destroy()
                self.app.status(f"已将 {updated} 名学生分配到 {class_name}")
        
        tk.Button(dialog, text="确认分配", command=save, bg=MID_BLUE, fg=WHITE,
                 relief=tk.FLAT, padx=20, font=("Microsoft YaHei", 10)).pack(pady=10)
    
    def import_from_excel(self):
        """批量从Excel/CSV文件导入学生 - 修复版"""
        filepath = filedialog.askopenfilename(
            title="选择学生名单文件",
            filetypes=[("学生名单", "*.xlsx *.xlsm *.csv"), ("Excel文件", "*.xlsx *.xlsm"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not filepath:
            return

        try:
            from excel_importer import SmartExcelImporter
            importer = SmartExcelImporter(filepath)
            ok, msg = importer.load_file()
            if not ok:
                messagebox.showerror("导入失败", msg)
                return

            valid, info = importer.validate_data()
            students_data = importer.get_students()
            if not students_data:
                detail = "\n".join(info[:8]) if info else "请检查文件中是否包含学号和姓名。"
                messagebox.showerror("导入失败", f"没有找到有效的学生数据。\n\n{detail}")
                return

            self.show_import_preview(filepath, students_data, importer)
        except Exception as e:
            messagebox.showerror("错误", f"读取名单失败：{e}")

    def show_import_preview(self, filepath, students_data, importer=None):
        """显示导入预览窗口：支持勾选、全选、全不选、反选后再导入。"""
        from collections import Counter

        preview_win = tk.Toplevel(self.app.root)
        preview_win.title("批量导入学生 - 勾选确认")
        win_w, win_h = 920, 640
        preview_win.geometry(f"{win_w}x{win_h}")
        preview_win.configure(bg=WHITE)
        preview_win.transient(self.app.root)
        preview_win.grab_set()

        # 居中
        preview_win.update_idletasks()
        x = self.app.root.winfo_x() + (self.app.root.winfo_width() - win_w) // 2
        y = self.app.root.winfo_y() + (self.app.root.winfo_height() - win_h) // 2
        preview_win.geometry(f"{win_w}x{win_h}+{x}+{y}")

        sid_counts = Counter(str(stu.get('student_id', '')).strip() for stu in students_data)

        info_frame = tk.Frame(preview_win, bg=WHITE, padx=20, pady=10)
        info_frame.pack(fill=tk.X)

        tk.Label(info_frame, text=f"文件: {os.path.basename(filepath)}",
                font=("Microsoft YaHei", 10), bg=WHITE).pack(anchor=tk.W)
        tk.Label(info_frame, text=f"识别到 {len(students_data)} 名学生，请在左侧“是否导入”列确认，只有显示“是”的学生才会写入系统。",
                font=("Microsoft YaHei", 10), bg=WHITE, fg="#2f855a", wraplength=860, justify=tk.LEFT).pack(anchor=tk.W, pady=(3, 0))
        tk.Label(info_frame, text="操作提示：默认已全选；单击某一行最左侧“是否导入”可切换；也可以使用下方“全选 / 全不选 / 反选”。",
                font=("Microsoft YaHei", 9), bg=WHITE, fg="#4a5568", wraplength=860, justify=tk.LEFT).pack(anchor=tk.W, pady=(2, 0))

        if importer:
            col_info = importer.get_column_info()
            if col_info.get('detected_columns'):
                col_text = "，".join([f"{k}=第{v+1}列" for k, v in sorted(col_info['detected_columns'].items(), key=lambda x: x[1])])
                tk.Label(info_frame, text=f"识别字段: {col_text}",
                        font=("Microsoft YaHei", 9), bg=WHITE, fg="gray", wraplength=860, justify=tk.LEFT).pack(anchor=tk.W)
            if col_info.get('warnings'):
                warning_text = "；".join(col_info['warnings'][:3])
                tk.Label(info_frame, text=f"提示: {warning_text}",
                        font=("Microsoft YaHei", 9), bg=WHITE, fg="#b7791f", wraplength=860, justify=tk.LEFT).pack(anchor=tk.W)

        class_frame = tk.Frame(preview_win, bg=WHITE, padx=20, pady=8)
        class_frame.pack(fill=tk.X)

        tk.Label(class_frame, text="导入到班级:", font=("Microsoft YaHei", 10), bg=WHITE).pack(side=tk.LEFT)

        class_var = tk.StringVar()
        class_combo = ttk.Combobox(class_frame, textvariable=class_var,
                                   state="readonly", width=28, font=("Microsoft YaHei", 10))
        class_combo.pack(side=tk.LEFT, padx=10)

        classes = self.db.get_all_classes()
        class_combo["values"] = ["按表格班级/不指定"] + [c["class_name"] for c in classes]
        class_combo.current(0)
        tk.Label(class_frame, text="选择具体班级会覆盖表格中的班级列。",
                font=("Microsoft YaHei", 9), bg=WHITE, fg="gray").pack(side=tk.LEFT, padx=8)

        list_frame = tk.Frame(preview_win, bg=WHITE)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 8))

        columns = ("select", "idx", "row", "sid", "name", "class", "status")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=17)
        tree.heading("select", text="是否导入")
        tree.heading("idx", text="序号")
        tree.heading("row", text="表格行")
        tree.heading("sid", text="学号")
        tree.heading("name", text="姓名")
        tree.heading("class", text="班级")
        tree.heading("status", text="导入状态")
        tree.column("select", width=80, anchor=tk.CENTER, stretch=False)
        tree.column("idx", width=55, anchor=tk.CENTER, stretch=False)
        tree.column("row", width=70, anchor=tk.CENTER, stretch=False)
        tree.column("sid", width=160, anchor=tk.CENTER)
        tree.column("name", width=110, anchor=tk.CENTER)
        tree.column("class", width=160, anchor=tk.CENTER)
        tree.column("status", width=210, anchor=tk.W)
        tree.tag_configure("checked", background="#f0fff4")
        tree.tag_configure("unchecked", background="#edf2f7")
        tree.tag_configure("duplicate", background="#fffaf0")

        yscroll = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        selected_indices = set(range(len(students_data)))  # 默认全选，方便直接导入
        item_by_index = {}

        def build_status(stu, index):
            sid = str(stu.get('student_id', '')).strip()
            parts = []
            try:
                existing = self.db.get_student_by_id(sid)
            except Exception:
                existing = None
            parts.append("更新已有" if existing else "新增")
            if sid and sid_counts.get(sid, 0) > 1:
                parts.append("名单内重复")
            return "；".join(parts)

        def row_values(index):
            stu = students_data[index]
            return (
                "是" if index in selected_indices else "否",
                index + 1,
                stu.get('_row_num', ''),
                stu.get('student_id', ''),
                stu.get('name', ''),
                stu.get('class_name', '') or '',
                build_status(stu, index),
            )

        for i, stu in enumerate(students_data):
            tags = ["checked"]
            sid = str(stu.get('student_id', '')).strip()
            if sid and sid_counts.get(sid, 0) > 1:
                tags.append("duplicate")
            item_id = tree.insert("", "end", values=row_values(i), tags=tuple(tags))
            item_by_index[i] = item_id

        count_var = tk.StringVar()

        def refresh_count():
            count_var.set(f"已选择 {len(selected_indices)} / {len(students_data)} 名学生")

        def refresh_row(index):
            item_id = item_by_index[index]
            sid = str(students_data[index].get('student_id', '')).strip()
            if index in selected_indices:
                tags = ["checked"]
            else:
                tags = ["unchecked"]
            if sid and sid_counts.get(sid, 0) > 1:
                tags.append("duplicate")
            tree.item(item_id, values=row_values(index), tags=tuple(tags))

        def toggle_index(index):
            if index in selected_indices:
                selected_indices.remove(index)
            else:
                selected_indices.add(index)
            refresh_row(index)
            refresh_count()

        def on_tree_click(event):
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if not row_id or col_id != "#1":
                return
            for idx, item_id in item_by_index.items():
                if item_id == row_id:
                    toggle_index(idx)
                    break

        tree.bind("<ButtonRelease-1>", on_tree_click)

        select_frame = tk.Frame(preview_win, bg=WHITE, padx=20, pady=4)
        select_frame.pack(fill=tk.X)

        tk.Label(select_frame, textvariable=count_var,
                font=("Microsoft YaHei", 10, "bold"), bg=WHITE, fg="#2c5282").pack(side=tk.LEFT)

        def set_all(value):
            if value:
                selected_indices.update(range(len(students_data)))
            else:
                selected_indices.clear()
            for idx in range(len(students_data)):
                refresh_row(idx)
            refresh_count()

        def do_invert_selection():
            current = set(selected_indices)
            selected_indices.clear()
            selected_indices.update(set(range(len(students_data))) - current)
            for idx in range(len(students_data)):
                refresh_row(idx)
            refresh_count()

        tk.Button(select_frame, text="全选", command=lambda: set_all(True),
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=18, pady=5,
                 font=("Microsoft YaHei", 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(select_frame, text="全不选", command=lambda: set_all(False),
                 bg="#718096", fg=WHITE, relief=tk.FLAT, padx=18, pady=5,
                 font=("Microsoft YaHei", 10)).pack(side=tk.RIGHT, padx=5)
        tk.Button(select_frame, text="反选", command=do_invert_selection,
                 bg="#805ad5", fg=WHITE, relief=tk.FLAT, padx=18, pady=5,
                 font=("Microsoft YaHei", 10)).pack(side=tk.RIGHT, padx=5)

        refresh_count()

        btn_frame = tk.Frame(preview_win, bg=WHITE, pady=12)
        btn_frame.pack(fill=tk.X)

        def do_import():
            if not selected_indices:
                messagebox.showwarning("未选择学生", "请至少勾选一名需要导入的学生。")
                return

            selected_students = [students_data[i] for i in range(len(students_data)) if i in selected_indices]
            if not messagebox.askyesno("确认导入", f"确定只导入已选择的 {len(selected_students)} 名学生吗？\n\n未选择的学生不会写入系统。"):
                return

            class_name = class_var.get()
            target_class = None if class_name == "按表格班级/不指定" else class_name

            success, failed, errors = self.db.add_student_batch(selected_students, target_class)
            preview_win.destroy()
            self.load_classes()
            self.refresh()
            try:
                self.app.page1.refresh()
                self.app.page3.load_classes()
            except Exception:
                pass
            self.app.status(f"导入完成：已选择 {len(selected_students)} 名，成功/更新 {success} 名，失败 {failed} 名")
            detail = ""
            if errors:
                detail = "\n\n部分问题：\n" + "\n".join(errors[:8])
            messagebox.showinfo("导入完成", f"已选择: {len(selected_students)} 名\n成功/更新: {success} 名\n失败: {failed} 名{detail}")

        tk.Button(btn_frame, text="确认导入已选择", command=do_import,
                 bg="#38a169", fg=WHITE, relief=tk.FLAT, padx=30, pady=8,
                 font=("Microsoft YaHei", 11, "bold")).pack(side=tk.LEFT, padx=20)

        tk.Button(btn_frame, text="取消", command=preview_win.destroy,
                 bg="gray", fg=WHITE, relief=tk.FLAT, padx=30, pady=8,
                 font=("Microsoft YaHei", 11)).pack(side=tk.LEFT)

# ==================== 文件重命名页面 ====================
class FileRenamePage:
    def __init__(self, parent, db, app):
        self.db = db
        self.app = app
        self.frame = tk.Frame(parent, bg=LIGHT_GRAY)
        self.rename_map = []  # 存储重命名映射
        self.deep_match_stage = 0  # 深度匹配阶段: 0=未执行, 1=文件名匹配, 2=内容深度匹配
        
        # 创建滚动画布
        self.canvas = tk.Canvas(self.frame, bg=LIGHT_GRAY, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=LIGHT_GRAY)
        
        def on_frame_configure(e):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            canvas_width = self.canvas.winfo_width()
            if canvas_width > 1:
                self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.scrollable_frame.bind("<Configure>", on_frame_configure)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 内容框架
        content = tk.Frame(self.scrollable_frame, bg=LIGHT_GRAY)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # 输入文件夹区
        input_frame = tk.Frame(content, bg=WHITE, padx=20, pady=15)
        input_frame.pack(fill=tk.X)
        
        tk.Label(input_frame, text="1. 选择源文件夹 (原始文件):", 
                font=("Microsoft YaHei", 11, "bold"),
                bg=WHITE, fg=DARK_BLUE).pack(anchor=tk.W)
        
        path_frame = tk.Frame(input_frame, bg=WHITE)
        path_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.input_path = tk.StringVar()
        tk.Entry(path_frame, textvariable=self.input_path, width=50,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(path_frame, text="浏览", command=self.browse_input,
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=15,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=10)
        
        # 输出文件夹区
        output_frame = tk.Frame(content, bg=WHITE, padx=20, pady=15)
        output_frame.pack(fill=tk.X)
        
        tk.Label(output_frame, text="2. 选择输出文件夹 (重命名后文件):", 
                font=("Microsoft YaHei", 11, "bold"),
                bg=WHITE, fg=DARK_BLUE).pack(anchor=tk.W)
        
        path_frame2 = tk.Frame(output_frame, bg=WHITE)
        path_frame2.pack(fill=tk.X, pady=(10, 0))
        
        self.output_path = tk.StringVar()
        tk.Entry(path_frame2, textvariable=self.output_path, width=50,
                font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(path_frame2, text="浏览", command=self.browse_output,
                 bg=MID_BLUE, fg=WHITE, relief=tk.FLAT, padx=15,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=10)
        
        # 重命名格式区（新增）
        format_frame = tk.Frame(content, bg=WHITE, padx=20, pady=15)
        format_frame.pack(fill=tk.X)
        
        tk.Label(format_frame, text="3. 重命名格式模板:", 
                font=("Microsoft YaHei", 11, "bold"),
                bg=WHITE, fg=DARK_BLUE).pack(anchor=tk.W)
        
        format_desc = tk.Label(format_frame, 
                text="可用变量: {学号} {姓名} | 示例: {学号}{姓名}实验报告一", 
                font=("Microsoft YaHei", 9),
                bg=WHITE, fg="gray")
        format_desc.pack(anchor=tk.W, pady=(5, 5))
        
        format_input_frame = tk.Frame(format_frame, bg=WHITE)
        format_input_frame.pack(fill=tk.X)
        
        self.format_var = tk.StringVar(value="{学号}{姓名}实验报告一")
        self.format_entry = tk.Entry(format_input_frame, textvariable=self.format_var, width=40,
                font=("Microsoft YaHei", 10))
        self.format_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(format_input_frame, text="应用格式", command=self.apply_format,
                 bg="#805ad5", fg=WHITE, relief=tk.FLAT, padx=15,
                 font=("Microsoft YaHei", 10)).pack(side=tk.LEFT, padx=10)
        
        # 班级选择区
        class_frame = tk.Frame(content, bg=WHITE, padx=20, pady=15)
        class_frame.pack(fill=tk.X)
        
        tk.Label(class_frame, text="4. 选择班级:", 
                font=("Microsoft YaHei", 11, "bold"),
                bg=WHITE, fg=DARK_BLUE).pack(side=tk.LEFT)
        
        self.class_var = tk.StringVar()
        self.class_combo = ttk.Combobox(class_frame, textvariable=self.class_var, 
                                        state="readonly", width=25, font=("Microsoft YaHei", 10))
        self.class_combo.pack(side=tk.LEFT, padx=15)
        
        tk.Button(class_frame, text="扫描文件", command=self.scan_files,
                 bg=LIGHT_BLUE, fg=WHITE, relief=tk.FLAT, padx=15,
                 font=("Microsoft YaHei", 10, "bold")).pack(side=tk.LEFT, padx=15)
        
        # 深度匹配按钮（扫描后可见）
        self.deep_match_btn = tk.Button(class_frame, text="深度智能匹配", 
                                       command=self.deep_match,
                 bg="#805ad5", fg=WHITE, relief=tk.FLAT, padx=15,
                 font=("Microsoft YaHei", 10, "bold"))
        self.deep_match_btn.pack(side=tk.LEFT, padx=5)
        self.deep_match_btn.configure(state=tk.DISABLED)
        
        # 可拖动分割条区域
        self.split_frame = tk.Frame(content, bg=LIGHT_GRAY, height=8, cursor="sb_v_double_arrow")
        self.split_frame.pack(fill=tk.X, pady=(5, 5))
        self.split_frame.pack_propagate(False)
        
        # 分割条拖动功能
        self.preview_height = 250  # 初始预览高度
        self.split_dragging = False
        self._min_preview_height = 100
        self._max_preview_height = 600
        
        def on_split_press(event):
            self.split_dragging = True
            self._drag_start_y = event.y_root
            self._drag_start_height = self.split_frame.winfo_rooty() - self.frame.winfo_rooty()
        
        def on_split_drag(event):
            if self.split_dragging:
                current_y = event.y_root - self.frame.winfo_rooty()
                new_height = max(self._min_preview_height, min(self._max_preview_height, self.split_frame.winfo_rooty() - self.frame.winfo_rooty() + 4))
                self.preview_height = new_height
                # 更新内容框架高度约束
                content.configure(height=max(600, self.app.root.winfo_height() - 150))
        
        def on_split_release(event):
            self.split_dragging = False
        
        self.split_frame.bind("<ButtonPress-1>", on_split_press)
        self.split_frame.bind("<B1-Motion>", on_split_drag)
        self.split_frame.bind("<ButtonRelease-1>", on_split_release)
        
        # 窗口大小变化监听
        self.app.root.bind("<Configure>", self._on_window_resize)
        
        # 分割条装饰线
        handle = tk.Frame(self.split_frame, bg=MID_BLUE, height=4)
        handle.place(relx=0.5, y=2, anchor=tk.CENTER, width=100)
        
        # 预览/结果区（可调整高度，可随窗口拉伸）
        self.preview_section = tk.Frame(content, bg=WHITE)
        self.preview_section.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(self.preview_section, text="5. 预览结果 (拖动上方分割条调整高度):", 
                font=("Microsoft YaHei", 11, "bold"),
                bg=WHITE, fg=DARK_BLUE).pack(anchor=tk.W, pady=(10, 5), padx=15)
        
        # 预览列表容器（使用 Treeview 实现可调整列宽）
        preview_box = tk.Frame(self.preview_section, bg=WHITE)
        preview_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 5))
        
        # 创建Treeview表格
        columns = ("col0", "col1", "col2", "col3", "col4")
        self.preview_tree = ttk.Treeview(preview_box, columns=columns, show="headings", height=8)
        
        # 使用ttk Style配置Treeview，确保tag颜色生效
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Microsoft YaHei", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))
        
        # 配置tag样式（交替行颜色 + 匹配状态颜色）
        self.preview_tree.tag_configure("even", background="#ffffff")
        self.preview_tree.tag_configure("odd", background="#f7fafc")
        self.preview_tree.tag_configure("matched", foreground=GREEN, font=("Microsoft YaHei", 9))  # 绿色
        self.preview_tree.tag_configure("unmatched", foreground=RED, font=("Microsoft YaHei", 9, "bold"))  # 红色
        
        # 设置列标题
        self.preview_tree.heading("col0", text="序号")
        self.preview_tree.heading("col1", text="原文件名")
        self.preview_tree.heading("col2", text="→")
        self.preview_tree.heading("col3", text="新文件名")
        self.preview_tree.heading("col4", text="状态")
        
        # 设置列宽（使用权重使其可伸缩）
        self.preview_tree.column("col0", width=50, minwidth=40)
        self.preview_tree.column("col1", width=200, minwidth=100)
        self.preview_tree.column("col2", width=30, minwidth=30, stretch=False)
        self.preview_tree.column("col3", width=200, minwidth=100)
        self.preview_tree.column("col4", width=120, minwidth=80)
        
        # 添加滚动条
        ysb = ttk.Scrollbar(preview_box, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=ysb.set)
        
        xsb = ttk.Scrollbar(preview_box, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(xscrollcommand=xsb.set)
        
        # 布局
        self.preview_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        preview_box.grid_rowconfigure(0, weight=1)
        preview_box.grid_columnconfigure(0, weight=1)
        
        # 状态标签
        self.count_label = tk.Label(self.preview_section, text="",
                font=("Microsoft YaHei", 9), bg=WHITE, fg=MID_BLUE)
        self.count_label.pack(anchor=tk.W, pady=5, padx=15)
        
        # 底部按钮区
        bottom_frame = tk.Frame(content, bg=WHITE, pady=10)
        bottom_frame.pack(fill=tk.X)
        
        # 执行按钮
        tk.Button(bottom_frame, text="确定导出", command=self.execute_rename,
                 bg="#2f855a", fg=WHITE, relief=tk.FLAT, padx=35, pady=10,
                 font=("Microsoft YaHei", 12, "bold")).pack(side=tk.RIGHT, padx=20)
        
        # 加载班级
        self.load_classes()
    
    def _on_window_resize(self, event):
        """窗口大小变化时调整预览区"""
        if event.widget == self.app.root:
            # 调整canvas的滚动区域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # 确保预览区域填满剩余空间
            self.app.root.update_idletasks()
    
    def _adjust_preview_height(self, delta):
        """调整预览区高度"""
        new_height = max(self._min_preview_height, min(self._max_preview_height, self.preview_height + delta))
        self.preview_height = new_height
    
    def apply_format(self):
        """应用新的重命名格式并更新预览"""
        if not self.rename_map:
            messagebox.showinfo("提示", "请先扫描文件")
            return
        
        format_template = self.format_var.get().strip()
        if not format_template:
            messagebox.showwarning("提示", "请输入重命名格式")
            return
        
        # 清空预览
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        matched_count = 0
        unmatched_count = 0
        
        for i, item in enumerate(self.rename_map):
            student = item.get("student")
            original = item["original"]
            ext = os.path.splitext(original)[1]
            
            if student:
                # 使用格式模板生成新文件名
                new_name = self.format_template(format_template, student, ext)
                item["new"] = new_name
                matched_count += 1
            else:
                new_name = original
                unmatched_count += 1
            
            # 显示预览 - 使用 Treeview
            stu_text = f"{student['name']}({student['student_id']})" if student else "未匹配"
            tag = "even" if i % 2 == 0 else "odd"
            self.preview_tree.insert("", "end", values=(str(i+1), original, "→", new_name, stu_text), tags=(tag,))
        
        self.count_label.config(text=f"格式已更新! 共 {len(self.rename_map)} 个文件，已匹配 {matched_count} 个")
        self.app.status(f"重命名格式已更新为: {format_template}")
    
    def format_template(self, template, student, ext):
        """根据模板格式化文件名"""
        result = template
        # 替换学号和姓名变量
        result = result.replace("{学号}", student.get("student_id", ""))
        result = result.replace("{姓名}", student.get("name", ""))
        # 添加扩展名
        if not result.endswith(ext):
            result += ext
        return result
    
    def load_classes(self):
        classes = self.db.get_all_classes()
        class_list = ["全部班级"] + [c["class_name"] for c in classes]
        self.class_combo["values"] = class_list
        if class_list:
            self.class_combo.current(0)
    
    def browse_input(self):
        folder = filedialog.askdirectory(title="选择源文件夹")
        if folder:
            self.input_path.set(folder)
    
    def browse_output(self):
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_path.set(folder)
    
    def read_doc_content(self, filepath):
        """读取docx/doc文件内容，提取学号和姓名"""
        try:
            ext = os.path.splitext(filepath)[1].lower()
            
            if ext == ".docx":
                from docx import Document
                doc = Document(filepath)
                text = "\n".join([p.text for p in doc.paragraphs])
                
                # 表格内容
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            text += "\n" + cell.text
                
                return text
            elif ext == ".doc":
                # 对于.doc文件，尝试用textract或其他方式
                # 这里简单返回空或提示
                return ""
        except Exception as e:
            return ""
        return ""
    
    def extract_info_from_text(self, text):
        """从文本中提取学号和姓名"""
        student_id = None
        name = None
        
        # 学号通常是10-12位数字
        id_pattern = r'\b(\d{10,12})\b'
        id_match = re.search(id_pattern, text)
        if id_match:
            student_id = id_match.group(1)
        
        # 尝试匹配"姓名:XXX"或"姓名XXX"格式
        name_patterns = [
            r'姓名[：:]\s*(\S{2,4})',
            r'姓\s*名[：:]\s*(\S{2,4})',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1)
                break
        
        return student_id, name
    
    def match_student(self, student_id, name, students, filename=None):
        """匹配学生信息：优先学号精确匹配，其次姓名/文件名匹配"""
        filename = filename or ""
        sid_text = str(student_id or "").strip()
        name_text = str(name or "").strip()

        # 1. 学号精确匹配
        if sid_text:
            for stu in students:
                if str(stu.get("student_id", "")) == sid_text:
                    return stu

        # 2. 文件名中的学号匹配
        if filename:
            nums = re.findall(r'\d{6,20}', filename)
            for num in nums:
                for stu in students:
                    db_sid = str(stu.get("student_id", ""))
                    if db_sid and (db_sid == num or db_sid in num or num in db_sid):
                        return stu

        # 3. 姓名匹配
        if name_text:
            for stu in students:
                db_name = str(stu.get("name", ""))
                if db_name and (db_name == name_text or db_name in name_text or name_text in db_name):
                    return stu

        # 4. 文件名中的姓名匹配
        if filename:
            for stu in students:
                db_name = str(stu.get("name", ""))
                if len(db_name) >= 2 and db_name in filename:
                    return stu
        return None
    
    def scan_files(self):
        input_folder = self.input_path.get().strip()
        output_folder = self.output_path.get().strip()
        class_name = self.class_var.get()
        
        if not input_folder:
            messagebox.showwarning("提示", "请选择源文件夹")
            return
        
        if not os.path.exists(input_folder):
            messagebox.showerror("错误", "源文件夹不存在")
            return
        
        # 获取学生列表
        if class_name == "全部班级" or not class_name:
            students = self.db.get_all_students()
        else:
            students = self.db.get_students_by_class(class_name)
        
        if not students:
            messagebox.showwarning("提示", "当前班级没有学生，请先添加学生")
            return
        
        # 扫描文件
        files = []
        for f in os.listdir(input_folder):
            if f.lower().endswith(('.docx', '.doc')):
                files.append(f)
        
        if not files:
            messagebox.showwarning("提示", "源文件夹中没有找到docx或doc文件")
            return
        
        # 清空预览
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        self.rename_map = []
        
        # 处理每个文件
        matched_count = 0
        unmatched_count = 0
        
        for i, filename in enumerate(sorted(files)):
            filepath = os.path.join(input_folder, filename)
            ext = os.path.splitext(filename)[1]
            
            # 读取文件内容
            content = self.read_doc_content(filepath)
            
            # 提取学号和姓名
            student_id, name = self.extract_info_from_text(content)
            
            # 匹配学生：先用内容中的学号/姓名，再用文件名兜底匹配
            student = self.match_student(student_id, name, students, filename=filename)
            
            if student:
                format_template = self.format_var.get().strip() or "{学号}{姓名}实验报告一"
                new_name = self.format_template(format_template, student, ext)
                matched_count += 1
            else:
                # 未匹配到，保留原名
                new_name = filename
                unmatched_count += 1
            
            self.rename_map.append({
                "original": filename,
                "new": new_name,
                "student": student,
                "path": filepath
            })
            
            # 显示预览 - 使用 Treeview，添加匹配状态颜色
            if student:
                stu_text = f"✓匹配成功 {student['name']}({student['student_id']})"
                row_tags = ("even" if i % 2 == 0 else "odd", "matched")
            else:
                stu_text = "✗未匹配"
                row_tags = ("even" if i % 2 == 0 else "odd", "unmatched")
            self.preview_tree.insert("", "end", values=(str(i+1), filename, "→", new_name, stu_text), tags=row_tags)
        
        self.count_label.config(text=f"共 {len(files)} 个文件，已匹配 {matched_count} 个，未匹配 {unmatched_count} 个")
        self.app.status("扫描完成，请检查预览结果")
        
        # 重置深度匹配状态
        self.deep_match_stage = 0
        # 启用并重置深度匹配按钮
        self.deep_match_btn.configure(state=tk.NORMAL, text="深度智能匹配")
    
    def deep_match(self):
        """深度智能匹配 - 分两阶段执行
        阶段1: 文件名级别模糊匹配
        阶段2: 文件内容深度扫描匹配
        """
        if not self.rename_map:
            messagebox.showwarning("提示", "请先扫描文件")
            return
        
        class_name = self.class_var.get()
        if class_name == "全部班级" or not class_name:
            students = self.db.get_all_students()
        else:
            students = self.db.get_students_by_class(class_name)
        
        if not students:
            messagebox.showwarning("提示", "当前班级没有学生，请先添加学生")
            return
        
        matched_count = 0
        new_matched_count = 0
        unmatched_count = 0
        
        # 清空预览
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        # 根据当前阶段执行不同的匹配策略
        if self.deep_match_stage == 0:
            # ===== 阶段1: 文件名级别模糊匹配 =====
            self.app.status("正在执行文件名级别模糊匹配...")
            
            for i, item in enumerate(self.rename_map):
                filename = item["original"]
                filepath = item["path"]
                
                # 跳过已匹配的文件
                if item["student"]:
                    matched_count += 1
                    new_matched_count += 1
                else:
                    student = None
                    
                    # 策略1: 模糊匹配姓名（文件名中包含部分姓名）
                    for stu in students:
                        if len(stu["name"]) >= 2 and stu["name"][:2] in filename:
                            student = stu
                            break
                    
                    # 策略2: 从文件名中提取学号
                    if not student:
                        numbers = re.findall(r'\d+', filename)
                        for num in numbers:
                            if len(num) >= 8:
                                for stu in students:
                                    if stu["student_id"].startswith(num) or num.startswith(stu["student_id"][-8:]):
                                        student = stu
                                        break
                            if student:
                                break
                    
                    # 策略3: 文件名相似度匹配
                    if not student:
                        for stu in students:
                            if stu["student_id"][-4:] in filename or stu["name"][0] in filename:
                                if any(c in filename for c in stu["name"]):
                                    student = stu
                                    break
                    
                    # 更新映射
                    if student:
                        ext = os.path.splitext(filename)[1]
                        format_template = self.format_var.get().strip() or "{学号}{姓名}实验报告一"
                        new_name = self.format_template(format_template, student, ext)
                        item["student"] = student
                        item["new"] = new_name
                        matched_count += 1
                        new_matched_count += 1
                    else:
                        unmatched_count += 1
                        item["new"] = filename
                
                # 显示预览
                student = item["student"]
                if student:
                    stu_text = f"✓匹配成功 {student['name']}({student['student_id']})"
                    row_tags = ("even" if i % 2 == 0 else "odd", "matched")
                else:
                    stu_text = "✗未匹配"
                    row_tags = ("even" if i % 2 == 0 else "odd", "unmatched")
                self.preview_tree.insert("", "end", values=(str(i+1), filename, "→", item["new"], stu_text), tags=row_tags)
            
            self.deep_match_stage = 1
            self.deep_match_btn.configure(text="深度内容扫描")
            self.count_label.config(text=f"文件名匹配完成: 共 {len(self.rename_map)} 个文件，已匹配 {matched_count} 个，新增 {new_matched_count} 个，未匹配 {unmatched_count} 个")
            self.app.status("文件名匹配完成，请再次点击进行内容深度扫描")
            
        elif self.deep_match_stage == 1:
            # ===== 阶段2: 文件内容深度扫描匹配 =====
            self.app.status("正在执行文件内容深度扫描...")
            
            for i, item in enumerate(self.rename_map):
                filename = item["original"]
                filepath = item["path"]
                
                # 跳过已匹配的文件
                if item["student"]:
                    matched_count += 1
                else:
                    # 深度扫描文件内容
                    content = self.read_doc_content(filepath)
                    student = None
                    
                    if content:
                        # 策略1: 从内容中提取12位学号
                        id_pattern = r'\b(\d{12})\b'
                        id_match = re.search(id_pattern, content)
                        if id_match:
                            extracted_id = id_match.group(1)
                            for stu in students:
                                if stu["student_id"] == extracted_id:
                                    student = stu
                                    break
                        
                        # 策略2: 从内容中提取姓名（更宽松的模式）
                        if not student:
                            name_patterns = [
                                r'姓名[：:]\s*(\S{2,4})',
                                r'姓\s*名[：:]\s*(\S{2,4})',
                                r'学生[姓名：:]\s*(\S{2,4})',
                            ]
                            for pattern in name_patterns:
                                match = re.search(pattern, content)
                                if match:
                                    extracted_name = match.group(1)
                                    for stu in students:
                                        if extracted_name in stu["name"] or stu["name"] in extracted_name:
                                            student = stu
                                            break
                                    if student:
                                        break
                        
                        # 策略3: 如果找到学号但未匹配到学生，尝试学号后8位匹配
                        if not student and id_match:
                            extracted_id = id_match.group(1)
                            for stu in students:
                                if stu["student_id"].endswith(extracted_id[-8:]) or extracted_id.endswith(stu["student_id"][-8:]):
                                    student = stu
                                    break
                        
                        # 策略4: 扫描内容中所有数字，尝试匹配
                        if not student:
                            all_numbers = re.findall(r'\d{8,12}', content)
                            for num in all_numbers:
                                for stu in students:
                                    # 学号包含关系
                                    if num in stu["student_id"] or stu["student_id"] in num:
                                        student = stu
                                        break
                                if student:
                                    break
                    
                    # 更新映射
                    if student:
                        ext = os.path.splitext(filename)[1]
                        format_template = self.format_var.get().strip() or "{学号}{姓名}实验报告一"
                        new_name = self.format_template(format_template, student, ext)
                        item["student"] = student
                        item["new"] = new_name
                        matched_count += 1
                        new_matched_count += 1
                    else:
                        unmatched_count += 1
                        item["new"] = filename
                
                # 显示预览
                student = item["student"]
                if student:
                    stu_text = f"✓匹配成功 {student['name']}({student['student_id']})"
                    row_tags = ("even" if i % 2 == 0 else "odd", "matched")
                else:
                    stu_text = "✗未匹配"
                    row_tags = ("even" if i % 2 == 0 else "odd", "unmatched")
                self.preview_tree.insert("", "end", values=(str(i+1), filename, "→", item["new"], stu_text), tags=row_tags)
            
            self.deep_match_stage = 2
            self.deep_match_btn.configure(text="深度匹配完成", state=tk.DISABLED)
            self.count_label.config(text=f"深度扫描完成: 共 {len(self.rename_map)} 个文件，已匹配 {matched_count} 个，新增 {new_matched_count} 个，未匹配 {unmatched_count} 个")
            self.app.status("深度扫描完成，无法再进行更多匹配")
    
    def execute_rename(self):
        if not self.rename_map:
            messagebox.showwarning("提示", "请先扫描文件")
            return
        
        output_folder = self.output_path.get().strip()
        if not output_folder:
            messagebox.showwarning("提示", "请选择输出文件夹")
            return
        
        # 统计匹配数量
        matched = sum(1 for item in self.rename_map if item["student"])
        
        # 确认对话框
        confirm = messagebox.askyesno("确认重命名", 
            f"即将重命名 {len(self.rename_map)} 个文件\n\n"
            f"已匹配: {matched} 个\n"
            f"未匹配: {len(self.rename_map) - matched} 个\n\n"
            f"输出目录: {output_folder}\n\n"
            f"是否继续？")
        
        if not confirm:
            return
        
        os.makedirs(output_folder, exist_ok=True)
        
        success_count = 0
        skip_count = 0
        
        for item in self.rename_map:
            src = item["path"]
            dst = os.path.join(output_folder, item["new"])
            
            # 如果目标文件已存在，自动追加序号，避免直接跳过
            if os.path.exists(dst):
                base, ext = os.path.splitext(dst)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                dst = f"{base}_{counter}{ext}"
                skip_count += 1
            
            try:
                shutil.copy2(src, dst)
                success_count += 1
            except Exception as e:
                print(f"复制失败: {src} -> {dst}, 错误: {e}")
        
        messagebox.showinfo("完成", f"重命名完成！\n成功: {success_count}\n重名自动改名: {skip_count}")
        self.app.status(f"重命名完成: 成功 {success_count}, 重名自动改名 {skip_count}")

# ==================== 启动 ====================
if __name__ == "__main__":
    app = App()
    app.run()
