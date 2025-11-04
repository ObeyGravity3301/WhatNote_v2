"""
WhatNote 工具调用系统

为 LLM 提供可调用的工具集合，支持窗口管理、文件操作、待办管理等功能。
遵循 OpenAI Function Calling 标准格式。
"""

from .tool_registry import ToolRegistry, tool_registry
from .tool_executor import ToolExecutor, tool_executor
from .schemas import ToolDefinition, ToolCall, ToolResult, ToolStatus, ToolHandler
from .builtin_tools import register_builtin_tools

__all__ = [
    'ToolRegistry',
    'tool_registry',
    'ToolExecutor', 
    'tool_executor',
    'ToolDefinition',
    'ToolCall',
    'ToolResult',
    'ToolStatus',
    'ToolHandler',
    'register_builtin_tools'
]

