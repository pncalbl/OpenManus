"""
进度显示组件

提供多种风格的进度显示（rich、simple、minimal）。
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from app.progress.events import ProgressEvent, ProgressEventType


def detect_terminal_capabilities() -> str:
    """
    检测终端能力，自动选择显示风格

    Returns:
        "rich", "simple", 或 "minimal"
    """
    # 检查是否为 TTY
    if not sys.stdout.isatty():
        return "minimal"

    # 检查终端类型
    term = os.environ.get("TERM", "")
    if term in ["dumb", "unknown"]:
        return "minimal"

    # 检查颜色支持
    if sys.platform == "win32":
        # Windows 10+ 通常支持 ANSI
        return "rich"

    # 其他 Unix-like 系统
    return "rich"


class ProgressDisplay:
    """
    进度显示组件

    负责渲染进度条、状态信息和中间结果。
    """

    def __init__(
        self,
        style: Optional[str] = None,
        show_percentage: bool = True,
        show_eta: bool = True,
        show_steps: bool = True,
        show_intermediate_results: bool = True,
        intermediate_results_max_length: int = 200,
    ):
        """
        初始化显示组件

        Args:
            style: 显示风格 ("rich", "simple", "minimal")，None 则自动检测
            show_percentage: 是否显示百分比
            show_eta: 是否显示预估剩余时间
            show_steps: 是否显示步骤计数
            show_intermediate_results: 是否显示中间结果
            intermediate_results_max_length: 中间结果最大长度
        """
        self.style = style or detect_terminal_capabilities()
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.show_steps = show_steps
        self.show_intermediate_results = show_intermediate_results
        self.intermediate_results_max_length = intermediate_results_max_length

        # 初始化 rich 组件（如果需要）
        self._console = None
        self._progress = None
        self._task_ids: Dict[Any, Any] = {}

        if self.style == "rich":
            self._init_rich()

    def _init_rich(self) -> None:
        """初始化 Rich 组件"""
        try:
            from rich.console import Console
            from rich.progress import (
                BarColumn,
                Progress,
                SpinnerColumn,
                TextColumn,
                TimeRemainingColumn,
            )

            self._console = Console()

            # 构建进度条列
            columns = [
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
            ]

            if self.show_steps:
                columns.append(TextColumn("[cyan]{task.completed}/{task.total}"))

            columns.append(BarColumn())

            if self.show_percentage:
                columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))

            if self.show_eta:
                columns.append(TimeRemainingColumn())

            self._progress = Progress(*columns, console=self._console)
            self._progress.start()

        except ImportError:
            # Rich 未安装，降级到 simple 模式
            print("Warning: rich library not installed, falling back to simple mode")
            self.style = "simple"

    def create_task(
        self,
        tracker: "ProgressTracker",  # Forward reference
        description: str,
        total: Optional[int] = None,
    ) -> Any:
        """
        创建进度任务

        Args:
            tracker: 进度追踪器
            description: 任务描述
            total: 总步骤数

        Returns:
            任务 ID（用于后续更新）
        """
        if self.style == "rich" and self._progress:
            task_id = self._progress.add_task(description, total=total or 100)
            self._task_ids[tracker] = task_id
            return task_id
        return None

    def update_task(
        self,
        tracker: "ProgressTracker",
        advance: Optional[int] = None,
        completed: Optional[int] = None,
        description: Optional[str] = None,
        total: Optional[int] = None,
    ) -> None:
        """
        更新任务进度

        Args:
            tracker: 进度追踪器
            advance: 增量进度
            completed: 完成的步骤数
            description: 新的描述
            total: 新的总数
        """
        if self.style == "rich" and self._progress:
            task_id = self._task_ids.get(tracker)
            if task_id is not None:
                kwargs = {}
                if advance is not None:
                    kwargs["advance"] = advance
                if completed is not None:
                    kwargs["completed"] = completed
                if description is not None:
                    kwargs["description"] = description
                if total is not None:
                    kwargs["total"] = total

                self._progress.update(task_id, **kwargs)

        elif self.style == "simple":
            # 简单文本输出
            if description:
                timestamp = datetime.now().strftime("%H:%M:%S")
                if tracker.total_steps:
                    percentage = tracker.percentage
                    steps_info = f"[{percentage:>3.0f}%] {tracker.current_step}/{tracker.total_steps}"
                    print(f"[{timestamp}] {steps_info} {description}")
                else:
                    print(f"[{timestamp}] {description}")

    def complete_task(self, tracker: "ProgressTracker", message: str = "") -> None:
        """
        完成任务

        Args:
            tracker: 进度追踪器
            message: 完成消息
        """
        if self.style == "rich" and self._progress:
            task_id = self._task_ids.get(tracker)
            if task_id is not None:
                # 设置为 100%
                self._progress.update(task_id, completed=tracker.total_steps or 100)

                # 显示完成消息
                if message:
                    self.show_status(message, "success")

        elif self.style == "simple":
            duration_text = self._format_duration(tracker.duration)
            msg = message or "Completed"
            print(f"✓ {msg} (took {duration_text})")

        elif self.style == "minimal":
            print(f"Completed in {self._format_duration(tracker.duration)}")

    def show_status(
        self,
        message: str,
        status: str = "info",
        style_override: Optional[str] = None,
    ) -> None:
        """
        显示状态消息

        Args:
            message: 消息内容
            status: 状态类型 (info, success, warning, error)
            style_override: 覆盖当前显示风格
        """
        display_style = style_override or self.style

        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        icon = icons.get(status, "•")

        if display_style == "rich" and self._console:
            colors = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
            }
            color = colors.get(status, "white")
            self._console.print(f"[{color}]{icon}[/{color}] {message}")

        else:
            # simple 和 minimal 都使用简单文本
            print(f"{icon} {message}")

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
            category: 结果类别
        """
        if not self.show_intermediate_results:
            return

        # 截断过长的内容
        if len(content) > self.intermediate_results_max_length:
            content = content[: self.intermediate_results_max_length] + "..."

        if self.style == "rich" and self._console:
            # 使用 Rich Panel
            try:
                from rich.panel import Panel

                # 根据类别选择颜色
                colors = {
                    "result": "green",
                    "error": "red",
                    "warning": "yellow",
                    "info": "blue",
                }
                color = colors.get(category, "white")

                panel = Panel(
                    content,
                    title=f"[bold]{title}[/bold]",
                    border_style=color,
                )
                self._console.print(panel)
            except Exception:
                # Fallback 到简单显示
                print(f"\n{title}:")
                print(content)
                print()

        else:
            # simple 和 minimal
            print(f"\n{title}:")
            print(content)
            print()

    def stop(self) -> None:
        """停止显示"""
        if self._progress:
            self._progress.stop()

    def _format_duration(self, seconds: float) -> str:
        """
        格式化持续时间

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串
        """
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def _format_eta(self, eta: Optional[float]) -> str:
        """
        格式化预估时间

        Args:
            eta: 预估剩余秒数

        Returns:
            格式化的 ETA 字符串
        """
        if eta is None:
            return "?"

        return self._format_duration(eta)


class ProgressEventHandler:
    """
    进度事件处理器

    监听进度事件并更新显示。
    """

    def __init__(self, display: ProgressDisplay):
        """
        初始化事件处理器

        Args:
            display: 显示组件
        """
        self.display = display
        self._active_trackers: Dict[Any, bool] = {}

    def handle_event(self, event: ProgressEvent) -> None:
        """
        处理进度事件

        Args:
            event: 进度事件
        """
        tracker = event.tracker

        if event.event_type == ProgressEventType.STARTED:
            # 创建任务
            self.display.create_task(
                tracker=tracker,
                description=event.data.get("description", ""),
                total=event.data.get("total_steps"),
            )
            self._active_trackers[tracker] = True

        elif event.event_type == ProgressEventType.UPDATED:
            # 更新任务
            message = event.data.get("message", "")
            if message:
                description = f"{tracker.description}: {message}"
            else:
                description = tracker.description

            self.display.update_task(
                tracker=tracker,
                completed=event.data.get("step"),
                description=description,
                total=event.data.get("total"),
            )

        elif event.event_type == ProgressEventType.COMPLETED:
            # 完成任务
            self.display.complete_task(
                tracker=tracker,
                message=event.data.get("message", ""),
            )
            self._active_trackers.pop(tracker, None)

        elif event.event_type == ProgressEventType.FAILED:
            # 失败
            error_msg = event.data.get("message") or event.data.get("error", "Unknown error")
            self.display.show_status(f"Failed: {error_msg}", "error")
            self._active_trackers.pop(tracker, None)

        elif event.event_type == ProgressEventType.STEP_STARTED:
            # 步骤开始
            step_name = event.data.get("step_name", "")
            if step_name:
                self.display.update_task(
                    tracker=tracker,
                    description=f"{tracker.description}: {step_name}",
                )

        elif event.event_type == ProgressEventType.STEP_COMPLETED:
            # 步骤完成
            step_name = event.data.get("step_name", "")
            result = event.data.get("result")
            if result:
                self.display.show_status(f"✓ {step_name}: {result}", "success")

        elif event.event_type == ProgressEventType.INTERMEDIATE_RESULT:
            # 中间结果
            self.display.show_intermediate_result(
                title=event.data.get("title", "Result"),
                content=event.data.get("content", ""),
                category=event.data.get("category", "result"),
            )

        elif event.event_type == ProgressEventType.MESSAGE:
            # 消息
            text = event.data.get("text", "")
            level = event.data.get("level", "info")
            self.display.show_status(text, level)

    def cleanup(self) -> None:
        """清理资源"""
        self.display.stop()
        self._active_trackers.clear()
