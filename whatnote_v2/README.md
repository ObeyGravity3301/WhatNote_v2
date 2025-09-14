# WhatNote V2

现代化的桌面笔记应用，基于 React + Electron + FastAPI 构建。支持多媒体内容、Markdown/LaTeX 渲染、拖拽编辑等功能。

## 🚀 快速启动

### 一键启动（推荐）

#### Windows:
双击 `start.bat` 文件，或在命令行运行：
```bash
start.bat
```

#### Linux/Mac:
```bash
./start.sh
```

#### 跨平台:
```bash
python start.py
```

### 手动启动

#### 环境要求
- Python 3.8+
- Node.js 16+
- npm

#### 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

#### 启动服务
```bash
# 启动后端 (端口 8081)
cd backend
python run.py

# 启动前端 (端口 3000)
cd frontend
npm start
```

## 📁 项目结构

```
whatnote_v2/
├── backend/              # Python FastAPI 后端
│   ├── config.py        # 配置文件
│   ├── logger.py        # 日志工具
│   ├── main.py          # 主应用
│   ├── run.py           # 启动脚本
│   ├── static/          # 静态文件
│   └── storage/         # 存储模块
│       ├── file_manager.py      # 文件系统管理
│       └── content_manager.py   # 内容管理
├── frontend/            # React + Electron 前端
│   ├── public/          # 公共资源
│   ├── src/             # 源代码
│   │   ├── components/  # React 组件
│   │   ├── App.js       # 主应用组件
│   │   └── index.js     # 入口文件
│   └── package.json     # 前端依赖
├── whatnote_data/       # 数据存储目录
│   └── courses/         # 课程数据
├── docs/                # 项目文档
├── start.py             # 跨平台启动脚本
├── start.bat            # Windows 启动脚本
├── start.sh             # Linux/Mac 启动脚本
└── README.md            # 项目说明
```

## 🎯 核心功能

### ✅ 已实现功能

- **📚 课程管理**: 创建、删除课程，支持层级组织
- **📋 展板系统**: 每个课程可包含多个展板
- **🪟 窗口系统**: 支持文本、图片、视频、音频、PDF 窗口
- **📝 Markdown 支持**: 实时渲染 Markdown 语法
- **🧮 LaTeX 支持**: 数学公式渲染 (KaTeX)
- **📤 文件上传**: 拖拽上传多媒体文件
- **🎨 拖拽编辑**: 可拖拽调整窗口位置
- **🔄 实时同步**: WebSocket 实时通信
- **💾 文件系统存储**: 基于目录结构的数据持久化
- **🌐 Web API**: 完整的 RESTful API

### 🔧 技术特性

- **模块化架构**: 后端存储系统完全模块化
- **内容隔离**: 每个展板独立存储，避免数据污染
- **删除即消失**: 删除展板时自动清理所有相关文件
- **无全局缓存**: 避免数据不一致问题
- **跨平台支持**: Windows、Linux、Mac 全平台支持
- **开发热重载**: 支持代码修改实时生效

## 🛠️ 技术栈

- **后端**: Python 3.8+, FastAPI, Uvicorn, pathlib
- **前端**: React 18+, Electron 20+, react-router-dom
- **UI组件**: 自定义 CSS，响应式设计
- **渲染引擎**: react-markdown, remark-gfm, rehype-katex
- **数据存储**: 文件系统 + JSON 元数据
- **通信协议**: HTTP REST API + WebSocket
- **开发工具**: VS Code, npm, pip

## 📊 API 接口

### 课程管理
- `GET /api/courses` - 获取课程列表
- `POST /api/courses` - 创建课程
- `GET /api/courses/{course_id}/boards` - 获取展板列表
- `POST /api/courses/{course_id}/boards` - 创建展板

### 展板管理
- `GET /api/boards/{board_id}` - 获取展板信息
- `DELETE /api/boards/{board_id}` - 删除展板
- `GET /api/boards/{board_id}/windows` - 获取窗口列表
- `POST /api/boards/{board_id}/windows` - 创建窗口
- `PUT /api/boards/{board_id}/windows/{window_id}` - 更新窗口
- `DELETE /api/boards/{board_id}/windows/{window_id}` - 删除窗口

### 文件管理
- `POST /api/boards/{board_id}/upload` - 文件上传
- `GET /api/boards/{board_id}/files/serve` - 文件服务

### 实时通信
- `WebSocket /ws/logs` - 实时日志推送

## 🎮 使用指南

### 基本操作

1. **创建课程**: 点击侧边栏 "新建课程" 按钮
2. **创建展板**: 选择课程后点击 "+ 展板" 按钮
3. **添加内容**: 点击顶部工具栏添加不同类型的窗口
4. **编辑内容**: 直接在窗口中编辑文本或上传文件
5. **拖拽调整**: 拖拽窗口标题栏调整位置

### 高级功能

- **Markdown 语法**: 在文本窗口中使用标准 Markdown 语法
- **LaTeX 公式**: 使用 `$公式$` 或 `$$公式$$` 渲染数学公式
- **快捷键**: `Ctrl+Shift+C` 切换开发者控制台

## 📖 文档

详细文档位于 `docs/` 目录：

- [第二阶段完成报告](docs/PHASE2_FINAL_REPORT.md)
- [第三阶段完成报告](docs/PHASE3_COMPLETION_REPORT.md)
- [API 使用指南](docs/USAGE_GUIDE.md)
- [问题解决方案](docs/PROBLEM_SOLUTION_SUMMARY.md)

## 🔍 故障排除

### 端口冲突
如果遇到端口占用，启动脚本会自动清理。也可手动清理：
```bash
# Windows
netstat -ano | findstr :8081
taskkill /F /PID <PID>

# Linux/Mac
lsof -ti:8081 | xargs kill -9
```

### 依赖问题
```bash
# 重新安装后端依赖
pip install -r requirements.txt --force-reinstall

# 重新安装前端依赖
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 数据重置
删除 `whatnote_data/` 目录可完全重置所有数据。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发流程
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

MIT License

---

**WhatNote V2** - 让笔记更简单，让思维更自由 ✨