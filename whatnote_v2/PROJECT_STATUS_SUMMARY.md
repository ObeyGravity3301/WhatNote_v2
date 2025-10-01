# WhatNote V2 项目状态总结

## 📋 项目概览

WhatNote V2 是一个基于 **FastAPI + React + Electron** 的笔记管理系统，具有类似Windows 98风格的桌面界面。核心特色是**基于真实文件系统的存储架构**（非JSON模拟），以及最近新增的**多模态LLM聊天功能**。

## 🏗️ 技术架构

### 后端 (FastAPI)
- **主要文件**: `backend/main.py` - 核心API服务器
- **端口**: 8081
- **存储管理器**:
  - `FileSystemManager` - 文件系统操作
  - `ContentManager` - 内容管理
  - `ConversationManager` - LLM对话管理
  - `APIConfigManager` - 全局API配置管理
- **服务模块**:
  - `LLMService` - 多服务商LLM API调用
  - `FileWatcher` - 文件变化监控
  - `DocumentConverter` - 文档转换

### 前端 (React + Electron)
- **主要组件**:
  - `App.js` - 主应用，包含任务栏和课程管理
  - `BoardCanvas.js` - 展板画布，统一窗口管理系统
  - `ChatWindow.js` - LLM聊天窗口（最新功能）
  - `Header.js`, `Sidebar.js` - 界面组件
- **端口**: 3000 (开发模式)

## 💾 存储架构详解

### 🎯 核心理念：真实文件系统存储
**不是JSON模拟**，而是基于真实的文件和文件夹结构：

```
whatnote_data/
├── api_config.json                    # 全局LLM API配置
├── courses/                           # 课程根目录
│   ├── course-1756987907632/         # 课程文件夹（时间戳ID）
│   │   ├── course.json               # 课程元数据
│   │   ├── board-1756987954946/      # 展板文件夹（时间戳ID）
│   │   │   ├── board.json            # 展板元数据
│   │   │   ├── windows/              # 窗口状态存储
│   │   │   │   ├── window_xxx.json   # 每个窗口的位置、大小等
│   │   │   │   └── icon-positions.json # 桌面图标位置
│   │   │   ├── files/                # 用户文件存储
│   │   │   │   ├── images/           # 图片文件
│   │   │   │   ├── videos/           # 视频文件
│   │   │   │   ├── audios/           # 音频文件
│   │   │   │   ├── pdfs/             # PDF文件
│   │   │   │   ├── texts/            # 文本文件
│   │   │   │   ├── pages/            # PDF分页提取内容（新增）
│   │   │   │   │   └── PDF文件名/
│   │   │   │   │       ├── PDF_page_001.md  # 页面文字提取
│   │   │   │   │       └── PDF_note_001.md  # 页面注释内容
│   │   │   │   └── *.jpg, *.pdf, *.md # 直接存储的文件
│   │   │   └── llm_conversations/    # LLM对话记录
│   │   │       ├── conv-xxx.json     # LLM-1 主对话记录
│   │   │       ├── outline-pdf-xxx-3.json      # LLM-3 大纲整合对话
│   │   │       ├── outline-pdf-xxx-3A.json     # LLM-3A 分组对话
│   │   │       └── outline-pdf-xxx-3B.json     # LLM-3B 分组对话
│   │   └── board-yyy/               # 其他展板
│   └── course-yyy/                  # 其他课程
└── trash/                           # 回收站
    ├── deleted_files...
    └── trash_info.json
```

### 🔑 存储特点

1. **层次化结构**: 课程 → 展板 → 文件/窗口/对话
2. **时间戳ID**: 所有实体使用时间戳作为唯一标识
3. **元数据分离**: 每个实体都有对应的JSON配置文件
4. **文件类型分类**: 自动按类型组织文件到不同子目录
5. **状态持久化**: 窗口位置、图标位置等UI状态实时保存

## 🤖 LLM聊天功能（最新完成）

### 功能特性
- **多服务商支持**: OpenAI、Anthropic、Gemini、Qwen（通义千问API已修复）
- **全局配置**: API配置存储在比课程更高级别，所有展板共享
- **流式响应**: 支持打字机效果的实时回复，带流式输出指示器
- **多模态支持**: 可发送展板中的图片、音频、视频、PDF文件
- **对话持久化**: 每个展板独立的对话记录
- **Markdown渲染**: 完整支持粗体、斜体、代码、表格等格式
- **Mermaid图表**: 支持流程图、时序图、甘特图等图表渲染
- **LaTeX公式**: 支持数学公式渲染（行内和块级）

### 技术实现
- **后端**: `LLMService` 处理不同服务商的API格式差异，支持OpenAI兼容模式
- **前端**: 集成在统一窗口管理系统中，支持拖拽、缩放
- **存储**: 对话记录存储在 `llm_conversations/` 目录
- **配置**: 全局API配置存储在 `api_config.json`
- **渲染**: 使用ReactMarkdown + remarkGfm + remarkMath + rehypeKatex
- **图表**: 集成Mermaid.js支持多种图表类型
- **流式输出**: 基于Server-Sent Events (SSE) 实现实时响应

### API端点
- `GET /api/llm/config` - 获取API配置
- `POST /api/llm/config/{provider}` - 更新服务商配置
- `POST /api/llm/provider/{provider}` - 设置当前服务商
- `POST /api/llm/chat` - 流式对话API

## 🎨 UI设计理念

### Windows 98风格
- **任务栏**: 底部状态栏，显示时间和窗口按钮
- **窗口系统**: 统一的拖拽、缩放、层级管理
- **图标**: 桌面图标对应实际文件
- **色彩**: 经典的灰色调和3D按钮效果

### 窗口管理系统
- **统一管理**: `BoardCanvas.js` 统一管理所有窗口类型
- **窗口类型**: `text`, `image`, `video`, `audio`, `pdf`, `chat`
- **状态同步**: 窗口状态实时保存到后端
- **特殊处理**: 聊天窗口不创建桌面图标，仅通过任务栏按钮控制

## 📊 最近开发工作

### 已完成功能
1. **全局API配置系统** - 所有展板共享LLM API配置
2. **多服务商LLM集成** - 支持4大主流LLM服务商（通义千问API已修复）
3. **流式响应** - 实时显示LLM回复，带流式输出指示器
4. **文件发送功能** - 聊天中可选择展板现有文件发送
5. **自适应输入框** - 输入框高度自动调整（1-6行）
6. **设置面板** - 完整的API配置UI
7. **Markdown渲染** - 完整支持格式化文本显示
8. **Mermaid图表** - 支持多种图表类型渲染
9. **LaTeX公式** - 支持数学公式渲染
10. **PDF注释功能** - 完整的PDF分页注释系统（新增）
11. **LLM智能注释** - 基于LLM的智能注释生成（开发中）

### 当前状态
- ✅ 后端LLM服务完全实现
- ✅ 前端聊天界面完全实现  
- ✅ API配置管理完全实现
- ✅ 文件系统存储完全实现
- ✅ **通义千问API修复** - 使用OpenAI兼容模式
- ✅ **流式输出优化** - 实时指示器和打字机效果
- ✅ **Markdown渲染** - 完整格式化支持
- ✅ **Mermaid图表** - 多种图表类型支持
- ✅ **LaTeX公式** - 数学公式渲染支持
- ✅ **PDF注释系统** - 基础功能完全实现
- 🚧 **LLM智能注释** - 分层大纲生成系统开发中

## 📝 PDF注释功能（最新功能 - 2025-10-01）

### 功能概述
完整的PDF分页注释系统，支持手动注释和LLM智能生成注释。

### 核心功能

#### 1. PDF分页和文字提取
- **自动分页**: PDF上传后自动按页提取文字内容
- **存储位置**: `files/pages/PDF文件名/PDF_page_001.md`
- **内容包含**: 页码、来源、提取时间、纯文字内容

#### 2. 注释侧栏系统
- **位置**: PDF分页模式右侧300px宽侧栏
- **功能按钮**:
  - **ℹ 信息按钮**: 显示文件创建时间、修改时间、大小等元数据
  - **LLM按钮**: 展开智能注释功能菜单
  - **编辑/预览切换**: 支持Markdown预览和编辑模式

#### 3. 注释存储
- **存储位置**: `files/pages/PDF文件名/PDF_note_001.md`
- **存储内容**: 纯用户输入内容（不包含元数据）
- **文件信息**: 使用文件系统的真实创建/修改时间
- **自动保存**: 1秒防抖自动保存机制

#### 4. LLM智能注释菜单
- **生成注释**: 基于PDF页面文字内容生成注释
- **视觉生成**: 基于PDF页面图像生成注释（计划中）
- **批量处理**: 批量生成多页注释（计划中）

### API端点
- `GET /api/boards/{board_id}/windows/{window_id}/annotations/{page}` - 获取注释内容
- `PUT /api/boards/{board_id}/windows/{window_id}/annotations/{page}` - 保存注释内容
- `GET /api/boards/{board_id}/windows/{window_id}/annotations/{page}/info` - 获取文件信息

### LLM-3分层大纲生成系统（开发中）

#### 系统架构
```
PDF上传 → 分页提取 → 分组处理(30页/组) → 大纲整合 → 插入LLM-1上下文
         (pages/)   (LLM-3A/B/C)        (LLM-3)    (system消息)
```

#### 处理流程
1. **分组策略**:
   - ≤30页: 单个LLM-3处理
   - >30页: 每30页一组，分配给LLM-3A/B/C...

2. **局部大纲生成**:
   - 每组生成结构化JSON大纲
   - 包含章节层级、页码区间、主题概括

3. **大纲整合**:
   - LLM-3收集所有分组大纲
   - 生成完整的层级化大纲

4. **上下文注入**:
   - 将完整大纲作为system消息
   - 插入LLM-1主对话上下文

#### 对话文件命名
- `outline-{pdf_name}-3.json` - LLM-3主整合对话
- `outline-{pdf_name}-3A.json` - 第1-30页分组对话
- `outline-{pdf_name}-3B.json` - 第31-60页分组对话
- 以此类推...

### 技术特点
- **无元数据污染**: 注释文件只包含用户输入内容
- **文件系统时间**: 使用真实文件创建/修改时间
- **Markdown支持**: 预览模式支持完整Markdown渲染
- **Windows 98风格**: 符合整体UI设计理念
- **点击外部关闭**: LLM菜单支持ESC键和点击外部关闭

## 🎯 下一步计划

1. **LLM-3大纲系统**: 完成分层大纲生成和整合功能
2. **智能注释生成**: 实现基于LLM的自动注释生成
3. **多模态增强**: 完善文件内容解析和发送
4. **性能优化**: 大文件处理和响应速度优化
5. **错误处理**: 完善API调用失败的重试机制
6. **用户体验**: 添加更多交互反馈和状态指示

## 🔧 开发环境

### 启动方式
```bash
# 方式1: 使用统一启动脚本
python start.py

# 方式2: 分别启动
cd backend && python run.py
cd frontend && npm start
```

### 端口分配
- 前端: http://localhost:3000
- 后端: http://localhost:8081
- API文档: http://localhost:8081/docs

## 💡 关键设计决策

1. **真实文件系统**: 选择真实文件存储而非数据库，便于用户直接访问文件
2. **时间戳ID**: 确保全局唯一性，避免ID冲突
3. **统一窗口管理**: 所有窗口类型使用相同的管理系统，保证一致性
4. **全局配置**: LLM API配置全局共享，避免重复配置
5. **流式响应**: 提供更好的用户体验，特别是长回复场景

---

**最后更新**: 2025-10-01
**版本**: v2.2.0
**状态**: PDF注释功能完全实现，LLM智能注释和分层大纲生成系统开发中

### 🆕 v2.2.0 更新内容 (2025-10-01)

#### PDF注释系统
- ✅ PDF分页和文字提取功能
- ✅ 注释侧栏UI（信息按钮、LLM按钮、编辑/预览切换）
- ✅ 注释文件自动保存（1秒防抖）
- ✅ 文件信息显示（使用文件系统时间）
- ✅ Markdown预览模式
- ✅ LLM智能注释菜单（基础UI）
- 🚧 LLM-3分层大纲生成系统（设计完成，开发中）
- 🚧 基于LLM的智能注释生成（计划中）
- 🚧 批量注释生成功能（计划中）

#### API端点新增
- `GET /api/boards/{board_id}/windows/{window_id}/annotations/{page}` - 获取注释
- `PUT /api/boards/{board_id}/windows/{window_id}/annotations/{page}` - 保存注释
- `GET /api/boards/{board_id}/windows/{window_id}/annotations/{page}/info` - 获取文件信息

#### 文件结构变更
- 新增 `files/pages/PDF文件名/` 目录结构
- PDF页面提取文件：`PDF_page_001.md`
- PDF注释文件：`PDF_note_001.md`
- LLM-3对话记录：`llm_conversations/outline-*.json`
