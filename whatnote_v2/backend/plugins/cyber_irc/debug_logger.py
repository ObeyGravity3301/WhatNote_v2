import logging
import os

# Create a dedicated logger
debug_logger = logging.getLogger("cyber_chat_debug")
debug_logger.setLevel(logging.INFO)

# File handler
# Write to project root or current dir
log_file = "agent_debug.log" 
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

# Avoid duplicate logs if re-imported
if not debug_logger.handlers:
    debug_logger.addHandler(file_handler)
    # Don't propagate to root logger (avoid console spam in main log)
    debug_logger.propagate = False

def dlog(msg):
    """Log to debug file only."""
    debug_logger.info(msg)








