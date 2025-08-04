#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加载动画模块
提供六点字符转圈的加载动画，支持独立线程运行
"""

import sys
import time
import threading
from typing import Optional

class LoadingAnimation:
    """加载动画类，使用六点字符实现转圈动画"""
    
    # 六点字符动画帧
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, interval: float = 0.1):
        """
        初始化加载动画
        
        Args:
            interval: 动画帧间隔时间（秒）
        """
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._message = ""
        self._lock = threading.Lock()
    
    def _animate(self):
        """动画循环函数"""
        frame_index = 0
        
        while not self._stop_event.is_set():
            with self._lock:
                # 清除当前行并显示动画
                frame = self.FRAMES[frame_index]
                output = f"\r{frame} {self._message}"
                sys.stdout.write(output)
                sys.stdout.flush()
            
            # 更新帧索引
            frame_index = (frame_index + 1) % len(self.FRAMES)
            
            # 等待指定间隔
            self._stop_event.wait(self.interval)
    
    def start(self, message: str = "加载中..."):
        """
        启动加载动画
        
        Args:
            message: 加载消息文本
        """
        if self._thread and self._thread.is_alive():
            return  # 已经在运行
        
        with self._lock:
            self._message = message
            self._stop_event.clear()
        
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
    
    def stop(self, clear_line: bool = True):
        """
        停止加载动画
        
        Args:
            clear_line: 是否清除当前行
        """
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)  # 等待最多1秒
        
        if clear_line:
            with self._lock:
                # 清除当前行
                sys.stdout.write("\r" + " " * (len(self._message) + 10) + "\r")
                sys.stdout.flush()
    
    def update_message(self, message: str):
        """
        更新加载消息
        
        Args:
            message: 新的加载消息
        """
        with self._lock:
            self._message = message
    
    def is_running(self) -> bool:
        """
        检查动画是否正在运行
        
        Returns:
            bool: 动画是否正在运行
        """
        return self._thread is not None and self._thread.is_alive()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()

# 全局加载动画实例
_global_loader: Optional[LoadingAnimation] = None
_loader_lock = threading.Lock()

def start_loading(message: str = "加载中...") -> LoadingAnimation:
    """
    启动全局加载动画
    
    Args:
        message: 加载消息
        
    Returns:
        LoadingAnimation: 加载动画实例
    """
    global _global_loader
    
    with _loader_lock:
        if _global_loader is None:
            _global_loader = LoadingAnimation()
        
        _global_loader.start(message)
        return _global_loader

def stop_loading(clear_line: bool = True):
    """
    停止全局加载动画
    
    Args:
        clear_line: 是否清除当前行
    """
    global _global_loader
    
    with _loader_lock:
        if _global_loader is not None:
            _global_loader.stop(clear_line)

def update_loading_message(message: str):
    """
    更新全局加载动画消息
    
    Args:
        message: 新的加载消息
    """
    global _global_loader
    
    with _loader_lock:
        if _global_loader is not None:
            _global_loader.update_message(message)

def is_loading() -> bool:
    """
    检查全局加载动画是否正在运行
    
    Returns:
        bool: 是否正在加载
    """
    global _global_loader
    
    with _loader_lock:
        return _global_loader is not None and _global_loader.is_running()

# 便捷的上下文管理器
class loading_context:
    """
    加载动画上下文管理器
    
    使用示例:
        with loading_context("正在处理..."):
            # 执行耗时操作
            time.sleep(2)
    """
    
    def __init__(self, message: str = "加载中..."):
        self.message = message
        self.loader = None
    
    def __enter__(self):
        self.loader = start_loading(self.message)
        return self.loader
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        stop_loading()

if __name__ == "__main__":
    # 测试代码
    print("测试加载动画...")
    
    # 测试基本功能
    loader = LoadingAnimation()
    loader.start("测试动画...")
    time.sleep(3)
    loader.update_message("更新消息...")
    time.sleep(2)
    loader.stop()
    
    print("\n测试完成！")
    
    # 测试上下文管理器
    print("\n测试上下文管理器...")
    with loading_context("上下文测试..."):
        time.sleep(2)
    
    print("\n所有测试完成！")