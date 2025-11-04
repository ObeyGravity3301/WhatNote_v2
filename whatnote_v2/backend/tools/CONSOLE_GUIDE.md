# WhatNote 工具控制台使用指南

## 启动控制台

在前端界面点击：
```
开始菜单 -> 工具控制台
```

控制台会以 Win98 CMD 风格窗口的形式出现在右下角。

---

## 基本命令

### 查看帮助
```
help
```
显示所有可用命令的列表

### 查看工具详情
```
help <tool_name>
```
例如:
```
help create_window
help get_windows
```

### 列出所有工具
```
tools
```
显示所有可用工具及其描述

### 查看命令历史
```
history
```
显示最近 20 条执行的命令

### 切换当前展板
```
use board-1234567890
```
设置后，后续命令会自动填充 board_id

### 清屏
```
clear
```

### 退出
```
exit
```

---

## 工具调用语法

### 基本格式
```
<tool_name> param1="value1" param2="value2"
```

### 参数类型
- **字符串**: 用引号包裹 `title="我的窗口"`
- **数字**: 直接写 `limit=10`
- **布尔**: 写 `true` 或 `false`

### 示例

#### 1. 获取窗口列表
```
get_windows board_id="board-1756987954946"
```

#### 2. 创建新窗口
```
create_window board_id="board-1756987954946" title="测试窗口" content="# Hello World"
```

#### 3. 读取窗口内容
```
read_window board_id="board-1756987954946" window_id="window_1234567890"
```

#### 4. 更新窗口内容（追加模式）
```
update_window board_id="board-1756987954946" window_id="window_1234567890" content="新增内容" mode="append"
```

#### 5. 搜索窗口
```
search_windows board_id="board-1756987954946" query="笔记" search_in="both" limit=5
```

#### 6. 删除窗口（移到回收站）
```
delete_window board_id="board-1756987954946" window_id="window_1234567890"
```

#### 7. 永久删除窗口
```
delete_window board_id="board-1756987954946" window_id="window_1234567890" permanent=true
```

---

## 使用技巧

### 使用 use 简化操作
```
use board-1756987954946
get_windows
create_window title="新窗口"
```
设置 `use` 后，不需要每次都输入 board_id

### 使用方向键浏览历史
- **↑**: 上一条命令
- **↓**: 下一条命令

### 复制输出内容
选中控制台输出文本即可复制（Ctrl+C）

---

## 可用工具列表

| 工具名称 | 功能 | 必需参数 |
|---------|------|---------|
| `create_window` | 创建新窗口 | board_id, title |
| `get_windows` | 获取窗口列表 | board_id |
| `read_window` | 读取窗口内容 | board_id, window_id |
| `update_window` | 更新窗口内容 | board_id, window_id, content |
| `delete_window` | 删除窗口 | board_id, window_id |
| `search_windows` | 搜索窗口 | board_id, query |

---

## 输出说明

### 成功输出（绿色）
```
执行成功: create_window
------------------------------------------------------------

{
  "window_id": "window_1234567890",
  "title": "新窗口",
  "type": "text",
  "message": "成功创建窗口 '新窗口'"
}
```

### 错误输出（红色）
```
执行失败: 展板不存在或创建失败: board-invalid
```

### 普通文本（灰色）
帮助信息、工具列表等

---

## 常见问题

### Q: 如何知道 board_id？
**A**: 在前端选中一个展板后，打开控制台，输入 `boards` 命令（或直接在前端地址栏查看）

### Q: 控制台显示"未连接"？
**A**: 检查后端服务是否运行：
```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2/backend
python main.py
```

### Q: 如何查看工具的完整参数列表？
**A**: 使用 `help <tool_name>`
```
help create_window
```

### Q: 可以批量执行命令吗？
**A**: 当前版本不支持，需要逐条执行。后续可能添加脚本支持。

---

## 开发者提示

### 添加新工具
1. 在 `tools/builtin_tools.py` 中定义工具
2. 使用 `register_builtin_tools` 注册
3. 重启后端服务

### WebSocket 端点
```
ws://localhost:8000/ws/console
```

### 消息格式
**发送（客户端 → 服务器）:**
```
"get_windows board_id=\"board-123\""
```

**接收（服务器 → 客户端）:**
```json
{
  "type": "success",
  "content": "执行成功...",
  "data": { ... }
}
```




