from pathlib import Path

# 数据存储根目录
# 使用绝对路径，确保无论从哪里启动都能找到正确的数据目录
import os
DATA_DIR = Path(os.path.dirname(__file__)) / "whatnote_data"
TRASH_DIR = Path(os.path.dirname(__file__)) / "whatnote_data" / "trash"

# API配置
API_HOST = "127.0.0.1"
API_PORT = 8081

# WebSocket配置
WS_HOST = "127.0.0.1"
WS_PORT = 8001

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 