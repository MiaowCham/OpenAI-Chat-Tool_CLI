#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n国际化模块 (i18n.py)
负责多语言支持和文本本地化
"""

import json
import os
from typing import Dict, Any, Optional


class I18n:
    """国际化管理类"""
    
    def __init__(self, default_language: str = 'zh-CN'):
        """
        初始化国际化管理器
        
        Args:
            default_language: 默认语言代码
        """
        self.current_language = default_language
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.available_languages = ['zh-CN', 'en-US']
        self.i18n_dir = os.path.join(os.path.dirname(__file__), 'i18n')
        
        # 加载所有可用语言
        self._load_all_languages()
        
        # 设置当前语言
        self.set_language(default_language)
    
    def _load_all_languages(self):
        """加载所有可用的语言文件"""
        for lang_code in self.available_languages:
            self._load_language(lang_code)
    
    def _load_language(self, language_code: str) -> bool:
        """
        加载指定语言文件
        
        Args:
            language_code: 语言代码
            
        Returns:
            是否加载成功
        """
        try:
            lang_file = os.path.join(self.i18n_dir, f'{language_code}.json')
            
            if not os.path.exists(lang_file):
                print(f"Warning: Language file {lang_file} not found")
                return False
            
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations[language_code] = json.load(f)
            
            return True
            
        except Exception as e:
            print(f"Error loading language {language_code}: {e}")
            return False
    
    def set_language(self, language_code: str) -> bool:
        """
        设置当前语言
        
        Args:
            language_code: 语言代码
            
        Returns:
            是否设置成功
        """
        if language_code not in self.available_languages:
            return False
        
        if language_code not in self.translations:
            if not self._load_language(language_code):
                return False
        
        self.current_language = language_code
        return True
    
    def get_language(self) -> str:
        """获取当前语言代码"""
        return self.current_language
    
    def get_available_languages(self) -> list:
        """获取所有可用语言列表"""
        return self.available_languages.copy()
    
    def get_language_name(self, language_code: str) -> str:
        """获取语言显示名称"""
        language_names = {
            'zh-CN': '中文',
            'en-US': 'English'
        }
        return language_names.get(language_code, language_code)
    
    def t(self, key: str, *args, **kwargs) -> str:
        """
        获取翻译文本
        
        Args:
            key: 翻译键，支持点号分隔的嵌套键，如 'config.loading_failed'
            *args: 格式化参数（位置参数）
            **kwargs: 格式化参数（关键字参数）
            
        Returns:
            翻译后的文本
        """
        # 获取当前语言的翻译数据
        current_translations = self.translations.get(self.current_language, {})
        
        # 解析嵌套键
        keys = key.split('.')
        value = current_translations
        
        try:
            for k in keys:
                value = value[k]
            
            # 如果找到了翻译文本
            if isinstance(value, str):
                # 处理格式化参数
                if args or kwargs:
                    try:
                        # 支持位置参数格式化 {0}, {1}, ...
                        if args:
                            value = value.format(*args)
                        # 支持关键字参数格式化 {name}, {value}, ...
                        elif kwargs:
                            value = value.format(**kwargs)
                    except (KeyError, IndexError, ValueError) as e:
                        print(f"Warning: Format error for key '{key}': {e}")
                
                return value
            else:
                print(f"Warning: Translation key '{key}' is not a string")
                return key
                
        except (KeyError, TypeError):
            # 如果当前语言没有找到，尝试使用默认语言（中文）
            if self.current_language != 'zh-CN':
                default_translations = self.translations.get('zh-CN', {})
                value = default_translations
                
                try:
                    for k in keys:
                        value = value[k]
                    
                    if isinstance(value, str):
                        if args or kwargs:
                            try:
                                if args:
                                    value = value.format(*args)
                                elif kwargs:
                                    value = value.format(**kwargs)
                            except (KeyError, IndexError, ValueError):
                                pass
                        return value
                except (KeyError, TypeError):
                    pass
            
            # 如果都没找到，返回原始键
            print(f"Warning: Translation not found for key '{key}'")
            return key
    
    def has_translation(self, key: str, language_code: Optional[str] = None) -> bool:
        """
        检查是否存在指定键的翻译
        
        Args:
            key: 翻译键
            language_code: 语言代码，如果为None则使用当前语言
            
        Returns:
            是否存在翻译
        """
        if language_code is None:
            language_code = self.current_language
        
        translations = self.translations.get(language_code, {})
        keys = key.split('.')
        value = translations
        
        try:
            for k in keys:
                value = value[k]
            return isinstance(value, str)
        except (KeyError, TypeError):
            return False
    
    def get_weekday_name(self, weekday_index: int) -> str:
        """
        获取星期几的本地化名称
        
        Args:
            weekday_index: 星期索引 (0=Monday, 6=Sunday)
            
        Returns:
            本地化的星期名称
        """
        weekday_keys = [
            'weekdays.monday',
            'weekdays.tuesday', 
            'weekdays.wednesday',
            'weekdays.thursday',
            'weekdays.friday',
            'weekdays.saturday',
            'weekdays.sunday'
        ]
        
        if 0 <= weekday_index < len(weekday_keys):
            return self.t(weekday_keys[weekday_index])
        else:
            return str(weekday_index)


# 全局i18n实例
_i18n_instance: Optional[I18n] = None


def init_i18n(language: str = 'zh-CN') -> I18n:
    """
    初始化全局i18n实例
    
    Args:
        language: 默认语言
        
    Returns:
        I18n实例
    """
    global _i18n_instance
    _i18n_instance = I18n(language)
    return _i18n_instance


def get_i18n() -> I18n:
    """
    获取全局i18n实例
    
    Returns:
        I18n实例
    """
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18n()
    return _i18n_instance


def t(key: str, *args, **kwargs) -> str:
    """
    获取翻译文本的便捷函数
    
    Args:
        key: 翻译键
        *args: 格式化参数
        **kwargs: 格式化参数
        
    Returns:
        翻译后的文本
    """
    return get_i18n().t(key, *args, **kwargs)


def set_language(language_code: str) -> bool:
    """
    设置当前语言的便捷函数
    
    Args:
        language_code: 语言代码
        
    Returns:
        是否设置成功
    """
    return get_i18n().set_language(language_code)


def get_language() -> str:
    """
    获取当前语言的便捷函数
    
    Returns:
        当前语言代码
    """
    return get_i18n().get_language()


def get_available_languages() -> list:
    """
    获取可用语言列表的便捷函数
    
    Returns:
        可用语言列表
    """
    return get_i18n().get_available_languages()


def get_language_name(language_code: str) -> str:
    """
    获取语言显示名称的便捷函数
    
    Args:
        language_code: 语言代码
        
    Returns:
        语言显示名称
    """
    return get_i18n().get_language_name(language_code)


# 测试代码
if __name__ == "__main__":
    # 测试i18n功能
    print("=== i18n功能测试 ===")
    
    # 初始化
    i18n = init_i18n('zh-CN')
    
    # 测试基本翻译
    print(f"中文: {t('app.welcome')}")
    print(f"配置加载失败: {t('config.loading_failed')}")
    print(f"格式化测试: {t('config.loaded', 'Test Config', 'test_001')}")
    
    # 切换到英文
    set_language('en-US')
    print(f"\n英文: {t('app.welcome')}")
    print(f"配置加载失败: {t('config.loading_failed')}")
    print(f"格式化测试: {t('config.loaded', 'Test Config', 'test_001')}")
    
    # 测试星期几
    print(f"\n星期几测试:")
    for i in range(7):
        weekday = i18n.get_weekday_name(i)
        print(f"  {i}: {weekday}")
    
    # 测试可用语言
    print(f"\n可用语言: {get_available_languages()}")
    print(f"当前语言: {get_language()}")
    
    print("\n=== 测试完成 ===")