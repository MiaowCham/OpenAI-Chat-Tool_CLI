#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI Chat Tool CLI (octool_cli)
一个基于 OpenAI 库编写的一个简单的命令行 API 聊天工具，支持多种模型、多语言界面和智能功能
"""

# 版本信息
VERSION = "2.0.0"

import os
import sys
import time
import yaml
import argparse
from typing import Dict, Any, Optional, List
from openai import OpenAI

# 导入自定义模块
from history import create_history_manager, ChatHistory
from summary import create_summarizer, ChatSummarizer
from template import process_template
from i18n import init_i18n, t, set_language, get_language

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
        
        # 初始化i18n
        init_i18n()
        
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
- '/lang [language]': {t('commands.lang_desc')}
{COLOR_RESET}"""
    
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
        
        max_tokens = input(f"{COLOR_YELLOW}{t('input.max_tokens_prompt')}{COLOR_RESET}").strip()
        try:
            max_tokens = int(max_tokens) if max_tokens else 4000
        except ValueError:
            max_tokens = 4000
        
        summary_tokens = input(f"{COLOR_YELLOW}{t('input.summary_tokens_prompt')}{COLOR_RESET}").strip()
        try:
            summary_tokens = int(summary_tokens) if summary_tokens else 1000
        except ValueError:
            summary_tokens = 1000
        
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
            'summary_tokens': summary_tokens,
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
        self.client = OpenAI(api_key=api_key, base_url=api_endpoint)
        
        # 初始化历史记录管理器
        if config.get('history', False):
            self.history_manager = create_history_manager(config_id)
            self.history_manager.model = config.get('model', 'deepseek-chat')
            
            # 添加系统消息（确保包含时间信息并处理模板变量）
            system_prompt = config.get('system_Prompt', '')
            enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
            processed_prompt = process_template(enhanced_prompt)
            self.history_manager.add_message('system', processed_prompt)
        
        # 初始化总结器
        if config.get('summary', False) and config.get('history', False):
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
                print(f"{COLOR_BLUE}{t('config.name_label')}: {config.get('name', 'Unknown')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.ai_name_label')}: {config.get('ai_name', 'AI')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.model_label')}: {config.get('model', 'Unknown')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.history_label')}: {t('config.enabled') if config.get('history') else t('config.disabled')}{COLOR_RESET}")
                print(f"{COLOR_BLUE}{t('config.summary_label')}: {t('config.enabled') if config.get('summary') else t('config.disabled')}{COLOR_RESET}")
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
            
            print(f"\n{COLOR_BLUE}{t('processing.processing_request')}{COLOR_RESET}")
            
            # 调用API
            response = self.client.chat.completions.create(
                model=self.current_config.get('model', 'deepseek-chat'),
                messages=messages,
                stream=False
            )
            
            print("\033[F\033[K", end="")  # 清除"正在处理"行
            
            ai_name = self.current_config.get('ai_name', 'AI')
            ai_response = response.choices[0].message.content
            
            print(f"{COLOR_CYAN}{ai_name}:{COLOR_RESET}")
            print(ai_response)
            
            # 添加AI回复到历史记录
            if self.history_manager:
                self.history_manager.add_message('assistant', ai_response)
                
                # 检查是否需要总结
                if self.summarizer and self.current_config.get('summary', False):
                    max_tokens = self.current_config.get('max_tokens', 4000)
                    
                    if self.summarizer.should_summarize(self.history_manager.get_total_tokens(), max_tokens):
                        print(f"\n{COLOR_YELLOW}{t('summary.generating')}{COLOR_RESET}")
                        
                        keep_recent = 3  # 保留最近3条消息
                        summary_msg, new_messages = self.summarizer.summarize_messages(
                            self.history_manager.messages, keep_recent
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
            print(f"{COLOR_RED}{t('simple_mode.prompt_required')}{COLOR_RESET}")
            return
        
        # 使用临时配置
        api_key = args.key or "your_api_key_here"
        api_endpoint = args.endpoint or "https://api.deepseek.com"
        model = args.model or "deepseek-chat"
        
        if api_key == "your_api_key_here":
            print(f"{COLOR_RED}{t('simple_mode.api_key_required')}{COLOR_RESET}")
            return
        
        if not self.validate_api(api_key, api_endpoint):
            return
        
        try:
            client = OpenAI(api_key=api_key, base_url=api_endpoint)
            
            print(f"{COLOR_BLUE}{t('simple_mode.processing')}{COLOR_RESET}")
            
            # 为极简模式添加基本的系统提示词和时间信息
            system_prompt = t('simple_mode.default_system_prompt')
            enhanced_prompt = ensure_datetime_in_prompt(system_prompt)
            processed_prompt = process_template(enhanced_prompt)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": processed_prompt},
                    {"role": "user", "content": args.prompt}
                ],
                stream=False
            )
            
            print(f"\n{COLOR_CYAN}{t('simple_mode.ai_reply')}{COLOR_RESET}")
            print(response.choices[0].message.content)
            
        except Exception as e:
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
                    print(f"{COLOR_RED}{t('startup.cannot_load_config')}{COLOR_RESET}")
                    return
        
        # 清屏并显示欢迎信息
        print("\033[H\033[J", end="")
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
    
    return parser.parse_args()

def main():
    """主函数"""
    # 先初始化i18n
    init_i18n()
    
    # 尝试从配置文件中获取语言设置
    config_manager = ConfigManager()
    if config_manager.configs:
        # 获取默认配置的语言设置
        default_config = config_manager.get_config(config_manager.default_config_id)
        if default_config and 'language' in default_config:
            set_language(default_config['language'])
    
    args = parse_arguments()
    tool = ChatTool()
    
    # 列出配置
    if args.list:
        configs = tool.config_manager.list_configs()
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
        return
    
    # 交互模式
    tool.run_interactive_mode(args.config)

if __name__ == "__main__":
    main()