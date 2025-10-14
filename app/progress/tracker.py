"""
进度追踪器核心模块

提供任务进度追踪、时间估算和子任务管理功能。
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.progress.events import ProgressEvent, ProgressEventType


class ProgressTracker:
    """
    进度追踪器

    负责追踪任务进度、时间信息、子任务管理和发送进度事件。
    """

    def __init__(
        self,
        total_steps: Optional[int] = None,
        description: str = "",
        parent: Optional["ProgressTracker"] = None,
        show_progress: bool = True,
        event_bus: Optional[Any] = None,
    ):
        """
        初始化进度追踪器

        Args:
            total_steps: 总步骤数（None 表示未知）
            description: 任务描述
            parent: 父追踪器（用于子任务）
            show_progress: 是否显示进度
            event_bus: 事件总线实例（如果为 None 则使用全局实例）
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.parent = parent
        self.show_progress = show_progress

        # 时间追踪
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self._step_start_times: Dict[int, float] = {}
        self._step_durations: List[float] = []

        # 子任务和元数据
        self.children: List[ProgressTracker] = []
        self.metadata: Dict[str, Any] = {}

        # 状态标志
        self._is_completed = False
        self._is_failed = False
        self._last_message = ""

        # 事件总线
        if event_bus is None:
            # 延迟导入避免循环依赖
            from app.progress import get_event_bus

            self._event_bus = get_event_bus()
        else:
            self._event_bus = event_bus

        # 发送开始事件
        self._emit_event(
            ProgressEventType.STARTED,
            {
                "description": description,
                "total_steps": total_steps,
            },
        )

    def update(
        self,
        step: Optional[int] = None,
        message: str = "",
        increment: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        更新进度

        Args:
            step: 直接设置步骤数（如果提供）
            message: 进度消息
            increment: 增量步骤数（当 step 为 None 时使用）
            metadata: 额外的元数据
        """
        if self._is_completed or self._is_failed:
            return

        # 记录当前步骤的完成时间
        if self.current_step in self._step_start_times:
            duration = time.time() - self._step_start_times[self.current_step]
            self._step_durations.append(duration)

        # 更新步骤
        if step is not None:
            self.current_step = step
        else:
            self.current_step += increment

        # 记录新步骤的开始时间
        self._step_start_times[self.current_step] = time.time()

        # 更新元数据
        if metadata:
            self.metadata.update(metadata)

        self._last_message = message

        # 发送更新事件
        self._emit_event(
            ProgressEventType.UPDATED,
            {
                "step": self.current_step,
                "total": self.total_steps,
                "message": message,
                "percentage": self.percentage,
                "eta": self.eta,
                "metadata": metadata,
            },
        )

    def start_step(self, step_name: str) -> None:
        """
        标记步骤开始

        Args:
            step_name: 步骤名称
        """
        if self._is_completed or self._is_failed:
            return

        self._emit_event(
            ProgressEventType.STEP_STARTED,
            {
                "step": self.current_step,
                "step_name": step_name,
            },
        )

    def complete_step(self, step_name: str, result: Optional[str] = None) -> None:
        """
        标记步骤完成

        Args:
            step_name: 步骤名称
            result: 步骤结果
        """
        if self._is_completed or self._is_failed:
            return

        self._emit_event(
            ProgressEventType.STEP_COMPLETED,
            {
                "step": self.current_step,
                "step_name": step_name,
                "result": result,
            },
        )

    def show_intermediate_result(
        self,
        title: str,
        content: str,
        category: str = "result",
    ) -> None:
        """
        显示中间结果

        Args:
            title: 结果标题
            content: 结果内容
            category: 结果类别（result, error, warning 等）
        """
        if not self.show_progress:
            return

        self._emit_event(
            ProgressEventType.INTERMEDIATE_RESULT,
            {
                "title": title,
                "content": content,
                "category": category,
            },
        )

    def message(self, text: str, level: str = "info") -> None:
        """
        发送消息事件

        Args:
            text: 消息文本
            level: 消息级别（info, warning, error, success）
        """
        if not self.show_progress:
            return

        self._emit_event(
            ProgressEventType.MESSAGE,
            {
                "text": text,
                "level": level,
            },
        )

    def start_subtask(
        self,
        description: str,
        total_steps: Optional[int] = None,
    ) -> "ProgressTracker":
        """
        创建并启动子任务

        Args:
            description: 子任务描述
            total_steps: 子任务总步骤数

        Returns:
            子任务追踪器
        """
        subtask = ProgressTracker(
            total_steps=total_steps,
            description=description,
            parent=self,
            show_progress=self.show_progress,
            event_bus=self._event_bus,
        )
        self.children.append(subtask)
        return subtask

    def complete(self, message: str = "") -> None:
        """
        标记任务完成

        Args:
            message: 完成消息
        """
        if self._is_completed or self._is_failed:
            return

        self.end_time = datetime.now()
        self._is_completed = True
        self._last_message = message or "Completed"

        # 如果有总步骤数，设置为完成
        if self.total_steps is not None:
            self.current_step = self.total_steps

        self._emit_event(
            ProgressEventType.COMPLETED,
            {
                "message": message,
                "duration": self.duration,
                "total_steps": self.current_step,
            },
        )

    def fail(self, error: Exception, message: str = "") -> None:
        """
        标记任务失败

        Args:
            error: 错误对象
            message: 失败消息
        """
        if self._is_completed or self._is_failed:
            return

        self.end_time = datetime.now()
        self._is_failed = True
        self._last_message = message or str(error)

        self._emit_event(
            ProgressEventType.FAILED,
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "message": message,
                "duration": self.duration,
                "completed_steps": self.current_step,
            },
        )

    def set_total_steps(self, total: int) -> None:
        """
        设置或更新总步骤数

        Args:
            total: 新的总步骤数
        """
        self.total_steps = total
        self.update(message="Updated total steps")

    @property
    def percentage(self) -> float:
        """
        计算完成百分比

        Returns:
            完成百分比 (0-100)
        """
        if self.total_steps is None or self.total_steps == 0:
            return 0.0
        return min(100.0, (self.current_step / self.total_steps) * 100)

    @property
    def duration(self) -> float:
        """
        计算持续时间（秒）

        Returns:
            持续时间
        """
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def eta(self) -> Optional[float]:
        """
        预估剩余时间（秒）

        Returns:
            预估剩余时间，如果无法估算则返回 None
        """
        if self.total_steps is None or self.current_step == 0:
            return None

        if self.current_step >= self.total_steps:
            return 0.0

        # 使用最近步骤的平均时间
        if len(self._step_durations) > 0:
            # 使用最近 5 个步骤的平均时间
            recent_durations = self._step_durations[-5:]
            avg_time_per_step = sum(recent_durations) / len(recent_durations)
        else:
            # 使用总体平均时间
            avg_time_per_step = self.duration / self.current_step

        remaining_steps = self.total_steps - self.current_step
        return avg_time_per_step * remaining_steps

    @property
    def is_completed(self) -> bool:
        """任务是否完成"""
        return self._is_completed

    @property
    def is_failed(self) -> bool:
        """任务是否失败"""
        return self._is_failed

    @property
    def is_running(self) -> bool:
        """任务是否正在运行"""
        return not (self._is_completed or self._is_failed)

    @property
    def last_message(self) -> str:
        """最后的消息"""
        return self._last_message

    def get_progress_info(self) -> Dict[str, Any]:
        """
        获取完整的进度信息

        Returns:
            包含所有进度信息的字典
        """
        return {
            "description": self.description,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "percentage": self.percentage,
            "duration": self.duration,
            "eta": self.eta,
            "is_completed": self.is_completed,
            "is_failed": self.is_failed,
            "is_running": self.is_running,
            "last_message": self.last_message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "metadata": self.metadata,
            "children_count": len(self.children),
        }

    def _emit_event(self, event_type: ProgressEventType, data: Dict[str, Any]) -> None:
        """
        发送进度事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if not self.show_progress:
            return

        event = ProgressEvent(
            event_type=event_type,
            tracker=self,
            data=data,
        )
        self._event_bus.publish(event)

    def __enter__(self) -> "ProgressTracker":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        if exc_type is None:
            if not self._is_completed:
                self.complete()
        else:
            if not self._is_failed:
                self.fail(exc_val or Exception("Unknown error"))

    def __repr__(self) -> str:
        status = "completed" if self._is_completed else "failed" if self._is_failed else "running"
        return f"ProgressTracker(description='{self.description}', step={self.current_step}/{self.total_steps}, status={status})"
