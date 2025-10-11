# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenManus is a versatile AI agent framework built in Python that can solve various tasks using multiple tools. It's designed as an open-source alternative to Manus, providing browser automation, code execution, file editing, web search, and MCP (Model Context Protocol) tool integration.

## Key Commands

### Running the Application

```bash
# Main entry point - basic OpenManus agent
python main.py

# With command line prompt
python main.py --prompt "Your task here"

# MCP (Model Context Protocol) version
python run_mcp.py

# Multi-agent flow version (experimental)
python run_flow.py
```

### Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
# Or with uv (recommended)
uv pip install -r requirements.txt

# Install browser automation dependencies
playwright install

# Run pre-commit checks (required before PRs)
pre-commit run --all-files

# Code formatting and linting (automatic via pre-commit)
black .
isort --profile black --filter-files --lines-after-imports=2 .
autoflake --remove-all-unused-imports --recursive --in-place .
```

### Testing

```bash
# Basic tests are in tests/ directory
# No specific test runner configured - check tests/sandbox/ for available tests
```

## Architecture

### Core Components

1. **Agents** (`app/agent/`):
   - `Manus`: Main versatile agent with tool collection
   - `MCPAgent`: Agent with MCP tool integration
   - `DataAnalysis`: Specialized data analysis agent
   - `BrowserAgent`, `SWEAgent`: Specialized task agents

2. **Tools** (`app/tool/`):
   - `PythonExecute`: Python code execution
   - `BrowserUseTool`: Web browser automation
   - `StrReplaceEditor`: File editing capabilities
   - `AskHuman`: Human interaction tool
   - `MCPClientTool`: MCP protocol tools
   - Search tools: Google, Baidu, DuckDuckGo, Bing

3. **Configuration** (`app/config.py`, `config/`):
   - LLM configuration (OpenAI, Anthropic, Azure, Ollama, etc.)
   - Browser settings and proxy configuration
   - Search engine preferences
   - MCP server references

4. **Flow System** (`app/flow/`):
   - Planning-based workflow execution
   - Multi-agent coordination
   - Task decomposition and execution

### Entry Points

- `main.py`: Single agent execution with Manus
- `run_mcp.py`: MCP-enabled agent execution
- `run_flow.py`: Multi-agent workflow system
- `sandbox_main.py`: Sandbox environment execution

### Configuration Structure

Configuration uses TOML format in `config/config.toml`. Key sections:
- `[llm]`: Primary LLM configuration
- `[llm.vision]`: Vision model configuration
- `[browser]`: Browser automation settings
- `[search]`: Search engine configuration
- `[mcp]`: MCP server configuration
- `[runflow]`: Multi-agent workflow settings
- `[sandbox]`: Sandbox environment settings

### Tool Integration

Tools inherit from base classes in `app/tool/base.py` and are collected via `ToolCollection`. The agent system supports:
- Local Python tools (execute code, edit files)
- Browser automation (Playwright-based)
- Web search across multiple engines
- MCP protocol for external tool integration
- Human-in-the-loop interaction

### Agent Execution Flow

1. Agent initialization with tool collection
2. System prompt injection with workspace context
3. Tool call orchestration via `ToolCallAgent` base class
4. Result processing and next step determination
5. Cleanup and resource management

## Development Notes

- Python 3.12+ required (3.11-3.13 supported)
- Uses async/await patterns throughout
- Pydantic for data validation and configuration
- Pre-commit hooks enforce code quality (black, isort, autoflake)
- Browser automation via Playwright and browser-use library
- LLM integration supports multiple providers (OpenAI, Anthropic, Azure, Ollama)