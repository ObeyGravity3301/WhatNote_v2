# WhatNote 工具调用系统

## 📋 概述

为 LLM 提供结构化的工具调用能力，遵循 OpenAI Function Calling 标准格式，支持窗口管理、内容操作等功能。

## 🏗️ 架构

```
tools/
├── __init__.py              # 模块入口
├── schemas.py              # 数据结构定义（Pydantic）
├── tool_registry.py        # 工具注册中心（单例）
├── tool_executor.py        # 工具执行引擎（单例）
└── builtin_tools.py        # 内置工具实现
```

### 核心组件

1. **ToolRegistry（工具注册中心）**
   - 管理所有可用工具的定义和处理器
   - 支持按分类组织工具
   - 提供 OpenAI 格式的工具列表导出

2. **ToolExecutor（工具执行引擎）**
   - 验证工具调用参数
   - 执行工具处理器
   - 返回标准化的结果

3. **ToolDefinition（工具定义）**
   - 遵循 OpenAI Function Calling 格式
   - 包含名称、描述、参数 schema
   - 支持参数验证

4. **ToolHandler（工具处理器）**
   - 异步函数接口
   - 接收参数和上下文
   - 返回 `ToolResult` 对象

## 🔧 内置工具

目前提供 6 个窗口操作工具：

### 1. create_window
创建新窗口

**参数：**
- `board_id` (string, required): 展板ID
- `title` (string, required): 窗口标题
- `content` (string, optional): 初始内容
- `window_type` (enum, optional): 窗口类型
- `position` (object, optional): 初始位置 {x, y}
- `size` (object, optional): 初始大小 {width, height}

**返回：**
```json
{
  "window_id": "window_1234567890",
  "title": "新窗口",
  "type": "text",
  "message": "成功创建窗口 '新窗口'"
}
```

### 2. get_windows
获取窗口列表

**参数：**
- `board_id` (string, required): 展板ID
- `include_hidden` (boolean, optional): 是否包含隐藏窗口

**返回：**
```json
{
  "board_id": "board-1234567890",
  "count": 5,
  "windows": [
    {
      "id": "window_001",
      "title": "示例窗口",
      "type": "text",
      "created_at": "2025-11-02T...",
      "updated_at": "2025-11-02T...",
      "isMinimized": false
    }
  ]
}
```

### 3. read_window
读取窗口内容

**参数：**
- `board_id` (string, required): 展板ID
- `window_id` (string, required): 窗口ID

**返回：**
```json
{
  "window_id": "window_001",
  "title": "示例窗口",
  "type": "text",
  "content": "# 窗口内容\n...",
  "content_length": 123,
  "created_at": "2025-11-02T...",
  "updated_at": "2025-11-02T..."
}
```

### 4. update_window
更新窗口内容

**参数：**
- `board_id` (string, required): 展板ID
- `window_id` (string, required): 窗口ID
- `content` (string, required): 新内容
- `mode` (enum, optional): 更新模式
  - `replace`: 替换全部内容（默认）
  - `append`: 追加到末尾
  - `prepend`: 插入到开头

**返回：**
```json
{
  "window_id": "window_001",
  "mode": "append",
  "content_length": 456,
  "message": "成功更新窗口内容（append 模式）"
}
```

### 5. delete_window
删除窗口

**参数：**
- `board_id` (string, required): 展板ID
- `window_id` (string, required): 窗口ID
- `permanent` (boolean, optional): 是否永久删除（默认移到回收站）

**返回：**
```json
{
  "window_id": "window_001",
  "permanent": false,
  "message": "窗口已移动到回收站"
}
```

### 6. search_windows
搜索窗口

**参数：**
- `board_id` (string, required): 展板ID
- `query` (string, required): 搜索关键词
- `search_in` (enum, optional): 搜索范围
  - `title`: 仅标题
  - `content`: 仅内容
  - `both`: 标题和内容（默认）
- `limit` (integer, optional): 最多返回结果数（1-50，默认10）

**返回：**
```json
{
  "query": "测试",
  "board_id": "board-1234567890",
  "count": 2,
  "results": [
    {
      "id": "window_001",
      "title": "测试窗口",
      "type": "text",
      "matched_in": ["title", "content"],
      "updated_at": "2025-11-02T..."
    }
  ]
}
```

## 🚀 使用方法

### 在 main.py 中初始化

```python
from tools import tool_registry, register_builtin_tools
from storage.content_manager import ContentManager

# 初始化
register_builtin_tools(tool_registry, content_manager)

# 获取工具列表（OpenAI 格式）
tools = tool_registry.get_all_tools()
```

### LLM 调用工具

```python
from tools import tool_executor, ToolCall

# 构建工具调用（来自 LLM 响应）
tool_call = ToolCall(
    id="call_abc123",
    type="function",
    function={
        "name": "create_window",
        "arguments": {
            "board_id": "board-1234567890",
            "title": "新建笔记",
            "content": "# Hello World"
        }
    }
)

# 执行工具
result = await tool_executor.execute_tool_call(
    tool_call,
    context={"user_id": "user123"}
)

# 检查结果
if result.is_success():
    print(f"成功: {result.data}")
else:
    print(f"失败: {result.error}")

# 转换为 LLM 消息格式
llm_message = result.to_llm_message()
```

## 📦 添加自定义工具

### 1. 定义工具

```python
from tools import ToolDefinition

MY_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "my_custom_tool",
        "description": "工具描述",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数说明"
                }
            },
            "required": ["param1"]
        }
    }
)
```

### 2. 实现处理器

```python
from tools import ToolHandler, ToolResult, ToolStatus

async def my_tool_handler(args, context):
    try:
        param1 = args["param1"]
        
        # 执行业务逻辑
        result_data = do_something(param1)
        
        return ToolResult(
            tool_call_id=context.get("call_id", ""),
            tool_name="my_custom_tool",
            status=ToolStatus.SUCCESS,
            data=result_data
        )
    except Exception as e:
        return ToolResult(
            tool_call_id=context.get("call_id", ""),
            tool_name="my_custom_tool",
            status=ToolStatus.ERROR,
            error=str(e)
        )

handler = ToolHandler(executor=my_tool_handler)
```

### 3. 注册工具

```python
from tools import tool_registry

tool_registry.register_tool(
    MY_TOOL,
    handler,
    category="custom"
)
```

## 🧪 测试

运行内置工具测试：

```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2/backend
python test_builtin_tools.py
```

测试覆盖：
- ✅ 获取窗口列表
- ✅ 创建新窗口
- ✅ 读取窗口内容
- ✅ 更新窗口内容（追加模式）
- ✅ 搜索窗口
- ✅ 删除窗口（移到回收站）

## 📝 设计原则

1. **遵循标准**: 完全兼容 OpenAI Function Calling 格式
2. **类型安全**: 使用 Pydantic 进行参数验证
3. **异步优先**: 所有工具处理器都是异步函数
4. **错误隔离**: 工具执行错误不会影响系统稳定性
5. **可扩展性**: 易于添加新工具，支持分类管理
6. **标准化输出**: 统一的 `ToolResult` 格式

## 🔄 下一步计划

- [ ] 集成到 LLM 服务（llm_service.py）
- [ ] 实现流式响应处理
- [ ] 添加错误截断逻辑
- [ ] 实现待办管理工具
- [ ] 实现文件系统工具
- [ ] 添加工具执行日志记录
- [ ] 实现工具调用统计

## 📚 参考

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Qwen Tool Calling](https://help.aliyun.com/zh/model-studio/developer-reference/qwen-function-call)




