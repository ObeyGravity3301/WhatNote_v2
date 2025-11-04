# 控制台快速入门

## ❗ 重要提示

### 命令语法说明
在帮助文档中，你会看到这样的格式：

```
help TOOL_NAME      - 显示工具详细说明
use BOARD_ID        - 切换当前展板
```

**大写字母（如 TOOL_NAME、BOARD_ID）表示需要替换的内容，不是实际命令的一部分！**

---

## ✅ 正确示例

### 查看工具帮助
❌ **错误**: `help <get_windows>` (带尖括号)  
❌ **错误**: `help TOOL_NAME` (直接输入大写)  
✅ **正确**: `help get_windows` (实际工具名)

### 切换展板
❌ **错误**: `use <board-123>` (带尖括号)  
❌ **错误**: `use BOARD_ID` (直接输入大写)  
✅ **正确**: `use board-1756987954946` (实际展板 ID)

### 调用工具
❌ **错误**: `TOOL_NAME param1="value1"` (大写的工具名)  
✅ **正确**: `get_windows board_id="board-123"` (实际工具名和参数)

---

## 📚 常用命令速查

### 1. 基础命令
```bash
help                    # 显示帮助
tools                   # 列出所有工具
history                 # 查看历史命令
clear                   # 清屏
exit                    # 退出
```

### 2. 查看工具详情
```bash
help get_windows        # 查看 get_windows 工具说明
help create_window      # 查看 create_window 工具说明
help search_windows     # 查看 search_windows 工具说明
```

### 3. 设置当前展板
```bash
use board-1756987954946 # 设置后，后续命令自动填充 board_id
```

---

## 🚀 实战示例

### 示例 1: 获取窗口列表
```bash
# 方法1: 直接指定 board_id
get_windows board_id="board-1756987954946"

# 方法2: 先设置当前展板
use board-1756987954946
get_windows
```

### 示例 2: 创建新窗口
```bash
create_window board_id="board-1756987954946" title="我的笔记"

# 或设置展板后
use board-1756987954946
create_window title="我的笔记" content="# 第一个笔记"
```

### 示例 3: 搜索窗口
```bash
search_windows board_id="board-1756987954946" query="笔记" limit=5
```

### 示例 4: 读取窗口内容
```bash
# 先获取窗口 ID
get_windows board_id="board-1756987954946"

# 然后读取（假设窗口 ID 是 window_1234567890）
read_window board_id="board-1756987954946" window_id="window_1234567890"
```

### 示例 5: 更新窗口（追加内容）
```bash
update_window board_id="board-1756987954946" window_id="window_1234567890" content="新增内容" mode="append"
```

### 示例 6: 删除窗口
```bash
# 移到回收站
delete_window board_id="board-1756987954946" window_id="window_1234567890"

# 永久删除
delete_window board_id="board-1756987954946" window_id="window_1234567890" permanent=true
```

---

## 💡 使用技巧

### 1. 方向键浏览历史
- **↑** 上一条命令
- **↓** 下一条命令

### 2. 使用 use 简化输入
设置当前展板后，不需要每次都输入 `board_id`:
```bash
use board-1756987954946
get_windows              # 自动使用当前展板
create_window title="新窗口"
search_windows query="测试"
```

### 3. 复制输出
选中控制台中的文本即可复制

### 4. 参数类型
- **字符串**: 用引号包裹 `title="我的窗口"`
- **数字**: 直接写 `limit=10`
- **布尔**: 写 `true` 或 `false` (`permanent=true`)

---

## 📋 完整工作流示例

```bash
# 1. 查看帮助
help

# 2. 查看所有工具
tools

# 3. 设置当前展板
use board-1756987954946

# 4. 获取窗口列表
get_windows

# 5. 创建新窗口
create_window title="测试笔记" content="# 测试内容"

# 6. 搜索窗口
search_windows query="测试"

# 7. 读取窗口（假设 ID 是 window_1234567890）
read_window window_id="window_1234567890"

# 8. 更新内容
update_window window_id="window_1234567890" content="追加内容" mode="append"

# 9. 查看历史
history

# 10. 清屏
clear
```

---

## ❓ 常见错误

### 错误 1: 带尖括号/大写
```bash
❌ help <get_windows>    # 错误！
❌ help TOOL_NAME        # 错误！
✅ help get_windows      # 正确！
```

### 错误 2: 缺少引号
```bash
❌ create_window title=我的窗口          # 错误！空格会断开
✅ create_window title="我的窗口"        # 正确！
```

### 错误 3: 参数名错误
```bash
❌ get_windows boardId="board-123"      # 错误！应该是 board_id
✅ get_windows board_id="board-123"     # 正确！
```

### 错误 4: 使用了不存在的工具
```bash
❌ list_windows board_id="board-123"    # 错误！工具不存在
✅ get_windows board_id="board-123"     # 正确！先用 tools 查看
```

---

## 🎓 学习路径

1. **第一步**: 输入 `help` 查看基础命令
2. **第二步**: 输入 `tools` 查看所有工具
3. **第三步**: 输入 `help get_windows` 学习第一个工具
4. **第四步**: 实际执行 `get_windows board_id="你的展板ID"`
5. **第五步**: 探索其他工具

---

## 🔍 如何找到展板 ID？

1. 在前端选择一个展板
2. 查看浏览器地址栏（可能会有）
3. 或者输入 `boards` 命令查看（功能待实现）
4. 临时方案：在前端控制台执行 `console.log(window.location)` 查看

---

## 📞 需要帮助？

- 随时输入 `help` 查看命令列表
- 输入 `help TOOL_NAME` 查看具体工具（记得替换 TOOL_NAME）
- 输入 `tools` 查看所有可用工具
- 查看 [完整文档](./CONSOLE_GUIDE.md)




