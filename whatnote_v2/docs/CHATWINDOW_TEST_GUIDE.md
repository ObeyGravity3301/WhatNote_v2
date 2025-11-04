# ChatWindow 工具调用测试指南

## 🧪 测试场景

### 测试 1：查询任务（无需 board_id）

**用户**：
```
今天有什么任务？
```

**预期效果**：
```
🔧 正在调用工具: list_tasks
✅ 工具执行完成: list_tasks
💬 今天有5个任务：...
```

---

### 测试 2：创建窗口（需要 board_id）⭐

**用户**：
```
帮我创建一个笔记窗口，标题是"测试笔记"，内容是"这是一个测试"
```

**预期效果**：
```
🔧 正在调用工具: create_window
✅ 工具执行完成: create_window
💬 已为您创建窗口"测试笔记"！
```

**验证**：在当前展板上应该出现新窗口

---

### 测试 3：询问上下文

**用户**：
```
你知道我们现在在哪个展板吗？
```

**预期效果**：
```
💬 是的，我们目前在展板"[展板名]"（ID: board-xxx）。
    您可以让我在这个展板上创建窗口、搜索内容等操作。
```

---

### 测试 4：搜索窗口

**用户**：
```
搜索一下这个展板上有关Python的内容
```

**预期效果**：
```
🔧 正在调用工具: search_windows
✅ 工具执行完成: search_windows
💬 找到 X 个包含"Python"的窗口：...
```

---

### 测试 5：创建课程（无需 board_id）

**用户**：
```
帮我创建一个"测试课程"
```

**预期效果**：
```
🔧 正在调用工具: create_course
✅ 工具执行完成: create_course
💬 已为您创建课程"测试课程"！
```

**验证**：侧边栏应该出现新课程

---

## 🔍 调试技巧

### 1. 查看工具状态

```bash
curl http://localhost:8081/api/tools/status
```

应该返回：
```json
{"total_tools":16,"tools":["create_window",...]}
```

### 2. 查看上下文消息

在浏览器控制台查看发送的消息：
```javascript
// 打开控制台，发送消息前执行：
XMLHttpRequest.prototype.send = function(data) {
  console.log('发送数据:', JSON.parse(data));
  return originalSend.call(this, data);
};
```

应该看到第一条消息是：
```json
{
  "role": "system",
  "content": "当前上下文信息：\n- 展板名称：xxx\n- 展板ID：board-xxx..."
}
```

### 3. 查看工具调用日志

后端日志应该显示：
```
[LLM Tools] 开始工具调用对话，可用工具: 16 个
[LLM Tools] 第 1 轮对话
[LLM Tools] 调用 qwen API，工具数: 16
[LLM Tools] 检测到 1 个工具调用
🔧 开始执行工具: create_window
✅ 工具执行成功: create_window
```

---

## ⚠️ 常见问题

### 问题 1：LLM 说"无法获取 board_id"

**原因**：上下文消息没有正确添加

**检查**：
1. 工具调用开关是否启用（🔧 按钮为蓝色）
2. boardId 和 boardName props 是否正确传递

**解决**：刷新页面重试

---

### 问题 2：工具调用失败

**症状**：`❌ LLM调用失败`

**检查**：
```bash
# 1. 工具是否注册
curl http://localhost:8081/api/tools/status

# 2. API 配置是否正确
# 打开聊天窗口 → 设置 → 检查 API 密钥

# 3. 后端日志
tail -f /tmp/whatnote.log | grep ERROR
```

---

### 问题 3：流式显示不流畅

**症状**：内容一次性全部出现

**原因**：这是正常的，因为：
1. 工具调用使用非流式API（需要等待完整响应）
2. 每个事件会立即显示，但工具执行较快

**不是问题**：只要能看到 🔧 → ✅ → 💬 的过程就是正常的

---

### 问题 4：创建的窗口没出现

**检查**：
1. 刷新页面（Ctrl+F5）
2. 检查是否在正确的展板
3. 查看后端日志确认创建成功

---

## 📝 测试清单

- [ ] 基础对话（无工具调用）
- [ ] 查询任务（list_tasks）
- [ ] 创建窗口（create_window）✅ 需要 board_id
- [ ] 搜索窗口（search_windows）✅ 需要 board_id
- [ ] 读取窗口（read_window）✅ 需要 window_id
- [ ] 创建课程（create_course）
- [ ] 创建展板（create_board）
- [ ] 添加任务（add_task）
- [ ] 错误处理（参数错误、工具不存在等）

---

## 🎯 完整测试对话示例

```
用户: 你好
AI: 你好！我是 WhatNote 智能助手...

用户: 你能看到你可以使用的tools吗
AI: 是的，我可以使用 16 个工具...

用户: 你知道我们现在在哪个展板吗？
AI: 是的，我们在展板"xxx"（ID: board-xxx）

用户: 帮我创建一个笔记，标题是"AI测试"
AI: 🔧 正在调用工具: create_window
    ✅ 工具执行完成: create_window
    💬 已为您创建窗口"AI测试"！

用户: 今天有什么任务？
AI: 🔧 正在调用工具: list_tasks
    ✅ 工具执行完成: list_tasks
    💬 今天有5个任务：...

用户: 搜索一下这里有关Python的内容
AI: 🔧 正在调用工具: search_windows
    ✅ 工具执行完成: search_windows
    💬 找到3个相关窗口...
```

---

**测试愉快！** 🎉

