#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录模块 (history.py)
负责管理聊天历史记录的保存、加载和Token管理
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import tiktoken
from i18n import t

class ChatHistory:
    """聊天历史记录管理类"""
    
    def __init__(self, config_id: str, history_dir: str = "chat-history"):
        """
        初始化历史记录管理器
        
        Args:
            config_id: 配置ID
            history_dir: 历史记录目录
        """
        self.config_id = config_id
        self.history_dir = history_dir
        self.session_id = self._generate_session_id()
        self.messages = []
        self.total_tokens = 0
        self.model = "deepseek-chat"
        self.created_at = datetime.now().isoformat()
        
        # 确保历史记录目录存在
        os.makedirs(history_dir, exist_ok=True)
        
        # 初始化tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except:
            # 如果模型不支持，使用默认编码
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"sess_{timestamp}_{unique_id}"
    
    def _get_history_filename(self) -> str:
        """获取历史记录文件名"""
        date_str = datetime.now().strftime("%y%m%d")
        return f"{date_str}-{self.config_id}-{self.session_id}.json"
    
    def _get_history_filepath(self) -> str:
        """获取历史记录文件完整路径"""
        filename = self._get_history_filename()
        return os.path.join(self.history_dir, filename)
    
    def _count_tokens(self, text: str) -> int:
        """计算文本的Token数量"""
        try:
            return len(self.tokenizer.encode(str(text)))
        except Exception:
            # 如果编码失败，使用简单估算（1个Token约4个字符）
            return len(str(text)) // 4 + 1
    
    def add_message(self, role: str, content: str, message_type: str = "original") -> str:
        """
        添加消息到历史记录
        
        Args:
            role: 消息角色 (system/user/assistant)
            content: 消息内容
            message_type: 消息类型 (original/summary)
            
        Returns:
            消息ID
        """
        message_id = f"msg_{len(self.messages):03d}"
        tokens = self._count_tokens(content)
        
        message = {
            "id": message_id,
            "type": message_type,
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "tokens": tokens
        }
        
        self.messages.append(message)
        self.total_tokens += tokens
        
        return message_id
    
    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """
        获取用于API调用的消息格式
        
        Returns:
            适用于OpenAI API的消息列表
        """
        api_messages = []
        for msg in self.messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        return api_messages
    
    def get_total_tokens(self) -> int:
        """获取总Token数量"""
        return self.total_tokens
    
    def check_token_limit(self, max_tokens: int) -> bool:
        """
        检查是否超过Token限制
        
        Args:
            max_tokens: 最大Token限制
            
        Returns:
            是否超过限制
        """
        return self.total_tokens > max_tokens
    
    def is_over_token_limit(self, max_tokens: int) -> bool:
        """
        检查是否超过Token限制（别名方法）
        
        Args:
            max_tokens: 最大Token限制
            
        Returns:
            是否超过限制
        """
        return self.check_token_limit(max_tokens)
    
    def remove_old_messages(self, keep_recent: int = 5) -> int:
        """
        移除旧消息，保留最近的消息
        
        Args:
            keep_recent: 保留的最近消息数量
            
        Returns:
            移除的消息数量
        """
        if len(self.messages) <= keep_recent:
            return 0
        
        # 保留system消息和最近的消息
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        non_system_messages = [msg for msg in self.messages if msg["role"] != "system"]
        
        if len(non_system_messages) <= keep_recent:
            return 0
        
        # 计算需要移除的消息数量
        remove_count = len(non_system_messages) - keep_recent
        kept_messages = non_system_messages[remove_count:]
        
        # 重新计算Token数量
        self.messages = system_messages + kept_messages
        self.total_tokens = sum(msg["tokens"] for msg in self.messages)
        
        return remove_count
    
    def save_to_file(self) -> bool:
        """
        保存历史记录到文件
        
        Returns:
            是否保存成功
        """
        try:
            history_data = {
                "model": self.model,
                "created_at": self.created_at,
                "session_id": self.session_id,
                "config_id": self.config_id,
                "total_tokens": self.total_tokens,
                "messages": self.messages
            }
            
            filepath = self._get_history_filepath()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"{t('history.save_failed', error=str(e))}")
            return False
    
    def load_from_file(self, session_id_or_filepath: str) -> bool:
        """
        从文件加载历史记录
        
        Args:
            session_id_or_filepath: 会话ID或历史记录文件路径
            
        Returns:
            是否加载成功
        """
        try:
            # 如果是会话ID，需要查找对应的文件
            if not session_id_or_filepath.endswith('.json'):
                # 查找包含该会话ID的文件
                found_file = None
                if os.path.exists(self.history_dir):
                    for filename in os.listdir(self.history_dir):
                        if session_id_or_filepath in filename and filename.endswith('.json'):
                            found_file = os.path.join(self.history_dir, filename)
                            break
                
                if not found_file:
                    print(f"{t('history.session_file_not_found', session_id=session_id_or_filepath)}")
                    return False
                
                filepath = found_file
            else:
                filepath = session_id_or_filepath
            
            with open(filepath, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.model = history_data.get("model", "deepseek-chat")
            self.created_at = history_data.get("created_at", datetime.now().isoformat())
            self.session_id = history_data.get("session_id", self._generate_session_id())
            self.config_id = history_data.get("config_id", self.config_id)
            self.total_tokens = history_data.get("total_tokens", 0)
            self.messages = history_data.get("messages", [])
            
            return True
        except Exception as e:
            print(f"{t('history.load_failed', error=str(e))}")
            return False
    
    def get_recent_history_files(self, limit: int = 10) -> List[str]:
        """
        获取最近的历史记录文件列表
        
        Args:
            limit: 返回文件数量限制
            
        Returns:
            历史记录文件路径列表
        """
        try:
            if not os.path.exists(self.history_dir):
                return []
            
            # 获取所有历史记录文件
            files = []
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.json') and self.config_id in filename:
                    filepath = os.path.join(self.history_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    files.append((filepath, mtime))
            
            # 按修改时间排序，最新的在前
            files.sort(key=lambda x: x[1], reverse=True)
            
            return [filepath for filepath, _ in files[:limit]]
        except Exception as e:
            print(f"{t('history.get_files_failed', error=str(e))}")
            return []
    
    def start_new_session(self) -> str:
        """
        开始新的会话
        
        Returns:
            新的会话ID
        """
        # 保存当前会话
        if self.messages:
            self.save_to_file()
        
        # 重置会话状态
        self.session_id = self._generate_session_id()
        self.messages = []
        self.total_tokens = 0
        self.created_at = datetime.now().isoformat()
        
        return self.session_id
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        获取当前会话信息
        
        Returns:
            会话信息字典
        """
        return {
            "session_id": self.session_id,
            "config_id": self.config_id,
            "created_at": self.created_at,
            "total_tokens": self.total_tokens,
            "message_count": len(self.messages),
            "model": self.model
        }


def get_recent_history_files(history_dir: str, limit: int = 10) -> List[tuple]:
    """
    获取最近的历史记录文件列表
    
    Args:
        history_dir: 历史记录目录
        limit: 返回文件数量限制
        
    Returns:
        历史记录文件信息列表 [(filepath, session_id, timestamp), ...]
    """
    try:
        if not os.path.exists(history_dir):
            return []
        
        # 获取所有历史记录文件
        files = []
        for filename in os.listdir(history_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(history_dir, filename)
                mtime = os.path.getmtime(filepath)
                
                # 从文件名提取会话ID
                parts = filename.replace('.json', '').split('-')
                session_id = parts[-1] if len(parts) > 2 else filename.replace('.json', '')
                
                files.append((filepath, session_id, mtime))
        
        # 按修改时间排序，最新的在前
        files.sort(key=lambda x: x[2], reverse=True)
        
        return files[:limit]
    except Exception as e:
        print(f"{t('history.get_files_failed', error=str(e))}")
        return []


def start_new_session(config_id: str, history_dir: str = "chat-history") -> str:
    """
    开始新的会话
    
    Args:
        config_id: 配置ID
        history_dir: 历史记录目录
        
    Returns:
        新的会话ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"sess_{timestamp}_{unique_id}"


def create_history_manager(config_id: str, history_dir: str = "chat-history") -> ChatHistory:
    """
    创建历史记录管理器的工厂函数
    
    Args:
        config_id: 配置ID
        history_dir: 历史记录目录
        
    Returns:
        ChatHistory实例
    """
    return ChatHistory(config_id, history_dir)


if __name__ == "__main__":
    # 测试代码
    history = create_history_manager("Prompt_000")
    
    # 添加测试消息
    history.add_message("system", t('test.system_message'))
    history.add_message("user", t('test.user_message'))
    history.add_message("assistant", t('test.assistant_message'))
    
    # 显示会话信息
    print(f"{t('test.session_info')}:", history.get_session_info())
    
    # 保存到文件
    if history.save_to_file():
        print(t('test.save_success'))
    else:
        print(t('test.save_failed'))