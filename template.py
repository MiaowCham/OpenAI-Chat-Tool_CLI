#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板变量处理模块
支持在系统提示词中使用模板变量，如 {{time}}、{{date}} 等
"""

import re
import time
from datetime import datetime
from typing import Dict, Callable

class TemplateProcessor:
    """模板变量处理器"""
    
    def __init__(self):
        """初始化模板处理器"""
        self.variables: Dict[str, Callable[[], str]] = {
            'time': self._get_time,
            'date': self._get_date,
            'datetime': self._get_datetime,
            'timestamp': self._get_timestamp,
            'weekday': self._get_weekday,
            'year': self._get_year,
            'month': self._get_month,
            'day': self._get_day
        }
        
        # 模板变量匹配正则表达式
        self.pattern = re.compile(r'\{\{\s*(\w+)\s*\}\}')
    
    def _get_time(self) -> str:
        """获取当前时间 (HH:MM:SS)"""
        return datetime.now().strftime('%H:%M:%S')
    
    def _get_date(self) -> str:
        """获取当前日期 (YYYY-MM-DD)"""
        return datetime.now().strftime('%Y-%m-%d')
    
    def _get_datetime(self) -> str:
        """获取当前日期时间 (YYYY-MM-DD HH:MM:SS)"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _get_timestamp(self) -> str:
        """获取Unix时间戳"""
        return str(int(time.time()))
    
    def _get_weekday(self) -> str:
        """获取星期几"""
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[datetime.now().weekday()]
    
    def _get_year(self) -> str:
        """获取当前年份"""
        return str(datetime.now().year)
    
    def _get_month(self) -> str:
        """获取当前月份"""
        return str(datetime.now().month)
    
    def _get_day(self) -> str:
        """获取当前日期"""
        return str(datetime.now().day)
    
    def process(self, text: str) -> str:
        """处理文本中的模板变量
        
        Args:
            text: 包含模板变量的文本
            
        Returns:
            处理后的文本，模板变量已被替换为实际值
        """
        if not text:
            return text
        
        def replace_variable(match):
            """替换单个模板变量"""
            var_name = match.group(1).lower()
            if var_name in self.variables:
                try:
                    return self.variables[var_name]()
                except Exception as e:
                    # 如果获取变量值失败，返回原始模板变量
                    print(f"警告: 获取模板变量 '{var_name}' 失败: {e}")
                    return match.group(0)
            else:
                # 未知的模板变量，返回原始文本
                print(f"警告: 未知的模板变量 '{var_name}'")
                return match.group(0)
        
        # 替换所有模板变量
        return self.pattern.sub(replace_variable, text)
    
    def get_available_variables(self) -> list:
        """获取所有可用的模板变量列表"""
        return list(self.variables.keys())
    
    def add_variable(self, name: str, func: Callable[[], str]):
        """添加自定义模板变量
        
        Args:
            name: 变量名
            func: 返回变量值的函数
        """
        self.variables[name.lower()] = func

# 全局模板处理器实例
_template_processor = TemplateProcessor()

def process_template(text: str) -> str:
    """处理模板变量的便捷函数
    
    Args:
        text: 包含模板变量的文本
        
    Returns:
        处理后的文本
    """
    return _template_processor.process(text)

def get_available_variables() -> list:
    """获取所有可用的模板变量列表"""
    return _template_processor.get_available_variables()

def add_template_variable(name: str, func: Callable[[], str]):
    """添加自定义模板变量"""
    _template_processor.add_variable(name, func)

if __name__ == "__main__":
    # 测试代码
    test_text = """
当前时间: {{time}}
当前日期: {{date}}
当前日期时间: {{datetime}}
时间戳: {{timestamp}}
今天是: {{weekday}}
年份: {{year}}
月份: {{month}}
日期: {{day}}
未知变量: {{unknown}}
    """.strip()
    
    print("原始文本:")
    print(test_text)
    print("\n处理后文本:")
    print(process_template(test_text))
    print("\n可用变量:", get_available_variables())