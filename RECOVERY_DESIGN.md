# 智能错误恢复机制 - 设计文档

## 概述

为 OpenManus 添加智能错误恢复机制，包括自动重试、错误诊断和回滚功能。

---

## 目标

1. **自动重试** - API 调用失败时自动重试（指数退避）
2. **错误诊断** - 分析错误并提供修复建议
3. **检查点机制** - 保存状态并支持回滚
4. **优雅降级** - 部分功能失败时继续执行

---

## 架构设计

### 模块结构

```
app/recovery/
├── __init__.py          # 模块入口
├── retry.py             # 重试机制
├── diagnosis.py         # 错误诊断
├── checkpoint.py        # 检查点管理
├── errors.py            # 错误分类
└── README.md            # 文档
```

### 核心组件

#### 1. 错误分类 (errors.py)

```python
class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"           # 网络错误
    API = "api"                   # API 错误
    RATE_LIMIT = "rate_limit"     # 速率限制
    AUTHENTICATION = "auth"       # 认证错误
    BROWSER = "browser"           # 浏览器错误
    FILESYSTEM = "filesystem"     # 文件系统错误
    TIMEOUT = "timeout"           # 超时错误
    UNKNOWN = "unknown"           # 未知错误

class RetryableError(Exception):
    """可重试的错误"""
    def __init__(self, message: str, category: ErrorCategory):
        self.message = message
        self.category = category
        self.retryable = True

class FatalError(Exception):
    """致命错误（不可重试）"""
    def __init__(self, message: str, category: ErrorCategory):
        self.message = message
        self.category = category
        self.retryable = False
```

#### 2. 重试机制 (retry.py)

```python
class RetryStrategy:
    """重试策略"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """计算延迟时间（指数退避）"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        return delay

class RetryHandler:
    """重试处理器"""
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        strategy: RetryStrategy = None,
        **kwargs
    ):
        """带重试的执行"""
        strategy = strategy or RetryStrategy()

        for attempt in range(strategy.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except RetryableError as e:
                if attempt >= strategy.max_retries:
                    logger.error(f"Max retries reached: {e}")
                    raise

                delay = strategy.get_delay(attempt)
                logger.warning(f"Retry {attempt + 1}/{strategy.max_retries} after {delay:.1f}s: {e}")
                await asyncio.sleep(delay)
            except FatalError as e:
                logger.error(f"Fatal error (not retrying): {e}")
                raise
```

#### 3. 错误诊断 (diagnosis.py)

```python
class ErrorDiagnosis:
    """错误诊断"""
    def __init__(self):
        self.error_patterns = self._load_error_patterns()

    def diagnose(self, error: Exception) -> dict:
        """诊断错误并提供建议"""
        category = self._categorize_error(error)

        return {
            "category": category,
            "message": str(error),
            "cause": self._analyze_cause(error, category),
            "suggestions": self._get_suggestions(error, category),
            "docs_link": self._get_docs_link(category)
        }

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_str = str(error).lower()

        if any(word in error_str for word in ["connection", "network", "timeout"]):
            return ErrorCategory.NETWORK
        elif "rate limit" in error_str or "429" in error_str:
            return ErrorCategory.RATE_LIMIT
        elif any(word in error_str for word in ["api key", "authentication", "unauthorized", "401"]):
            return ErrorCategory.AUTHENTICATION
        # ... 更多模式匹配

        return ErrorCategory.UNKNOWN

    def _get_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """获取修复建议"""
        suggestions = {
            ErrorCategory.NETWORK: [
                "检查网络连接",
                "确认防火墙设置",
                "尝试使用代理"
            ],
            ErrorCategory.RATE_LIMIT: [
                "等待几分钟后重试",
                "检查 API 配额使用情况",
                "考虑升级 API 计划"
            ],
            ErrorCategory.AUTHENTICATION: [
                "检查 API Key 是否正确",
                "验证 API Key 是否过期",
                "确认 API Key 权限"
            ],
            # ... 更多建议
        }

        return suggestions.get(category, ["查看日志获取更多信息"])
```

#### 4. 检查点机制 (checkpoint.py)

```python
class Checkpoint:
    """检查点"""
    def __init__(
        self,
        checkpoint_id: str,
        timestamp: datetime,
        state: dict,
        memory_snapshot: Memory
    ):
        self.checkpoint_id = checkpoint_id
        self.timestamp = timestamp
        self.state = state
        self.memory_snapshot = memory_snapshot

class CheckpointManager:
    """检查点管理器"""
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path("workspace/checkpoints")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Checkpoint] = []

    def save_checkpoint(
        self,
        state: dict,
        memory: Memory,
        description: str = None
    ) -> str:
        """保存检查点"""
        checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            state=state.copy(),
            memory_snapshot=copy.deepcopy(memory)
        )

        # 保存到文件
        self._save_to_file(checkpoint)
        self.checkpoints.append(checkpoint)

        logger.info(f"Checkpoint saved: {checkpoint_id}")
        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> Tuple[dict, Memory]:
        """恢复检查点"""
        checkpoint = self._load_checkpoint(checkpoint_id)

        if checkpoint:
            logger.info(f"Restored checkpoint: {checkpoint_id}")
            return checkpoint.state, checkpoint.memory_snapshot
        else:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    def list_checkpoints(self) -> List[dict]:
        """列出所有检查点"""
        return [
            {
                "id": cp.checkpoint_id,
                "timestamp": cp.timestamp,
                "state_keys": list(cp.state.keys())
            }
            for cp in self.checkpoints
        ]

    def rollback_to_latest(self) -> Tuple[dict, Memory]:
        """回滚到最新检查点"""
        if not self.checkpoints:
            raise ValueError("No checkpoints available")

        latest = self.checkpoints[-1]
        return self.restore_checkpoint(latest.checkpoint_id)
```

---

## 集成点

### 1. Agent 集成

在 `ToolCallAgent` 中集成错误恢复：

```python
# app/agent/toolcall.py
class ToolCallAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_handler = RetryHandler()
        self.checkpoint_manager = CheckpointManager()
        self.error_diagnosis = ErrorDiagnosis()

    async def run(self, prompt: str) -> str:
        # 保存初始检查点
        self.checkpoint_manager.save_checkpoint(
            state={"step": "start"},
            memory=self.memory,
            description="Initial state"
        )

        try:
            result = await self._run_with_recovery(prompt)
            return result
        except Exception as e:
            # 错误诊断
            diagnosis = self.error_diagnosis.diagnose(e)
            logger.error(f"Task failed: {diagnosis}")

            # 尝试恢复
            if self._should_recover(e):
                return await self._recover_and_retry(prompt, diagnosis)
            raise

    async def _run_with_recovery(self, prompt: str) -> str:
        """带恢复机制的运行"""
        return await self.retry_handler.execute_with_retry(
            self._run_original,
            prompt,
            strategy=RetryStrategy(max_retries=3)
        )
```

### 2. Tool 调用集成

```python
# 在工具调用时自动重试
async def call_tool_with_retry(self, tool_name: str, **kwargs):
    """带重试的工具调用"""
    return await self.retry_handler.execute_with_retry(
        self._call_tool_original,
        tool_name,
        **kwargs
    )
```

### 3. LLM 调用集成

```python
# app/llm.py
class LLM:
    def __init__(self):
        self.retry_handler = RetryHandler()

    async def agenerate(self, messages: List[dict], **kwargs):
        """带重试的生成"""
        return await self.retry_handler.execute_with_retry(
            self._agenerate_original,
            messages,
            strategy=RetryStrategy(
                max_retries=5,  # API 调用重试更多次
                initial_delay=2.0
            ),
            **kwargs
        )
```

---

## 配置

在 `config/config.toml` 添加配置：

```toml
[recovery]
enabled = true                    # 启用错误恢复
max_retries = 3                   # 最大重试次数
initial_delay = 1.0               # 初始延迟（秒）
max_delay = 60.0                  # 最大延迟（秒）
exponential_base = 2.0            # 指数基数
jitter = true                     # 添加随机抖动

# 检查点设置
checkpoint_enabled = true         # 启用检查点
checkpoint_interval = 5           # 每 N 步保存一次
checkpoint_max_count = 10         # 最多保存 N 个检查点
auto_rollback = false             # 错误时自动回滚

# 错误诊断
diagnosis_enabled = true          # 启用错误诊断
show_suggestions = true           # 显示修复建议
```

---

## 使用示例

### 基本使用

```python
# 自动启用（无需手动配置）
agent = Manus()
result = await agent.run("分析数据")  # 自动重试和恢复
```

### 手动检查点

```python
agent = Manus()

# 保存检查点
checkpoint_id = agent.checkpoint_manager.save_checkpoint(
    state={"current_step": "data_loaded"},
    memory=agent.memory
)

try:
    # 执行危险操作
    await agent.run("删除临时文件")
except Exception as e:
    # 回滚到检查点
    state, memory = agent.checkpoint_manager.restore_checkpoint(checkpoint_id)
    agent.memory = memory
```

### CLI 集成

```bash
# 启用错误恢复
python main.py --enable-recovery --prompt "任务"

# 列出检查点
python main.py --list-checkpoints

# 从检查点恢复
python main.py --restore-checkpoint CHECKPOINT_ID
```

---

## 错误场景处理

### 场景 1：API 速率限制

```python
# 检测到 429 错误
# → 分类为 RATE_LIMIT
# → 等待更长时间后重试（60秒）
# → 显示建议：检查配额
```

### 场景 2：网络超时

```python
# 检测到连接超时
# → 分类为 NETWORK
# → 指数退避重试（1s, 2s, 4s）
# → 显示建议：检查网络连接
```

### 场景 3：浏览器崩溃

```python
# 检测到浏览器错误
# → 分类为 BROWSER
# → 保存当前进度到检查点
# → 重启浏览器
# → 从检查点恢复
```

### 场景 4：认证失败

```python
# 检测到 401 错误
# → 分类为 AUTHENTICATION
# → 不重试（致命错误）
# → 显示建议：检查 API Key
```

---

## 测试计划

### 单元测试

1. `test_retry_strategy.py` - 测试重试策略
2. `test_error_diagnosis.py` - 测试错误诊断
3. `test_checkpoint.py` - 测试检查点机制

### 集成测试

1. `test_recovery_integration.py` - 测试完整恢复流程
2. `test_agent_recovery.py` - 测试 Agent 集成

### 场景测试

1. 模拟 API 速率限制
2. 模拟网络超时
3. 模拟浏览器崩溃

---

## 实施计划

### Phase 1: 核心组件（1-2 天）
- [x] 错误分类系统
- [ ] 重试机制
- [ ] 错误诊断

### Phase 2: 检查点机制（1 天）
- [ ] 检查点管理器
- [ ] 状态序列化
- [ ] 回滚功能

### Phase 3: 集成（1 天）
- [ ] Agent 集成
- [ ] LLM 集成
- [ ] Tool 集成

### Phase 4: 测试和文档（1 天）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 用户文档

---

## 预期效果

### 性能指标
- 任务成功率提升：70% → 95%
- 平均恢复时间：< 5 秒
- 自动恢复成功率：> 80%

### 用户体验
- 减少手动重试次数
- 提供清晰的错误提示
- 自动处理临时性错误

---

## 下一步

开始实施 Phase 1：核心组件
