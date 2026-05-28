# -*- coding: utf-8 -*-
"""
文件夹批量重命名工具 - 配置模块
"""

# 重命名规则配置
RENAME_RULES = {
    # 前缀（可留空）
    'prefix': '',
    # 后缀（可留空）
    'suffix': '',
    # 起始序号
    'start_number': 1,
    # 序号位数（不够补零）
    'number_width': 3,
    # 替换的字符（将文件名中的特殊字符替换为指定字符）
    'replace_chars': {
        ' ': '_',      # 空格替换为下划线
        '（': '(',     # 全角括号转为半角
        '）': ')',
    },
    # 是否保留原扩展名
    'keep_extension': True,
}

# 支持的文件扩展名（留空表示所有文件）
ALLOWED_EXTENSIONS = ['']

# 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL = 'INFO'

# 冲突处理策略: 'skip'（跳过）, 'overwrite'（覆盖）, 'add_suffix'（添加后缀）
CONFLICT_STRATEGY = 'add_suffix'
