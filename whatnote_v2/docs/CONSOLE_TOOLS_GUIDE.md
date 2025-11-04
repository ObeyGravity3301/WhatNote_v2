# WhatNote 控制台工具使用指南

## 🎯 概述

WhatNote 控制台是一个强大的命令行工具，允许您通过文本命令来操作课程、展板和窗口，同时前端界面会实时同步您的操作。

## 🚀 打开控制台

### 方式 1：开始菜单
点击桌面左下角的 **开始** 按钮 → 选择 **工具控制台**

### 方式 2：快捷键
按下 `Ctrl + Shift + C`

---

## 📂 导航系统

控制台采用类似文件系统的导航结构：
```
/ (根目录)
├── 课程A/
│   ├── 展板1
│   ├── 展板2
│   └── ...
├── 课程B/
└── ...
```

### 当前路径

控制台提示符会显示您当前所在的位置：
- `C:\WHATNOTE>` - 在根目录
- `/课程名>` - 在课程目录
- `/课程名/展板名>` - 在展板目录

---

## 🔧 基础命令

### 1. `courses` - 查看所有课程
```bash
C:\WHATNOTE> courses
```
显示所有课程的列表，包括课程名称、ID和描述。

### 2. `cd` - 切换目录

#### 进入课程
```bash
C:\WHATNOTE> cd "生态"
已进入课程: 生态
使用 'boards' 查看展板列表

/生态> 
```

#### 进入展板（在课程目录中）
```bash
/生态> cd "第一章"
已进入展板: 第一章
现在可以使用窗口工具了

/生态/第一章> 
```

#### 直接跳转到展板（一步到位）
```bash
C:\WHATNOTE> cd "生态/第一章"
已进入展板: 生态/第一章
现在可以使用窗口工具了

/生态/第一章> 
```
✨ **前端同步**：执行 cd 到展板后，前端会自动切换到对应的展板！

#### 返回上一级
```bash
/生态/第一章> cd ..
已返回课程目录

/生态> 
```

#### 返回根目录
```bash
/生态/第一章> cd /
已返回根目录

C:\WHATNOTE> 
```

### 3. `boards` - 查看当前课程的展板列表
```bash
/生态> boards
展板列表 (共 3 个):
============================================================

 1. 第一章
    ID: board-1758563606686

 2. 第二章 <- 当前
    ID: board-1758712716432

 3. 实验笔记
    ID: board-1759273825368

使用 'cd "展板名"' 进入展板
```

### 4. `ls` - 列出当前目录内容
- 在根目录：等同于 `courses`
- 在课程目录：等同于 `boards`
- 在展板目录：提示使用 `get_windows`

### 5. `pwd` - 显示当前路径
```bash
/生态/第一章> pwd
当前路径: /生态/第一章
```

### 6. `help` - 查看帮助
```bash
C:\WHATNOTE> help
显示所有可用命令和使用说明
```

查看特定工具的帮助：
```bash
C:\WHATNOTE> help create_window
显示 create_window 工具的详细参数说明和示例
```

### 7. `tools` - 列出所有工具
```bash
C:\WHATNOTE> tools
可用工具 (共 6 个):
============================================================

 1. create_window - 在指定展板上创建一个新窗口
 2. get_windows - 获取指定展板上的所有窗口列表
 3. read_window - 读取指定窗口的完整内容
 4. update_window - 更新窗口的内容
 5. delete_window - 删除指定窗口
 6. search_windows - 搜索展板上的窗口
```

### 8. `history` - 查看命令历史
```bash
C:\WHATNOTE> history
显示最近执行的命令
```

### 9. `clear` - 清空控制台
```bash
C:\WHATNOTE> clear
```

---

## 🛠️ 窗口管理工具

### 前提条件
**所有窗口工具都需要先进入展板目录**（使用 `cd` 命令）

### 1. `create_window` - 创建窗口

#### 基础用法
```bash
/生态/第一章> create_window title="我的笔记" content="# 标题\n这是内容"
成功创建窗口
============================================================

窗口ID: window_1761285759559
标题: 我的笔记
类型: text

提示: 使用 'read_window window_id="..."' 查看窗口内容
```

#### 参数说明
- `title` (必需)：窗口标题
- `content` (可选)：初始内容，支持 Markdown 格式
- `window_type` (可选)：窗口类型，默认 `text`
  - 可选值：`text`, `image`, `video`, `audio`, `pdf`, `document`
- `position` (可选)：窗口位置 `{"x": 100, "y": 100}`
- `size` (可选)：窗口大小 `{"width": 600, "height": 400}`

#### 特性
✨ **前端同步**：创建窗口后，前端展板会自动刷新，新窗口图标会立即出现！

✨ **完整流程**：窗口创建遵循与右键菜单相同的逻辑，包括：
- 生成唯一的窗口 ID
- 创建 JSON 配置文件 (`files/窗口标题.md.json`)
- 创建 Markdown 内容文件 (`files/窗口标题.md`)
- 自动分配桌面图标网格位置

### 2. `get_windows` - 列出窗口

```bash
/生态/第一章> get_windows
窗口列表 (共 5 个):
============================================================

 1. 概念笔记 [text]
    ID: window_1758563710234
    创建: 2024-11-01T10:15:30
    更新: 2024-11-01T14:30:45

 2. 实验数据 [text]
    ID: window_1758563810567
    创建: 2024-11-01T11:20:15

 3. 参考资料.pdf [pdf]
    ID: window_1758564120789
    创建: 2024-11-01T12:45:00

使用 'create_window title="标题" content="内容"' 创建新窗口
```

#### 参数
- `include_hidden` (可选)：是否包含隐藏的窗口，默认 `false`

```bash
/生态/第一章> get_windows include_hidden=true
```

### 3. `read_window` - 读取窗口内容

```bash
/生态/第一章> read_window window_id="window_1758563710234"
窗口内容
============================================================

窗口ID: window_1758563710234
标题: 概念笔记
类型: text
内容长度: 523 字符
创建时间: 2024-11-01T10:15:30
更新时间: 2024-11-01T14:30:45

内容:
------------------------------------------------------------
# 生态学基本概念

## 生态系统的定义
生态系统是指在一定时间内生物和环境构成的统一整体...

[详细内容]
```

#### 特性
✨ **读取真实内容**：从 `files/窗口标题.md` 文件读取实际的 Markdown 内容，而不仅仅是 JSON 配置！

#### 内容显示
- 完整显示 ≤500 字符的内容
- 超过 500 字符会截断显示，并提示查看前端窗口

### 4. `update_window` - 更新窗口内容

#### 替换全部内容（默认）
```bash
/生态/第一章> update_window window_id="window_1758563710234" content="# 新标题\n\n全新的内容"
成功更新窗口
============================================================

窗口ID: window_1758563710234
更新模式: replace
新内容长度: 24 字符

提示: 使用 'read_window' 查看更新后的内容
```

#### 追加内容到末尾
```bash
/生态/第一章> update_window window_id="window_1758563710234" content="\n\n## 新增章节\n补充内容..." mode="append"
```

#### 插入内容到开头
```bash
/生态/第一章> update_window window_id="window_1758563710234" content="## 序言\n这是开头内容\n\n" mode="prepend"
```

#### 参数
- `window_id` (必需)：窗口 ID
- `content` (必需)：新内容
- `mode` (可选)：更新模式
  - `replace`：替换全部内容（默认）
  - `append`：追加到末尾
  - `prepend`：插入到开头

#### 特性
✨ **前端同步**：更新后前端展板会自动刷新！

### 5. `delete_window` - 删除窗口

```bash
/生态/第一章> delete_window window_id="window_1758563710234"
成功删除窗口
============================================================

窗口ID: window_1758563710234

窗口已移至回收站
```

#### 特性
✨ **前端同步**：删除后前端展板会自动刷新，窗口图标消失！
✨ **安全删除**：窗口被移到回收站，不是永久删除！

### 6. `search_windows` - 搜索窗口

```bash
/生态/第一章> search_windows query="生态系统"
搜索结果 (共 2 个):
============================================================
关键词: 生态系统

 1. 概念笔记
    ID: window_1758563710234
    匹配位置: title, content

 2. 实验总结
    ID: window_1758564320456
    匹配位置: content
```

#### 参数
- `query` (必需)：搜索关键词
- `limit` (可选)：最多返回多少个结果，默认 `10`
- `search_in` (可选)：搜索范围
  - `all`：标题和内容（默认）
  - `title`：仅标题
  - `content`：仅内容

```bash
/生态/第一章> search_windows query="生态" limit=5 search_in="title"
```

---

## 💡 实用技巧

### 1. 命令简写
您可以使用首字母缩写：
```bash
C:\WHATNOTE> c     # courses
C:\WHATNOTE> b     # boards  
C:\WHATNOTE> t     # tools
C:\WHATNOTE> h     # help
```

### 2. 自动补全 board_id
进入展板后，所有窗口工具会自动使用当前展板的 ID，无需手动指定 `board_id` 参数！

❌ **不需要这样写：**
```bash
/生态/第一章> create_window board_id="board-1758563606686" title="笔记"
```

✅ **只需这样写：**
```bash
/生态/第一章> create_window title="笔记"
```

### 3. 命令历史导航
- 按 `↑` (上箭头)：查看上一条命令
- 按 `↓` (下箭头)：查看下一条命令

### 4. 带引号的参数
如果参数值包含空格或特殊字符，请使用引号包裹：
```bash
/生态/第一章> create_window title="第一章 概念总结" content="# 内容\n这里有换行"
```

### 5. 快速工作流

#### 创建笔记并查看
```bash
C:\WHATNOTE> cd "生态/第一章"
/生态/第一章> create_window title="今日笔记" content="# 今日学习\n\n## 要点"
/生态/第一章> get_windows
/生态/第一章> read_window window_id="window_..."
```

#### 更新笔记内容
```bash
/生态/第一章> read_window window_id="window_1758563710234"
/生态/第一章> update_window window_id="window_1758563710234" content="\n\n## 新增内容\n补充..." mode="append"
/生态/第一章> read_window window_id="window_1758563710234"
```

---

## ⚡ 前后端同步

### 同步机制

控制台操作会通过事件系统与前端实时同步：

| 操作 | 前端响应 |
|------|---------|
| `cd` 到展板 | 自动切换到该展板 |
| `create_window` | 刷新展板，显示新窗口图标 |
| `update_window` | 刷新展板，更新窗口内容 |
| `delete_window` | 刷新展板，移除窗口图标 |

### 查看同步日志

打开浏览器控制台（F12），可以看到同步事件的详细日志：
```
[Console] 执行前端同步操作: {type: 'switch_board', course_id: '...', board_id: '...'}
[App] 控制台切换展板: {...}
[App] 已切换到展板: 第一章
[BoardCanvas] 收到刷新展板请求
```

---

## ❌ 错误处理

### 常见错误

#### 1. 工具不存在
```bash
C:\WHATNOTE> create
未知命令或工具: create
你是否想输入: create_window
```

#### 2. 缺少必需参数
```bash
/生态/第一章> create_window content="内容"
执行失败: 缺少必需参数: 'title'
```

#### 3. 未进入展板
```bash
C:\WHATNOTE> create_window title="笔记"
执行失败: 缺少必需参数: 'board_id'
提示: 请先使用 'cd' 命令进入展板
```

### 智能提示

控制台会提供智能错误提示和建议：
```bash
C:\WHATNOTE> windw
未知命令或工具: windw
相似工具: get_windows
相似工具: update_window

使用 'help' 查看所有命令
使用 'tools' 查看所有工具
```

---

## 📝 示例场景

### 场景 1：创建课程笔记

```bash
# 1. 查看所有课程
C:\WHATNOTE> courses

# 2. 进入目标课程
C:\WHATNOTE> cd "生态学"

# 3. 查看展板
/生态学> boards

# 4. 进入展板
/生态学> cd "第三章"

# 5. 创建笔记窗口
/生态学/第三章> create_window title="种群生态学" content="# 种群生态学\n\n## 种群的概念\n种群是指..."

# 6. 查看刚创建的窗口
/生态学/第三章> get_windows

# 7. 读取内容确认
/生态学/第三章> read_window window_id="window_1761285759559"
```

### 场景 2：批量查看和编辑

```bash
# 快速进入展板
C:\WHATNOTE> cd "数据结构/第二章"

# 列出所有窗口
/数据结构/第二章> get_windows

# 读取第一个窗口
/数据结构/第二章> read_window window_id="window_xxx1"

# 追加内容
/数据结构/第二章> update_window window_id="window_xxx1" content="\n\n## 补充说明\n..." mode="append"

# 读取第二个窗口
/数据结构/第二章> read_window window_id="window_xxx2"

# 替换内容
/数据结构/第二章> update_window window_id="window_xxx2" content="# 全新内容\n..."
```

### 场景 3：搜索和清理

```bash
# 进入展板
C:\WHATNOTE> cd "项目管理/任务看板"

# 搜索包含"已完成"的窗口
/项目管理/任务看板> search_windows query="已完成"

# 删除不需要的窗口
/项目管理/任务看板> delete_window window_id="window_xxx1"
/项目管理/任务看板> delete_window window_id="window_xxx2"

# 确认删除结果
/项目管理/任务看板> get_windows
```

---

## 🎓 进阶使用

### 多行内容与转义字符

控制台支持常见的转义字符，可以在参数中使用：

| 转义序列 | 实际字符 | 说明 |
|---------|---------|------|
| `\n` | 换行符 | 创建新的一行 |
| `\t` | 制表符 | 插入制表符（Tab） |
| `\r` | 回车符 | 回车 |
| `\\` | 反斜杠 | 输入反斜杠本身 |
| `\"` | 双引号 | 在双引号字符串中输入引号 |
| `\'` | 单引号 | 在单引号字符串中输入引号 |

#### 示例 1：使用 `\n` 创建多行内容
```bash
/生态/第一章> create_window title="笔记" content="# 第一部分\n\n内容1\n\n## 第二部分\n\n内容2"
```

**实际创建的内容：**
```markdown
# 第一部分

内容1

## 第二部分

内容2
```

#### 示例 2：使用 `\n` 追加内容
```bash
/生态/第一章> update_window window_id="window_xxx" content="\n\n## 新增章节\n\n这是新增的内容" mode="append"
```

**实际追加的内容：**
```markdown

## 新增章节

这是新增的内容
```

#### 示例 3：包含引号的内容
```bash
/生态/第一章> create_window title="笔记" content="他说\"这很重要\""
```

**实际内容：**
```
他说"这很重要"
```

#### 示例 4：包含反斜杠
```bash
/生态/第一章> create_window title="路径示例" content="文件路径：C:\\Users\\Documents\\file.txt"
```

**实际内容：**
```
文件路径：C:\Users\Documents\file.txt
```

### 💡 提示

- ✅ **推荐使用双引号**：参数值用双引号包裹时，转义字符会被正确处理
- ✅ **`\n\n` 创建段落**：Markdown 中连续两个换行会创建新段落
- ⚠️ **注意转义顺序**：反斜杠 `\\` 要放在其他转义字符之前处理

---

## 🔍 调试技巧

### 查看详细日志

打开浏览器开发者工具（F12），在控制台标签页可以看到：
- WebSocket 连接状态
- 命令发送和响应
- 前端同步事件
- 展板刷新日志

### 后端日志

查看后端日志文件：
```bash
tail -f /tmp/whatnote.log
```

---

## 📚 总结

WhatNote 控制台提供了一种快速、高效的方式来管理您的课程笔记：

✅ **类文件系统导航**：直观的 `cd`, `ls`, `pwd` 命令  
✅ **自动前端同步**：操作即时反映到界面  
✅ **完整文件操作**：读写真实的 `.md` 文件  
✅ **智能错误提示**：友好的错误信息和建议  
✅ **简化工作流程**：自动补全参数，减少输入

掌握这些命令后，您可以快速创建、查看、编辑和管理笔记，同时享受命令行的高效和前端界面的直观！

---

**最后更新**: 2025-11-03  
**版本**: 1.0

