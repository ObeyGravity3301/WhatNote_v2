# Function Calling vs MCP：当前实现与协议对比

## 📋 目录

1. [当前项目实现：Function Calling](#当前项目实现-function-calling)
2. [MCP（Model Context Protocol）简介](#mcp-model-context-protocol-简介)
3. [核心区别对比](#核心区别对比)
4. [架构对比图](#架构对比图)
5. [迁移到 MCP 的考虑](#迁移到-mcp-的考虑)

---

## 🎯 当前项目实现：Function Calling

### 什么是 Function Calling？

**Function Calling**（也称为 **Tool Calling**）是一种让 LLM 能够调用外部函数/工具的机制。它是 OpenAI、Anthropic、通义千问等主流 LLM 提供商提供的原生功能。

### 我们项目的实现架构

```
┌─────────────────────────────────────────────────────────┐
│                    WhatNote 应用                         │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │  LLM Service │────────▶│ Tool Registry│             │
│  │  (llm_service│         │  (16个工具)  │             │
│  │   .py)       │         └──────┬───────┘             │
│  └──────┬───────┘                │                     │
│         │                         │                     │
│         │ 1. 获取工具定义          │                     │
│         │    (OpenAI格式)         │                     │
│         │                         │                     │
│         ▼                         ▼                     │
│  ┌──────────────────────────────────────┐              │
│  │       LLM API (qwen-plus)            │              │
│  │  POST /chat/completions               │              │
│  │  {                                    │              │
│  │    "model": "qwen-plus",             │              │
│  │    "messages": [...],                │              │
│  │    "tools": [                        │              │
│  │      {                               │              │
│  │        "type": "function",           │              │
│  │        "function": {                 │              │
│  │          "name": "list_tasks",       │              │
│  │          "description": "...",       │              │
│  │          "parameters": {...}        │              │
│  │        }                             │              │
│  │      }                               │              │
│  │    ]                                 │              │
│  │  }                                    │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                       │
│                 │ 2. LLM 返回 tool_calls               │
│                 │    {                                 │
│                 │      "finish_reason": "tool_calls",  │
│                 │      "tool_calls": [{                │
│                 │        "id": "call_xxx",            │
│                 │        "function": {                │
│                 │          "name": "list_tasks",       │
│                 │          "arguments": "{\"date\":...}"│
│                 │        }                             │
│                 │      }]                              │
│                 │    }                                 │
│                 ▼                                       │
│  ┌──────────────────────────────────────┐              │
│  │      Tool Executor                   │              │
│  │  - 验证参数                           │              │
│  │  - 执行工具处理器                      │              │
│  │  - 返回结果                           │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                       │
│                 │ 3. 执行结果                          │
│                 │    {                                  │
│                 │      "date": "2025-11-04",           │
│                 │      "count": 5,                     │
│                 │      "tasks": [...]                  │
│                 │    }                                  │
│                 │                                       │
│                 ▼                                       │
│  ┌──────────────────────────────────────┐              │
│  │  将结果加入对话上下文，继续对话         │              │
│  │  messages.append({                    │              │
│  │    "role": "tool",                    │              │
│  │    "tool_call_id": "call_xxx",       │              │
│  │    "content": "{...}"                │              │
│  │  })                                    │              │
│  └───────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. **ToolRegistry** (`tool_registry.py`)
- **职责**：管理所有工具的定义和处理器
- **功能**：
  - 注册/注销工具
  - 按分类组织工具
  - 导出 OpenAI 格式的工具定义
- **特点**：单例模式，全局唯一

```python
# 工具定义格式（OpenAI 标准）
{
    "type": "function",
    "function": {
        "name": "list_tasks",
        "description": "列出指定日期的所有任务",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期，格式 YYYY-MM-DD"
                }
            },
            "required": []
        }
    }
}
```

#### 2. **ToolExecutor** (`tool_executor.py`)
- **职责**：执行工具调用
- **功能**：
  - 解析 LLM 返回的 `tool_calls`
  - 验证参数（JSON Schema）
  - 调用工具处理器
  - 返回结构化结果
- **特点**：支持并发执行、超时控制

#### 3. **LLMService** (`llm_service.py`)
- **方法**：`chat_with_tools()`
- **流程**：
  1. 获取工具定义
  2. 调用 LLM API（带 `tools` 参数）
  3. 检测 `tool_calls`
  4. 执行工具
  5. 将结果加入上下文
  6. 继续对话（最多5轮）

### 已实现的工具（16个）

#### 窗口管理（7个）
- `create_window` - 创建窗口
- `get_windows` - 获取窗口列表
- `read_window` - 读取窗口内容
- `update_window` - 更新窗口内容
- `edit_window` - 精细编辑窗口
- `delete_window` - 删除窗口
- `search_windows` - 搜索窗口

#### 课程展板（2个）
- `create_course` - 创建课程
- `create_board` - 创建展板

#### 日历任务（7个）
- `add_task` - 添加任务
- `list_tasks` - 列出任务
- `toggle_task` - 切换完成状态
- `update_task` - 更新任务
- `delete_task` - 删除任务
- `search_tasks` - 搜索任务
- `get_upcoming_tasks` - 获取未来任务

### 工作流程示例

```
用户: "帮我查看一下今天有什么任务"

↓ LLM 分析并决定调用工具

LLM → API 返回:
{
  "finish_reason": "tool_calls",
  "tool_calls": [{
    "id": "call_xxx",
    "function": {
      "name": "list_tasks",
      "arguments": "{\"date\": \"2025-11-04\"}"
    }
  }]
}

↓ 后端执行工具

ToolExecutor → 执行 list_tasks("2025-11-04")
→ 查询 calendar_tasks.json
→ 返回: {"date": "2025-11-04", "count": 5, "tasks": [...]}

↓ 将结果加入上下文，继续对话

LLM → 生成友好回复:
"以下是 2025-11-04 的任务列表：
1. 任务标题: `1` - 时间: 10:00 - 状态: 已完成 ✅
..."
```

---

## 🌐 MCP（Model Context Protocol）简介

### 什么是 MCP？

**Model Context Protocol（模型上下文协议）** 是由 **Anthropic** 推动的开放标准，旨在为 LLM 应用提供标准化的接口，使其能够连接外部数据源和工具。

### MCP 的核心理念

1. **标准化协议**：类似 JSON-RPC，定义统一的通信格式
2. **服务器-客户端架构**：工具作为独立的服务器运行
3. **动态发现**：客户端可以动态发现服务器提供的工具
4. **跨应用复用**：同一工具服务器可以被多个 LLM 应用使用

### MCP 架构

```
┌─────────────────────────────────────────────────────────┐
│              LLM 应用（MCP Client）                      │
│  ┌──────────────────────────────────────┐              │
│  │  Claude Desktop / Cursor IDE / ...   │              │
│  └──────────────┬───────────────────────┘              │
│                 │                                       │
│                 │  MCP Protocol (JSON-RPC)              │
│                 │  - initialize                        │
│                 │  - tools/list                        │
│                 │  - tools/call                        │
│                 │  - resources/read                    │
│                 ▼                                       │
│  ┌──────────────────────────────────────┐              │
│  │        MCP Server 1                   │              │
│  │  - GitHub 工具                        │              │
│  │  - Git 操作                           │              │
│  └───────────────────────────────────────┘              │
│                                                          │
│  ┌──────────────────────────────────────┐              │
│  │        MCP Server 2                   │              │
│  │  - 数据库工具                         │              │
│  │  - SQL 查询                          │              │
│  └───────────────────────────────────────┘              │
│                                                          │
│  ┌──────────────────────────────────────┐              │
│  │        MCP Server 3                   │              │
│  │  - 文件系统工具                      │              │
│  │  - 文件读写                          │              │
│  └───────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────┘
```

### MCP 通信协议

MCP 基于 **JSON-RPC 2.0**，使用标准的方法调用格式：

#### 1. 初始化连接
```json
// Client → Server
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "clientInfo": {
      "name": "claude-desktop",
      "version": "1.0.0"
    }
  }
}

// Server → Client
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "whatnote-tools",
      "version": "1.0.0"
    }
  }
}
```

#### 2. 列出可用工具
```json
// Client → Server
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}

// Server → Client
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "list_tasks",
        "description": "列出指定日期的所有任务",
        "inputSchema": {
          "type": "object",
          "properties": {
            "date": {
              "type": "string",
              "description": "日期，格式 YYYY-MM-DD"
            }
          }
        }
      }
    ]
  }
}
```

#### 3. 调用工具
```json
// Client → Server
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "list_tasks",
    "arguments": {
      "date": "2025-11-04"
    }
  }
}

// Server → Client
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"date\": \"2025-11-04\", \"count\": 5, \"tasks\": [...]}"
      }
    ]
  }
}
```

### MCP 的优势

1. **标准化**：统一的协议，不同的 LLM 应用可以使用相同的工具
2. **解耦**：工具作为独立服务器，可以单独开发、部署、更新
3. **可扩展**：添加新工具只需启动新的 MCP 服务器
4. **跨平台**：支持本地（STDIO）和远程（HTTP+SSE）连接
5. **生态丰富**：社区可以共享 MCP 服务器

### MCP 的局限性

1. **复杂度**：需要实现 JSON-RPC 协议栈
2. **性能开销**：进程间通信（IPC）或网络通信
3. **部署复杂**：需要管理多个服务器进程
4. **生态依赖**：需要 LLM 应用支持 MCP 协议

---

## 🔄 核心区别对比

| 特性 | Function Calling（当前实现） | MCP（Model Context Protocol） |
|------|----------------------------|------------------------------|
| **协议标准** | 各厂商自定义（OpenAI/Anthropic/Qwen） | 统一的 JSON-RPC 2.0 标准 |
| **架构** | 单应用内嵌 | 服务器-客户端分离 |
| **工具发现** | 静态注册 | 动态发现（`tools/list`） |
| **通信方式** | 直接函数调用 | JSON-RPC 消息传递 |
| **部署** | 同一进程 | 独立进程/服务 |
| **复用性** | 仅限当前应用 | 跨应用复用 |
| **扩展性** | 需要修改代码重新注册 | 启动新服务器即可 |
| **复杂度** | 简单直接 | 需要协议栈 |
| **性能** | 低延迟（内存调用） | 有 IPC/网络开销 |
| **生态** | 依赖 LLM 提供商 | 社区共享工具 |
| **适用场景** | 单应用专用工具 | 通用工具、跨应用集成 |

### 详细对比

#### 1. 工具定义格式

**Function Calling（OpenAI 格式）**：
```json
{
  "type": "function",
  "function": {
    "name": "list_tasks",
    "description": "列出指定日期的所有任务",
    "parameters": {
      "type": "object",
      "properties": {
        "date": {"type": "string"}
      }
    }
  }
}
```

**MCP（JSON-RPC 格式）**：
```json
{
  "name": "list_tasks",
  "description": "列出指定日期的所有任务",
  "inputSchema": {
    "type": "object",
    "properties": {
      "date": {"type": "string"}
    }
  }
}
```

#### 2. 工具调用流程

**Function Calling**：
```
用户消息 → LLM API（带 tools 参数）
→ LLM 返回 tool_calls
→ 后端直接执行函数
→ 返回结果给 LLM
→ LLM 生成最终回复
```

**MCP**：
```
用户消息 → LLM 应用
→ MCP Client 发送 tools/list 请求
→ MCP Server 返回工具列表
→ LLM 决定调用工具
→ MCP Client 发送 tools/call 请求
→ MCP Server 执行并返回结果
→ LLM 应用生成最终回复
```

#### 3. 工具注册方式

**Function Calling**：
```python
# 代码中静态注册
tool_registry.register_tool(
    definition=LIST_TASKS_TOOL,
    handler=CalendarToolHandlers.list_tasks,
    category="calendar"
)
```

**MCP**：
```python
# 服务器启动时动态提供
@app.on_request("tools/list")
async def list_tools():
    return {
        "tools": [
            {
                "name": "list_tasks",
                "description": "...",
                "inputSchema": {...}
            }
        ]
    }
```

---

## 🏗️ 架构对比图

### Function Calling 架构（当前实现）

```
┌─────────────────────────────────────────┐
│          WhatNote 应用                   │
│                                         │
│  ┌────────────┐    ┌──────────────┐   │
│  │ LLM Service│────▶│Tool Registry │   │
│  └─────┬──────┘    └──────┬───────┘   │
│        │                   │            │
│        │ 直接调用            │            │
│        │                   │            │
│        ▼                   ▼            │
│  ┌──────────────────────────────┐     │
│  │     Tool Executor             │     │
│  │  (执行工具处理器)              │     │
│  └──────────────────────────────┘     │
│                                         │
│  所有组件在同一进程内                   │
└─────────────────────────────────────────┘
```

### MCP 架构

```
┌─────────────────────────────────────────┐
│    LLM 应用（Claude Desktop）            │
│  ┌─────────────────────────────────┐   │
│  │      MCP Client                 │   │
│  └──────────────┬──────────────────┘   │
│                 │ JSON-RPC               │
└─────────────────┼───────────────────────┘
                  │
                  │ STDIO / HTTP+SSE
                  │
┌─────────────────┼───────────────────────┐
│                 │                        │
│  ┌───────────────▼──────────────┐       │
│  │   WhatNote MCP Server        │       │
│  │  - 窗口管理工具               │       │
│  │  - 课程展板工具               │       │
│  │  - 日历任务工具               │       │
│  └──────────────────────────────┘       │
│                                         │
│  独立进程/服务                          │
└─────────────────────────────────────────┘
```

---

## 🤔 迁移到 MCP 的考虑

### 何时应该使用 MCP？

**适合使用 MCP 的场景**：
1. ✅ 工具需要被多个 LLM 应用共享（如 Claude Desktop、Cursor IDE）
2. ✅ 工具需要独立部署和更新
3. ✅ 希望工具可以被社区复用
4. ✅ 需要支持远程工具服务

**不需要 MCP 的场景**：
1. ✅ 工具仅用于当前应用（如 WhatNote）
2. ✅ 追求简单直接，不想引入额外复杂度
3. ✅ 性能要求高，需要低延迟
4. ✅ 工具与业务逻辑紧密耦合

### 当前项目的建议

**我们目前的实现（Function Calling）是合适的**，因为：

1. ✅ **简单直接**：工具直接在应用内，无需额外进程
2. ✅ **性能优秀**：无 IPC/网络开销
3. ✅ **易于维护**：所有代码在同一代码库
4. ✅ **功能完整**：已实现 16 个工具，满足需求

**未来可以考虑 MCP 的情况**：
- 如果希望将 WhatNote 工具开放给其他 LLM 应用使用
- 如果需要将工具作为独立服务部署
- 如果希望工具可以被社区共享

### 如何实现 MCP 支持（未来可选）

如果未来需要支持 MCP，可以：

1. **创建 MCP 服务器**：
```python
# mcp_server.py
from mcp import Server
from mcp.server.stdio import stdio_server

server = Server("whatnote-tools")

@server.list_tools()
async def list_tools():
    # 返回工具列表
    return [LIST_TASKS_TOOL, ...]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    # 执行工具
    return await tool_executor.execute(name, arguments)

if __name__ == "__main__":
    stdio_server(server)
```

2. **保持双重支持**：
   - 内部继续使用 Function Calling（性能好）
   - 对外提供 MCP 服务器（可复用）

---

## 📊 总结

### 当前项目：Function Calling ✅

- **类型**：OpenAI/Anthropic/Qwen 标准工具调用
- **架构**：单应用内嵌
- **状态**：✅ 已实现并测试通过
- **工具数**：16 个
- **适用场景**：WhatNote 专用工具

### MCP：更高层次的协议

- **类型**：Anthropic 推动的开放标准
- **架构**：服务器-客户端分离
- **状态**：❌ 未实现（未来可选）
- **适用场景**：跨应用共享工具

### 结论

**当前实现（Function Calling）完全满足需求**，无需立即迁移到 MCP。MCP 更适合需要工具复用和跨应用集成的场景。

---

## 📚 参考资料

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) - 官方文档（待确认）
- [JSON-RPC 2.0 规范](https://www.jsonrpc.org/specification)

---

**最后更新**：2025-11-04

