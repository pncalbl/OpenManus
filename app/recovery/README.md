# Error Recovery Module

智能错误恢复机制，提供自动重试、错误诊断和检查点/回滚功能。

## 功能特性

### 1. 自动重试（Retry）
- **指数退避**：使用指数退避算法智能计算重试延迟
- **随机抖动**：避免"惊群效应"
- **可配置策略**：灵活的重试配置
- **错误分类**：根据错误类型决定是否重试

### 2. 错误诊断（Diagnosis）
- **自动分类**：将错误分为 10 个类别
- **原因分析**：分析错误的可能原因
- **修复建议**：提供可操作的修复步骤
- **文档链接**：指向相关文档

### 3. 检查点机制（Checkpoint）
- **状态保存**：定期保存执行状态
- **快速回滚**：错误时恢复到稳定状态
- **自动管理**：自动清理旧检查点

## 错误分类

| 类别 | 描述 | 可重试 |
|------|------|--------|
| NETWORK | 网络连接问题 | ✅ |
| TIMEOUT | 操作超时 | ✅ |
| RATE_LIMIT | API 速率限制 | ✅ |
| API | API 服务错误 | ✅ |
| BROWSER | 浏览器自动化错误 | ✅ |
| AUTHENTICATION | 认证失败 | ❌ |
| CONFIGURATION | 配置错误 | ❌ |
| FILESYSTEM | 文件系统错误 | 部分 |
| RESOURCE | 资源不足 | ❌ |
| UNKNOWN | 未知错误 | ❌ |

## 快速开始

### 基本使用（自动）

错误恢复默认启用，无需手动配置：

```python
from app.agent.manus import Manus

# 自动启用错误恢复
agent = Manus()
result = await agent.run("你的任务")  # 自动重试和诊断
```

### 手动重试

```python
from app.recovery import RetryHandler, RetryStrategy

retry_handler = RetryHandler()

# 使用默认策略
result = await retry_handler.execute_with_retry(
    your_function,
    arg1, arg2,
    kwarg1=value1
)

# 使用自定义策略
strategy = RetryStrategy(
    max_retries=5,
    initial_delay=2.0,
    max_delay=30.0
)

result = await retry_handler.execute_with_retry(
    your_function,
    strategy=strategy
)
```

### 错误诊断

```python
from app.recovery.diagnosis import ErrorDiagnosis

diagnosis = ErrorDiagnosis()

try:
    # 你的代码
    pass
except Exception as e:
    # 诊断错误
    info = diagnosis.diagnose(e)

    print(f"错误类别: {info['category']}")
    print(f"原因: {info['cause']}")
    print(f"建议:")
    for suggestion in info['suggestions']:
        print(f"  - {suggestion}")
```

### 检查点管理

```python
from app.recovery.checkpoint import CheckpointManager

checkpoint_mgr = CheckpointManager()

# 保存检查点
checkpoint_id = checkpoint_mgr.save_checkpoint(
    state={"step": 1, "data": data},
    memory=agent.memory,
    description="完成数据加载"
)

try:
    # 执行危险操作
    risky_operation()
except Exception as e:
    # 恢复到检查点
    state, memory = checkpoint_mgr.restore_checkpoint(checkpoint_id)
    agent.memory = memory
```

## 配置

在 `config/config.toml` 中配置：

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

# 诊断设置
diagnosis_enabled = true          # 启用错误诊断
show_suggestions = true           # 显示修复建议
```

## 预定义策略

模块提供了几个预定义的重试策略：

### API_RETRY_STRATEGY
适用于 API 调用（更激进的重试）：
- 最多重试 5 次
- 初始延迟 2 秒
- 最大延迟 60 秒

### BROWSER_RETRY_STRATEGY
适用于浏览器操作：
- 最多重试 3 次
- 初始延迟 1 秒
- 最大延迟 30 秒

### FILESYSTEM_RETRY_STRATEGY
适用于文件操作：
- 最多重试 2 次
- 初始延迟 0.5 秒
- 最大延迟 5 秒

### QUICK_RETRY_STRATEGY
适用于快速重试：
- 最多重试 2 次
- 初始延迟 0.5 秒
- 最大延迟 2 秒

## 错误诊断示例

### 网络错误

```
类别: network
原因: 网络连接问题或服务不可达
建议:
  1. 检查网络连接是否正常
  2. 确认目标服务是否可访问
  3. 检查防火墙或代理设置
  4. 尝试使用 VPN 或更换网络环境
```

### API 速率限制

```
类别: rate_limit
原因: API 请求频率超过限制
建议:
  1. 等待几分钟后重试
  2. 检查 API 配额使用情况
  3. 考虑升级 API 计划或增加配额
  4. 实现请求速率控制
```

### 认证失败

```
类别: auth
原因: 认证失败，API Key 可能无效或过期
建议:
  1. 检查 API Key 是否正确配置在 config.toml 中
  2. 验证 API Key 是否有效且未过期
  3. 确认 API Key 具有所需的权限
  4. 登录服务提供商网站查看 API Key 状态
```

## 高级用法

### 自定义错误处理

```python
from app.recovery import RetryHandler, RetryableError, FatalError
from app.recovery.errors import ErrorCategory

async def my_function():
    try:
        # 你的代码
        pass
    except SomeRetryableError as e:
        # 标记为可重试错误
        raise RetryableError(
            message=str(e),
            category=ErrorCategory.NETWORK,
            original_error=e,
            suggested_delay=5.0  # 建议延迟 5 秒
        )
    except SomeFatalError as e:
        # 标记为致命错误（不重试）
        raise FatalError(
            message=str(e),
            category=ErrorCategory.AUTHENTICATION,
            original_error=e
        )
```

### 重试回调

```python
def on_retry_callback(error, attempt, delay):
    print(f"重试 {attempt + 1} 次，等待 {delay:.1f} 秒")
    print(f"错误: {error}")

result = await retry_handler.execute_with_retry(
    your_function,
    on_retry=on_retry_callback
)
```

### 检查点列表

```python
# 列出所有检查点
checkpoints = checkpoint_mgr.list_checkpoints()

for cp in checkpoints:
    print(f"ID: {cp['id']}")
    print(f"时间: {cp['timestamp']}")
    print(f"状态键: {cp['state_keys']}")
```

### 回滚到最新检查点

```python
try:
    # 执行操作
    do_something()
except Exception as e:
    # 自动回滚到最新检查点
    state, memory = checkpoint_mgr.rollback_to_latest()
    print(f"已回滚到检查点")
```

## API 参考

### RetryStrategy

```python
RetryStrategy(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on_categories: Optional[set[ErrorCategory]] = None
)
```

### RetryHandler

```python
async def execute_with_retry(
    func: Callable,
    *args,
    strategy: Optional[RetryStrategy] = None,
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any
```

### ErrorDiagnosis

```python
def diagnose(error: Exception) -> Dict:
    """
    返回:
    {
        "category": str,
        "error_type": str,
        "message": str,
        "cause": str,
        "suggestions": List[str],
        "docs_link": str,
        "is_retryable": bool
    }
    """
```

### CheckpointManager

```python
def save_checkpoint(
    state: Dict[str, Any],
    memory: Optional[Memory] = None,
    description: Optional[str] = None
) -> str

def restore_checkpoint(
    checkpoint_id: str
) -> Tuple[Dict[str, Any], Optional[Memory]]

def list_checkpoints() -> List[Dict]

def rollback_to_latest() -> Tuple[Dict[str, Any], Optional[Memory]]
```

## 最佳实践

1. **使用预定义策略**：优先使用模块提供的预定义策略
2. **合理设置重试次数**：避免过多重试浪费时间
3. **定期保存检查点**：在关键步骤前保存检查点
4. **记录诊断信息**：将诊断信息记录到日志
5. **处理致命错误**：对于不可重试的错误，及时向用户报告

## 故障排查

### 问题：重试次数过多

**原因**：可能是网络问题或服务持续不可用

**解决**：
1. 检查网络连接
2. 确认服务状态
3. 调整 `max_retries` 配置

### 问题：检查点占用过多空间

**原因**：保存的检查点过多

**解决**：
1. 调整 `checkpoint_max_count` 配置
2. 手动清理旧检查点
3. 减少 `checkpoint_interval`

### 问题：错误诊断不准确

**原因**：错误分类模式可能不完整

**解决**：
1. 提交 Issue 报告新的错误模式
2. 查看完整错误日志
3. 使用自定义错误类型

## 性能影响

- **重试延迟**：根据配置，每次重试会增加延迟
- **检查点存储**：每个检查点约占用几 KB 到几 MB（取决于状态大小）
- **内存使用**：检查点保存在内存中，注意内存使用

## 未来计划

- [ ] 支持分布式检查点（Redis/数据库）
- [ ] 更智能的错误分类（ML 模型）
- [ ] 可视化重试和恢复过程
- [ ] 错误模式学习和优化
- [ ] 自动调整重试策略

## 贡献

欢迎贡献新的错误模式、诊断建议和改进！

## 许可

MIT License
