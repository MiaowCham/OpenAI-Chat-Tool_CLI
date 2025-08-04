#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能总结模块 (summary.py)
负责对聊天历史进行智能总结，优化Token使用
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI
from i18n import t

class ChatSummarizer:
    """聊天总结器类"""
    
    def __init__(self, api_key: str, api_endpoint: str, model: str = "deepseek-chat"):
        """
        初始化总结器
        
        Args:
            api_key: API密钥
            api_endpoint: API端点
            model: 使用的模型
        """
        self.client = OpenAI(api_key=api_key, base_url=api_endpoint)
        self.model = model
        
        # 总结提示词模板
        self.summary_prompt = t('summary.prompt_template')
    
    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        将消息格式化为适合总结的文本
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的对话文本
        """
        formatted_text = ""
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            # 跳过总结类型的消息
            if msg.get("type") == "summary":
                continue
            
            # 格式化角色名称
            if role == "system":
                role_name = t('summary.role_system')
            elif role == "user":
                role_name = t('summary.role_user')
            elif role == "assistant":
                role_name = t('summary.role_assistant')
            else:
                role_name = role
            
            # 添加到格式化文本
            if timestamp:
                formatted_text += f"[{timestamp[:19]}] {role_name}: {content}\n\n"
            else:
                formatted_text += f"{role_name}: {content}\n\n"
        
        return formatted_text.strip()
    
    def _create_summary_message(self, summary_content: str, 
                              summarized_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        创建总结消息对象
        
        Args:
            summary_content: 总结内容
            summarized_messages: 被总结的消息列表
            
        Returns:
            总结消息对象
        """
        # 计算被总结消息的Token数量
        original_tokens = sum(msg.get("tokens", 0) for msg in summarized_messages)
        
        # 获取被总结消息的ID列表
        summarized_ids = [msg.get("id", "") for msg in summarized_messages]
        
        # 计算总结内容的Token数量（简单估算）
        summary_tokens = len(summary_content) // 4 + 1
        
        summary_message = {
            "id": f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "summary",
            "role": "system",
            "content": f"{t('summary.context_prefix')}{summary_content}",
            "timestamp": datetime.now().isoformat(),
            "tokens": summary_tokens,
            "summary_metadata": {
                "trigger_reason": "token_threshold_reached",
                "original_tokens": original_tokens,
                "summarized_tokens": summary_tokens,
                "summarized_message_ids": summarized_ids,
                "summary_model": self.model,
                "compression_ratio": round(summary_tokens / original_tokens, 3) if original_tokens > 0 else 0
            }
        }
        
        return summary_message
    
    def summarize_messages(self, messages: List[Dict[str, Any]], 
                          keep_recent: int = 3) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        对消息列表进行总结
        
        Args:
            messages: 要总结的消息列表
            keep_recent: 保留最近的消息数量
            
        Returns:
            (总结消息, 保留的消息列表)
        """
        if len(messages) <= keep_recent + 1:  # +1 for system message
            return None, messages
        
        # 分离system消息和其他消息
        system_messages = [msg for msg in messages if msg.get("role") == "system" and msg.get("type") != "summary"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system" or msg.get("type") == "summary"]
        
        if len(non_system_messages) <= keep_recent:
            return None, messages
        
        # 确定要总结的消息和要保留的消息
        messages_to_summarize = non_system_messages[:-keep_recent] if keep_recent > 0 else non_system_messages
        messages_to_keep = non_system_messages[-keep_recent:] if keep_recent > 0 else []
        
        if not messages_to_summarize:
            return None, messages
        
        try:
            # 格式化对话历史
            conversation_text = self._format_messages_for_summary(messages_to_summarize)
            
            if not conversation_text.strip():
                return None, messages
            
            # 调用AI进行总结
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": self.summary_prompt.format(conversation_history=conversation_text)
                    }
                ],
                temperature=0.3,  # 较低的温度以获得更一致的总结
                max_tokens=1000   # 限制总结长度
            )
            
            summary_content = response.choices[0].message.content.strip()
            
            if not summary_content:
                return None, messages
            
            # 创建总结消息
            summary_message = self._create_summary_message(summary_content, messages_to_summarize)
            
            # 构建新的消息列表：system消息 + 总结消息 + 保留的消息
            new_messages = system_messages + [summary_message] + messages_to_keep
            
            return summary_message, new_messages
            
        except Exception as e:
            print(f"{t('summary.generation_error', error=str(e))}")
            return None, messages
    
    def should_summarize(self, total_tokens: int, max_tokens: int, 
                        threshold_ratio: float = 0.8) -> bool:
        """
        判断是否需要进行总结
        
        Args:
            total_tokens: 当前总Token数
            max_tokens: 最大Token限制
            threshold_ratio: 触发总结的阈值比例
            
        Returns:
            是否需要总结
        """
        return total_tokens >= (max_tokens * threshold_ratio)
    
    def get_summary_stats(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取总结统计信息
        
        Args:
            messages: 消息列表
            
        Returns:
            总结统计信息
        """
        summary_messages = [msg for msg in messages if msg.get("type") == "summary"]
        original_messages = [msg for msg in messages if msg.get("type") != "summary"]
        
        total_summaries = len(summary_messages)
        total_original_tokens = sum(msg.get("tokens", 0) for msg in original_messages)
        total_summary_tokens = sum(msg.get("tokens", 0) for msg in summary_messages)
        
        # 计算压缩比
        if total_summaries > 0:
            total_original_from_summaries = sum(
                msg.get("summary_metadata", {}).get("original_tokens", 0) 
                for msg in summary_messages
            )
            compression_ratio = (total_summary_tokens / total_original_from_summaries 
                               if total_original_from_summaries > 0 else 0)
        else:
            compression_ratio = 0
        
        return {
            "total_summaries": total_summaries,
            "original_message_count": len(original_messages),
            "total_original_tokens": total_original_tokens,
            "total_summary_tokens": total_summary_tokens,
            "compression_ratio": round(compression_ratio, 3),
            "total_tokens": total_original_tokens + total_summary_tokens
        }
    
    def extract_summary_content(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        提取所有总结内容
        
        Args:
            messages: 消息列表
            
        Returns:
            总结内容列表
        """
        summaries = []
        for msg in messages:
            if msg.get("type") == "summary" and msg.get("role") == "system":
                content = msg.get("content", "")
                # 移除总结前缀
                prefix = t('summary.context_prefix')
                if content.startswith(prefix):
                    content = content[len(prefix):].strip()
                summaries.append(content)
        return summaries


def create_summarizer(api_key: str, api_endpoint: str, model: str = "deepseek-chat") -> ChatSummarizer:
    """
    创建聊天总结器的工厂函数
    
    Args:
        api_key: API密钥
        api_endpoint: API端点
        model: 使用的模型
        
    Returns:
        ChatSummarizer实例
    """
    return ChatSummarizer(api_key, api_endpoint, model)


if __name__ == "__main__":
    # 测试代码
    import os
    
    # 注意：这里需要实际的API密钥进行测试
    api_key = "your_api_key_here"
    api_endpoint = "https://api.deepseek.com"
    
    if api_key != "your_api_key_here":
        summarizer = create_summarizer(api_key, api_endpoint)
        
        # 创建测试消息
        test_messages = [
            {
                "id": "msg_001",
                "type": "original",
                "role": "system",
                "content": t('test.system_message'),
                "timestamp": "2025-01-04T10:00:00",
                "tokens": 8
            },
            {
                "id": "msg_002",
                "type": "original",
                "role": "user",
                "content": t('test.user_question'),
                "timestamp": "2025-01-04T10:01:00",
                "tokens": 12
            },
            {
                "id": "msg_003",
                "type": "original",
                "role": "assistant",
                "content": t('test.assistant_response'),
                "timestamp": "2025-01-04T10:01:30",
                "tokens": 150
            }
        ]
        
        # 测试总结功能
        summary_msg, new_messages = summarizer.summarize_messages(test_messages, keep_recent=1)
        
        if summary_msg:
            print(t('test.summary_generated'))
            print(f"{t('test.summary_content')}: {summary_msg['content']}")
            print(f"{t('test.new_message_count')}: {len(new_messages)}")
        else:
            print(t('test.no_summary_generated'))
    else:
        print(t('test.set_valid_api_key'))