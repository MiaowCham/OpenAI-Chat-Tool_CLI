#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Chat Tool CLI (octool_cli)
一个基于 OpenAI 库编写的一个简单的命令行 API 聊天工具，支持多种模型、多语言界面和智能功能
"""

# 在所有其他导入之前启动早期加载动画
#from early_loading import start_early_loading, stop_early_loading
# start_early_loading("程序启动中...")

# 先初始化i18n，再启动加载动画
from i18n import init_i18n, t, set_language, get_language
init_i18n()  # 提前初始化

from loading_animation import start_loading, stop_loading, loading_context
start_loading(t('processing.app_launch'))

# 版本信息
VERSION = "1.2.0"

import os
import sys
import time
import yaml
import argparse
from typing import Dict, Any, Optional, List
# 导入自定义模块 - 延迟导入重型模块以提升启动速度
from template import process_template
from markdown_renderer import render_ai_response, render_streaming_response, render_system_message

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

def ensure_datetime_in_prompt(prompt: str) -> str:
    """确保系统提示词包含时间信息
    
    Args:
        prompt: 原始系统提示词
        
    Returns:
        包含时间信息的系统提示词
    """
    if not prompt:
        prompt = "你是一个有用的AI助手。"
    
    # 检查是否已经包含时间相关的模板变量
    time_keywords = ['{{time}}', '{{date}}', '{{datetime}}', '{{timestamp}}', '{{weekday}}', '{{year}}', '{{month}}', '{{day}}']
    has_time_info = any(keyword in prompt for keyword in time_keywords)
    
    # 如果没有时间信息，自动添加
    if not has_time_info:
        prompt += "\n\n当前时间：{{datetime}}"
    
    return prompt

def get_multiline_input(prompt_text: str) -> str:
    """获取多行输入，支持Alt+Enter换行，Ctrl+J换行（备用方案）
    
    Args:
        prompt_text: 提示文本
        
    Returns:
        str: 用户输入的文本
    """
    if PROMPT_TOOLKIT_AVAILABLE:
        # 创建自定义键绑定
        kb = KeyBindings()
        
        @kb.add('enter')
        def _(event):
            """Enter键提交输入"""
            event.app.exit(result=event.app.current_buffer.text)
        
        @kb.add('escape', 'enter')  # Alt+Enter换行 (替代Shift+Enter)
        def _(event):
            """Alt+Enter换行"""
            event.app.current_buffer.insert_text('\n')
        
        @kb.add('c-j')  # Ctrl+J换行 (备用方案)
        def _(event):
            """Ctrl+J换行 (备用方案)"""
            event.app.current_buffer.insert_text('\n')
        
        try:
            # 使用prompt-toolkit获取输入，移除ANSI颜色代码
            clean_prompt = prompt_text.replace('\033[33m', '').replace('\033[0m', '')
            print(prompt_text, end='')  # 先打印带颜色的提示
            result = prompt(
                '',  # 空提示，因为我们已经打印了
                key_bindings=kb,
                multiline=True,  # 启用多行支持
                wrap_lines=True
            )
            return result
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception:
            # 如果prompt-toolkit出错，回退到标准输入
            print(prompt_text, end='')
            return input()
    else:
        # 如果没有prompt-toolkit，使用标准输入
        print(f"{prompt_text}(提示: 此环境不支持Shift+Enter换行功能)", end='')
        return input()

# 颜色定义
COLOR_YELLOW = "\033[33m"
COLOR_GREEN = "\033[32m"
COLOR_BLUE = "\033[34m"
COLOR_RED = "\033[31m"
COLOR_CYAN = "\033[36m"
COLOR_RESET = "\033[0m"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = ".octool_cli/config.yaml"):
        self.config_path = config_path
        self.configs = {}
        self.default_config_id = "Prompt_000"
        self.ensure_config_dir()
        self.load_configs()
    
    def get_multilang_field(self, config: Dict[str, Any], field_base: str, language: str = None) -> str:
        """获取多语言字段值，支持向后兼容"""
        if language is None:
            from i18n import get_language
            language = get_language()
        
        # 根据语言选择字段
        if language == 'en-US':
            field_key = f"{field_base}_en"
        else:
            field_key = f"{field_base}_cn"
        
        # 尝试获取多语言字段
        if field_key in config:
            return config[field_key]
        
        # 向后兼容：如果没有多语言字段，使用原字段
        if field_base in config:
            return config[field_base]
        
        # 提供默认值
        defaults = {
            'name': '默认' if language != 'en-US' else 'Default',
            'welcome_message': '我可以帮你写代码、读文件、写作各种创意内容，请把你的任务交给我吧~' if language != 'en-US' else 'I can help you write code, read files, and write all kinds of creative content, please leave your task to me~'
        }
        return defaults.get(field_base, '')
    
    def ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
    
    def load_configs(self) -> bool:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # 提取默认配置ID
                self.default_config_id = data.pop('default_config', 'Prompt_000')
                
                # 加载所有配置
                self.configs = {k: v for k, v in data.items() if isinstance(v, dict)}
                
                return True
            return False
        except Exception as e:
            print(f"{COLOR_RED}配置加载失败: {str(e)}{COLOR_RESET}")
            return False
    
    def save_configs(self) -> bool:
        """保存配置文件"""
        try:
            data = dict(self.configs)
            data['default_config'] = self.default_config_id
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"{COLOR_RED}配置保存失败: {str(e)}{COLOR_RESET}")
            return False
    
    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """获取指定配置"""
        return self.configs.get(config_id)
    
    def get_config_by_name_or_alias(self, identifier: str) -> Optional[tuple]:
        """通过名称或别名获取配置"""
        for config_id, config in self.configs.items():
            if config.get('name') == identifier:
                return config_id, config
            
            aliases = config.get('alias', [])
            if isinstance(aliases, list) and identifier in aliases:
                return config_id, config
        
        return None
    
    def list_configs(self) -> List[tuple]:
        """列出所有配置"""
        result = []
        for config_id, config in self.configs.items():
            name = self.get_multilang_field(config, 'name')
            aliases = config.get('alias', [])
            result.append((config_id, name, aliases))
        return result
    
    def add_config(self, config_id: str, config_data: Dict[str, Any]) -> bool:
        """添加新配置"""
        self.configs[config_id] = config_data
        return self.save_configs()
    
    def delete_config(self, config_id: str) -> bool:
        """删除配置"""
        if config_id in self.configs:
            del self.configs[config_id]
            return self.save_configs()
        return False
    
    def set_default_config(self, config_id: str) -> bool:
        """设置默认配置"""
        if config_id in self.configs:
            self.default_config_id = config_id
            return self.save_configs()
        return False
    
    def update_config(self, config_id: str, config_data: Dict[str, Any]) -> bool:
        """更新指定配置"""
        if config_id in self.configs:
            self.configs[config_id] = config_data
            return self.save_configs()
        return False
    
class ChatTool:
    """聊天工具主类"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.current_config = None
        self.current_config_id = None
        self.client = None
        self.history_manager = None
        self.summarizer = None
        
        # 帮助信息
        self.help_msg = f"""{COLOR_YELLOW}{t('commands.help_title')}{COLOR_BLUE}
- '/help': {t('commands.help_desc')}
- '/clear': {t('commands.clear_desc')}
- '/exit': {t('commands.exit_desc')}
- '/config list': {t('commands.config_list_desc')}
- '/config switch [ID]': {t('commands.config_switch_desc')}
- '/config new [ID]': {t('commands.config_new_desc')}
- '/config edit [ID]': {t('commands.config_edit_desc')}
- '/config delete [ID]': {t('commands.config_delete_desc')}
- '/config current': {t('commands.config_current_desc')}
- '/history': {t('commands.history_desc')}
- '/new': {t('commands.new_desc')}
- '/refresh': {t('commands.refresh_desc')}
- '/summary': {t('commands.summary_desc')}
- '/last_summary': {t('commands.last_summary_desc')}
- '/lang [language]': {t('commands.lang_desc')}
- '/markdown [on/off]': {t('commands.markdown_desc')}
{COLOR_RESET}"""
    
    def _parse_token_value(self, token_input: str, default_value: int) -> int:
        """解析Token值，支持K/k单位"""
        if not token_input:
            return default_value
        
        token_input = token_input.strip().upper()
        
        try:
            if token_input.endswith('K'):
                # 移除K并转换为数字，然后乘以1000
                number = float(token_input[:-1])
                return int(number * 1000)
            else:
                return int(token_input)
        except ValueError:
            return default_value
    
    def select_initial_language(self):
        """首次使用时选择语言"""
        print(f"{COLOR_YELLOW}Please select your language / 请选择您的语言:{COLOR_RESET}")
        print(f"{COLOR_BLUE}1. 中文 (zh-CN){COLOR_RESET}")
        print(f"{COLOR_BLUE}2. English (en-US){COLOR_RESET}")
        
        while True:
            choice = input(f"{COLOR_YELLOW}Enter your choice (1 or 2) / 请输入选择 (1 或 2): {COLOR_RESET}").strip()
            if choice == '1':
                set_language('zh-CN')
                print(f"{COLOR_GREEN}语言已设置为中文{COLOR_RESET}")
                break
            elif choice == '2':
                set_language('en-US')
                print(f"{COLOR_GREEN}Language set to English{COLOR_RESET}")
                break
            else:
                print(f"{COLOR_RED}Invalid choice, please enter 1 or 2 / 无效选择，请输入 1 或 2{COLOR_RESET}")
    
    def validate_api(self, api_key: str, api_endpoint: str) -> bool:
        """验证API有效性"""
        try:
            from openai import OpenAI  # 延迟导入
            client = OpenAI(api_key=api_key, base_url=api_endpoint)
            client.models.list()
            return True
        except Exception as e:
            print(f"{COLOR_RED}{t('api.validation_failed', error=str(e))}{COLOR_RESET}")
            return False
    
    def input_config_interactive(self, config_id: str = None) -> Optional[Dict[str, Any]]:
        """交互式配置输入"""
        print(f"{COLOR_YELLOW}{t('input.enter_config_info')}{COLOR_RESET}")
        
        # API配置
        while True:
            api_key = input(f"{COLOR_YELLOW}API Key: {COLOR_RESET}").strip()
            if not api_key:
                continue
            
            api_endpoint = input(f"{COLOR_YELLOW}{t('input.api_endpoint_prompt')}{COLOR_RESET}").strip()
            if not api_endpoint:
                api_endpoint = "https://api.deepseek.com"
            
            print(f"{COLOR_GREEN}{t('api.validating')}{COLOR_RESET}")
            if self.validate_api(api_key, api_endpoint):
                print(f"{COLOR_GREEN}{t('api.validation_success')}{COLOR_RESET}")
                break
            else:
                print(f"{COLOR_RED}{t('api.validation_failed_retry')}{COLOR_RESET}")
        
        # 其他配置
        name = input(f"{COLOR_YELLOW}{t('input.config_name_prompt')}{COLOR_RESET}").strip() or "default"
        
        # 多语言配置名称
        name_cn = input(f"{COLOR_YELLOW}{t('input.name_cn')}{COLOR_RESET}").strip() or name
        name_en = input(f"{COLOR_YELLOW}{t('input.name_en')}{COLOR_RESET}").strip() or name
        
        alias_input = input(f"{COLOR_YELLOW}{t('input.alias_prompt')}{COLOR_RESET}").strip()
        aliases = [a.strip() for a in alias_input.split(',') if a.strip()] if alias_input else []
        
        model = input(f"{COLOR_YELLOW}{t('input.model_prompt')}{COLOR_RESET}").strip() or "deepseek-chat"
        ai_name = input(f"{COLOR_YELLOW}{t('input.ai_name_prompt')}{COLOR_RESET}").strip() or "AI"
        system_prompt = input(f"{COLOR_YELLOW}{t('input.system_prompt_prompt')}{COLOR_RESET}").strip() or t('input.default_system_prompt')
        
        # 多语言欢迎消息
        welcome_message_cn = input(f"{COLOR_YELLOW}{t('input.welcome_message_cn')}{COLOR_RESET}").strip() or "我可以帮你写代码、读文件、写作各种创意内容，请把你的任务交给我吧~"
        welcome_message_en = input(f"{COLOR_YELLOW}{t('input.welcome_message_en')}{COLOR_RESET}").strip() or "I can help you write code, read files, and write all kinds of creative content, please leave your task to me~"
        
        # 功能配置
        history_input = input(f"{COLOR_YELLOW}{t('input.enable_history_prompt')}{COLOR_RESET}").strip().lower()
        history = history_input != 'n'
        
        summary_input = input(f"{COLOR_YELLOW}{t('input.enable_summary_prompt')}{COLOR_RESET}").strip().lower()
        summary = summary_input != 'n' and history  # 总结需要历史记录支持
        
        # Token配置 - 支持K/k单位
        max_tokens_input = input(f"{COLOR_YELLOW}{t('input.max_tokens_prompt')}{COLOR_RESET}").strip()
        max_tokens = self._parse_token_value(max_tokens_input, 64000)  # 默认64K
        
        # 流式响应配置
        stream_input = input(f"{COLOR_YELLOW}{t('input.enable_stream_prompt')}{COLOR_RESET}").strip().lower()
        stream = stream_input != 'n'  # 默认启用流式响应
        
        # Markdown渲染配置
        markdown_input = input(f"{COLOR_YELLOW}{t('input.enable_markdown_prompt')}{COLOR_RESET}").strip().lower()
        markdown = markdown_input != 'n'  # 默认启用Markdown渲染
        
        return {
            'name': name,
            'name_cn': name_cn,
            'name_en': name_en,
            'alias': aliases,
            'API_key': api_key,
            'API_endpoint': api_endpoint,
            'model': model,
            'ai_name': ai_name,
            'system_Prompt': system_prompt,
            'welcome_message_cn': welcome_message_cn,
            'welcome_message_en': welcome_message_en,
            'history': history,
            'summary': summary,
            'max_tokens': max_tokens,
            'stream': stream,
            'markdown': markdown,
            'language': get_language()
        }
    
    def load_config(self, config_id: str) -> bool:
        """加载指定配置"""
        config = self.config_manager.get_config(config_id)
        if not config:
            # 尝试通过名称或别名查找
            result = self.config_manager.get_config_by_name_or_alias(config_id)
            if result:
                config_id, config = result
            else:
                print(f"{COLOR_RED}{t('config.not_exist', name=config_id)}{COLOR_RESET}")
                return False
        
        # 设置语言
        language = config.get('language', 'zh-CN')
        set_language(language)
        
        # 验证API
        api_key = config.get('API_key')
        api_endpoint = config.get('API_endpoint')
        
        if not api_key or not api_endpoint:
            print(f"{COLOR_RED}{t('config.missing_api_info', name=config_id)}{COLOR_RESET}")
            return False
        
        if not self.validate_api(api_key, api_endpoint):
            print(f"{COLOR_RED}{t('config.invalid_api', name=config_id)}{COLOR_RESET}")
            return False
        
        # 设置当前配置
        self.current_config = config
        self.current_config_id = config_id
        
        # 延迟导入OpenAI
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=api_endpoint)
        
        # 初始化历史记录管理器
        if config.get('history', False):
            # 延迟导入history模块
            from history import create_history_manager
            self.history_manager = create_history_manager(config_id)
            self.history_manager.model = config.get('model', 'deepseek-chat')
            
            # 添加系统消息（确保包含时间信息并处理模板变量）
            system_prompt = config.get('system_Prompt', '')
            enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
            processed_prompt = process_template(enhanced_prompt)
            self.history_manager.add_message('system', processed_prompt)
        
        # 初始化总结器
        if config.get('summary', False) and config.get('history', False):
            # 延迟导入summary模块
            from summary import create_summarizer
            self.summarizer = create_summarizer(api_key, api_endpoint, config.get('model', 'deepseek-chat'))
        
        config_name = self.config_manager.get_multilang_field(config, 'name')
        print(f"{COLOR_GREEN}{t('config.loaded', name=config_name, id=config_id)}{COLOR_RESET}")
        return True
    
    def handle_config_command(self, parts: List[str]) -> bool:
        """处理配置相关命令"""
        if len(parts) < 2:
            print(f"{COLOR_YELLOW}{t('config.usage_title')}{COLOR_BLUE}")
            print(f"- /config list: {t('config.list_usage')}")
            print(f"- /config switch [ID]: {t('config.switch_usage')}")
            print(f"- /config new [ID]: {t('config.new_usage')}")
            print(f"- /config edit [ID]: {t('config.edit_usage')}")
            print(f"- /config delete [ID]: {t('config.delete_usage')}")
            print(f"- /config current: {t('config.current_usage')}{COLOR_RESET}")
            return True
        
        subcommand = parts[1].lower()
        
        if subcommand == 'list':
            configs = self.config_manager.list_configs()
            if not configs:
                print(f"{COLOR_YELLOW}{t('config.no_configs_available')}{COLOR_RESET}")
            else:
                print(f"{COLOR_YELLOW}{t('config.available_configs')}{COLOR_RESET}")
                for config_id, name, aliases in configs:
                    alias_str = f" ({t('config.alias_label')}: {', '.join(aliases)})" if aliases else ""
                    current_mark = f" [{t('config.current_label')}]" if config_id == self.current_config_id else ""
                    print(f"{COLOR_BLUE}- {config_id}: {name}{alias_str}{current_mark}{COLOR_RESET}")
        
        elif subcommand == 'switch':
            if len(parts) < 3:
                print(f"{COLOR_RED}{t('config.specify_config_id')}{COLOR_RESET}")
                return True
            
            config_id = parts[2]
            if self.load_config(config_id):
                print(f"{COLOR_GREEN}{t('config.switched_to', id=config_id)}{COLOR_RESET}")
            
        elif subcommand == 'new':
            config_id = parts[2] if len(parts) > 2 else None
            if not config_id:
                # 自动生成配置ID
                existing_ids = list(self.config_manager.configs.keys())
                for i in range(1000):
                    test_id = f"Prompt_{i:03d}"
                    if test_id not in existing_ids:
                        config_id = test_id
                        break
            
            if config_id in self.config_manager.configs:
                print(f"{COLOR_RED}{t('config.already_exists', id=config_id)}{COLOR_RESET}")
                return True
            
            print(f"{COLOR_YELLOW}{t('config.creating_new', id=config_id)}{COLOR_RESET}")
            config_data = self.input_config_interactive(config_id)
            
            if config_data:
                if self.config_manager.add_config(config_id, config_data):
                    print(f"{COLOR_GREEN}{t('config.created_success', id=config_id)}{COLOR_RESET}")
                    
                    # 询问是否切换
                    switch = input(f"{COLOR_YELLOW}{t('config.switch_to_new_prompt')}{COLOR_RESET}").strip().lower()
                    if switch == 'y':
                        self.load_config(config_id)
                else:
                    print(f"{COLOR_RED}{t('config.save_failed')}{COLOR_RESET}")
        
        elif subcommand == 'current':
            if self.current_config:
                config = self.current_config
                print(f"{COLOR_YELLOW}{t('config.current_info_title')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}ID: {self.current_config_id}{COLOR_RESET}")
                config_name = self.config_manager.get_multilang_field(config, 'name')
                print(f"{COLOR_BLUE}{t('config.name_label')}: {config_name}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.ai_name_label')}: {config.get('ai_name', 'AI')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.model_label')}: {config.get('model', 'Unknown')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.history_label')}: {t('config.enabled') if config.get('history') else t('config.disabled')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.summary_label')}: {t('config.enabled') if config.get('summary') else t('config.disabled')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.markdown_label')}: {t('config.enabled') if config.get('markdown', True) else t('config.disabled')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('config.no_config_loaded')}{COLOR_RESET}")
        
        else:
            print(f"{COLOR_RED}{t('config.unknown_command', command=subcommand)}{COLOR_RESET}")
        
        return True
    
    def handle_lang_command(self, command: str) -> None:
        """处理语言切换命令"""
        from i18n import set_language, get_language, get_available_languages
        
        parts = command.split()
        
        if len(parts) == 1:
            # 显示当前语言和可用语言
            current_lang = get_language()
            available_langs = get_available_languages()
            print(f"{COLOR_CYAN}{t('lang.current_language')}: {current_lang}{COLOR_RESET}")
            print(f"{COLOR_CYAN}{t('lang.available_languages')}: {', '.join(available_langs)}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('lang.usage_hint')}{COLOR_RESET}")
        elif len(parts) == 2:
            new_lang = parts[1]
            available_langs = get_available_languages()
            
            if new_lang in available_langs:
                set_language(new_lang)
                print(f"{COLOR_GREEN}{t('lang.switched_to', language=new_lang)}{COLOR_RESET}")
                
                # 更新当前配置的语言设置
                if self.current_config and self.current_config_id:
                    self.current_config['language'] = new_lang
                    if self.config_manager.update_config(self.current_config_id, self.current_config):
                        print(f"{COLOR_BLUE}{t('lang.config_updated')}{COLOR_RESET}")
                    else:
                        print(f"{COLOR_RED}{t('lang.config_update_failed')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('lang.unsupported_language', language=new_lang)}{COLOR_RESET}")
                print(f"{COLOR_YELLOW}{t('lang.available_languages')}: {', '.join(available_langs)}{COLOR_RESET}")
        elif len(parts) == 3 and parts[1] == 'switch':
            # 支持 /lang switch <语言代码> 格式
            new_lang = parts[2]
            available_langs = get_available_languages()
            
            if new_lang in available_langs:
                set_language(new_lang)
                print(f"{COLOR_GREEN}{t('lang.switched_to', language=new_lang)}{COLOR_RESET}")
                
                # 更新当前配置的语言设置
                if self.current_config and self.current_config_id:
                    self.current_config['language'] = new_lang
                    if self.config_manager.update_config(self.current_config_id, self.current_config):
                        print(f"{COLOR_BLUE}{t('lang.config_updated')}{COLOR_RESET}")
                    else:
                        print(f"{COLOR_RED}{t('lang.config_update_failed')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('lang.unsupported_language', language=new_lang)}{COLOR_RESET}")
                print(f"{COLOR_YELLOW}{t('lang.available_languages')}: {', '.join(available_langs)}{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}{t('lang.invalid_usage')}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('lang.usage_hint')}{COLOR_RESET}")
    
    def handle_summary_command(self) -> bool:
        """处理主动总结命令"""
        if not self.history_manager:
            print(f"{COLOR_RED}{t('summary.history_not_enabled')}{COLOR_RESET}")
            return True
        
        # 显示历史记录状态
        info = self.history_manager.get_session_info()
        print(f"{COLOR_YELLOW}{t('summary.status_title')}{COLOR_RESET}")
        print(f"{COLOR_BLUE}{t('history.session_id_label')}: {info['session_id']}{COLOR_RESET}")
        print(f"{COLOR_BLUE}{t('history.message_count_label')}: {info['message_count']}{COLOR_RESET}")
        print(f"{COLOR_BLUE}{t('history.total_tokens_label')}: {info['total_tokens']}{COLOR_RESET}")
        
        # 显示总结统计信息
        if self.summarizer:
            stats = self.summarizer.get_summary_stats(self.history_manager.messages)
            print(f"{COLOR_BLUE}{t('history.summary_count_label')}: {stats['total_summaries']}{COLOR_RESET}")
            print(f"{COLOR_BLUE}{t('history.compression_ratio_label')}: {stats['compression_ratio']}{COLOR_RESET}")
        
        # 检查是否有足够的消息进行总结
        if len(self.history_manager.messages) <= 4:  # system + 至少3条对话
            print(f"{COLOR_YELLOW}{t('summary.insufficient_messages')}{COLOR_RESET}")
            return True
        
        # 二次确认
        print(f"\n{COLOR_YELLOW}{t('summary.confirm_prompt')}{COLOR_RESET}")
        confirm = input(f"{COLOR_CYAN}{t('summary.confirm_input')}{COLOR_RESET}").strip().lower()
        
        if confirm not in ['y', 'yes', '是', '确认']:
            print(f"{COLOR_YELLOW}{t('summary.cancelled')}{COLOR_RESET}")
            return True
        
        # 执行总结
        try:
            if not self.summarizer:
                # 即使未开启总结配置，也允许手动总结
                api_key = self.current_config.get('API_key')
                api_endpoint = self.current_config.get('API_endpoint')
                model = self.current_config.get('model', 'deepseek-chat')
                self.summarizer = create_summarizer(api_key, api_endpoint, model)
            
            print(f"\n{COLOR_YELLOW}{t('summary.generating')}{COLOR_RESET}")
            
            max_tokens_raw = self.current_config.get('max_tokens', 64000)
            max_tokens = self._parse_token_value(str(max_tokens_raw), 64000)
            keep_recent = 3  # 保留最近3条消息
        
            summary_msg, new_messages = self.summarizer.summarize_messages(
                self.history_manager.messages, keep_recent, max_tokens
            )
            
            if summary_msg:
                self.history_manager.messages = new_messages
                self.history_manager.total_tokens = sum(msg.get('tokens', 0) for msg in new_messages)
                self.history_manager.save_to_file()
                print(f"{COLOR_GREEN}{t('summary.manual_completed')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('summary.failed')}{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}{t('summary.generation_error', error=str(e))}{COLOR_RESET}")
        
        return True
    
    def handle_last_summary_command(self) -> bool:
        """处理查看上次总结内容命令"""
        if not self.history_manager:
            print(f"{COLOR_RED}{t('summary.history_not_enabled')}{COLOR_RESET}")
            return True
        
        # 查找最近的总结消息
        summaries = []
        for msg in reversed(self.history_manager.messages):
            if msg.get('type') == 'summary' and msg.get('role') == 'system':
                summaries.append(msg)
        
        if not summaries:
            print(f"{COLOR_YELLOW}{t('summary.no_summaries_found')}{COLOR_RESET}")
            return True
        
        # 显示最近的总结
        latest_summary = summaries[0]
        content = latest_summary.get('content', '')
        
        # 移除总结前缀
        prefix = t('summary.context_prefix')
        if content.startswith(prefix):
            content = content[len(prefix):].strip()
        
        print(f"{COLOR_YELLOW}{t('summary.last_summary_title')}{COLOR_RESET}")
        print(f"{COLOR_CYAN}{t('summary.timestamp_label')}: {latest_summary.get('timestamp', 'Unknown')}{COLOR_RESET}")
        
        # 显示总结元数据
        metadata = latest_summary.get('summary_metadata', {})
        if metadata:
            print(f"{COLOR_BLUE}{t('summary.original_messages_label')}: {metadata.get('original_message_count', 'Unknown')}{COLOR_RESET}")
            print(f"{COLOR_BLUE}{t('summary.original_tokens_label')}: {metadata.get('original_tokens', 'Unknown')}{COLOR_RESET}")
            print(f"{COLOR_BLUE}{t('summary.summary_tokens_label')}: {metadata.get('summarized_tokens', 'Unknown')}{COLOR_RESET}")
            print(f"{COLOR_BLUE}{t('summary.compression_ratio_label')}: {metadata.get('compression_ratio', 'Unknown')}{COLOR_RESET}")
        
        print(f"\n{COLOR_GREEN}{t('summary.content_label')}:{COLOR_RESET}")
        print(content)
        
        return True
    
    def handle_markdown_command(self, command: str) -> None:
        """处理Markdown渲染切换命令"""
        parts = command.split()
        
        if len(parts) == 1:
            # 显示当前Markdown渲染状态
            current_status = self.current_config.get('markdown', True)
            status_text = t('markdown.enabled') if current_status else t('markdown.disabled')
            print(f"{COLOR_CYAN}{t('markdown.current_status')}: {status_text}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('markdown.usage_hint')}{COLOR_RESET}")
        elif len(parts) == 2:
            option = parts[1].lower()
            
            if option in ['on', 'enable', '开启', '启用']:
                self.current_config['markdown'] = True
                if self.config_manager.update_config(self.current_config_id, self.current_config):
                    print(f"{COLOR_GREEN}{t('markdown.enabled_success')}{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}{t('markdown.update_failed')}{COLOR_RESET}")
            elif option in ['off', 'disable', '关闭', '禁用']:
                self.current_config['markdown'] = False
                if self.config_manager.update_config(self.current_config_id, self.current_config):
                    print(f"{COLOR_GREEN}{t('markdown.disabled_success')}{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}{t('markdown.update_failed')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('markdown.invalid_option', option=option)}{COLOR_RESET}")
                print(f"{COLOR_YELLOW}{t('markdown.usage_hint')}{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}{t('markdown.invalid_usage')}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('markdown.usage_hint')}{COLOR_RESET}")
    
    def handle_stream_command(self, command: str) -> None:
        """处理流式响应切换命令"""
        parts = command.split()
        
        if len(parts) == 1:
            # 显示当前流式响应状态
            current_status = self.current_config.get('stream', True)
            status_text = t('stream.enabled') if current_status else t('stream.disabled')
            print(f"{COLOR_CYAN}{t('stream.current_status')}: {status_text}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('stream.usage_hint')}{COLOR_RESET}")
        elif len(parts) == 2:
            option = parts[1].lower()
            
            if option in ['on', 'enable', '开启', '启用']:
                self.current_config['stream'] = True
                if self.config_manager.update_config(self.current_config_id, self.current_config):
                    print(f"{COLOR_GREEN}{t('stream.enabled_success')}{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}{t('stream.update_failed')}{COLOR_RESET}")
            elif option in ['off', 'disable', '关闭', '禁用']:
                self.current_config['stream'] = False
                if self.config_manager.update_config(self.current_config_id, self.current_config):
                    print(f"{COLOR_GREEN}{t('stream.disabled_success')}{COLOR_RESET}")
                else:
                    print(f"{COLOR_RED}{t('stream.update_failed')}{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}{t('stream.invalid_option', option=option)}{COLOR_RESET}")
                print(f"{COLOR_YELLOW}{t('stream.usage_hint')}{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}{t('stream.invalid_usage')}{COLOR_RESET}")
            print(f"{COLOR_YELLOW}{t('stream.usage_hint')}{COLOR_RESET}")
    
    def handle_command(self, user_input: str) -> bool:
        """处理用户命令"""
        if not user_input.startswith('/'):
            return False
        
        parts = user_input.split()
        command = parts[0].lower()
        
        if command == '/help':
            print(self.help_msg)
            return True
        
        elif command == '/clear':
            print("\033[H\033[J", end="")  # 清屏
            self.show_welcome()
            return True
        
        elif command == '/exit':
            if self.history_manager:
                self.history_manager.save_to_file()
            print(f"{COLOR_GREEN}{t('app.goodbye')}{COLOR_RESET}")
            sys.exit(0)
        
        elif command.startswith('/lang'):
            self.handle_lang_command(user_input)
            return True
        
        elif command.startswith('/markdown'):
            self.handle_markdown_command(user_input)
            return True
        
        elif command.startswith('/stream'):
            self.handle_stream_command(user_input)
            return True
        
        elif command == '/config':
            return self.handle_config_command(parts)
        
        elif command == '/history':
            if self.history_manager:
                info = self.history_manager.get_session_info()
                print(f"{COLOR_YELLOW}{t('history.status_title')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('history.session_id_label')}: {info['session_id']}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('history.message_count_label')}: {info['message_count']}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('history.total_tokens_label')}: {info['total_tokens']}{COLOR_RESET}")
                
                if self.summarizer:
                    stats = self.summarizer.get_summary_stats(self.history_manager.messages)
                    print(f"{COLOR_BLUE}{t('history.summary_count_label')}: {stats['total_summaries']}{COLOR_RESET}")
                    print(f"{COLOR_BLUE}{t('history.compression_ratio_label')}: {stats['compression_ratio']}{COLOR_RESET}")
            else:
                print(f"{COLOR_YELLOW}{t('history.not_enabled')}{COLOR_RESET}")
            return True
        
        elif command == '/new':
            if self.history_manager:
                new_session_id = self.history_manager.start_new_session()
                # 重新添加系统消息（确保包含时间信息并处理模板变量）
                system_prompt = self.current_config.get('system_Prompt', '')
                enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
                processed_prompt = process_template(enhanced_prompt)
                self.history_manager.add_message('system', processed_prompt)
                print(f"{COLOR_GREEN}{t('history.new_session_started', session_id=new_session_id)}{COLOR_RESET}")
            else:
                print(f"{COLOR_YELLOW}{t('history.cannot_create_session')}{COLOR_RESET}")
            return True
        
        elif command == '/summary':
            return self.handle_summary_command()
        
        elif command == '/last_summary':
            return self.handle_last_summary_command()
        
        elif command == '/refresh':
            from markdown_renderer import refresh_display
            refresh_display()
            print(f"{COLOR_GREEN}{t('refresh.completed')}{COLOR_RESET}")
            return True
        
        elif command == '/version':
            print(f"{COLOR_CYAN}{t('version.title')}{COLOR_RESET}")
            print(f"{COLOR_GREEN}{t('version.description')}{COLOR_RESET}")
            print()
            print(f"{COLOR_YELLOW}{t('version.version_info', version=VERSION)}{COLOR_RESET}")
            print(f"{COLOR_BLUE}{t('version.repository')}{COLOR_RESET}")
            return True
        
        else:
            print(f"{COLOR_RED}{t('commands.unknown_command', command=command)}{COLOR_RESET}")
            return True
    
    def show_welcome(self):
        """显示欢迎信息"""
        if self.current_config:
            ai_name = self.current_config.get('ai_name', 'AI')
            config_name = self.config_manager.get_multilang_field(self.current_config, 'name')
            welcome_message = self.config_manager.get_multilang_field(self.current_config, 'welcome_message')
            print(f"{COLOR_GREEN}{t('app.ai_greeting', ai_name=ai_name)}{COLOR_RESET}")
            print(f"{COLOR_GREEN}{t('app.current_config', name=config_name, id=self.current_config_id)}{COLOR_RESET}")
            print(f"{COLOR_GREEN}{welcome_message}{COLOR_RESET}")
        else:
            print(f"{COLOR_YELLOW}{t('app.welcome')}{COLOR_RESET}")
    
    def process_message(self, user_input: str):
        """处理用户消息"""
        if not self.current_config or not self.client:
            print(f"{COLOR_RED}{t('processing.load_config_first')}{COLOR_RESET}")
            return
        
        # 添加用户消息到历史记录
        if self.history_manager:
            self.history_manager.add_message('user', user_input)
        
        try:
            # 准备API消息
            if self.history_manager:
                messages = self.history_manager.get_messages_for_api()
            else:
                system_prompt = self.current_config.get('system_Prompt', '')
                enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
                processed_prompt = process_template(enhanced_prompt)
                messages = [
                    {"role": "system", "content": processed_prompt},
                    {"role": "user", "content": user_input}
                ]
            
            # 检查是否启用流式响应
            use_stream = self.current_config.get('stream', True)
            ai_name = self.current_config.get('ai_name', 'AI')
            
            if use_stream:
                # 流式响应 - 不显示"正在处理"消息，让Live组件直接处理
                ai_response = ""
                response = self.client.chat.completions.create(
                    model=self.current_config.get('model', 'deepseek-chat'),
                    messages=messages,
                    stream=True
                )
                
                # 对于流式响应，根据配置决定是否使用Markdown渲染
                use_markdown = self.current_config.get('markdown', True)
                if use_markdown:
                    ai_response = render_streaming_response(response, ai_name)
                else:
                    # 不使用Markdown，直接输出文本
                    ai_response = ""
                    print(f"\n{COLOR_BLUE}💬 {ai_name}{COLOR_RESET}")
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            print(content, end="", flush=True)
                            ai_response += content
                    print()  # 换行
            else:
                # 非流式响应 - 使用加载动画
                start_loading(t('processing.processing_request'))
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.current_config.get('model', 'deepseek-chat'),
                        messages=messages,
                        stream=False
                    )
                    
                    ai_response = response.choices[0].message.content
                finally:
                    # 确保停止加载动画
                    stop_loading()
                
                # 根据配置决定是否使用Markdown渲染
                use_markdown = self.current_config.get('markdown', True)
                if use_markdown:
                    render_ai_response(ai_response, ai_name)
                else:
                    # 不使用Markdown，直接输出文本
                    print(f"\n{COLOR_BLUE}💬 {ai_name}{COLOR_RESET}")
                    print(ai_response)
            
            # 添加AI回复到历史记录
            if self.history_manager:
                self.history_manager.add_message('assistant', ai_response)
                
                # 检查是否需要总结
                if self.summarizer and self.current_config.get('summary', False):
                    max_tokens_raw = self.current_config.get('max_tokens', 4000)
                    max_tokens = self._parse_token_value(str(max_tokens_raw), 4000)
                    
                    if self.summarizer.should_summarize(self.history_manager.get_total_tokens(), max_tokens):
                        print(f"\n{COLOR_YELLOW}{t('summary.generating')}{COLOR_RESET}")
                        
                        keep_recent = 3  # 保留最近3条消息
                        summary_msg, new_messages = self.summarizer.summarize_messages(
                            self.history_manager.messages, keep_recent, max_tokens
                        )
                        
                        if summary_msg:
                            self.history_manager.messages = new_messages
                            self.history_manager.total_tokens = sum(msg.get('tokens', 0) for msg in new_messages)
                            print(f"{COLOR_GREEN}{t('summary.completed')}{COLOR_RESET}")
                        else:
                            print(f"{COLOR_YELLOW}{t('summary.failed')}{COLOR_RESET}")
                
                # 保存历史记录
                self.history_manager.save_to_file()
        
        except Exception as e:
            print(f"\n{COLOR_RED}{t('processing.error', error=str(e))}{COLOR_RESET}")
    
    def run_simple_mode(self, args):
        """极简模式运行"""
        if not args.prompt:
            stop_loading()
            print(f"{COLOR_RED}{t('simple_mode.prompt_required')}{COLOR_RESET}")
            return
        
        # 使用临时配置，优先使用命令行参数，其次使用默认配置
        api_key = args.key
        api_endpoint = args.endpoint
        model = args.model
        
        # 如果没有提供命令行参数，尝试从默认配置获取
        if not api_key or not api_endpoint or not model:
            default_config = None
            if self.config_manager.default_config_id:
                default_config = self.config_manager.get_config(self.config_manager.default_config_id)
            
            if default_config:
                api_key = api_key or default_config.get('API_key')
                api_endpoint = api_endpoint or default_config.get('API_endpoint')
                model = model or default_config.get('model', 'deepseek-chat')
        
        # 设置默认值
        api_key = api_key or "your_api_key_here"
        api_endpoint = api_endpoint or "https://api.deepseek.com"
        model = model or "deepseek-chat"
        
        if api_key == "your_api_key_here":
            stop_loading()
            print(f"{COLOR_RED}{t('simple_mode.api_key_required')}{COLOR_RESET}")
            return
        
        if not self.validate_api(api_key, api_endpoint):
            stop_loading()
            return
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=api_endpoint)
            
            # 为极简模式添加基本的系统提示词和时间信息
            system_prompt = t('simple_mode.default_system_prompt')
            enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
            processed_prompt = process_template(enhanced_prompt)
            stop_loading()
            
            # 根据参数决定是否使用流式响应
            use_stream = not args.unstream

            if not use_stream:
                start_loading(t('processing.processing_request'))
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": processed_prompt},
                    {"role": "user", "content": args.prompt}
                ],
                stream=use_stream
            )
            
            # 根据参数决定输出方式
            if args.unstream:
                # 非流式响应
                if args.nomd:
                    stop_loading()
                    # 直接输出原始文本，不使用Markdown格式化
                    print(response.choices[0].message.content)
                else:
                    # 使用Markdown格式化但非流式
                    stop_loading()
                    from markdown_renderer import render_markdown
                    render_markdown(response.choices[0].message.content)
            else:
                # 流式响应
                if args.nomd:
                    # 流式输出但不使用Markdown格式化
                    for chunk in response:
                        if chunk.choices[0].delta.content is not None:
                            print(chunk.choices[0].delta.content, end='', flush=True)
                    print()  # 换行
                else:
                    # 流式Markdown渲染
                    render_streaming_response(response, t('simple_mode.ai_reply'))
            
        except Exception as e:
            stop_loading()
            print(f"{COLOR_RED}{t('simple_mode.processing_error', error=str(e))}{COLOR_RESET}")
    
    def run_interactive_mode(self, config_id: str = None):
        """交互模式运行"""
        # 加载配置
        if config_id:
            if not self.load_config(config_id):
                print(f"{COLOR_YELLOW}{t('startup.using_default_config')}{COLOR_RESET}")
                config_id = self.config_manager.default_config_id
        else:
            config_id = self.config_manager.default_config_id
        
        # 如果没有配置或加载失败，进行首次配置
        if not self.current_config:
            if not self.config_manager.configs:
                stop_loading()
                print(f"{COLOR_YELLOW}{t('startup.first_time_setup')}{COLOR_RESET}")
                
                # 首次使用时先选择语言
                self.select_initial_language()
                
                config_data = self.input_config_interactive()
                if config_data:
                    self.config_manager.add_config(config_id, config_data)
                    self.config_manager.set_default_config(config_id)
                    self.load_config(config_id)
                else:
                    print(f"{COLOR_RED}{t('startup.config_creation_failed')}{COLOR_RESET}")
                    return
            else:
                if not self.load_config(config_id):
                    stop_loading()
                    print(f"{COLOR_RED}{t('startup.cannot_load_config')}{COLOR_RESET}")
                    return
        
        # 清屏并显示欢迎信息
        print("\033[H\033[J", end="")
        stop_loading()
        self.show_welcome()
        
        # 主循环
        while True:
            try:
                ai_name = self.current_config.get('ai_name', 'AI')
                prompt_text = f"\n{COLOR_YELLOW}{t('app.send_message_prompt', ai_name=ai_name)}{COLOR_RESET}\n"
                
                # 使用多行输入函数
                user_input = get_multiline_input(prompt_text)
                
                if not user_input.strip():
                    print(f"{COLOR_RED}{t('app.input_cannot_be_empty')}{COLOR_RESET}")
                    continue
                
                # 处理命令
                if self.handle_command(user_input):
                    continue
                
                # 处理普通消息
                self.process_message(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{COLOR_YELLOW}{t('app.program_interrupted')}{COLOR_RESET}")
                if self.history_manager:
                    self.history_manager.save_to_file()
                break
            except EOFError:
                print(f"\n{COLOR_GREEN}{t('app.goodbye')}{COLOR_RESET}")
                if self.history_manager:
                    self.history_manager.save_to_file()
                break

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description=t('args.description'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t('args.examples')
    )
    
    parser.add_argument('--config', '-c', type=str, help=t('args.config_help'))
    parser.add_argument('--list', '-l', action='store_true', help=t('args.list_help'))
    parser.add_argument('--simple', '-s', action='store_true', help=t('args.simple_help'))
    parser.add_argument('--key', type=str, help=t('args.key_help'))
    parser.add_argument('--endpoint', type=str, help=t('args.endpoint_help'))
    parser.add_argument('--model', '-m', type=str, help=t('args.model_help'))
    parser.add_argument('--prompt', '-p', type=str, help=t('args.prompt_help'))
    parser.add_argument('--nomd', '-n', action='store_true', help=t('args.nomd_help'))
    parser.add_argument('--unstream', '-u', action='store_true', help=t('args.unstream_help'))
    
    return parser.parse_args()

def main():
    """主函数"""
    try:
        # 先初始化i18n
        init_i18n()
        
        # 包装parse_arguments调用以处理--help等参数的SystemExit异常
        try:
            args = parse_arguments()
        except SystemExit as e:
            # argparse在显示帮助信息后会抛出SystemExit异常
            # 确保在退出前停止加载动画
            stop_loading()
            raise e
        
        tool = ChatTool()
        
        # 尝试从配置文件中获取语言设置（复用ChatTool中的config_manager）
        if tool.config_manager.configs:
            # 获取默认配置的语言设置
            default_config = tool.config_manager.get_config(tool.config_manager.default_config_id)
            if default_config and 'language' in default_config:
                set_language(default_config['language'])
        
        # 列出配置
        if args.list:
            configs = tool.config_manager.list_configs()
            stop_loading()
            if not configs:
                print(f"{COLOR_YELLOW}{t('config.no_configs_available')}{COLOR_RESET}")
            else:
                print(f"{COLOR_YELLOW}{t('config.available_configs')}{COLOR_RESET}")
                for config_id, name, aliases in configs:
                    alias_str = f" ({t('config.alias_label')}: {', '.join(aliases)})" if aliases else ""
                    print(f"{COLOR_BLUE}- {config_id}: {name}{alias_str}{COLOR_RESET}")
            return
        
        # 极简模式
        if args.simple:
            tool.run_simple_mode(args)
            stop_loading()
            return
        
        # 交互模式
        tool.run_interactive_mode(args.config)

    except KeyboardInterrupt:
        # 处理用户中断
        stop_loading()
        print(f"\n{COLOR_YELLOW}程序被用户中断{COLOR_RESET}")
        sys.exit(0)
    except Exception as e:
        # 如果启动过程中出错，确保停止加载动画
        stop_loading()
        print(f"\n{COLOR_RED}程序启动失败: {str(e)}{COLOR_RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()