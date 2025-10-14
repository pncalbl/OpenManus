"""
进度事件系统

定义进度事件类型、事件类和事件总线。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProgressEventType(Enum):
    """进度事件类型"""

    STARTED = "started"  # 任务开始
    UPDATED = "updated"  # 进度更新
    COMPLETED = "completed"  # 任务完成
    FAILED = "failed"  # 任务失败
    STEP_STARTED = "step_started"  # 步骤开始
    STEP_COMPLETED = "step_completed"  # 步骤完成
    INTERMEDIATE_RESULT = "intermediate_result"  # 中间结果
    MESSAGE = "message"  # 消息


class ProgressEvent:
    """
    进度事件

    包含事件类型、关联的追踪器、事件数据和时间戳。
    """

    def __init__(
        self,
        event_type: ProgressEventType,
        tracker: "ProgressTracker",  # Forward reference
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化进度事件

        Args:
            event_type: 事件类型
            tracker: 关联的进度追踪器
            data: 事件数据
        """
        self.event_type = event_type
        self.tracker = tracker
        self.data = data or {}
        self.timestamp = datetime.now()

    def __repr__(self) -> str:
        return f"ProgressEvent(type={self.event_type.value}, data={self.data})"


class ProgressEventBus:
    """
    进度事件总线

    负责管理事件监听器和发布事件。
    """

    def __init__(self):
        """初始化事件总线"""
        self.listeners: Dict[ProgressEventType, List[Callable[[ProgressEvent], None]]] = {}
        self._global_listeners: List[Callable[[ProgressEvent], None]] = []

    def subscribe(
        self,
        event_type: ProgressEventType,
        callback: Callable[[ProgressEvent], None],
    ) -> None:
        """
        订阅特定类型的事件

        Args:
            event_type: 要订阅的事件类型
            callback: 事件回调函数
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        订阅所有类型的事件

        Args:
            callback: 事件回调函数
        """
        self._global_listeners.append(callback)

    def unsubscribe(
        self,
        event_type: ProgressEventType,
        callback: Callable[[ProgressEvent], None],
    ) -> None:
        """
        取消订阅特定类型的事件

        Args:
            event_type: 事件类型
            callback: 要移除的回调函数
        """
        if event_type in self.listeners:
            try:
                self.listeners[event_type].remove(callback)
            except ValueError:
                pass

    def unsubscribe_all(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        取消订阅所有事件

        Args:
            callback: 要移除的回调函数
        """
        try:
            self._global_listeners.remove(callback)
        except ValueError:
            pass

    def publish(self, event: ProgressEvent) -> None:
        """
        发布事件

        Args:
            event: 要发布的事件
        """
        # 通知全局监听器
        for callback in self._global_listeners:
            try:
                callback(event)
            except Exception as e:
                # 避免回调错误影响其他监听器
                print(f"Error in global event callback: {e}")

        # 通知特定类型的监听器
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback for {event.event_type}: {e}")

    def clear(self) -> None:
        """清除所有监听器"""
        self.listeners.clear()
        self._global_listeners.clear()

    def get_listener_count(self, event_type: Optional[ProgressEventType] = None) -> int:
        """
        获取监听器数量

        Args:
            event_type: 事件类型，如果为 None 则返回总数

        Returns:
            监听器数量
        """
        if event_type is None:
            total = len(self._global_listeners)
            for listeners in self.listeners.values():
                total += len(listeners)
            return total
        else:
            return len(self.listeners.get(event_type, []))
