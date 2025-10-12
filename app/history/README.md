# Conversation History Management

This module provides persistent conversation history storage for OpenManus agents, enabling session resumption and long-term conversation tracking.

## Features

- **Session Persistence**: Save and restore complete conversation sessions
- **Session Management**: List, delete, and cleanup old sessions via CLI
- **Metadata Tracking**: Track agent type, message count, timestamps, and task summaries
- **Automatic Cleanup**: Configure retention policies to auto-delete old sessions
- **Opt-in Design**: Disabled by default, enable via CLI flag or configuration
- **Atomic Writes**: Safe file operations prevent data corruption

## Architecture

### Module Structure

```
app/history/
├── __init__.py          # Module entry point with lazy initialization
├── models.py            # Data models (SessionMetadata, SessionData)
├── serializer.py        # Message serialization/deserialization
├── manager.py           # Core HistoryManager class
├── cli.py              # CLI formatting utilities
└── README.md           # This file
```

### Key Components

#### 1. `HistoryManager` (manager.py)
Core class handling all history operations:
- `create_session()`: Generate new session ID
- `save_session()`: Save conversation to JSON file
- `load_session()`: Restore conversation from JSON
- `list_sessions()`: Get all session metadata
- `delete_session()`: Remove specific session
- `cleanup_old_sessions()`: Auto-delete based on retention policy

#### 2. `SessionMetadata` (models.py)
Metadata for each session:
```python
{
    "session_id": "session_20241012_143022_abc123def",
    "created_at": "2024-10-12T14:30:22",
    "updated_at": "2024-10-12T14:35:18",
    "agent_name": "manus",
    "agent_type": "Manus",
    "message_count": 15,
    "task_summary": "Analyze sales data",
    "workspace_path": "/workspace"
}
```

#### 3. `SessionData` (models.py)
Complete session storage:
```python
{
    "metadata": { /* SessionMetadata */ },
    "messages": [ /* List of Message dicts */ ]
}
```

#### 4. `Serializer` (serializer.py)
Handles conversion between Memory objects and JSON format:
- `serialize_memory()`: Memory → JSON-serializable dict
- `deserialize_memory()`: JSON dict → Memory object

## Configuration

### config.toml Settings

```toml
[history]
enabled = false           # Enable conversation history saving (default: false)
storage_dir = "history"   # Directory under workspace/ for storing sessions
retention_days = 30       # Auto-delete sessions older than N days, 0 = keep forever
auto_cleanup = true       # Auto-cleanup old sessions on startup (default: true)
max_sessions = 100        # Maximum sessions to keep, 0 = unlimited (default: 100)
```

### Storage Location

Sessions are stored in: `{workspace_root}/{storage_dir}/`
- Default: `workspace/history/`
- Format: One JSON file per session
- Filename: `{session_id}.json`

## CLI Usage

### All Entry Points Support History

History CLI arguments are available in:
- `main.py` - Main OpenManus agent
- `run_mcp.py` - MCP agent
- `run_flow.py` - Multi-agent flow

### Basic Commands

```bash
# Enable history for current session
python main.py --enable-history --prompt "Your task"

# Resume previous session (restores full conversation context)
python main.py --resume-session session_20241012_143022_abc123def

# List all saved sessions
python main.py --list-sessions

# Limit number of sessions displayed
python main.py --list-sessions --limit 20

# Delete specific session
python main.py --delete-session session_20241012_143022_abc123def

# Cleanup old sessions (based on retention_days)
python main.py --cleanup-sessions
```

### Session List Output

```
====================================================================================================
Available Conversation Sessions
====================================================================================================
Session ID                          Agent        Messages   Created              Task
----------------------------------------------------------------------------------------------------
session_20241012_143022_abc123def   manus        15         2024-10-12 14:30:22  Analyze sales data
session_20241012_105511_def456ghi   manus        8          2024-10-12 10:55:11  Debug authentication bug
====================================================================================================
Total: 2 session(s)
```

## Programmatic Usage

### In Agent Code

```python
from app.history import get_history_manager

# Get singleton instance
history_manager = get_history_manager()

# Create new session
session_id = history_manager.create_session(
    agent_name="manus",
    agent_type="Manus",
    workspace_path="/workspace"
)

# Save session
success = history_manager.save_session(
    session_id=session_id,
    memory=agent.memory,
    agent_name="manus",
    agent_type="Manus",
    workspace_path="/workspace"
)

# Load session
loaded_memory = history_manager.load_session(session_id)
if loaded_memory:
    agent.memory = loaded_memory
    agent.session_id = session_id
```

### Auto-Save Integration

History is automatically saved during agent cleanup if `session_id` is set:

```python
# In app/agent/toolcall.py cleanup() method
if self.session_id:
    if config.history_config.enabled:
        history_manager = get_history_manager()
        history_manager.save_session(
            session_id=self.session_id,
            memory=self.memory,
            agent_name=self.name,
            agent_type=self.__class__.__name__,
            workspace_path=str(config.workspace_root)
        )
```

## Session ID Format

Session IDs follow the pattern: `session_YYYYMMDD_HHMMSS_<short_uuid>`

Example: `session_20241012_143022_abc123def`

Components:
- `session_` - Prefix for identification
- `YYYYMMDD` - Date (2024-10-12)
- `HHMMSS` - Time (14:30:22)
- `<short_uuid>` - First 8 chars of UUID for uniqueness

## Data Safety

### Atomic Writes
Session saves use atomic write pattern:
1. Write to temporary file (`{session_id}.tmp`)
2. Rename to final file (`{session_id}.json`)
3. This prevents data corruption from interrupted writes

### Error Handling
- File I/O errors are logged and handled gracefully
- Invalid JSON data returns None instead of crashing
- Missing sessions return None (not exceptions)

## Testing

### Basic Module Test

```bash
# Test history module functionality
python test_history_basic.py
```

Tests:
- Module imports
- HistoryManager initialization
- Session listing
- CLI formatters

### Integration Test

To test with actual agents, install dependencies first:
```bash
pip install -r requirements.txt
```

Then run:
```bash
# Test with Manus agent
python main.py --enable-history --prompt "test task"
python main.py --list-sessions
```

## Migration Guide

### For Existing Agents

To add history support to existing agents:

1. **No changes needed** - History is opt-in by default

2. **To enable history**:
   ```bash
   # Via CLI
   python main.py --enable-history

   # Via config
   # Set enabled = true in [history] section
   ```

3. **To resume sessions**:
   ```bash
   python main.py --resume-session SESSION_ID
   ```

### For New Agents

New agents automatically inherit history support from `BaseAgent`:

```python
from app.agent.toolcall import ToolCallAgent

class MyAgent(ToolCallAgent):
    # session_id field is inherited from BaseAgent
    # cleanup() method handles history saving
    pass
```

## Performance Considerations

- **File I/O**: Each save writes one JSON file (minimal overhead)
- **Memory**: Full conversation loaded into memory when resuming
- **Cleanup**: Auto-cleanup runs on startup (configurable)
- **List Operations**: Scans all JSON files in history directory

For large deployments:
- Consider setting `max_sessions` limit
- Adjust `retention_days` for automatic cleanup
- Monitor `workspace/history/` disk usage

## Troubleshooting

### Issue: Sessions not saving
**Check:**
1. Is history enabled? (`--enable-history` or config)
2. Is `session_id` set on agent?
3. Check logs for errors during cleanup
4. Verify write permissions on `workspace/history/`

### Issue: Cannot resume session
**Check:**
1. Does session file exist in `workspace/history/`?
2. Is JSON file valid? (check for corruption)
3. Verify session ID format matches expected pattern

### Issue: Too many old sessions
**Solution:**
```bash
# Manual cleanup
python main.py --cleanup-sessions

# Adjust retention in config
[history]
retention_days = 7  # Keep only 7 days
auto_cleanup = true
```

## Future Enhancements

Potential improvements:
- Database backend (SQLite, PostgreSQL)
- Session search and filtering
- Session export/import
- Compression for large sessions
- Session tags and categories
- Multi-user session isolation
- Session sharing between agents
