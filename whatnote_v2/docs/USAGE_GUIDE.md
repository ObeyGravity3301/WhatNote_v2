# WhatNote V2 使用指南

## 🚀 快速开始

### 1. 启动系统
```bash
python quick_start.py
```

### 2. 演示存储系统
```bash
python demo_storage.py
```

### 3. 测试API
```bash
python test_api_endpoints.py
```

## 📡 API使用

### 基础URL
```
http://127.0.0.1:8081
```

### 主要API端点

#### 健康检查
```bash
curl http://127.0.0.1:8081/api/health
```

#### 获取所有课程
```bash
curl http://127.0.0.1:8081/api/courses
```

#### 创建新课程
```bash
curl -X POST "http://127.0.0.1:8081/api/courses?name=课程名称&description=课程描述"
```

#### 获取课程的展板
```bash
curl http://127.0.0.1:8081/api/courses/{course_id}/boards
```

#### 创建新展板
```bash
curl -X POST "http://127.0.0.1:8081/api/courses/{course_id}/boards?board_name=展板名称"
```

#### 获取展板信息
```bash
curl http://127.0.0.1:8081/api/boards/{board_id}
```

#### 创建窗口
```bash
curl -X POST "http://127.0.0.1:8081/api/boards/{board_id}/windows" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "text",
    "title": "窗口标题",
    "content": "窗口内容",
    "position": {"x": 100, "y": 100},
    "size": {"width": 300, "height": 200}
  }'
```

#### 删除展板
```bash
curl -X DELETE "http://127.0.0.1:8081/api/boards/{board_id}"
```

## 🎯 功能演示

### 存储系统演示
运行 `python demo_storage.py` 可以看到：
- ✅ 创建课程和展板
- ✅ 保存窗口内容
- ✅ 验证文件系统结构
- ✅ 删除展板并验证文件夹消失

### API功能演示
运行 `python test_api_endpoints.py` 可以看到：
- ✅ 健康检查
- ✅ 课程管理（创建、获取）
- ✅ 展板管理（创建、获取）
- ✅ 窗口管理（创建、获取）
- ✅ 完整的CRUD操作

## 📁 文件系统结构

创建课程和展板后，会在 `whatnote_data/` 目录下生成：

```
whatnote_data/
└── courses/
    └── course-xxx/
        ├── course_info.json
        └── board-xxx/
            ├── board_info.json
            ├── windows/
            │   └── window_xxx.json
            ├── images/
            ├── videos/
            ├── pdfs/
            ├── notes/
            ├── llm_context/
            └── handwriting/
```

## 🔧 开发调试

### 查看API文档
访问：http://127.0.0.1:8081/docs

### 查看实时日志
启动后可以在控制台看到详细的日志信息

### 检查数据文件
所有数据都存储在 `whatnote_data/` 目录中，可以直接查看文件内容

## ✅ 验证功能

### 1. 真实文件系统存储
- 所有内容都存储在对应的文件夹中
- 不使用JSON文件模拟文件夹

### 2. 内容隔离
- 每个展板的内容完全独立存储
- 不同展板之间不会相互影响

### 3. 删除即消失
- 删除展板后，整个文件夹立即消失
- 软件中对应内容立即消失

### 4. 无全局缓存
- 直接使用文件系统
- 不依赖内存缓存

## 🎉 成功标志

当您看到以下信息时，表示系统运行正常：

```
✅ 健康检查通过
✅ 获取课程成功
✅ 创建课程成功
✅ 创建展板成功
✅ 创建窗口成功
✅ 获取展板信息成功
```

## 📞 故障排除

### 如果API无法访问
1. 确保服务器正在运行：`python quick_start.py`
2. 检查端口8081是否被占用
3. 查看控制台错误信息

### 如果存储功能异常
1. 检查 `whatnote_data/` 目录权限
2. 运行 `python demo_storage.py` 验证存储系统
3. 查看生成的文件夹结构

### 如果导入失败
1. 确保在正确的目录中运行
2. 检查Python环境
3. 安装依赖：`pip install -r requirements.txt`

---

*WhatNote V2 - 基于真实文件系统的笔记软件* 🚀 