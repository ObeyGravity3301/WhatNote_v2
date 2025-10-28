# 📝 批量注释流程详细分析

## 🎯 入口：用户点击"批量生成所有注释"

**前端位置**：`BoardCanvas.js` 第 3068-3353 行

### 用户操作
```javascript
// 用户点击 "批量生成所有注释" 按钮
onClick={async () => {
  // 1. 数据检查
  if (!batchOutline || !batchSubdivisions) {
    return // 数据不完整，退出
  }
  
  // 2. 用户确认
  const confirmStart = window.confirm(`即将并行生成所有 ${batchOutline.outline.length} 个分段的注释`)
  if (!confirmStart) return
  
  // 3. 开始批量生成
  console.log('开始批量生成所有分段的注释')
}}
```

---

## 📊 阶段3：并行生成注释

### 前端并行策略

```javascript
// 为每个分段创建独立的生成任务
const generatePromises = batchOutline.outline.map(async (section, sectionIndex) => {
  // 每个分段并行执行
  const response = await fetch(
    `/api/boards/${boardId}/windows/${windowId}/annotations/batch/generate-section`,
    {
      method: 'POST',
      body: JSON.stringify({
        section_index: sectionIndex,      // 分段索引
        section_data: section,            // 分段数据
        subdivision_data: subdivision,    // 细分数据
        annotation_style: 'detailed',     // 注释风格
        promptTemplate: '...'             // 提示词模板
      })
    }
  )
})

// 并行等待所有分段完成
const results = await Promise.all(generatePromises)
```

**关键特点**：
- ✅ **并行执行**：所有分段同时发送请求
- ✅ **独立任务**：每个分段是独立的HTTP请求
- ✅ **流式响应**：使用SSE (Server-Sent Events) 实时反馈进度

---

## 🔄 后端API：generate_section_annotations

**API路径**：`POST /api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-section`

**后端位置**：`main.py` 第 2238 行开始

### 第1步：读取页面内容

```python
# 读取该分段所有页面的内容
pages_content = []
for page in range(page_start, page_end + 1):
    # 调用 get_pdf_page_contents（关键方法！）
    page_data = content_manager.get_pdf_page_contents(board_id, window_id, page)
    if page_data and page_data.get('current'):
        pages_content.append({
            'page': page,
            'content': page_data['current']  # ← 只取当前页内容
        })
```

**📄 [文件读取] 日志输出位置**：
```python
# content_manager.py 第 2254-2270 行
print(f"📄 [文件读取] 第{page-1}页 (LLM/PDF) → xxx_page_001_llm.md")
print(f"📄 [文件读取] 第{page}页 (LLM/PDF) → xxx_page_002.md")
print(f"📄 [文件读取] 第{page+1}页 (LLM/PDF) → xxx_page_003_llm.md")
```

### 📦 发送给LLM的PDF内容结构

```json
{
  "pages_content": [
    {
      "page": 1,
      "content": "# Presentation-Report-guidelines-2026 - 第 1 页\n来源: xxx.pdf\n页码: 1\n---\n\n[页面实际内容]"
    },
    {
      "page": 2,
      "content": "# Presentation-Report-guidelines-2026 - 第 2 页\n来源: xxx.pdf\n页码: 2\n---\n\n[页面实际内容]"
    },
    ...
  ]
}
```

**关键特点**：
- ✅ **只包含当前页**：不包括前一页和后一页
- ✅ **完整的Markdown内容**：包括标题、元数据和正文
- ✅ **根据版本配置读取**：LLM提取 or PyPDF提取

---

## 💾 上下文存储位置

### 1. 页面内容文件（磁盘存储）

```
pages/
  └── document/
      ├── document_page_001.md        ← PyPDF提取的内容
      ├── document_page_001_llm.md    ← LLM提取的内容
      ├── document_page_002.md
      ├── document_page_002_llm.md
      └── ...
```

**内容格式**：
```markdown
# Presentation-Report-guidelines-2026 - 第 1 页 (LLM提取)

来源: Presentation-Report-guidelines-2026.pdf
更新时间: 2025-01-15 10:30:45
页码: 1
提取方式: 多模态LLM

---

## 文本内容

[页面文字内容]

## 图片描述

[图片/图表描述]
```

### 2. 版本配置文件（磁盘存储）

```
pages/
  └── document/
      └── page_versions.json
```

**配置格式**：
```json
{
  "default_version": "pdf",
  "page_versions": {
    "1": "llm",    ← 第1页使用LLM版本
    "2": "llm",    ← 第2页使用LLM版本
    "3": "pdf",    ← 第3页使用PyPDF版本
    "5": "llm"
  }
}
```

### 3. 注释文件（磁盘存储）

```
files/
  └── document/
      └── annotations/
          ├── page_001.md    ← 第1页的注释
          ├── page_002.md    ← 第2页的注释
          └── ...
```

### 4. 前端内存缓存

```javascript
// 当前页的注释缓存
const [annotations, setAnnotations] = useState({
  1: "第1页的注释内容",
  2: "第2页的注释内容",
  ...
})

// 提取内容缓存
const [extractedContents, setExtractedContents] = useState({
  1: { text: "...", image: "...", full: "..." },
  2: { text: "...", image: "...", full: "..." },
  ...
})

// 版本配置缓存
const [pageVersions, setPageVersions] = useState({
  1: 'llm',
  2: 'llm',
  3: 'pdf',
  ...
})
```

---

## 🔍 版本选择逻辑（关键！）

### get_pdf_page_contents 方法

**位置**：`content_manager.py` 第 2189-2274 行

```python
def get_pdf_page_contents(self, board_id: str, window_id: str, page: int) -> dict:
    """
    获取PDF页面内容（前一页、当前页、下一页）
    用于LLM生成注释
    
    Returns:
        dict: {'previous': str, 'current': str, 'next': str}
    """
    
    def get_page_file_by_version(page_num: int) -> tuple[Optional[Path], str]:
        """根据版本配置获取对应的页面文件"""
        # 1. 读取版本配置
        version = self.get_page_version(board_id, window_id, page_num)
        
        if version == 'llm':
            # 2. 优先使用LLM提取的内容
            llm_file = pdf_pages_dir / f"{pdf_name}_page_{page_num:03d}_llm.md"
            if llm_file.exists():
                return llm_file, 'llm'
            else:
                # LLM文件不存在，回退到PyPDF
                print(f"⚠️ [版本回退] 第{page_num}页 → LLM文件不存在，回退到PyPDF")
        
        # 3. 使用PyPDF版本
        pdf_file = pdf_pages_dir / f"{pdf_name}_page_{page_num:03d}.md"
        if pdf_file.exists():
            return pdf_file, 'pdf'
        
        return None, ''
    
    # 读取前一页内容
    if page > 1:
        prev_page_file, prev_version = get_page_file_by_version(page - 1)
        if prev_page_file:
            print(f"📄 [文件读取] 第{page-1}页 ({prev_version.upper()}) → {prev_page_file.name}")
            with open(prev_page_file, 'r', encoding='utf-8') as f:
                result['previous'] = f.read()
    
    # 读取当前页内容（必须存在）
    current_page_file, current_version = get_page_file_by_version(page)
    if current_page_file:
        print(f"📄 [文件读取] 第{page}页 ({current_version.upper()}) → {current_page_file.name}")
        with open(current_page_file, 'r', encoding='utf-8') as f:
            result['current'] = f.read()
    
    # 读取下一页内容
    next_page_file, next_version = get_page_file_by_version(page + 1)
    if next_page_file:
        print(f"📄 [文件读取] 第{page+1}页 ({next_version.upper()}) → {next_page_file.name}")
        with open(next_page_file, 'r', encoding='utf-8') as f:
            result['next'] = f.read()
    
    return result
```

---

## 📊 并行处理详解

### 问题：是否真的并行？

**答案：✅ 是的！**

#### 前端层面：并行HTTP请求

```javascript
// Promise.all 并行等待所有请求
const results = await Promise.all([
  generateSection(0),  // ← 同时发送
  generateSection(1),  // ← 同时发送
  generateSection(2),  // ← 同时发送
  ...
])
```

#### 后端层面：FastAPI异步处理

```python
@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-section")
async def generate_section_annotations(board_id: str, window_id: str, request: Request):
    """
    FastAPI 使用 async/await
    每个请求在独立的协程中执行
    不会阻塞其他请求
    """
    async def event_generator():
        for page in range(page_start, page_end + 1):
            # 生成注释
            annotation = await llm_service.generate_annotation(...)
            yield f"data: {json.dumps({'type': 'page_done', 'page': page})}\n\n"
```

**实际执行效果**：
```
时间线：
  0s:  前端发送 5个分段 的请求 →→→→→→→→ 后端收到5个请求
  0s:  后端同时处理 5个分段（FastAPI异步）
  10s: 分段1 完成 → 返回
  12s: 分段2 完成 → 返回
  15s: 分段3 完成 → 返回
  18s: 分段4 完成 → 返回
  20s: 分段5 完成 → 返回
```

---

## 🔄 流式响应流程

### 单个分段的注释生成

```
前端                                    后端
  │                                      │
  ├─ POST generate-section ─────────→  │
  │                                      ├─ 读取页面内容
  │                                      │  📄 [文件读取] 第1页 (LLM) → xxx_page_001_llm.md
  │                                      │  📄 [文件读取] 第2页 (PDF) → xxx_page_002.md
  │                                      │  📄 [文件读取] 第3页 (LLM) → xxx_page_003_llm.md
  │                                      │
  │  ←──── data: {type: 'status'} ─────┤  开始生成第1页
  │  ←──── data: {type: 'content'} ────┤  LLM输出内容...
  │  ←──── data: {type: 'page_done'}──┤  第1页完成
  │                                      │
  │  ←──── data: {type: 'status'} ─────┤  开始生成第2页
  │  ←──── data: {type: 'content'} ────┤  LLM输出内容...
  │  ←──── data: {type: 'page_done'}──┤  第2页完成
  │                                      │
  │  ←──── data: {type: 'complete'} ───┤  分段完成
  │                                      │
  └─ 更新进度条 & 刷新注释               └─ 保存注释文件
```

---

## 📝 LLM提示词结构

### 批量注释的提示词

```python
prompt = f"""你是一位专业的PDF阅读助手，请为以下PDF分段生成详细的注释。

**PDF信息**:
- 文件名: {pdf_filename}
- 分段: {section_title}
- 页码范围: {page_start} - {page_end}

**页面内容**:
{pages_content_text}

**注释要求**:
{annotation_style_prompt}

请为每一页单独生成注释，使用以下格式：

--- PAGE {page_num} ---
[该页的注释内容]
--- END PAGE {page_num} ---
"""
```

**关键特点**：
- ✅ 一次性发送所有页面内容
- ✅ LLM返回所有页面的注释（用分隔符分隔）
- ✅ 后端解析后保存到独立文件

---

## 🎯 关键日志输出

### 1. 文件读取日志

```
📄 [文件读取] 第1页 (LLM) → Presentation-Report-guidelines-2026_page_001_llm.md
📄 [文件读取] 第2页 (PDF) → Presentation-Report-guidelines-2026_page_002.md
📄 [文件读取] 第3页 (LLM) → Presentation-Report-guidelines-2026_page_003_llm.md
```

**位置**：`content_manager.py` 第 2254-2270 行

### 2. 版本配置日志

```
💾 [版本配置] 页面1 已保存为 LLM 版本
💾 [版本配置] 页面2 已保存为 PDF 版本
```

**位置**：`content_manager.py` 第 2183 行

### 3. 版本回退日志

```
⚠️ [版本回退] 第5页 → LLM文件不存在，回退到PyPDF
```

**位置**：`content_manager.py` 第 2241 行

---

## 📊 完整流程总结

```
1. 用户点击 "批量生成所有注释"
   ↓
2. 前端并行发送 N 个分段请求 (Promise.all)
   ↓
3. 后端每个分段独立处理（FastAPI异步）:
   ├─ 读取页面内容:
   │  ├─ 调用 get_pdf_page_contents(page)
   │  ├─ 读取 page_versions.json
   │  ├─ 根据配置选择文件:
   │  │  ├─ version == 'llm' → 读取 xxx_page_001_llm.md
   │  │  └─ version == 'pdf' → 读取 xxx_page_001.md
   │  └─ 📄 [文件读取] 第X页 (LLM/PDF) → xxx.md
   ↓
4. 发送给LLM:
   ├─ pages_content: [页面1内容, 页面2内容, ...]
   ├─ 注释风格提示词
   └─ 分段信息（标题、页码范围）
   ↓
5. LLM返回所有页面注释（流式输出）
   ↓
6. 后端解析并保存:
   ├─ 解析 LLM 输出（按 PAGE 分隔符）
   ├─ 保存到 files/document/annotations/page_XXX.md
   └─ 发送 SSE 事件 → 前端更新进度
   ↓
7. 前端接收 SSE 事件:
   ├─ page_done → 更新进度条
   ├─ complete → 标记分段完成
   └─ 刷新当前页注释显示
   ↓
8. 所有分段完成（Promise.all resolve）
   ↓
9. 开始阶段4：融合重叠页注释
```

---

## ✅ 总结

### 是否并行？
**✅ 是的！**
- 前端：`Promise.all` 并行发送所有分段请求
- 后端：FastAPI 异步处理，每个请求独立

### PDF内容包括什么？
**✅ 每个分段的所有页面内容**
- 只包含当前页（不包括前后页）
- 根据版本配置读取（LLM or PyPDF）
- 完整的Markdown格式

### 上下文存储在哪？
**✅ 3个地方**
1. **磁盘**：`pages/document/xxx_page_001.md` / `xxx_page_001_llm.md`
2. **磁盘**：`pages/document/page_versions.json`（版本配置）
3. **内存**：前端 state（annotations, extractedContents, pageVersions）

### 文件读取监听
**✅ 已实现**
- 📄 [文件读取] 第X页 (LLM/PDF) → 文件名
- 每次读取页面内容时自动输出
- 位置：`content_manager.py` 第 2254-2270 行

