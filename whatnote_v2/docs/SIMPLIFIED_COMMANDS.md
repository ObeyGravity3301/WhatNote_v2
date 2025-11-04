# 简化命令使用指南

## 🎯 设计理念

新的简化命令系统采用**位置参数**风格，让命令更加直观和简洁，减少输入量。

## ⭐ 新特性：智能窗口识别

所有需要指定窗口的命令现在都支持**使用窗口标题**代替窗口ID！

**传统方式**（需要记住或复制长ID）：
```bash
read window_1762160636035
edit window_1762160636035 "新内容"
delete window_1762160636035
```

**新方式**（直接使用标题）：
```bash
read 今日笔记
edit 今日笔记 "新内容"
delete 今日笔记
```

### 智能匹配规则
1. ✅ **精确匹配**：完全匹配窗口标题
2. ✅ **模糊匹配**：包含指定文本的窗口（不区分大小写）
3. ✅ **自动识别ID**：以 `window_` 开头自动作为ID处理

---

### 对比

**旧格式**（API 风格）：
```bash
create_window board_id="board-xxx" window_id="window_xxx" title="标题" content="内容"
```

**新格式**（命令行风格）：
```bash
create "标题" "内容"
```

---

## 📋 完整命令列表

### 1. create - 创建窗口

#### 语法
```bash
create "标题" ["内容"]
```

#### 参数
- 第1个：窗口标题（必需）
- 第2个：窗口内容（可选，默认为空）

#### 示例
```bash
# 只有标题
/生态/第一章> create "今日笔记"

# 标题 + 内容
/生态/第一章> create "今日笔记" "# 学习笔记\n\n今天学习了..."

# 多行内容
/生态/第一章> create "章节总结" "# 第一章总结\n\n## 要点1\n内容1\n\n## 要点2\n内容2"
```

#### 别名
- `new` - 同 `create`

---

### 2. read - 读取窗口内容

#### 语法
```bash
read <窗口ID或标题>
```

#### 参数
- 窗口ID或标题（必需）

#### 示例 1：使用窗口ID
```bash
/生态/第一章> ls
# 看到窗口列表...
#  1. 今日笔记 [text]
#     ID: window_1762160636035

/生态/第一章> read window_1762160636035
```

#### 示例 2：使用窗口标题 ⭐ 新功能
```bash
/生态/第一章> ls
# 看到窗口列表...
#  1. 今日笔记 [text]
#  2. 概念总结 [text]

# 直接使用标题读取（精确匹配）
/生态/第一章> read 今日笔记

# 或使用部分标题（模糊匹配）
/生态/第一章> read 概念
```

#### 别名
- `cat` - 同 `read`（类似 Linux 的 cat 命令）

#### 💡 智能匹配规则
1. **优先精确匹配**：完全匹配窗口标题
2. **模糊匹配备用**：如果精确匹配失败，搜索包含该文本的窗口（不区分大小写）
3. **自动识别ID**：如果输入以 `window_` 开头，直接作为ID使用

---

### 3. edit - 编辑窗口内容

#### 语法

**文本操作：**
```bash
# 追加内容（默认）
edit <窗口ID或标题> "新内容"

# 替换文本
edit <窗口ID或标题> "新文本" replace "旧文本" [all]

# 在指定位置插入
edit <窗口ID或标题> "插入内容" insert "位置标记" [before|after|at]

# 删除文本
edit <窗口ID或标题> "" delete "要删除的文本" [all]
```

**行操作：**
```bash
# 插入新行
edit <窗口ID或标题> "新行内容" insert-line "行号" [before|after|at]

# 替换行
edit <窗口ID或标题> "新内容" replace-line "行号或范围"

# 删除行
edit <窗口ID或标题> "" delete-line "行号或范围"
```

#### 参数说明

1. **窗口ID或标题**（必需）- 目标窗口的ID或标题 ⭐
2. **新内容**（必需）- 要添加/替换的内容（删除时可为空）
3. **操作类型**（可选）：
   - 不写 = `append`（追加到末尾）
   - `replace` = 替换指定文本
   - `insert` = 在指定位置插入文本
   - `delete` = 删除指定文本
   - `insert-line` = 插入新行
   - `replace-line` = 替换指定行
   - `delete-line` = 删除指定行
4. **目标**（条件必需）- 查找的文本或行号
5. **选项**（可选）：
   - `all` - 替换/删除所有匹配（文本操作）
   - `before`/`after`/`at` - 插入位置

---

#### 文本操作示例

##### 示例 1：追加内容（默认）
```bash
# 使用窗口ID
/生态/第一章> edit window_xxx "\n\n## 新增章节\n\n这是新增的内容"

# 使用窗口标题 ⭐
/生态/第一章> edit 今日笔记 "\n\n## 新增章节\n\n这是新增的内容"
```

##### 示例 2：替换文本（首个匹配）
```bash
# 使用窗口标题 ⭐
/生态/第一章> edit 概念总结 "新名称" replace "旧名称"
```

##### 示例 3：替换所有匹配
```bash
/生态/第一章> edit window_xxx "生态系统" replace "系统" all
```

##### 示例 4：在指定位置之后插入
```bash
# 在 "## 第二章" 之后插入内容
/生态/第一章> edit window_xxx "\n\n这是插入的内容\n" insert "## 第二章"

# 或明确指定 after
/生态/第一章> edit window_xxx "\n新内容" insert "## 标题" after
```

##### 示例 5：在指定位置之前插入
```bash
/生态/第一章> edit window_xxx "前言\n\n" insert "# 第一章" before
```

##### 示例 6：替换指定文本（at 模式）
```bash
# 替换 "TODO" 为 "已完成"
/生态/第一章> edit window_xxx "已完成" insert "TODO" at
```

##### 示例 7：删除文本（首个匹配）
```bash
/生态/第一章> edit window_xxx "" delete "[TODO] "
```

##### 示例 8：删除所有匹配
```bash
# 删除所有草稿标记
/生态/第一章> edit window_xxx "" delete "（草稿）" all
```

---

#### 行操作示例

##### 示例 9：在指定行之后插入新行
```bash
# 在第 5 行之后插入新行
/生态/第一章> edit window_xxx "这是新插入的一行" insert-line "5"

# 或明确指定 after
/生态/第一章> edit window_xxx "新行内容" insert-line "5" after
```

##### 示例 10：在指定行之前插入新行
```bash
# 在第 1 行之前插入（添加文件头）
/生态/第一章> edit window_xxx "# 文档标题" insert-line "1" before
```

##### 示例 11：替换单行
```bash
# 替换第 10 行的内容
/生态/第一章> edit window_xxx "这是第10行的新内容" replace-line "10"
```

##### 示例 12：替换多行
```bash
# 替换第 5-8 行
/生态/第一章> edit window_xxx "这段内容替换原来的5-8行" replace-line "5-8"
```

##### 示例 13：删除单行
```bash
# 删除第 15 行
/生态/第一章> edit window_xxx "" delete-line "15"
```

##### 示例 14：删除多行
```bash
# 删除第 10-20 行
/生态/第一章> edit window_xxx "" delete-line "10-20"
```

---

#### 组合使用示例

##### 场景：修复代码注释
```bash
# 1. 查看内容
/项目/代码> read window_xxx

# 2. 删除旧注释（第 5 行）
/项目/代码> edit window_xxx "" delete-line "5"

# 3. 在第 4 行之后插入新注释
/项目/代码> edit window_xxx "    # 这是更新的注释" insert-line "4" after

# 4. 验证结果
/项目/代码> read window_xxx
```

##### 场景：批量更新术语
```bash
# 替换所有 "数据库" 为 "Database"
/技术文档> edit window_xxx "Database" replace "数据库" all
```

##### 场景：在多个位置插入内容
```bash
# 在每个章节标题后插入提示
/笔记> edit window_xxx "\n> **重点**: 待补充\n" insert "## " after
```

---

### 4. delete - 删除窗口

#### 语法
```bash
delete <窗口ID或标题>
```

#### 参数
- 窗口ID或标题（必需）

#### 示例 1：使用窗口ID
```bash
/生态/第一章> delete window_1762160636035
```

#### 示例 2：使用窗口标题 ⭐
```bash
/生态/第一章> delete 今日笔记

# 或使用别名
/生态/第一章> rm 草稿笔记
```

#### 别名
- `rm` - 同 `delete`（类似 Linux 的 rm 命令）

#### 💡 智能匹配
与 `read` 和 `edit` 相同，支持：
- 精确标题匹配
- 模糊标题匹配
- 自动识别 `window_` 格式的ID

---

### 5. search - 搜索窗口

#### 语法
```bash
search "关键词"
```

#### 参数
- 关键词（必需）

#### 示例
```bash
/生态/第一章> search "生态系统"

搜索结果 (共 3 个):
============================================================
关键词: 生态系统

 1. 概念笔记
    ID: window_1758563710234

 2. 实验总结
    ID: window_1758564320456

 3. 参考资料
    ID: window_1758565123789
```

#### 别名
- `find` - 同 `search`

---

### 6. ls - 列出窗口（已有命令）

#### 语法
```bash
ls
```

#### 说明
在展板中列出所有窗口（等同于 `get_windows`）

#### 示例
```bash
/生态/第一章> ls

窗口列表 (共 5 个):
============================================================

 1. 今日笔记 [text]
    ID: window_1762160636035
    创建: 2024-11-03T17:30:00

 2. 概念总结 [text]
    ID: window_1762161234567
    创建: 2024-11-03T16:45:00

...
```

---

## 🔄 完整工作流示例

### 场景：创建和编辑笔记

```bash
# 1. 进入展板
C:\WHATNOTE> cd "生态/第一章"

# 2. 创建笔记
/生态/第一章> create "学习笔记" "# 第一章\n\n## 概述\n待补充"

成功创建窗口
============================================================

窗口ID: window_1762160636035
标题: 学习笔记

提示: 使用 'read window_1762160636035' 查看内容

# 3. 列出窗口
/生态/第一章> ls

窗口列表 (共 1 个):
============================================================

 1. 学习笔记 [text]
    ID: window_1762160636035
    创建: 2024-11-03T17:30:00

# 4. 读取内容
/生态/第一章> read window_1762160636035

窗口内容
============================================================

窗口ID: window_1762160636035
标题: 学习笔记
类型: text
内容长度: 28 字符

内容:
------------------------------------------------------------
# 第一章

## 概述
待补充

# 5. 替换"待补充"
/生态/第一章> edit window_1762160636035 "这是补充的内容..." replace "待补充"

成功编辑窗口
============================================================

窗口ID: window_1762160636035
操作: replace

提示: 使用 'read window_1762160636035' 查看结果

# 6. 追加新章节
/生态/第一章> edit window_1762160636035 "\n\n## 详细内容\n\n这是详细的内容..."

成功编辑窗口
============================================================

窗口ID: window_1762160636035
操作: append

# 7. 最后读取确认
/生态/第一章> read window_1762160636035

窗口内容
============================================================
...
# 第一章

## 概述
这是补充的内容...

## 详细内容

这是详细的内容...
```

---

## 💡 快捷技巧

### 1. 使用别名
```bash
# 这些都是等价的
create "标题" "内容"
new "标题" "内容"

read window_xxx
cat window_xxx

delete window_xxx
rm window_xxx

search "关键词"
find "关键词"
```

### 2. 窗口ID 复制粘贴

在 `ls` 输出中可以直接复制窗口ID：
```bash
/生态/第一章> ls
 1. 笔记 [text]
    ID: window_1762160636035  # 复制这个ID

/生态/第一章> read window_1762160636035  # 粘贴使用
```

### 3. 多行内容用 `\n`
```bash
create "标题" "第一行\n第二行\n第三行"
```

等价于：
```
第一行
第二行
第三行
```

### 4. 快速追加内容
```bash
# 默认就是追加，不用写操作类型
edit window_xxx "\n\n补充内容"
```

---

## ⚙️ 新旧命令对照

| 操作 | 旧命令（API风格） | 新命令（简化） |
|------|------------------|---------------|
| 创建窗口 | `create_window board_id="xxx" title="标题" content="内容"` | `create "标题" "内容"` |
| 列出窗口 | `get_windows board_id="xxx"` | `ls` |
| 读取内容 | `read_window board_id="xxx" window_id="xxx"` | `read window_xxx` |
| 追加内容 | `update_window board_id="xxx" window_id="xxx" content="..." mode="append"` | `edit window_xxx "..."` |
| 替换文本 | `edit_window board_id="xxx" window_id="xxx" operation="replace_text" target="旧" content="新"` | `edit window_xxx "新" replace "旧"` |
| 删除窗口 | `delete_window board_id="xxx" window_id="xxx"` | `delete window_xxx` |
| 搜索窗口 | `search_windows board_id="xxx" query="关键词"` | `search "关键词"` |

---

## 🔍 两种格式的共存

- ✅ **新命令（简化格式）**：更直观，输入更快
- ✅ **旧命令（API格式）**：仍然支持，功能更完整

你可以根据需要选择使用：

### 简单操作 → 用新格式
```bash
create "标题" "内容"
read window_xxx
edit window_xxx "新内容"
```

### 复杂操作 → 用旧格式
```bash
# 使用行号编辑
edit_window window_id="xxx" operation="delete_line" target="10-15"

# 指定窗口类型
create_window title="图片" window_type="image"

# 替换所有匹配
edit_window window_id="xxx" operation="replace_text" target="旧" content="新" all=true
```

---

## 📚 命令速查

### 基础命令
- `cd` - 切换目录
- `ls` - 列出内容
- `pwd` - 显示当前路径
- `help` - 帮助

### 窗口操作（简化）
- `create "标题" "内容"` - 创建
- `read <ID>` - 读取
- `edit <ID> "内容"` - 编辑
- `delete <ID>` - 删除
- `search "词"` - 搜索

### 别名
- `new` = `create`
- `cat` = `read`
- `rm` = `delete`
- `find` = `search`

---

## 🎉 优势总结

### ✅ 更少的输入
```bash
# 旧: 73 个字符
create_window board_id="board-xxx" window_id="window_xxx" title="标题"

# 新: 16 个字符
create "标题"
```

### ✅ 更符合直觉
```bash
read window_xxx     # 像 cat file.txt
delete window_xxx   # 像 rm file.txt
search "关键词"     # 像 grep "pattern"
```

### ✅ 自动上下文
进入展板后，`board_id` 自动使用当前展板，无需手动指定！

### ✅ 向后兼容
旧的 API 格式命令仍然有效，不影响现有使用习惯。

---

**最后更新**: 2025-11-03  
**版本**: 2.0

