"""
优雅中断处理器

处理信号（SIGINT、SIGTERM）并实现优雅退出和状态保存。
"""

import json
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.logger import logger


class GracefulShutdownHandler:
    """
    优雅退出处理器

    处理中断信号（Ctrl+C），保存状态并优雅退出。
    """

    def __init__(
        self,
        tracker: Optional["ProgressTracker"] = None,  # noqa: F821
        save_state: bool = True,
        workspace_root: Optional[Path] = None,
    ):
        """
        初始化中断处理器

        Args:
            tracker: 进度追踪器实例
            save_state: 是否保存状态
            workspace_root: 工作空间根目录
        """
        self.tracker = tracker
        self.save_state = save_state
        self.workspace_root = workspace_root or Path("workspace")
        self.shutdown_requested = False
        self._original_handlers = {}

        # 注册信号处理器
        self.register_handlers()

    def register_handlers(self):
        """注册信号处理器"""
        try:
            # 保存原始处理器
            self._original_handlers[signal.SIGINT] = signal.signal(
                signal.SIGINT, self._handle_interrupt
            )

            # Windows 不支持 SIGTERM
            if hasattr(signal, "SIGTERM"):
                self._original_handlers[signal.SIGTERM] = signal.signal(
                    signal.SIGTERM, self._handle_interrupt
                )

            logger.debug("Interrupt handlers registered")
        except Exception as e:
            logger.warning(f"Failed to register interrupt handlers: {e}")

    def unregister_handlers(self):
        """恢复原始信号处理器"""
        try:
            for sig, handler in self._original_handlers.items():
                if handler is not None:
                    signal.signal(sig, handler)

            self._original_handlers.clear()
            logger.debug("Interrupt handlers unregistered")
        except Exception as e:
            logger.warning(f"Failed to unregister interrupt handlers: {e}")

    def _handle_interrupt(self, signum, frame):
        """
        处理中断信号

        Args:
            signum: 信号编号
            frame: 当前执行帧
        """
        if self.shutdown_requested:
            # 第二次 Ctrl+C，强制退出
            logger.warning("\n强制退出...")
            self.unregister_handlers()
            sys.exit(1)

        self.shutdown_requested = True
        signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else f"Signal {signum}"

        print(f"\n\n收到中断信号 ({signal_name})，正在优雅退出...")
        print("（再次按 Ctrl+C 强制退出）\n")

        # 标记追踪器失败
        if self.tracker and self.tracker.is_running:
            self.tracker.fail(
                Exception(f"Interrupted by {signal_name}"),
                message="Task interrupted by user"
            )

        # 保存当前状态
        if self.save_state and self.tracker:
            try:
                self._save_state()
                logger.info("✓ State saved successfully")
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

        # 优雅退出
        sys.exit(0)

    def _save_state(self):
        """保存当前状态到文件"""
        if not self.tracker:
            return

        # 确保工作空间目录存在
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # 准备状态数据
        state = {
            "interrupted_at": datetime.now().isoformat(),
            "description": self.tracker.description,
            "current_step": self.tracker.current_step,
            "total_steps": self.tracker.total_steps,
            "start_time": self.tracker.start_time.isoformat(),
            "duration": self.tracker.duration,
            "metadata": self.tracker.metadata,
            "last_message": self.tracker.last_message,
        }

        # 保存到文件
        state_file = self.workspace_root / ".interrupted_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 State saved to: {state_file}")

    @staticmethod
    def load_state(workspace_root: Optional[Path] = None) -> Optional[dict]:
        """
        从文件加载保存的状态

        Args:
            workspace_root: 工作空间根目录

        Returns:
            状态字典，如果文件不存在则返回 None
        """
        workspace_root = workspace_root or Path("workspace")
        state_file = workspace_root / ".interrupted_state.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            logger.info(f"📂 Loaded interrupted state from: {state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load interrupted state: {e}")
            return None

    @staticmethod
    def clear_state(workspace_root: Optional[Path] = None):
        """
        清除保存的状态文件

        Args:
            workspace_root: 工作空间根目录
        """
        workspace_root = workspace_root or Path("workspace")
        state_file = workspace_root / ".interrupted_state.json"

        if state_file.exists():
            try:
                state_file.unlink()
                logger.info(f"🗑️  Cleared interrupted state: {state_file}")
            except Exception as e:
                logger.error(f"Failed to clear interrupted state: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.unregister_handlers()
        return False  # 不抑制异常
