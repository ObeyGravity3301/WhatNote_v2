from pathlib import Path
import os
from dotenv import load_dotenv

# 加载环境变量
# 优先加载 backend 目录下的 .env 文件
env_path = Path(os.path.dirname(__file__)) / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # 兼容模式：如果 backend 下没有，尝试加载根目录下的
    load_dotenv()

# 数据存储根目录
DATA_DIR = Path(os.path.dirname(__file__)) / "whatnote_data"
TRASH_DIR = Path(os.path.dirname(__file__)) / "whatnote_data" / "trash"

# API配置
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 8081))

# 公网服务器配置（用于通义千问VL图片访问）
PUBLIC_SERVER_URL = os.getenv("PUBLIC_SERVER_URL", "https://your-domain.com")

# WebSocket配置
WS_HOST = os.getenv("WS_HOST", "127.0.0.1")
WS_PORT = int(os.getenv("WS_PORT", 8001))

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s" 