import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 设置模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.main import app

if __name__ == "__main__":
    print("启动WhatNote V2后端服务...")
    uvicorn.run(app, host="127.0.0.1", port=8081) 