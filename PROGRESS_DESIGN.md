# 实时进度反馈系统 - 架构设计

## 1. 概述

### 1.1 目标

为 OpenManus 提供实时进度反馈功能，让用户在长时间运行的任务中能够：
- 实时了解任务执行进度
- 查看当前执行的步骤
- 看到中间结果输出
- 预估剩余时间
- 优雅地中断任务

### 1.2 设计原则

- **非侵入性**: 最小化对现有代码的修改
- **高性能**: 进度更新不应显著影响任务执行速度
- **可配置**: 用户可以控制进度显示的详细程度
- **优雅降级**: 在不支持的终端环境中自动降级为简单输出
- **异步友好**: 完全支持 async/await 模式

## 2. 核心模块设计

### 2.1 模块结构

```
app/progress/
├── __init__.py           # 模块入口，导出主要类
├── tracker.py            # 进度追踪器核心
├── display.py            # 显示组件（进度条、状态）
├── events.py             # 事件系统
├── formatters.py         # 输出格式化
└── README.md             # 使用文档
```

### 2.2 核心类设计

#### 2.2.1 ProgressTracker - 进度追踪器

```python
from typing import Optional, Callable, Any
from datetime import datetime
import time

class ProgressTracker:
    """
    进度追踪器 - 核心组件

    负责：
    - 追踪任务进度（步骤、百分比）
    - 记录时间信息（开始、结束、预估）
    - 发送进度事件
    - 管理子任务
    """

    def __init__(
        self,
        total_steps: Optional[int] = None,
        description: str = "",
        parent: Optional["ProgressTracker"] = None,
        show_progress: bool = True,
    ):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.parent = parent
        self.show_progress = show_progress

        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None

        self.children: list[ProgressTracker] = []
        self.metadata: dict[str, Any] = {}

    def update(
        self,
        step: Optional[int] = None,
        message: str = "",
        increment: int = 1,
    ):
        """更新进度"""
        if step is not None:
            self.current_step = step
        else:
            self.current_step += increment

        # 触发更新事件
        self._emit_event("update", {
            "step": self.current_step,
            "total": self.total_steps,
            "message": message,
            "percentage": self.percentage,
        })

    def start_subtask(
        self,
        description: str,
        total_steps: Optional[int] = None,
    ) -> "ProgressTracker":
        """创建子任务"""
        subtask = ProgressTracker(
            total_steps=total_steps,
            description=description,
            parent=self,
            show_progress=self.show_progress,
        )
        self.children.append(subtask)
        return subtask

    def complete(self, message: str = ""):
        """标记任务完成"""
        self.end_time = datetime.now()
        self._emit_event("complete", {
            "message": message,
            "duration": self.duration,
        })

    def fail(self, error: Exception):
        """标记任务失败"""
        self.end_time = datetime.now()
        self._emit_event("fail", {
            "error": str(error),
            "duration": self.duration,
        })

    @property
    def percentage(self) -> float:
        """计算完成百分比"""
        if self.total_steps is None or self.total_steps == 0:
            return 0.0
        return min(100.0, (self.current_step / self.total_steps) * 100)

    @property
    def duration(self) -> float:
        """计算持续时间（秒）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def eta(self) -> Optional[float]:
        """预估剩余时间（秒）"""
        if self.total_steps is None or self.current_step == 0:
            return None

        avg_time_per_step = self.duration / self.current_step
        remaining_steps = self.total_steps - self.current_step
        return avg_time_per_step * remaining_steps

    def _emit_event(self, event_type: str, data: dict):
        """发送进度事件"""
        # 通过事件系统发送
        pass
```

#### 2.2.2 ProgressDisplay - 显示组件

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich.table import Table

class ProgressDisplay:
    """
    进度显示组件

    负责：
    - 渲染进度条
    - 显示状态信息
    - 格式化输出
    - 处理终端兼容性
    """

    def __init__(
        self,
        style: str = "rich",  # "rich", "simple", "minimal"
        show_percentage: bool = True,
        show_eta: bool = True,
        show_steps: bool = True,
    ):
        self.style = style
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.show_steps = show_steps

        self.console = Console()
        self._init_display()

    def _init_display(self):
        """初始化显示组件"""
        if self.style == "rich":
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
            )
        elif self.style == "simple":
            self.progress = None  # 使用简单文本输出
        else:
            self.progress = None  # 最小输出

    def create_task(
        self,
        description: str,
        total: Optional[int] = None,
    ) -> Any:
        """创建进度任务"""
        if self.progress:
            return self.progress.add_task(description, total=total)
        return None

    def update_task(
        self,
        task_id: Any,
        advance: int = 1,
        description: Optional[str] = None,
    ):
        """更新任务进度"""
        if self.progress and task_id is not None:
            self.progress.update(
                task_id,
                advance=advance,
                description=description,
            )
        elif self.style == "simple":
            # 简单文本输出
            if description:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {description}")

    def show_status(self, message: str, status: str = "info"):
        """显示状态消息"""
        icons = {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        icon = icons.get(status, "•")

        if self.style == "rich":
            colors = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
            }
            color = colors.get(status, "white")
            self.console.print(f"[{color}]{icon}[/{color}] {message}")
        else:
            print(f"{icon} {message}")

    def show_intermediate_result(
        self,
        title: str,
        content: str,
        category: str = "result",
    ):
        """显示中间结果"""
        if self.style == "rich":
            table = Table(title=title, show_header=False)
            table.add_row(content)
            self.console.print(table)
        else:
            print(f"\n{title}:")
            print(content)
            print()
```

#### 2.2.3 ProgressEvent - 事件系统

```python
from typing import Callable, Dict, List
from enum import Enum

class ProgressEventType(Enum):
    """进度事件类型"""
    STARTED = "started"
    UPDATED = "updated"
    COMPLETED = "completed"
    FAILED = "failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    INTERMEDIATE_RESULT = "intermediate_result"

class ProgressEvent:
    """进度事件"""
    def __init__(
        self,
        event_type: ProgressEventType,
        tracker: "ProgressTracker",
        data: Dict[str, Any],
    ):
        self.event_type = event_type
        self.tracker = tracker
        self.data = data
        self.timestamp = datetime.now()

class ProgressEventBus:
    """进度事件总线"""

    def __init__(self):
        self.listeners: Dict[ProgressEventType, List[Callable]] = {}

    def subscribe(
        self,
        event_type: ProgressEventType,
        callback: Callable[[ProgressEvent], None],
    ):
        """订阅事件"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)

    def publish(self, event: ProgressEvent):
        """发布事件"""
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # 错误处理
                    pass
```

## 3. Agent 集成

### 3.1 集成点

在以下位置集成进度追踪：

1. **ToolCallAgent** (`app/agent/toolcall.py`)
   - 在 `run()` 方法开始时创建进度追踪器
   - 每次工具调用时更新进度
   - 显示工具调用结果
   - 在 cleanup 时完成进度

2. **Tool 基类** (`app/tool/base.py`)
   - 在工具执行前后发送事件
   - 报告工具执行进度

3. **LLM 调用** (`app/llm/`)
   - 流式输出时实时显示
   - 显示 token 使用情况

### 3.2 集成示例

```python
# app/agent/toolcall.py

class ToolCallAgent(Agent):
    def __init__(self, *args, progress_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_enabled = progress_enabled
        self.progress_tracker: Optional[ProgressTracker] = None
        self.progress_display: Optional[ProgressDisplay] = None

    async def run(self, prompt: str, **kwargs) -> str:
        """执行任务"""

        # 初始化进度追踪
        if self.progress_enabled:
            self.progress_tracker = ProgressTracker(
                description=f"Running: {prompt[:50]}...",
                total_steps=None,  # 动态调整
            )
            self.progress_display = ProgressDisplay(
                style=Config.progress_config.display_style
            )

        try:
            # 执行任务循环
            while not self.is_finished:
                # 显示当前步骤
                if self.progress_tracker:
                    self.progress_tracker.update(
                        message=f"Step {self.current_step}: {self.current_action}"
                    )

                # 调用工具
                result = await self._execute_tool(tool_call)

                # 显示中间结果
                if self.progress_display and Config.progress_config.show_intermediate_results:
                    self.progress_display.show_intermediate_result(
                        title=f"Tool: {tool_name}",
                        content=result[:200],  # 截断长结果
                    )

                # 继续下一步
                self.current_step += 1

            # 完成
            if self.progress_tracker:
                self.progress_tracker.complete(message="Task completed successfully")

            return result

        except Exception as e:
            # 失败
            if self.progress_tracker:
                self.progress_tracker.fail(error=e)
            raise
```

## 4. 配置设计

### 4.1 配置项

在 `config/config.toml` 中添加：

```toml
[progress]
# 启用进度反馈
enabled = true

# 显示风格: "rich" (丰富), "simple" (简单), "minimal" (最小)
display_style = "rich"

# 显示选项
show_percentage = true          # 显示百分比
show_eta = true                 # 显示预估剩余时间
show_steps = true               # 显示步骤计数
show_intermediate_results = true # 显示中间结果

# 中间结果配置
intermediate_results_max_length = 200  # 中间结果最大显示长度
intermediate_results_categories = [    # 显示哪些类型的中间结果
    "tool_result",
    "llm_response",
    "error",
]

# 刷新频率
refresh_rate = 0.1              # 进度条刷新频率（秒）

# 任务中断
enable_graceful_shutdown = true # 启用优雅退出（Ctrl+C）
save_state_on_interrupt = true  # 中断时保存状态
```

### 4.2 配置类

```python
# app/config.py

class ProgressSettings(BaseModel):
    """进度反馈配置"""

    # 基本设置
    enabled: bool = Field(True, description="Enable progress feedback")
    display_style: str = Field("rich", description="Display style: rich, simple, minimal")

    # 显示选项
    show_percentage: bool = Field(True, description="Show completion percentage")
    show_eta: bool = Field(True, description="Show estimated time remaining")
    show_steps: bool = Field(True, description="Show step counter")
    show_intermediate_results: bool = Field(True, description="Show intermediate results")

    # 中间结果
    intermediate_results_max_length: int = Field(200, description="Max length for intermediate results")
    intermediate_results_categories: list[str] = Field(
        default_factory=lambda: ["tool_result", "llm_response", "error"],
        description="Categories of intermediate results to show",
    )

    # 性能
    refresh_rate: float = Field(0.1, description="Progress bar refresh rate in seconds")

    # 中断处理
    enable_graceful_shutdown: bool = Field(True, description="Enable graceful shutdown on Ctrl+C")
    save_state_on_interrupt: bool = Field(True, description="Save state when interrupted")

    @validator("display_style")
    def validate_display_style(cls, v):
        if v not in ["rich", "simple", "minimal"]:
            raise ValueError("display_style must be 'rich', 'simple', or 'minimal'")
        return v
```

## 5. 优雅中断设计

### 5.1 信号处理

```python
import signal
import asyncio

class GracefulShutdownHandler:
    """优雅退出处理器"""

    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker
        self.shutdown_requested = False

        # 注册信号处理
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """处理中断信号"""
        if self.shutdown_requested:
            # 第二次 Ctrl+C，强制退出
            print("\n强制退出...")
            sys.exit(1)

        self.shutdown_requested = True
        print("\n正在优雅退出（再次按 Ctrl+C 强制退出）...")

        # 保存当前状态
        if Config.progress_config.save_state_on_interrupt:
            self._save_state()

    def _save_state(self):
        """保存当前状态"""
        state = {
            "current_step": self.tracker.current_step,
            "total_steps": self.tracker.total_steps,
            "start_time": self.tracker.start_time.isoformat(),
            "metadata": self.tracker.metadata,
        }
        # 保存到文件
        with open("workspace/.interrupted_state.json", "w") as f:
            json.dump(state, f, indent=2)
```

## 6. 实现阶段

### 第一阶段：核心模块（1-2 天）

- ✅ 创建 `app/progress/` 目录结构
- ✅ 实现 `ProgressTracker` 核心类
- ✅ 实现 `ProgressDisplay` 显示组件
- ✅ 实现 `ProgressEvent` 事件系统
- ✅ 添加单元测试

### 第二阶段：Agent 集成（1-2 天）

- ⏳ 修改 `ToolCallAgent` 集成进度追踪
- ⏳ 修改 `Tool` 基类添加进度事件
- ⏳ 修改 LLM 调用显示流式输出
- ⏳ 测试所有 entry points（main.py, run_mcp.py, run_flow.py）

### 第三阶段：优雅中断（1 天）

- ⏳ 实现信号处理
- ⏳ 实现状态保存
- ⏳ 实现状态恢复
- ⏳ 测试中断场景

### 第四阶段：配置和文档（0.5-1 天）

- ⏳ 添加配置支持
- ⏳ 更新 `config.example.toml`
- ⏳ 编写使用文档
- ⏳ 添加使用示例

## 7. 兼容性考虑

### 7.1 终端兼容性

- **Rich 支持**: 现代终端（支持颜色、Unicode）
- **Simple 模式**: 基础终端（仅文本）
- **Minimal 模式**: 管道、重定向场景

### 7.2 自动检测

```python
def detect_terminal_capabilities() -> str:
    """检测终端能力，自动选择显示风格"""

    # 检查是否为 TTY
    if not sys.stdout.isatty():
        return "minimal"

    # 检查终端类型
    term = os.environ.get("TERM", "")
    if term in ["dumb", "unknown"]:
        return "minimal"

    # 检查颜色支持
    if sys.platform == "win32":
        # Windows 10+ 支持 ANSI
        return "rich" if sys.version_info >= (3, 10) else "simple"

    return "rich"
```

## 8. 性能影响

### 8.1 优化策略

- **批量更新**: 合并频繁的进度更新
- **异步刷新**: 使用独立线程更新显示
- **条件渲染**: 根据刷新率限制更新频率
- **延迟初始化**: 仅在需要时创建显示组件

### 8.2 性能目标

- 进度更新开销 < 1ms
- 显示刷新不阻塞主任务
- 内存占用 < 10MB

## 9. 测试计划

### 9.1 单元测试

- ProgressTracker 核心功能
- ProgressDisplay 格式化
- 事件系统
- 配置加载

### 9.2 集成测试

- Agent 集成
- Tool 集成
- End-to-end 场景

### 9.3 手动测试

- 各种终端环境
- 长时间运行任务
- 中断和恢复
- 不同配置组合

## 10. 用户体验示例

### 10.1 Rich 模式

```
⠋ Running: 分析数据并生成报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 0:00:12

✓ Tool: read_file
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Successfully read data.csv (1024 rows) ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

⠋ Step 3: Analyzing data...
```

### 10.2 Simple 模式

```
[10:30:15] Running: 分析数据并生成报告
[10:30:16] [45%] Step 2/5: Reading file...
[10:30:17] ✓ Tool: read_file - Successfully read data.csv (1024 rows)
[10:30:18] [60%] Step 3/5: Analyzing data...
```

### 10.3 Minimal 模式

```
Running task...
Step 1: Reading file... done
Step 2: Analyzing data... done
Step 3: Generating report... done
Completed in 12.3s
```

## 11. 未来扩展

### 11.1 可能的增强

- **Web UI**: 提供 web 界面查看进度
- **日志集成**: 将进度信息记录到日志
- **通知系统**: 任务完成时发送通知
- **进度持久化**: 保存进度历史供分析
- **多任务视图**: 同时显示多个并行任务

### 11.2 与其他功能的协同

- **历史管理**: 在会话历史中记录进度信息
- **错误恢复**: 结合 checkpoint 实现更好的恢复
- **性能分析**: 使用进度数据分析性能瓶颈

---

## 附录

### A. 依赖项

需要添加的新依赖：

```txt
rich>=13.0.0    # 终端美化库
```

### B. 文件清单

新增文件：
- `app/progress/__init__.py`
- `app/progress/tracker.py`
- `app/progress/display.py`
- `app/progress/events.py`
- `app/progress/formatters.py`
- `app/progress/README.md`
- `tests/test_progress.py`

修改文件：
- `app/config.py`
- `app/agent/toolcall.py`
- `app/tool/base.py`
- `config/config.example.toml`
- `requirements.txt`

### C. 时间估算

总工作量：3-5 天

- 架构设计：0.5 天（已完成）
- 核心实现：1-2 天
- Agent 集成：1-2 天
- 测试和文档：1 天

---

**文档版本**: 1.0
**创建时间**: 2024-10-14
**状态**: 待实施
