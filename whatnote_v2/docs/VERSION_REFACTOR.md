# 🎯 版本管理系统重构

## 📝 问题背景

用户问题：
> "我希望如果用户在其中几页选择了LLM提取，那发给AI助手时候也应该是带着LLM提取版本的，现在能做到这样吗？"

**之前的问题**：
- ❌ AI助手发送PDF需要 `board_id` 和 `window_id`
- ❌ 前端文件信息没有这两个ID
- ❌ 版本配置存储在 `pages/document/page_versions.json`
- ❌ 必须通过展板和窗口才能找到配置

**核心疑问**：
> "为什么要有这两个ID，没有就不行吗？"

**答案**：**可以！不需要这两个ID！**

---

## ✨ 解决方案

### 新的存储结构

**之前**：
```
pages/
  └── document/
      ├── page_versions.json    ← 需要board_id+window_id才能找到
      ├── document_page_001.md
      └── document_page_001_llm.md
```

**现在**：
```
files/
  └── pdfs/
      ├── document.pdf
      ├── document.pdf.versions.json    ← 🆕 直接在PDF旁边！
      └── pages/
          └── document/
              ├── document_page_001.md
              └── document_page_001_llm.md
```

### 配置文件格式

```json
{
  "default_version": "pdf",
  "page_versions": {
    "1": "llm",
    "2": "llm",
    "3": "pdf",
    "5": "llm"
  }
}
```

---

## 🔧 核心改进

### 1. 新增方法：基于PDF路径

```python
# content_manager.py

def get_page_version_from_pdf(self, pdf_path: str, page: int) -> str:
    """
    从PDF文件路径直接获取页面版本
    不需要 board_id 和 window_id
    """
    pdf_file = Path(pdf_path)
    version_file = pdf_file.parent / f"{pdf_file.name}.versions.json"
    
    if version_file.exists():
        config = json.load(open(version_file))
        return config.get('page_versions', {}).get(str(page), 'pdf')
    
    return 'pdf'

def save_page_version_for_pdf(self, pdf_path: str, page: int, version: str) -> bool:
    """
    为PDF文件保存页面版本
    不需要 board_id 和 window_id
    """
    pdf_file = Path(pdf_path)
    version_file = pdf_file.parent / f"{pdf_file.name}.versions.json"
    
    # 读取现有配置
    config = {'default_version': 'pdf', 'page_versions': {}}
    if version_file.exists():
        config = json.load(open(version_file))
    
    # 更新版本
    config['page_versions'][str(page)] = version
    
    # 保存
    json.dump(config, open(version_file, 'w'), ensure_ascii=False, indent=2)
    return True
```

### 2. 修改现有方法：兼容新旧

```python
def get_page_version(self, board_id: str, window_id: str, page: int) -> str:
    """兼容新旧两种方式"""
    # 1. 先尝试新方法
    windows = self.get_board_windows(board_id)
    for window in windows:
        if window.get('id') == window_id:
            pdf_path = window.get('content', '')
            if pdf_path:
                pdf_file = Path(pdf_path)
                new_version_file = pdf_file.parent / f"{pdf_file.name}.versions.json"
                
                # 如果新配置存在，使用新方法
                if new_version_file.exists():
                    return self.get_page_version_from_pdf(pdf_path, page)
            break
    
    # 2. 回退到旧方法
    old_config_path = self.get_page_version_config_path(board_id, window_id)
    if old_config_path and old_config_path.exists():
        config = json.load(open(old_config_path))
        return config.get('page_versions', {}).get(str(page), 'pdf')
    
    return 'pdf'
```

### 3. AI助手改进

```python
# llm_service.py

elif file_info.get('type') == 'pdfs':
    # 不再需要 board_id 和 window_id！
    pdf_path = file_info['path']
    
    for page_num in range(1, total_pages + 1):
        # 直接从PDF路径获取版本
        version = self.content_manager.get_page_version_from_pdf(pdf_path, page_num)
        
        # 根据版本读取文件
        if version == 'llm':
            file = f"{pdf_name}_page_{page_num:03d}_llm.md"
        else:
            file = f"{pdf_name}_page_{page_num:03d}.md"
```

---

## 📊 工作流程

### 用户提取页面

```
用户打开PDF窗口 →
  提取第1页（LLM）→
    保存内容：document_page_001_llm.md
    保存配置：document.pdf.versions.json
      {"page_versions": {"1": "llm"}}
  
  提取第2页（LLM）→
    保存内容：document_page_002_llm.md
    更新配置：document.pdf.versions.json
      {"page_versions": {"1": "llm", "2": "llm"}}
  
  第3页保持PyPDF（未提取）
```

### AI助手发送PDF

```
用户在AI助手选择PDF →
  前端：发送文件路径
  后端：llm_service.py
    ├─ 读取配置：document.pdf.versions.json
    ├─ 第1页：version='llm' → 读取 document_page_001_llm.md ✅
    ├─ 第2页：version='llm' → 读取 document_page_002_llm.md ✅
    └─ 第3页：version='pdf' → 读取 document_page_003.md (PyPDF)
  
  发送给LLM：
    --- 第 1 页 ---
    [LLM提取的内容，包含图片描述] ✅
    
    --- 第 2 页 ---
    [LLM提取的内容，包含图片描述] ✅
    
    --- 第 3 页 ---
    [PyPDF提取的纯文本]
```

---

## 🔍 日志输出

### AI助手发送PDF

```
📄 [AI助手] 处理PDF文件: document.pdf
📖 [AI助手] 使用版本管理系统读取PDF内容（基于路径）
📄 [文件读取] 第1页 (LLM) → document_page_001_llm.md
📄 [文件读取] 第2页 (LLM) → document_page_002_llm.md
📄 [文件读取] 第3页 (PDF) → document_page_003.md
✅ [AI助手] 版本管理读取成功: 1:LLM, 2:LLM, 3:PDF
✅ [AI助手] PDF内容发送成功，总页数: 3, 文本长度: 5432 字符
```

### 注释生成

```
📄 [文件读取] 第1页 (LLM) → document_page_001_llm.md
📄 [文件读取] 第2页 (LLM) → document_page_002_llm.md
📄 [文件读取] 第3页 (PDF) → document_page_003.md
```

### 版本保存

```
💾 [版本配置] document.pdf 第1页 → LLM
💾 [版本配置] document.pdf 第2页 → LLM
```

---

## 🔄 迁移工具

### API端点

```
POST /api/boards/{board_id}/migrate-version-configs
```

### 迁移逻辑

```python
def migrate_version_configs_to_new_location(self, board_id: str):
    """
    自动迁移旧配置到新位置
    旧：pages/document/page_versions.json
    新：files/pdfs/document.pdf.versions.json
    """
    for window in windows:
        if window.type == 'pdf':
            # 查找旧配置
            old_config = find_old_config()
            if old_config:
                # 复制到新位置
                save_to_new_location(old_config)
```

### 使用方法

```bash
# 在浏览器控制台执行
fetch('http://localhost:8081/api/boards/board-xxx/migrate-version-configs', {
  method: 'POST'
})
.then(r => r.json())
.then(data => console.log(data))
```

**输出**：
```json
{
  "message": "版本配置迁移完成",
  "result": {
    "board_id": "board-xxx",
    "migrated": 2,
    "skipped": 0,
    "total": 2
  }
}
```

**日志**：
```
🔄 开始迁移版本配置: board-xxx
  ✅ 迁移 document.pdf（2 个页面配置）
  ✅ 迁移 presentation.pdf（5 个页面配置）
✅ 迁移完成: 2 个PDF，跳过 0 个
```

---

## ✅ 优势对比

### 之前的方式

```python
# 需要4个参数！
version = content_manager.get_page_version(
    board_id='board-xxx',
    window_id='window-xxx',
    page=1
)
```

**问题**：
- ❌ AI助手没有 `board_id` 和 `window_id`
- ❌ 需要遍历所有窗口才能找到PDF
- ❌ 如果没有窗口，无法使用版本管理

### 现在的方式

```python
# 只需要2个参数！
version = content_manager.get_page_version_from_pdf(
    pdf_path='/path/to/document.pdf',
    page=1
)
```

**优势**：
- ✅ AI助手直接支持（有文件路径）
- ✅ 不需要查找窗口
- ✅ 即使没有窗口也能用
- ✅ 更简单、更直观

---

## 🎯 实际效果

### 测试场景

1. **打开PDF窗口**
   - 提取第1、2页（使用LLM多模态）
   - 第3页保持PyPDF

2. **切换到AI助手**
   - 选择该PDF文件
   - 发送给AI

3. **查看日志**
```
📄 [AI助手] 处理PDF文件: Presentation-Report-guidelines-2026.pdf
📖 [AI助手] 使用版本管理系统读取PDF内容（基于路径）
📄 [文件读取] 第1页 (LLM) → Presentation-Report-guidelines-2026_page_001_llm.md
📄 [文件读取] 第2页 (LLM) → Presentation-Report-guidelines-2026_page_002_llm.md
📄 [文件读取] 第3页 (PDF) → Presentation-Report-guidelines-2026_page_003.md
✅ [AI助手] 版本管理读取成功: 1:LLM, 2:LLM, 3:PDF
```

4. **AI回复**
   - ✅ 第1、2页包含图片描述（LLM提取）
   - ✅ 第3页只有纯文本（PyPDF）

---

## 📚 相关文件

- `backend/storage/content_manager.py` - 核心版本管理逻辑
- `backend/llm_service.py` - AI助手PDF处理
- `backend/main.py` - 迁移API端点
- `docs/VERSION_REFACTOR.md` - 本文档
- `docs/AI_ASSISTANT_PDF_VERSION.md` - 之前的实现

---

## 🎉 总结

### 核心改进

1. **不再需要 `board_id` 和 `window_id`**
   - 直接从PDF路径读取版本配置

2. **配置文件直接在PDF旁边**
   - `document.pdf` → `document.pdf.versions.json`

3. **AI助手自动支持版本管理**
   - 有文件路径就能读取版本
   - 自动使用LLM提取的内容

4. **向后兼容**
   - 自动检测新旧配置
   - 无缝回退到旧方法

### 用户体验

**之前**：
- AI助手发送PDF → 只能用PyPDF → 丢失图片描述

**现在**：
- AI助手发送PDF → 自动使用版本管理 → 保留LLM提取的图片描述 ✅

### 技术优势

- ✅ 简化API（减少2个参数）
- ✅ 更直观（配置和文件在一起）
- ✅ 更灵活（不依赖窗口）
- ✅ 更可靠（向后兼容）

现在真正做到了"用户提取了LLM版本，AI助手就用LLM版本"！🎉

