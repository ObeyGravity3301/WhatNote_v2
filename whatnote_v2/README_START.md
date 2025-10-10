# WhatNote V2 启动说明

## 快速启动（推荐）

### Linux/macOS
```bash
./start_simple.sh
```

### Windows
```cmd
start.bat
```

## 详细说明

### 方式一：简化脚本（最可靠）

**Linux/macOS:**
```bash
chmod +x start_simple.sh
./start_simple.sh
```

这个脚本会：
- 自动清理8081和3000端口
- 启动后端服务（使用虚拟环境）
- 启动前端服务
- 显示服务状态

**特点：**
- ✅ 最简单可靠
- ✅ 自动清理端口
- ✅ 实时显示状态
- ✅ Ctrl+C 一键停止

### 方式二：跨平台脚本

```bash
# Linux/macOS
python3 start_universal.py

# Windows  
python start_universal.py
```

**特点：**
- ✅ 支持Windows/Linux/macOS
- ✅ 自动创建虚拟环境
- ✅ 自动安装依赖
- ⚠️ 在某些文件系统上可能有兼容性问题

### 方式三：手动启动

**后端：**
```bash
cd backend
source ../venv/bin/activate  # Linux/macOS
# 或 ..\venv\Scripts\activate  # Windows
python run.py
```

**前端：**
```bash
cd frontend
npm start
```

## 访问地址

- 前端界面：http://localhost:3000
- 后端API：http://localhost:8081
- API文档：http://localhost:8081/docs

## 停止服务

- 如果使用脚本启动：按 `Ctrl+C`
- 手动停止：
  ```bash
  # 停止后端
  pkill -f "python.*run.py"
  
  # 停止前端
  pkill -f "react-scripts"
  ```

## 常见问题

### 端口被占用
脚本会自动清理端口，如果仍有问题：
```bash
# Linux/macOS
lsof -ti :8081 | xargs kill -9
lsof -ti :3000 | xargs kill -9

# Windows
netstat -ano | findstr :8081
taskkill /F /PID <PID>
```

### 虚拟环境问题
如果虚拟环境有问题，重新创建：
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 依赖安装失败
手动安装依赖：
```bash
# 后端
source venv/bin/activate
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

## 推荐使用

- **Linux用户**：使用 `./start_simple.sh`（最稳定）
- **Windows用户**：使用 `start.bat`
- **需要自动化部署**：使用 `start_universal.py`
