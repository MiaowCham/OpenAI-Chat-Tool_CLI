"""Markdown渲染模块
使用rich库在终端中渲染Markdown格式的文本
支持终端窗口大小变化时自动重新渲染
"""

import os
import signal
import platform
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from typing import Optional, Iterator, Any, Dict, List, Tuple
from dataclasses import dataclass
from threading import Lock

@dataclass
class RenderedContent:
    """渲染内容的缓存结构"""
    content: str
    title: str
    border_style: str
    content_type: str  # 'ai_response', 'user_message', 'system_message', 'error_message'
    is_markdown: bool = True

class MarkdownRenderer:
    """Markdown渲染器"""
    
    def __init__(self):
        self.console = Console()
        self.rendered_history: List[RenderedContent] = []  # 渲染历史缓存
        self.max_history = 50  # 最大缓存数量
        self._lock = Lock()  # 线程锁
        self._signal_handler_installed = False
        
        # 只在Unix系统上安装信号处理器
        if platform.system() != 'Windows':
            self._install_resize_handler()
    
    def _install_resize_handler(self) -> None:
        """安装窗口大小变化信号处理器"""
        try:
            if hasattr(signal, 'SIGWINCH') and not self._signal_handler_installed:
                signal.signal(signal.SIGWINCH, self._handle_resize)
                self._signal_handler_installed = True
        except (AttributeError, OSError) as e:
            # 如果信号不可用或安装失败，静默忽略
            pass
    
    def _handle_resize(self, signum, frame) -> None:
        """处理窗口大小变化信号"""
        try:
            with self._lock:
                if self.rendered_history:
                    # 清屏
                    self.console.clear()
                    
                    # 重新渲染最近的内容
                    recent_count = min(10, len(self.rendered_history))  # 只重新渲染最近10条
                    for rendered_content in self.rendered_history[-recent_count:]:
                        self._render_cached_content(rendered_content)
        except Exception:
            # 信号处理中不应该抛出异常
            pass
    
    def _render_cached_content(self, rendered_content: RenderedContent) -> None:
        """重新渲染缓存的内容"""
        try:
            title = Text(rendered_content.title, style=f"bold {rendered_content.border_style}")
            
            if rendered_content.is_markdown and rendered_content.content_type == 'ai_response':
                try:
                    markdown = Markdown(rendered_content.content)
                    content = markdown
                except Exception:
                    content = rendered_content.content
            else:
                content = rendered_content.content
            
            panel = Panel(
                content,
                title=title,
                title_align="left",
                border_style=rendered_content.border_style,
                padding=(0, 1)
            )
            
            self.console.print(panel)
        except Exception:
            # 渲染失败时静默忽略
            pass
    
    def _add_to_history(self, content: str, title: str, border_style: str, content_type: str, is_markdown: bool = True) -> None:
        """添加内容到渲染历史"""
        with self._lock:
            rendered_content = RenderedContent(
                content=content,
                title=title,
                border_style=border_style,
                content_type=content_type,
                is_markdown=is_markdown
            )
            
            self.rendered_history.append(rendered_content)
            
            # 限制历史记录数量
            if len(self.rendered_history) > self.max_history:
                self.rendered_history = self.rendered_history[-self.max_history:]
    
    def render_ai_response(self, content: str, ai_name: str = "AI") -> None:
        """渲染AI回复，支持Markdown格式
        
        Args:
            content: AI回复内容
            ai_name: AI名称
        """
        title_text = f"💬 {ai_name}"
        
        try:
            # 创建Markdown对象
            markdown = Markdown(content)
            
            # 创建标题
            title = Text(title_text, style="bold blue")
            
            # 使用Panel包装，提供更好的视觉效果
            panel = Panel(
                markdown,
                title=title,
                title_align="left",
                border_style="blue",
                padding=(0, 1)
            )
            
            # 渲染到终端
            self.console.print(panel)
            
            # 添加到渲染历史
            self._add_to_history(content, title_text, "blue", "ai_response", True)
            
        except Exception as e:
            # 如果Markdown渲染失败，回退到普通文本
            self.render_plain_text(content, ai_name)
    
    def render_streaming_response(self, stream: Iterator[Any], ai_name: str = "AI") -> str:
        """渲染流式AI回复，支持实时Markdown格式
        
        Args:
            stream: 流式响应迭代器
            ai_name: AI名称
            
        Returns:
            完整的AI回复内容
        """
        accumulated_content = ""
        title_text = f"💬 {ai_name}"
        title = Text(title_text, style="bold blue")
        
        # 初始化空的Panel
        initial_panel = Panel(
            "",
            title=title,
            title_align="left",
            border_style="blue",
            padding=(0, 1)
        )
        
        try:
            with Live(initial_panel, refresh_per_second=4, console=self.console) as live:
                for chunk in stream:
                    if hasattr(chunk, 'choices') and chunk.choices and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        accumulated_content += content
                        
                        # 尝试渲染Markdown，失败时显示纯文本
                        try:
                            markdown = Markdown(accumulated_content)
                            panel = Panel(
                                markdown,
                                title=title,
                                title_align="left",
                                border_style="blue",
                                padding=(0, 1)
                            )
                            live.update(panel)
                        except Exception:
                            # Markdown解析失败时显示纯文本
                            panel = Panel(
                                accumulated_content,
                                title=title,
                                title_align="left",
                                border_style="blue",
                                padding=(0, 1)
                            )
                            live.update(panel)
        except Exception as e:
            # 如果Live渲染失败，回退到普通显示
            self.render_plain_text(accumulated_content, ai_name)
        
        # 添加到渲染历史
        if accumulated_content:
            self._add_to_history(accumulated_content, title_text, "blue", "ai_response", True)
        
        return accumulated_content
    
    def render_plain_text(self, content: str, ai_name: str = "AI") -> None:
        """渲染普通文本（回退方案）
        
        Args:
            content: 文本内容
            ai_name: AI名称
        """
        title_text = f"💬 {ai_name}"
        title = Text(title_text, style="bold blue")
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style="blue",
            padding=(0, 1)
        )
        
        self.console.print(panel)
        
        # 添加到渲染历史
        self._add_to_history(content, title_text, "blue", "ai_response", False)
    
    def render_user_message(self, content: str, user_name: str = "You") -> None:
        """渲染用户消息
        
        Args:
            content: 用户消息内容
            user_name: 用户名称
        """
        title_text = f"👤 {user_name}"
        title = Text(title_text, style="bold green")
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style="green",
            padding=(0, 1)
        )
        
        self.console.print(panel)
        
        # 添加到渲染历史
        self._add_to_history(content, title_text, "green", "user_message", False)
    
    def render_system_message(self, content: str, message_type: str = "System") -> None:
        """渲染系统消息
        
        Args:
            content: 系统消息内容
            message_type: 消息类型
        """
        title_text = f"⚙️ {message_type}"
        title = Text(title_text, style="bold yellow")
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style="yellow",
            padding=(0, 1)
        )
        
        self.console.print(panel)
        
        # 添加到渲染历史
        self._add_to_history(content, title_text, "yellow", "system_message", False)
    
    def render_error_message(self, content: str) -> None:
        """渲染错误消息
        
        Args:
            content: 错误消息内容
        """
        title_text = "❌ Error"
        title = Text(title_text, style="bold red")
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style="red",
            padding=(0, 1)
        )
        
        self.console.print(panel)
        
        # 添加到渲染历史
        self._add_to_history(content, title_text, "red", "error_message", False)
    
    def print_separator(self) -> None:
        """打印分隔线"""
        self.console.print("─" * 80, style="dim")
    
    def print_newline(self) -> None:
        """打印空行"""
        self.console.print()

# 创建全局渲染器实例
markdown_renderer = MarkdownRenderer()

# 便捷函数
def render_ai_response(content: str, ai_name: str = "AI") -> None:
    """渲染AI回复的便捷函数"""
    markdown_renderer.render_ai_response(content, ai_name)

def render_streaming_response(stream: Iterator[Any], ai_name: str = "AI") -> str:
    """渲染流式AI回复的便捷函数"""
    return markdown_renderer.render_streaming_response(stream, ai_name)

def render_user_message(content: str, user_name: str = "You") -> None:
    """渲染用户消息的便捷函数"""
    markdown_renderer.render_user_message(content, user_name)

def render_system_message(content: str, message_type: str = "System") -> None:
    """渲染系统消息的便捷函数"""
    markdown_renderer.render_system_message(content, message_type)

def render_error_message(content: str) -> None:
    """渲染错误消息的便捷函数"""
    markdown_renderer.render_error_message(content)