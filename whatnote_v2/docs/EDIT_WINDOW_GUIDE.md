# edit_window 工具使用指南

## 🎯 概述

`edit_window` 是一个强大的精细编辑工具，允许您对窗口内容进行精确的插入、替换和删除操作，无需替换整个文件内容。

---

## 📋 操作类型

### 文本操作
1. **insert** - 在指定文本位置插入新内容
2. **replace_text** - 替换指定的文本片段
3. **delete_text** - 删除指定的文本片段

### 行操作
4. **insert_line** - 在指定行号插入新行
5. **replace_line** - 替换指定行的内容
6. **delete_line** - 删除指定行

---

## 🔧 参数说明

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `board_id` | string | 是* | 展板ID（在展板目录中会自动填充） |
| `window_id` | string | 是 | 窗口ID |
| `operation` | string | 是 | 操作类型（见上方列表） |
| `target` | string | 条件必需 | 操作目标（文本或行号） |
| `content` | string | 条件必需 | 新内容（用于插入/替换操作） |
| `position` | string | 否 | 插入位置：`before`/`after`/`at`（默认 `after`） |
| `all` | boolean | 否 | 是否替换/删除所有匹配（默认 `false`） |

\* 在展板目录中时，`board_id` 会自动填充

---

## 📝 文本操作详解

### 1. insert - 插入文本

在指定文本的前/后插入新内容。

#### 语法
```bash
edit_window window_id="窗口ID" operation="insert" target="查找文本" content="新内容" position="before|after|at"
```

#### 参数
- `target`: 要查找的文本（作为插入位置的标记）
- `content`: 要插入的新内容
- `position`: 插入位置
  - `before`: 在目标文本**之前**插入
  - `after`: 在目标文本**之后**插入（默认）
  - `at`: **替换**目标文本

#### 示例 1：在标题后插入内容
```bash
# 原内容：
# ## 概述
# 这是概述部分

/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="## 概述" content="\n\n这是新增的内容" position="after"
```

**结果：**
```markdown
## 概述

这是新增的内容
这是概述部分
```

#### 示例 2：在标题前插入内容
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="## 第二章" content="## 第一章\n\n第一章的内容\n\n" position="before"
```

**结果：**
```markdown
## 第一章

第一章的内容

## 第二章
...
```

#### 示例 3：替换特定文本（使用 at）
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="TODO" content="已完成" position="at"
```

**结果：** `TODO` → `已完成`

---

### 2. replace_text - 替换文本

查找并替换指定的文本片段。

#### 语法
```bash
edit_window window_id="窗口ID" operation="replace_text" target="旧文本" content="新文本" all=true|false
```

#### 参数
- `target`: 要查找的旧文本
- `content`: 替换成的新文本
- `all`: 是否替换所有匹配项
  - `false`: 只替换第一个匹配（默认）
  - `true`: 替换所有匹配

#### 示例 1：替换第一个匹配
```bash
# 原内容：旧名称出现了3次
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="旧名称" content="新名称"
```

**结果：** 只有第一个"旧名称"被替换为"新名称"

#### 示例 2：替换所有匹配
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="旧名称" content="新名称" all=true
```

**结果：** 所有"旧名称"都被替换为"新名称"

#### 示例 3：替换 Markdown 语法
```bash
# 将所有 ## 二级标题改为 ### 三级标题
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="## " content="### " all=true
```

#### 示例 4：更新链接
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="http://old-domain.com" content="https://new-domain.com" all=true
```

---

### 3. delete_text - 删除文本

删除指定的文本片段。

#### 语法
```bash
edit_window window_id="窗口ID" operation="delete_text" target="要删除的文本" all=true|false
```

#### 参数
- `target`: 要删除的文本
- `all`: 是否删除所有匹配项
  - `false`: 只删除第一个匹配（默认）
  - `true`: 删除所有匹配

#### 示例 1：删除特定标记
```bash
# 删除 TODO 标记
/生态/第一章> edit_window window_id="window_xxx" operation="delete_text" target="[TODO] "
```

#### 示例 2：删除所有特定文本
```bash
# 删除所有草稿标记
/生态/第一章> edit_window window_id="window_xxx" operation="delete_text" target="（草稿）" all=true
```

#### 示例 3：删除代码块
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="delete_text" target="```python\nold_code()\n```"
```

---

## 📏 行操作详解

### 行号说明
- 行号从 **1** 开始（不是 0）
- 支持单行：`"5"`
- 支持范围：`"5-10"`

### 4. insert_line - 插入新行

在指定行号位置插入新行。

#### 语法
```bash
edit_window window_id="窗口ID" operation="insert_line" target="行号" content="新行内容" position="before|after|at"
```

#### 参数
- `target`: 行号（如 `"5"`）
- `content`: 新行的内容
- `position`:
  - `before`: 在指定行**之前**插入新行
  - `after`: 在指定行**之后**插入新行（默认）
  - `at`: **替换**指定行

#### 示例 1：在第3行之后插入
```bash
# 原内容：
# 1. 第一行
# 2. 第二行
# 3. 第三行
# 4. 第四行

/生态/第一章> edit_window window_id="window_xxx" operation="insert_line" target="3" content="这是新插入的一行" position="after"
```

**结果：**
```
1. 第一行
2. 第二行
3. 第三行
这是新插入的一行
4. 第四行
```

#### 示例 2：在第1行之前插入（添加文件头）
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="insert_line" target="1" content="# 文档标题" position="before"
```

---

### 5. replace_line - 替换行内容

替换指定行或行范围的内容。

#### 语法
```bash
# 替换单行
edit_window window_id="窗口ID" operation="replace_line" target="行号" content="新内容"

# 替换多行
edit_window window_id="窗口ID" operation="replace_line" target="起始行-结束行" content="新内容"
```

#### 示例 1：替换第5行
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="replace_line" target="5" content="这是第5行的新内容"
```

#### 示例 2：替换第3-7行
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="replace_line" target="3-7" content="这段内容将替换原来的第3到第7行"
```

**注意：** 多行替换时，所有指定的行会被替换为一行新内容。

---

### 6. delete_line - 删除行

删除指定行或行范围。

#### 语法
```bash
# 删除单行
edit_window window_id="窗口ID" operation="delete_line" target="行号"

# 删除多行
edit_window window_id="窗口ID" operation="delete_line" target="起始行-结束行"
```

#### 示例 1：删除第10行
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="delete_line" target="10"
```

#### 示例 2：删除第5-8行
```bash
/生态/第一章> edit_window window_id="window_xxx" operation="delete_line" target="5-8"
```

#### 示例 3：删除最后一行
```bash
# 假设文件有 20 行
/生态/第一章> edit_window window_id="window_xxx" operation="delete_line" target="20"
```

---

## 🎯 实用场景

### 场景 1：添加新章节

```bash
# 1. 先查看当前内容，找到合适的插入位置
/生态/第一章> read_window window_id="window_xxx"

# 2. 在"## 第二章"之前插入新章节
/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="## 第二章" content="## 第一章\n\n这是第一章的内容。\n\n" position="before"

# 3. 验证结果
/生态/第一章> read_window window_id="window_xxx"
```

### 场景 2：批量更新术语

```bash
# 将所有"生态系统"替换为"生态系统（Ecosystem）"
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="生态系统" content="生态系统（Ecosystem）" all=true
```

### 场景 3：删除草稿内容

```bash
# 删除所有标记为草稿的段落
/生态/第一章> edit_window window_id="window_xxx" operation="delete_text" target="[草稿]\n" all=true
```

### 场景 4：修复列表格式

```bash
# 原内容使用了 * 作为列表标记，改为 -
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="* " content="- " all=true
```

### 场景 5：插入引用

```bash
# 在特定段落后插入引用
/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="这是关键论点。" content="\n\n> **参考文献**: Smith, J. (2024). *生态学原理*. 科学出版社." position="after"
```

### 场景 6：按行编辑代码块

```bash
# 假设代码在第 15-20 行，删除第 18 行的注释
/生态/第一章> edit_window window_id="window_xxx" operation="delete_line" target="18"

# 在第 16 行后插入新的代码行
/生态/第一章> edit_window window_id="window_xxx" operation="insert_line" target="16" content="    print('新增的代码')" position="after"
```

---

## 💡 最佳实践

### 1. 使用前先读取
```bash
# 先查看内容，确定编辑目标
/生态/第一章> read_window window_id="window_xxx"

# 再进行编辑
/生态/第一章> edit_window window_id="window_xxx" operation="..." ...

# 编辑后再次查看确认
/生态/第一章> read_window window_id="window_xxx"
```

### 2. 精确匹配目标文本

❌ **不好的做法**（目标文本太短，可能匹配错误位置）:
```bash
edit_window ... operation="replace_text" target="系统" content="...
```

✅ **好的做法**（使用更长的唯一文本）:
```bash
edit_window ... operation="replace_text" target="生态系统的基本概念" content="..."
```

### 3. 谨慎使用 `all=true`

```bash
# 先查看会匹配多少处
/生态/第一章> read_window window_id="window_xxx"

# 确认后再使用 all=true
/生态/第一章> edit_window window_id="window_xxx" operation="replace_text" target="..." content="..." all=true
```

### 4. 利用转义字符

```bash
# 插入多行内容
/生态/第一章> edit_window window_id="window_xxx" operation="insert" target="## 概述" content="\n\n### 子章节\n\n详细内容...\n\n" position="after"
```

### 5. 行号操作时检查总行数

```bash
# 先读取内容，确认总行数
/生态/第一章> read_window window_id="window_xxx"
# （假设看到有 50 行）

# 安全地操作最后几行
/生态/第一章> edit_window window_id="window_xxx" operation="delete_line" target="48-50"
```

---

## ⚠️ 注意事项

### 1. 文本不存在的错误

如果 `target` 文本不存在，会返回错误：
```
执行失败: 未找到目标文本: ...
```

**解决方法**：先使用 `read_window` 确认目标文本确实存在。

### 2. 行号超出范围

```
执行失败: 无效的行号: 100（总共 50 行）
```

**解决方法**：检查文件总行数，使用有效的行号。

### 3. 部分匹配问题

`target` 参数会精确匹配文本，包括空格、换行等：

❌ **会失败**:
```bash
# 目标文本实际是 "生态系统\n"（末尾有换行），但只查找 "生态系统"
edit_window ... target="生态系统" ...
```

✅ **正确**:
```bash
edit_window ... target="生态系统\n" ...
```

### 4. 特殊字符转义

记得使用转义字符：
- `\n` - 换行
- `\t` - 制表符
- `\"` - 引号
- `\\` - 反斜杠

---

## 🔄 与 update_window 的对比

| 特性 | update_window | edit_window |
|------|--------------|-------------|
| **操作粒度** | 整个文件 | 精确定位的部分 |
| **适用场景** | 重写整个文档 | 局部修改 |
| **是否需要读取全文** | 是（追加/前置模式） | 是（内部自动） |
| **错误风险** | 可能覆盖重要内容 | 仅影响目标部分 |
| **学习曲线** | 简单 | 中等 |

### 何时使用 `update_window`？
- 完全重写文档内容
- 简单的追加或前置操作
- 内容较短，容易管理

### 何时使用 `edit_window`？
- 精确修改文档的特定部分
- 批量替换/删除特定文本
- 按行号进行编辑
- 需要保留大部分原内容

---

## 📚 总结

`edit_window` 工具提供了 6 种强大的编辑操作：

**文本操作**（基于内容匹配）:
1. `insert` - 在指定文本附近插入
2. `replace_text` - 替换指定文本
3. `delete_text` - 删除指定文本

**行操作**（基于行号）:
4. `insert_line` - 插入新行
5. `replace_line` - 替换行内容
6. `delete_line` - 删除行

掌握这些操作，您就可以高效地进行精细化的内容编辑，而无需手动打开文件或重写整个文档！

---

**最后更新**: 2025-11-03  
**版本**: 1.0



