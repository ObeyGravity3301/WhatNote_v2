import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 设置模块路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.main import app
from backend.config import API_HOST, API_PORT

if __name__ == "__main__":
    print(f"启动WhatNote V2后端服务 @ {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT) 
