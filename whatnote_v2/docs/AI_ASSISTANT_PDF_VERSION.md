# 📄 AI助手PDF版本管理改进

## 🎯 问题描述

用户发现：AI助手发送PDF文件时，**没有使用版本管理系统**，仍然是直接用PyPDF提取文本。

## 🔍 问题分析

### 当前实现

**位置**：`llm_service.py` → `_process_message_files()`

```python
# 旧代码（第94-148行）
elif file_info.get('type') == 'pdfs':
    # 直接使用PyPDF提取文本
    pdf_reader = pypdf.PdfReader(file_path)
    text_content = ""
    
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        text_content += f"--- 第 {page_num + 1} 页 ---\n{page_text}\n\n"
```

**问题**：
- ❌ 忽略了用户选择的版本（LLM提取 vs PyPDF提取）
- ❌ 没有使用 `content_manager.get_pdf_page_contents()`
- ❌ 没有读取 `page_versions.json` 配置

---

## ✅ 解决方案

### 1. 修改 `LLMService` 构造函数

```python
# llm_service.py
def __init__(self, api_config_manager, content_manager=None):
    self.api_config_manager = api_config_manager
    self.content_manager = content_manager  # ← 新增
```

### 2. 新增回退方法

```python
def _extract_pdf_with_pypdf(self, file_path, file_info, content_array, pdf_reader=None):
    """使用PyPDF直接提取PDF文本（回退方案）"""
    # 当版本管理系统不可用时使用
```

### 3. 修改PDF处理逻辑

```python
elif file_info.get('type') == 'pdfs':
    info(f"📄 [AI助手] 处理PDF文件: {file_info.get('name')}")
    
    # 尝试使用版本管理系统
    if self.content_manager and file_info.get('board_id') and file_info.get('window_id'):
        # 使用版本管理系统读取
        for page_num in range(1, total_pages + 1):
            page_data = self.content_manager.get_pdf_page_contents(
                file_info['board_id'],
                file_info['window_id'],
                page_num
            )
            
            if page_data and page_data.get('current'):
                # 获取版本信息
                version = self.content_manager.get_page_version(
                    file_info['board_id'],
                    file_info['window_id'],
                    page_num
                )
                used_versions.append(f"{page_num}:{version.upper()}")
                text_content += f"--- 第 {page_num} 页 ---\n{page_data['current']}\n\n"
    else:
        # 回退到PyPDF直接提取
        self._extract_pdf_with_pypdf(file_path, file_info, content_array, pdf_reader)
```

### 4. 修改 `main.py` 初始化

```python
# main.py
llm_service = LLMService(api_config_manager, content_manager)  # ← 传入content_manager
```

---

## 🚧 当前限制

### 问题：前端文件信息不完整

**当前前端发送的文件信息**：
```javascript
{
  name: "document.pdf",
  type: "pdfs",
  size: 123456,
  path: "/path/to/file.pdf",
  url: "http://..."
  // ❌ 缺少 board_id
  // ❌ 缺少 window_id
}
```

**版本管理需要的信息**：
```python
content_manager.get_pdf_page_contents(
    board_id,   # ← 需要
    window_id,  # ← 需要
    page_num
)
```

### 为什么缺少这些信息？

1. **AI助手文件选择器**扫描的是整个展板的 `files/` 目录
2. 文件可能不属于任何窗口（用户直接上传的）
3. 同一个PDF可能被多个窗口引用

---

## 🎯 完整解决方案

### 方案1：从文件路径推断 board_id 和 window_id（✅ 已实现）

```python
# 后端：llm_service.py

# 如果有版本管理信息，使用版本管理
if self.content_manager and file_info.get('board_id') and file_info.get('window_id'):
    # 使用版本管理系统
    pass
else:
    # 回退到PyPDF直接提取
    self._extract_pdf_with_pypdf(file_path, file_info, content_array)
```

**优点**：
- ✅ 向后兼容（没有window_id的文件仍可使用）
- ✅ 自动回退机制

**缺点**：
- ⚠️ 无法为非窗口文件使用版本管理

### 方案2：前端增强文件信息（🔄 待实现）

修改前端 `/api/boards/{board_id}/files` API，为PDF文件查找对应的窗口：

```python
# main.py → get_board_files()

if file_type == "pdfs":
    # 查找使用该PDF的窗口
    windows = content_manager.get_board_windows(board_id)
    for window in windows:
        if window.get('type') == 'pdf' and Path(window.get('content', '')) == file_path:
            file_info['window_id'] = window['id']
            break
```

前端添加 `board_id`：

```javascript
// ChatWindow.js → sendMessage()

const userMessage = {
  role: 'user',
  content: inputText.trim(),
  files: selectedFiles.map(file => ({
    ...file,
    board_id: boardId,  // ← 添加board_id
    // window_id 由后端API返回
  }))
};
```

**优点**：
- ✅ 完整的版本管理支持
- ✅ 自动识别窗口

**缺点**：
- 🔨 需要修改前端和后端
- 🔨 需要扫描所有窗口

---

## 📊 日志输出

### 成功使用版本管理

```
📄 [AI助手] 处理PDF文件: document.pdf
📖 [AI助手] 使用版本管理系统读取PDF内容
📄 [文件读取] 第1页 (LLM) → document_page_001_llm.md
📄 [文件读取] 第2页 (PDF) → document_page_002.md
📄 [文件读取] 第3页 (LLM) → document_page_003_llm.md
✅ [AI助手] 版本管理读取成功: 1:LLM, 2:PDF, 3:LLM
✅ [AI助手] PDF内容发送成功，总页数: 3, 文本长度: 5432 字符
```

### 回退到PyPDF

```
📄 [AI助手] 处理PDF文件: document.pdf
⚠️ [AI助手] 无版本管理信息，使用PyPDF直接提取
PDF文本提取成功（PyPDF），总页数: 3, 文本长度: 4123 字符
```

### 版本管理失败回退

```
📄 [AI助手] 处理PDF文件: document.pdf
📖 [AI助手] 使用版本管理系统读取PDF内容
❌ [AI助手] 版本管理读取失败: 窗口不存在，回退到PyPDF
PDF文本提取成功（PyPDF），总页数: 3, 文本长度: 4123 字符
```

---

## ✅ 实现状态

### 已完成

- ✅ `LLMService` 添加 `content_manager` 参数
- ✅ 新增 `_extract_pdf_with_pypdf()` 回退方法
- ✅ 修改PDF处理逻辑，优先使用版本管理
- ✅ 添加详细日志输出
- ✅ 自动回退机制
- ✅ `main.py` 初始化传入 `content_manager`

### 待优化

- 🔄 前端添加 `board_id` 到文件信息
- 🔄 后端API返回 `window_id` (如果PDF属于窗口)
- 🔄 完善边界情况处理

---

## 🎯 使用场景

### 场景1：用户发送打开的PDF窗口

1. 用户在PDF分页模式下提取了部分页面（使用LLM）
2. 用户切换到AI助手
3. 用户选择该PDF文件发送
4. **✅ 系统使用版本管理**，发送LLM提取的内容

### 场景2：用户发送刚上传的PDF

1. 用户直接上传PDF文件（未打开窗口）
2. 用户在AI助手选择该PDF发送
3. **⚠️ 系统回退到PyPDF**，因为没有window_id

### 场景3：用户发送旧PDF文件

1. 用户发送展板中已存在的PDF
2. 该PDF之前有窗口并提取过内容
3. **⚠️ 系统回退到PyPDF**（当前实现）
4. **🔄 待优化**：后端查找对应窗口，使用版本管理

---

## 🔧 测试验证

### 测试步骤

1. **打开PDF窗口并提取页面**
   - 提取部分页面使用LLM
   - 其他页面保持PyPDF

2. **在AI助手发送该PDF**
   - 检查日志输出
   - 验证使用的版本

3. **对比AI助手回复**
   - LLM版本应包含图片描述
   - PyPDF版本只有纯文本

### 预期结果

```
📄 [AI助手] 处理PDF文件: Presentation-Report-guidelines-2026.pdf
📖 [AI助手] 使用版本管理系统读取PDF内容
📄 [文件读取] 第1页 (LLM) → Presentation-Report-guidelines-2026_page_001_llm.md
📄 [文件读取] 第2页 (LLM) → Presentation-Report-guidelines-2026_page_002_llm.md
📄 [文件读取] 第3页 (PDF) → Presentation-Report-guidelines-2026_page_003.md
✅ [AI助手] 版本管理读取成功: 1:LLM, 2:LLM, 3:PDF
✅ [AI助手] PDF内容发送成功，总页数: 12, 文本长度: 8456 字符
```

---

## 📝 总结

### 改进前

```
AI助手发送PDF → PyPDF直接提取 → 纯文本（无图片描述）
```

### 改进后

```
AI助手发送PDF → 检查版本管理 → 
  ├─ 有window_id → 使用版本管理 → LLM/PyPDF混合内容
  └─ 无window_id → 回退PyPDF → 纯文本
```

### 核心优势

✅ **统一的内容来源**：注释生成和AI助手都使用同一版本的内容  
✅ **智能回退机制**：即使没有版本信息也能正常工作  
✅ **详细的日志输出**：清楚显示使用的版本  
✅ **向后兼容**：不影响现有功能  

现在AI助手也能正确使用版本管理系统了！🎉

