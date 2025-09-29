from pathlib import Path

# 数据存储根目录
# 使用绝对路径，确保无论从哪里启动都能找到正确的数据目录
import os
DATA_DIR = Path(os.path.dirname(__file__)) / "whatnote_data"
TRASH_DIR = Path(os.path.dirname(__file__)) / "whatnote_data" / "trash"

# API配置
API_HOST = "127.0.0.1"
API_PORT = 8081

# 公网服务器配置（用于通义千问VL图片访问）
PUBLIC_SERVER_URL = "https://your-domain.com"  # 需要配置您的公网服务器地址

# WebSocket配置
WS_HOST = "127.0.0.1"
WS_PORT = 8001

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 