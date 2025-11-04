# LLM Tools Call 集成方案

## 🎯 目标

让 AI 助手能够通过工具调用来操作 WhatNote 系统，实现自然语言驱动的笔记管理。

---

## 📋 当前工具集

### 已实现的工具（16个）

#### 窗口管理 (7个)
1. `create_window` - 创建窗口
2. `get_windows` - 获取窗口列表
3. `read_window` - 读取窗口内容
4. `update_window` - 更新窗口内容
5. `edit_window` - 精细编辑窗口
6. `delete_window` - 删除窗口
7. `search_windows` - 搜索窗口

#### 课程展板 (2个)
8. `create_course` - 创建课程
9. `create_board` - 创建展板

#### 日历任务 (7个)
10. `add_task` - 添加任务
11. `list_tasks` - 列出任务
12. `toggle_task` - 切换完成状态
13. `update_task` - 修改任务
14. `delete_task` - 删除任务
15. `search_tasks` - 搜索任务
16. `get_upcoming_tasks` - 获取未来任务

---

## 🔧 集成方案

### 方案 A: 在 ChatWindow 中集成（推荐）⭐

**优势**：
- 用户已经习惯在 ChatWindow 中与 AI 对话
- 自然的对话界面
- 可以显示工具执行过程
- 支持多轮对话

**实现位置**：
- `llm_service.py` - LLM 服务层
- `ChatWindow.js` - 前端聊天窗口

**用户体验**：
```
用户: "帮我创建一个Python学习课程，包含基础语法和数据结构两个章节"

AI: 正在为您创建课程...
    [调用 create_course]
    [调用 create_board] × 2
    
    ✅ 已创建课程：Python学习
    - 章节1：基础语法
    - 章节2：数据结构
    
    您可以使用 'cd "Python学习"' 进入课程查看。
```

---

### 方案 B: 在控制台中添加 AI 模式

**优势**：
- 命令行风格，更加极客
- 可以混合使用自然语言和命令
- 适合高级用户

**实现位置**：
- `console_handler.py` - 添加 `ai` 命令
- `llm_service.py` - LLM 服务层

**用户体验**：
```bash
C:\WHATNOTE> ai "帮我整理今天的任务"

AI: 正在分析您的任务...
    [调用 list_tasks]
    [调用 search_tasks]
    
您今天有3个任务：
1. 09:00 晨会 ✓
2. 14:30 开会 (未完成)
3. 16:00 写报告 (未完成)

建议：先完成开会，再写报告。
```

---

## 🚀 实现步骤（方案 A）

### 步骤 1: 修改 `llm_service.py`

**1.1 添加工具参数**
```python
async def chat(self, messages, files=None, use_tools=True):
    # 获取可用工具
    if use_tools:
        from tools import tool_registry
        tools = tool_registry.get_all_tools()
    
    # 调用 LLM
    response = await client.chat.completions.create(
        model=self.model,
        messages=messages,
        tools=tools if use_tools else None,  # ⭐ 添加工具
        ...
    )
```

**1.2 实现工具调用循环**
```python
async def chat_with_tools(self, messages, files=None):
    max_iterations = 5  # 防止无限循环
    
    for i in range(max_iterations):
        response = await self.chat(messages, files, use_tools=True)
        
        # 检查是否有工具调用
        if response.choices[0].finish_reason == 'tool_calls':
            tool_calls = response.choices[0].message.tool_calls
            
            # 执行工具
            from tools import tool_executor
            tool_results = []
            
            for tool_call in tool_calls:
                result = await tool_executor.execute_tool_call(tool_call)
                tool_results.append(result)
            
            # 将结果添加到上下文
            messages.append(response.choices[0].message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result.data)
            })
            
            # 继续下一轮
            continue
        else:
            # 没有工具调用，返回结果
            return response
    
    # 达到最大迭代次数
    return response
```

**1.3 添加截断机制**
```python
# 按照您之前的想法，截断接收
if tool_calls:
    # 只处理第一个工具调用
    tool_call = tool_calls[0]
    result = await tool_executor.execute_tool_call(tool_call)
    # 返回结果，等待下一轮
```

---

### 步骤 2: 修改前端 ChatWindow

**2.1 添加工具调用开关**
```javascript
const [useTools, setUseTools] = useState(true);
```

**2.2 调用工具增强的 API**
```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({
    messages,
    use_tools: useTools  // ⭐ 启用工具
  })
});
```

**2.3 显示工具执行过程**
```javascript
// 显示正在调用的工具
if (message.tool_calls) {
  message.tool_calls.forEach(call => {
    addMessage({
      role: 'system',
      content: `🔧 正在调用工具: ${call.function.name}...`
    });
  });
}
```

---

### 步骤 3: 添加工具调用 API

**在 `main.py` 中添加**：
```python
@app.post("/api/chat/with-tools")
async def chat_with_tools(request: Dict):
    """支持工具调用的聊天API"""
    messages = request.get("messages", [])
    use_tools = request.get("use_tools", True)
    
    llm_service = LLMService()
    response = await llm_service.chat_with_tools(messages)
    
    return response
```

---

### 步骤 4: 测试场景

#### 场景 1: 创建课程和展板
```
用户: "帮我创建一个机器学习课程，包含监督学习、无监督学习、强化学习三个章节"

AI: [调用 create_course("机器学习", "AI基础课程")]
    [调用 create_board("course-xxx", "监督学习")]
    [调用 create_board("course-xxx", "无监督学习")]
    [调用 create_board("course-xxx", "强化学习")]
    
    "已为您创建课程'机器学习'，包含3个章节。"
```

#### 场景 2: 整理笔记
```
用户: "帮我整理一下生态学课程的笔记"

AI: [调用 get_windows("board-xxx")]
    [调用 search_windows("生态", "board-xxx")]
    
    "找到15个窗口，建议分类为：
     1. 基础概念 (5个)
     2. 生态系统 (7个)
     3. 应用案例 (3个)"
```

#### 场景 3: 任务规划
```
用户: "帮我规划明天的学习任务"

AI: [调用 add_task("2024-11-06", "复习概念", "09:00")]
    [调用 add_task("2024-11-06", "做练习", "10:30")]
    [调用 add_task("2024-11-06", "写总结", "14:00")]
    
    "已为您规划明天的任务：
     09:00 复习概念
     10:30 做练习
     14:00 写总结"
```

---

## ⚠️ 注意事项

### 1. 上下文管理
- 保持工具调用历史
- 避免上下文过长
- 定期清理旧消息

### 2. 错误处理
- 工具调用失败时的恢复
- 参数验证错误的提示
- 网络错误的重试

### 3. 安全性
- 限制工具调用次数（防止死循环）
- 验证工具调用的合法性
- 敏感操作需要用户确认

### 4. 用户体验
- 显示工具执行进度
- 可以中断长时间的操作
- 提供工具调用的详细日志

---

## 💡 推荐实现顺序

1. ✅ **基础工具系统** - 已完成
2. 🎯 **LLM 服务集成** - 下一步
3. **ChatWindow 增强** - UI 改进
4. **测试和优化** - 完善体验

---

准备开始实现！🚀

