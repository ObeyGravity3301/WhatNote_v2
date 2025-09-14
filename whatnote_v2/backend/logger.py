import logging
from config import LOG_LEVEL, LOG_FORMAT

# 配置logger
logger = logging.getLogger("WhatNote")
logger.setLevel(getattr(logging, LOG_LEVEL))

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))

# 创建格式化器
formatter = logging.Formatter(LOG_FORMAT)
console_handler.setFormatter(formatter)

# 添加处理器到logger
if not logger.handlers:
    logger.addHandler(console_handler)

def log_message(level, msg):
    """记录日志消息"""
    logger.log(level, msg)

def info(msg):
    """记录信息日志"""
    logger.info(msg)

def warning(msg):
    """记录警告日志"""
    logger.warning(msg)

def error(msg):
    """记录错误日志"""
    logger.error(msg)

def debug(msg):
    """记录调试日志"""
    logger.debug(msg) 