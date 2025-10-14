"""
实时进度反馈系统

提供实时任务进度追踪、显示和中断处理功能。
"""

from app.progress.events import ProgressEvent, ProgressEventBus, ProgressEventType
from app.progress.tracker import ProgressTracker


__all__ = [
    "ProgressTracker",
    "ProgressEvent",
    "ProgressEventBus",
    "ProgressEventType",
]

# 全局事件总线实例
_event_bus_instance = None


def get_event_bus() -> ProgressEventBus:
    """获取或创建全局事件总线实例"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = ProgressEventBus()
    return _event_bus_instance


def reset_event_bus():
    """重置全局事件总线（主要用于测试）"""
    global _event_bus_instance
    _event_bus_instance = None
