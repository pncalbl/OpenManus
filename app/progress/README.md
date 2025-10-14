# 实时进度反馈系统 - 使用文档

## 概述

实时进度反馈系统为 OpenManus 提供了任务执行过程中的可视化进度跟踪功能，让用户可以：

- 实时查看任务执行进度
- 了解当前执行的步骤
- 查看预估剩余时间
- 看到中间结果输出
- 优雅地中断任务

## 快速开始

### 1. 基本使用

进度反馈系统默认启用，无需额外配置。当运行任务时，会自动显示进度信息：

```bash
python main.py --prompt "分析数据文件"
```

你会看到类似这样的输出：

```
⠋ Running: 分析数据文件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 0:00:12

✓ Tool: read_file
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Successfully read data.csv (1024 rows) ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

⠋ Step 3/5: Analyzing data...
```

### 2. 配置选项

在 `config/config.toml` 中配置进度反馈：

```toml
[progress]
enabled = true                      # 启用进度反馈
display_style = "auto"              # 显示风格：rich, simple, minimal, auto
show_percentage = true              # 显示百分比
show_eta = true                     # 显示预估时间
show_steps = true                   # 显示步骤计数
show_intermediate_results = true    # 显示中间结果
```

### 3. 显示风格

系统支持三种显示风格：

#### Rich 模式（推荐）

使用丰富的终端 UI，包含彩色输出、进度条动画、表格等：

```toml
display_style = "rich"
```

特点：
- 彩色输出
- 动态进度条
- 表格和面板
- 支持 emoji 图标

#### Simple 模式

使用简单的文本输出，适合基础终端：

```toml
display_style = "simple"
```

输出示例：
```
[10:30:15] Running: 分析数据文件
[10:30:16] [45%] Step 2/5: Reading file...
[10:30:17] ✓ Tool: read_file - Success
```

#### Minimal 模式

最小化输出，适合日志记录和管道操作：

```toml
display_style = "minimal"
```

输出示例：
```
Running task...
Step 1: Reading file... done
Step 2: Analyzing data... done
Completed in 12.3s
```

#### Auto 模式（默认）

自动检测终端能力并选择最合适的显示风格：

```toml
display_style = "auto"
```

## 编程接口

### 基本用法

```python
from app.progress import ProgressTracker, get_event_bus
from app.progress.display import ProgressDisplay, ProgressEventHandler

# 创建进度追踪器
tracker = ProgressTracker(
    total_steps=5,
    description="Processing data",
)

# 创建显示组件
display = ProgressDisplay(style="rich")
handler = ProgressEventHandler(display)

# 订阅事件
event_bus = get_event_bus()
event_bus.subscribe_all(handler.handle_event)

# 执行任务
for i in range(5):
    tracker.start_step(f"Step {i+1}")
    # ... 执行工作 ...
    tracker.update(message=f"Completed step {i+1}")
    tracker.complete_step(f"Step {i+1}", result="Success")

# 完成任务
tracker.complete(message="All steps completed")

# 清理
handler.cleanup()
```

### 上下文管理器

使用上下文管理器自动处理完成/失败：

```python
from app.progress import ProgressTracker

with ProgressTracker(total_steps=3, description="Processing") as tracker:
    tracker.update(message="Step 1")
    # ... 执行工作 ...
    tracker.update(message="Step 2")
    # ... 执行工作 ...
    tracker.update(message="Step 3")
    # 自动调用 complete()
```

如果发生异常，会自动调用 `fail()`。

### 子任务

创建嵌套的子任务：

```python
tracker = ProgressTracker(total_steps=2, description="Main task")

# 创建子任务
subtask = tracker.start_subtask("Subtask 1", total_steps=3)
for i in range(3):
    subtask.update(message=f"Subtask step {i+1}")

subtask.complete()
tracker.update()

# 继续主任务
tracker.complete()
```

### 显示中间结果

显示工具调用结果或其他中间信息：

```python
tracker.show_intermediate_result(
    title="File Contents",
    content="First 200 characters of file...",
    category="result"  # result, error, warning, info
)
```

### 发送消息

发送状态消息：

```python
tracker.message("Starting analysis...", level="info")
tracker.message("Warning: Large file detected", level="warning")
tracker.message("Analysis complete", level="success")
tracker.message("Error occurred", level="error")
```

### 动态调整总步骤数

如果总步骤数在运行时才知道：

```python
tracker = ProgressTracker(description="Processing")  # 不指定 total_steps

# 稍后设置
tracker.set_total_steps(10)

# 或者在每次更新时动态调整
for item in items:
    tracker.set_total_steps(len(items))
    tracker.update(message=f"Processing {item}")
```

### 预估剩余时间

系统自动计算 ETA（预估剩余时间）：

```python
# 获取预估剩余时间（秒）
eta = tracker.eta

if eta is not None:
    print(f"Estimated time remaining: {eta:.1f}s")
```

ETA 基于最近步骤的平均耗时计算，随着任务进行会越来越准确。

### 获取进度信息

获取完整的进度信息：

```python
info = tracker.get_progress_info()
print(info)
```

输出：
```python
{
    'description': 'Processing data',
    'current_step': 3,
    'total_steps': 5,
    'percentage': 60.0,
    'duration': 15.2,
    'eta': 10.1,
    'is_completed': False,
    'is_failed': False,
    'is_running': True,
    'last_message': 'Processing item 3',
    'start_time': '2024-10-14T10:30:00',
    'end_time': None,
    'metadata': {},
    'children_count': 0
}
```

## Agent 集成

### ToolCallAgent 集成

系统已自动集成到 `ToolCallAgent` 中。如果配置启用，agent 会自动创建进度追踪器。

### 自定义 Agent 集成

在自定义 agent 中集成进度追踪：

```python
from app.agent.base import Agent
from app.progress import ProgressTracker
from app.progress.display import ProgressDisplay, ProgressEventHandler
from app.config import Config

class MyAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_enabled = Config().progress_config.enabled
        self.progress_tracker = None
        self.progress_display = None
        self.progress_handler = None

    async def run(self, prompt: str, **kwargs) -> str:
        # 初始化进度追踪
        if self.progress_enabled:
            self.progress_tracker = ProgressTracker(
                description=f"Running: {prompt[:50]}..."
            )

            display_style = Config().progress_config.display_style
            if display_style == "auto":
                from app.progress.display import detect_terminal_capabilities
                display_style = detect_terminal_capabilities()

            self.progress_display = ProgressDisplay(
                style=display_style,
                show_percentage=Config().progress_config.show_percentage,
                show_eta=Config().progress_config.show_eta,
                show_steps=Config().progress_config.show_steps,
                show_intermediate_results=Config().progress_config.show_intermediate_results,
            )

            self.progress_handler = ProgressEventHandler(self.progress_display)

            from app.progress import get_event_bus
            event_bus = get_event_bus()
            event_bus.subscribe_all(self.progress_handler.handle_event)

        try:
            # 执行任务
            result = await self._execute_task(prompt)

            if self.progress_tracker:
                self.progress_tracker.complete(message="Task completed")

            return result

        except Exception as e:
            if self.progress_tracker:
                self.progress_tracker.fail(e, message=str(e))
            raise

        finally:
            if self.progress_handler:
                self.progress_handler.cleanup()

    async def _execute_task(self, prompt: str) -> str:
        # 在任务执行中更新进度
        if self.progress_tracker:
            self.progress_tracker.update(message="Starting...")

        # ... 执行工作 ...

        return result
```

## Tool 集成

在自定义工具中报告进度：

```python
from app.tool.base import BaseTool
from app.progress import get_event_bus, ProgressEvent, ProgressEventType

class MyTool(BaseTool):
    async def execute(self, **kwargs):
        # 发送工具开始事件
        event_bus = get_event_bus()
        # 可以发送自定义事件或直接使用 logger

        result = await self._do_work(**kwargs)

        # 发送工具完成事件
        return result
```

## 优雅中断

### 基本使用

按 `Ctrl+C` 可以优雅地中断任务：

```
⠋ Running: Long running task
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 0:00:12

^C
正在优雅退出（再次按 Ctrl+C 强制退出）...
✓ State saved to workspace/.interrupted_state.json
```

再次按 `Ctrl+C` 会强制退出。

### 配置

```toml
[progress]
enable_graceful_shutdown = true      # 启用优雅退出
save_state_on_interrupt = true       # 中断时保存状态
```

### 恢复中断的任务

```python
import json
from pathlib import Path

# 加载保存的状态
state_file = Path("workspace/.interrupted_state.json")
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)

    # 从保存的步骤继续
    tracker = ProgressTracker(
        total_steps=state["total_steps"],
        description="Resuming task..."
    )
    tracker.current_step = state["current_step"]

    # 继续执行...
```

## 性能优化

### 刷新率控制

控制进度条更新频率以减少性能影响：

```toml
[progress]
refresh_rate = 0.1  # 每 0.1 秒更新一次（默认）
```

较低的值（如 0.05）提供更流畅的动画但可能增加 CPU 使用。
较高的值（如 0.5）减少更新频率，降低性能影响。

### 中间结果长度限制

限制中间结果显示长度以提高性能：

```toml
[progress]
intermediate_results_max_length = 200  # 最多显示 200 个字符
```

### 禁用特定功能

如果性能是关键考虑，可以禁用部分功能：

```toml
[progress]
show_intermediate_results = false  # 禁用中间结果
show_eta = false                   # 禁用 ETA 计算
```

## 终端兼容性

### 自动检测

系统会自动检测终端能力：

- **支持 ANSI 颜色的现代终端**：使用 rich 模式
- **基础终端**：降级到 simple 模式
- **管道/重定向**：降级到 minimal 模式

### 手动指定

如果自动检测不准确，可以手动指定：

```toml
[progress]
display_style = "simple"  # 强制使用 simple 模式
```

### 在 CI/CD 中使用

在 CI/CD 环境中，建议使用 minimal 模式：

```toml
[progress]
display_style = "minimal"
show_intermediate_results = false
```

或通过环境变量禁用：

```bash
# 临时禁用进度反馈
export PROGRESS_ENABLED=false
python main.py --prompt "task"
```

## 示例场景

### 场景 1：数据处理任务

```python
from app.progress import ProgressTracker

tracker = ProgressTracker(
    total_steps=len(data_files),
    description="Processing data files"
)

for i, file in enumerate(data_files):
    tracker.start_step(f"Processing {file}")

    # 读取文件
    data = read_file(file)
    tracker.message(f"Read {len(data)} records", "info")

    # 处理数据
    result = process_data(data)

    # 显示结果摘要
    tracker.show_intermediate_result(
        title=f"Results from {file}",
        content=f"Processed {len(result)} items",
        category="result"
    )

    tracker.complete_step(f"Processing {file}", result="Success")
    tracker.update()

tracker.complete(message=f"Processed {len(data_files)} files")
```

### 场景 2：多步骤工作流

```python
tracker = ProgressTracker(total_steps=4, description="Data analysis workflow")

# 步骤 1: 加载数据
tracker.start_step("Loading data")
data = load_data()
tracker.complete_step("Loading data", result=f"{len(data)} rows loaded")
tracker.update()

# 步骤 2: 清洗数据
tracker.start_step("Cleaning data")
cleaned_data = clean_data(data)
tracker.complete_step("Cleaning data", result=f"{len(cleaned_data)} rows after cleaning")
tracker.update()

# 步骤 3: 分析数据
tracker.start_step("Analyzing data")
analysis = analyze_data(cleaned_data)
tracker.show_intermediate_result(
    title="Analysis Results",
    content=str(analysis),
    category="result"
)
tracker.complete_step("Analyzing data", result="Analysis complete")
tracker.update()

# 步骤 4: 生成报告
tracker.start_step("Generating report")
report = generate_report(analysis)
tracker.complete_step("Generating report", result="Report saved")
tracker.update()

tracker.complete(message="Workflow completed successfully")
```

### 场景 3：并行任务

```python
import asyncio

async def process_item(item, parent_tracker):
    subtask = parent_tracker.start_subtask(
        f"Processing {item}",
        total_steps=3
    )

    subtask.update(message="Step 1")
    await asyncio.sleep(1)

    subtask.update(message="Step 2")
    await asyncio.sleep(1)

    subtask.update(message="Step 3")
    await asyncio.sleep(1)

    subtask.complete()

tracker = ProgressTracker(
    total_steps=len(items),
    description="Processing items in parallel"
)

# 并行处理
tasks = [process_item(item, tracker) for item in items]
await asyncio.gather(*tasks)

tracker.complete()
```

## 故障排除

### 问题：进度条不显示

检查：
1. 配置是否启用：`Config().progress_config.enabled == True`
2. 终端是否支持：尝试手动设置 `display_style = "simple"`
3. 输出是否重定向：重定向时会自动降级到 minimal 模式

### 问题：进度条闪烁

解决方案：
- 增加刷新率：`refresh_rate = 0.2`
- 检查是否有其他输出混入（如 print 语句）

### 问题：性能下降

解决方案：
- 禁用中间结果：`show_intermediate_results = false`
- 增加刷新率：`refresh_rate = 0.5`
- 使用 simple 或 minimal 模式

### 问题：Ctrl+C 不起作用

检查：
- 确保 `enable_graceful_shutdown = true`
- 检查是否有其他信号处理器
- 尝试按两次 Ctrl+C 强制退出

## API 参考

### ProgressTracker

主要的进度追踪类。

#### 构造函数

```python
ProgressTracker(
    total_steps: Optional[int] = None,
    description: str = "",
    parent: Optional[ProgressTracker] = None,
    show_progress: bool = True,
    event_bus: Optional[Any] = None
)
```

#### 方法

- `update(step=None, message="", increment=1, metadata=None)` - 更新进度
- `start_step(step_name: str)` - 标记步骤开始
- `complete_step(step_name: str, result=None)` - 标记步骤完成
- `show_intermediate_result(title, content, category="result")` - 显示中间结果
- `message(text, level="info")` - 发送消息
- `start_subtask(description, total_steps=None)` - 创建子任务
- `complete(message="")` - 标记完成
- `fail(error, message="")` - 标记失败
- `set_total_steps(total)` - 设置总步骤数
- `get_progress_info()` - 获取进度信息

#### 属性

- `percentage: float` - 完成百分比 (0-100)
- `duration: float` - 持续时间（秒）
- `eta: Optional[float]` - 预估剩余时间（秒）
- `is_completed: bool` - 是否完成
- `is_failed: bool` - 是否失败
- `is_running: bool` - 是否运行中
- `last_message: str` - 最后的消息

### ProgressDisplay

显示组件类。

#### 构造函数

```python
ProgressDisplay(
    style: Optional[str] = None,
    show_percentage: bool = True,
    show_eta: bool = True,
    show_steps: bool = True,
    show_intermediate_results: bool = True,
    intermediate_results_max_length: int = 200
)
```

#### 方法

- `create_task(tracker, description, total=None)` - 创建显示任务
- `update_task(tracker, advance=None, completed=None, description=None)` - 更新任务
- `complete_task(tracker, message="")` - 完成任务
- `show_status(message, status="info")` - 显示状态
- `show_intermediate_result(title, content, category="result")` - 显示中间结果
- `stop()` - 停止显示

### ProgressEventHandler

事件处理器类。

#### 构造函数

```python
ProgressEventHandler(display: ProgressDisplay)
```

#### 方法

- `handle_event(event: ProgressEvent)` - 处理事件
- `cleanup()` - 清理资源

## 最佳实践

1. **总是使用上下文管理器**
   ```python
   with ProgressTracker(...) as tracker:
       # 工作代码
   ```

2. **提供有意义的描述**
   ```python
   tracker = ProgressTracker(description="Processing data files")
   tracker.update(message="Reading file data.csv")
   ```

3. **合理使用中间结果**
   - 只显示关键信息
   - 控制内容长度
   - 使用适当的类别

4. **考虑性能影响**
   - 不要在紧密循环中频繁更新
   - 批量更新进度
   - 根据需要禁用功能

5. **处理异常**
   ```python
   try:
       # 工作代码
   except Exception as e:
       tracker.fail(e)
       raise
   ```

6. **清理资源**
   ```python
   finally:
       if progress_handler:
           progress_handler.cleanup()
   ```

## 依赖项

进度反馈系统依赖以下库：

- `rich>=13.0.0` - 终端美化库（可选，用于 rich 模式）

如果 rich 未安装，系统会自动降级到 simple 模式。

安装：
```bash
pip install rich
# 或
uv pip install rich
```

## 更新日志

### v1.0.0 (2024-10-14)

- 初始版本
- 支持三种显示风格（rich、simple、minimal）
- 自动终端能力检测
- 进度追踪和 ETA 计算
- 中间结果显示
- 优雅中断支持
- 完整的配置选项
- Agent 和 Tool 集成
