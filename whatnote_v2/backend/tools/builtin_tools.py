"""
WhatNote 内置工具集
提供窗口管理、内容操作等基础功能
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus, ToolCall
from storage.content_manager import ContentManager
from storage.file_manager import FileSystemManager
from logger import info, error
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import aiohttp


def normalize_web_url(url: str) -> str:
    if not url:
        return ""
    normalized = url.strip()
    if not normalized:
        return ""
    if not normalized.lower().startswith(("http://", "https://")):
        normalized = f"https://{normalized}"
    return normalized


# ==================== 工具定义 ====================

# 1. 创建新窗口
CREATE_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "create_window",
        "description": "在指定展板上创建一个新窗口。支持文本、图片、PDF等多种类型。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID，例如 'board-1234567890'"
                },
                "title": {
                    "type": "string",
                    "description": "窗口标题，会作为文件名"
                },
                "content": {
                    "type": "string",
                    "description": "窗口初始内容（文本类型时使用，支持 Markdown 格式）",
                    "default": ""
                },
                "window_type": {
                    "type": "string",
                    "enum": ["text", "image", "video", "audio", "pdf", "document", "web"],
                    "description": "窗口类型",
                    "default": "text"
                },
                "position": {
                    "type": "object",
                    "description": "窗口初始位置（可选）",
                    "properties": {
                        "x": {"type": "number", "description": "X坐标（像素）"},
                        "y": {"type": "number", "description": "Y坐标（像素）"}
                    }
                },
                "size": {
                    "type": "object",
                    "description": "窗口初始大小（可选）",
                    "properties": {
                        "width": {"type": "number", "description": "宽度（像素）"},
                        "height": {"type": "number", "description": "高度（像素）"}
                    }
                }
            },
            "required": ["board_id", "title"]
        }
    }
)


CREATE_WEB_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "create_web_window",
        "description": "创建一个网页窗口并加载指定的URL，适用于在白板中快速预览网页。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID，例如 'board-1234567890'"
                },
                "url": {
                    "type": "string",
                    "description": "要打开的网页URL，支持 http/https 协议"
                },
                "title": {
                    "type": "string",
                    "description": "窗口标题（可选）。未提供时会自动生成",
                    "default": ""
                },
                "position": {
                    "type": "object",
                    "description": "窗口初始位置（可选）",
                    "properties": {
                        "x": {"type": "number", "description": "X坐标（像素）"},
                        "y": {"type": "number", "description": "Y坐标（像素）"}
                    }
                },
                "size": {
                    "type": "object",
                    "description": "窗口初始大小（可选）",
                    "properties": {
                        "width": {"type": "number", "description": "宽度（像素）"},
                        "height": {"type": "number", "description": "高度（像素）"}
                    }
                }
            },
            "required": ["board_id", "url"]
        }
    }
)


# 2. 获取窗口列表
GET_WINDOWS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "get_windows",
        "description": "获取指定展板上的所有窗口列表，包括标题、类型、位置等信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "是否包含隐藏的窗口",
                    "default": False
                }
            },
            "required": ["board_id"]
        }
    }
)


# 3. 读取窗口内容
READ_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "read_window",
        "description": "读取指定窗口的完整内容。对于文本窗口返回 Markdown 内容，其他类型返回元数据。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "窗口ID，例如 'window_1234567890'"
                }
            },
            "required": ["board_id", "window_id"]
        }
    }
)


# 4. 更新窗口内容
UPDATE_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "update_window",
        "description": "更新窗口的内容。可以完全替换内容，或者追加内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "窗口ID"
                },
                "content": {
                    "type": "string",
                    "description": "新的内容（支持 Markdown）"
                },
                "mode": {
                    "type": "string",
                    "enum": ["replace", "append", "prepend"],
                    "description": "更新模式: replace=替换全部, append=追加到末尾, prepend=插入到开头",
                    "default": "replace"
                }
            },
            "required": ["board_id", "window_id", "content"]
        }
    }
)


UPDATE_WEB_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "update_web_window",
        "description": "更新网页窗口的URL、标题或位置/尺寸，并确保窗口保持web类型。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "窗口ID，例如 'window_1234567890'"
                },
                "url": {
                    "type": "string",
                    "description": "新的网页URL，支持 http/https 协议"
                },
                "title": {
                    "type": "string",
                    "description": "新的窗口标题（可选）"
                },
                "position": {
                    "type": "object",
                    "description": "要更新的窗口位置（可选）",
                    "properties": {
                        "x": {"type": "number", "description": "X坐标（像素）"},
                        "y": {"type": "number", "description": "Y坐标（像素）"}
                    }
                },
                "size": {
                    "type": "object",
                    "description": "要更新的窗口大小（可选）",
                    "properties": {
                        "width": {"type": "number", "description": "宽度（像素）"},
                        "height": {"type": "number", "description": "高度（像素）"}
                    }
                }
            },
            "required": ["board_id", "window_id", "url"]
        }
    }
)


# 4.5 精细编辑窗口内容
EDIT_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "edit_window",
        "description": "精细编辑窗口内容。支持插入、替换、删除文本，以及按行操作。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "窗口ID"
                },
                "operation": {
                    "type": "string",
                    "enum": ["insert", "replace_text", "delete_text", "insert_line", "replace_line", "delete_line"],
                    "description": "编辑操作类型:\n- insert: 在指定位置插入文本\n- replace_text: 替换指定文本\n- delete_text: 删除指定文本\n- insert_line: 在指定行号插入新行\n- replace_line: 替换指定行\n- delete_line: 删除指定行"
                },
                "target": {
                    "type": "string",
                    "description": "操作目标。对于 replace_text/delete_text: 要查找的文本；对于行操作: 行号（从1开始）或行号范围（如 '5' 或 '5-10'）"
                },
                "content": {
                    "type": "string",
                    "description": "新内容。用于 insert, replace_text, insert_line, replace_line 操作"
                },
                "position": {
                    "type": "string",
                    "enum": ["before", "after", "at"],
                    "description": "插入位置（仅用于 insert 和 insert_line）: before=之前, after=之后, at=替换",
                    "default": "after"
                },
                "all": {
                    "type": "boolean",
                    "description": "是否替换/删除所有匹配项（仅用于 replace_text/delete_text）",
                    "default": False
                }
            },
            "required": ["board_id", "window_id", "operation"]
        }
    }
)


# 5. 删除窗口
DELETE_WINDOW_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "delete_window",
        "description": "删除指定窗口。默认移动到回收站，可选择永久删除。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "窗口ID"
                },
                "permanent": {
                    "type": "boolean",
                    "description": "是否永久删除（默认移到回收站）",
                    "default": False
                }
            },
            "required": ["board_id", "window_id"]
        }
    }
)


# 6. 搜索窗口
SEARCH_WINDOWS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "search_windows",
        "description": "在指定展板上搜索窗口。可以按标题或内容搜索。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "search_in": {
                    "type": "string",
                    "enum": ["title", "content", "both"],
                    "description": "搜索范围: title=仅标题, content=仅内容, both=标题和内容",
                    "default": "both"
                },
                "limit": {
                    "type": "integer",
                    "description": "最多返回结果数",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10
                }
            },
            "required": ["board_id", "query"]
        }
    }
)

# 7. 读取PDF文本内容
READ_PDF_TEXT_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "read_pdf_text",
        "description": "读取PDF窗口的文本内容，可选PyPDF原始文本或LLM提取结果，支持按页或整本读取。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "PDF窗口ID"
                },
                "source": {
                    "type": "string",
                    "enum": ["auto", "pypdf", "llm"],
                    "description": "内容来源：auto=根据当前版本自动选择；pypdf=使用原始文本提取；llm=使用多模态提取结果",
                    "default": "auto"
                },
                "page": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "要读取的起始页码（可选，未提供时默认读取整本）"
                },
                "end_page": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "要读取的结束页码（可选，仅在指定page时有效）"
                }
            },
            "required": ["board_id", "window_id"]
        }
    }
)

# 8. 生成PDF注释
GENERATE_PDF_ANNOTATION_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "generate_pdf_annotation",
        "description": "为PDF窗口生成注释。支持单页、多页或批量注释。可以指定注释风格或使用自定义提示词。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "PDF窗口ID"
                },
                "pages": {
                    "oneOf": [
                        {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 1},
                            "description": "要注释的页码列表，例如 [1, 2, 3]"
                        },
                        {
                            "type": "string",
                            "enum": ["all"],
                            "description": "注释所有页面"
                        },
                        {
                            "type": "integer",
                            "minimum": 1,
                            "description": "单个页码"
                        }
                    ],
                    "description": "要注释的页码：可以是单个数字、数字数组，或 'all' 表示全部页面"
                },
                "style": {
                    "type": "string",
                    "enum": ["detailed", "simple", "academic", "qanda", "custom"],
                    "description": "注释风格：detailed=详细注释；simple=简洁注释；academic=学术注释；qanda=问答式注释；custom=自定义提示词",
                    "default": "detailed"
                },
                "custom_prompt": {
                    "type": "string",
                    "description": "自定义提示词模板（当style为custom时使用）。可以使用 {page} 作为页码占位符。例如：'请为第{page}页生成注释，重点关注...'"
                }
            },
            "required": ["board_id", "window_id", "pages"]
        }
    }
)

# 9. 生成PDF全文档笔记
GENERATE_PDF_SUMMARY_NOTE_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "generate_pdf_summary_note",
        "description": "为PDF文档生成全文档阅读笔记（Summary Note）。支持不同的笔记风格和自定义提示词。",
        "parameters": {
            "type": "object",
            "properties": {
                "board_id": {
                    "type": "string",
                    "description": "展板ID"
                },
                "window_id": {
                    "type": "string",
                    "description": "PDF窗口ID"
                },
                "style": {
                    "type": "string",
                    "enum": ["detailed", "concise", "academic", "outline", "custom"],
                    "description": "笔记风格：detailed=详细笔记；concise=简洁摘要；academic=学术综述；outline=大纲式笔记；custom=自定义提示词",
                    "default": "detailed"
                },
                "custom_prompt": {
                    "type": "string",
                    "description": "自定义提示词模板（当style为custom时使用）。"
                }
            },
            "required": ["board_id", "window_id"]
        }
    }
)


# ==================== 工具处理器 ====================

class WindowToolHandlers:
    """窗口工具处理器集合"""
    
    def __init__(self, content_manager: ContentManager):
        self.content_manager = content_manager
    
    async def create_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """创建新窗口"""
        try:
            board_id = args["board_id"]
            title = args["title"]
            content = args.get("content", "")
            window_type = args.get("window_type", "text")
            position = args.get("position", {})
            size = args.get("size", {})
            
            # 构建窗口数据
            window_data = {
                "id": f"window_{int(datetime.now().timestamp() * 1000)}",
                "title": title,
                "type": window_type,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "x": position.get("x", 100),
                "y": position.get("y", 100),
                "width": size.get("width", 600),
                "height": size.get("height", 400),
                "isMinimized": False,
                "isHidden": False,
                "zIndex": 1000
            }
            
            # 保存窗口
            success = self.content_manager.save_window_content(board_id, window_data)
            
            if not success:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_window",
                    status=ToolStatus.ERROR,
                    error=f"展板不存在或创建失败: {board_id}"
                )
            
            info(f"[工具] 创建窗口成功: {window_data['id']} @ {board_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_data["id"],
                    "title": title,
                    "type": window_type,
                    "message": f"成功创建窗口 '{title}'"
                }
            )
            
        except KeyError as e:
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_window",
                status=ToolStatus.ERROR,
                error=f"缺少必需参数: {e}"
            )
        except Exception as e:
            error(f"[工具] 创建窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_window",
                status=ToolStatus.ERROR,
                error=f"创建窗口时发生错误: {str(e)}"
            )

    async def create_web_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """创建网页窗口"""
        try:
            board_id = args["board_id"]
            raw_url = args["url"]
            normalized_url = normalize_web_url(raw_url)
            
            if not normalized_url:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_web_window",
                    status=ToolStatus.ERROR,
                    error="URL 无效，请提供 http 或 https 链接"
                )
            
            title = args.get("title") or f"网页窗口 {datetime.now().strftime('%H:%M:%S')}"
            position = args.get("position") or {}
            size = args.get("size") or {}
            
            x = position.get("x", 120)
            y = position.get("y", 120)
            width = size.get("width", 900)
            height = size.get("height", 600)
            
            window_id = f"window_{int(datetime.now().timestamp() * 1000)}"
            timestamp = datetime.now().isoformat()
            
            window_data = {
                "id": window_id,
                "title": title,
                "type": "web",
                "content": normalized_url,
                "web_url": normalized_url,
                "file_path": None,
                "created_at": timestamp,
                "updated_at": timestamp,
                "position": {"x": x, "y": y},
                "size": {"width": width, "height": height},
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "isMinimized": False,
                "isHidden": False,
                "zIndex": 1000
            }
            
            success = self.content_manager.save_window_content(board_id, window_data)
            
            if not success:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_web_window",
                    status=ToolStatus.ERROR,
                    error=f"创建网页窗口失败，展板不存在或存储异常 ({board_id})"
                )
            
            info(f"[工具] 创建网页窗口成功: {window_id} @ {board_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_web_window",
                status=ToolStatus.SUCCESS,
                data={
                    "board_id": board_id,
                    "window_id": window_id,
                    "title": title,
                    "url": normalized_url,
                    "position": {"x": x, "y": y},
                    "size": {"width": width, "height": height}
                }
            )
            
        except Exception as e:
            error(f"[工具] 创建网页窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_web_window",
                status=ToolStatus.ERROR,
                error=f"创建网页窗口失败: {str(e)}"
            )
    
    async def get_windows(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """获取窗口列表"""
        try:
            board_id = args["board_id"]
            include_hidden = args.get("include_hidden", False)
            
            # 获取窗口列表
            windows = self.content_manager.get_board_windows(board_id)
            
            # 过滤隐藏窗口
            if not include_hidden:
                windows = [w for w in windows if not w.get("isHidden", False)]
            
            # 简化返回的数据（只返回关键信息）
            simplified_windows = [
                {
                    "id": w.get("id"),
                    "title": w.get("title"),
                    "type": w.get("type"),
                    "created_at": w.get("created_at"),
                    "updated_at": w.get("updated_at"),
                    "isMinimized": w.get("isMinimized", False)
                }
                for w in windows
            ]
            
            info(f"[工具] 获取窗口列表成功: {board_id}, 共 {len(simplified_windows)} 个窗口")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="get_windows",
                status=ToolStatus.SUCCESS,
                data={
                    "board_id": board_id,
                    "count": len(simplified_windows),
                    "windows": simplified_windows
                }
            )
            
        except Exception as e:
            error(f"[工具] 获取窗口列表失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="get_windows",
                status=ToolStatus.ERROR,
                error=f"获取窗口列表失败: {str(e)}"
            )
    
    async def read_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """读取窗口内容"""
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            
            # 获取所有窗口以找到目标窗口
            windows = self.content_manager.get_board_windows(board_id)
            window = next((w for w in windows if w.get("id") == window_id), None)
            
            if not window:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="read_window",
                    status=ToolStatus.ERROR,
                    error=f"窗口不存在: {window_id}"
                )
            
            # 读取内容
            content = window.get("content", "")
            window_type = window.get("type", "text")
            title = window.get("title", "无标题")
            
            # 构建返回数据
            response_data = {
                "window_id": window_id,
                "title": title,
                "type": window_type,
                "created_at": window.get("created_at"),
                "updated_at": window.get("updated_at")
            }
            
            # 针对不同类型窗口返回不同内容
            if window_type == "image":
                # 返回文件路径，供 analyze_image 工具使用
                file_path = window.get("file_path") or content
                response_data["file_path"] = file_path
                response_data["message"] = "这是图片窗口。如果需要分析图片内容，请调用 analyze_image 工具，并提供此 file_path。"
                # 如果有OCR结果或其他描述（暂未实现，预留字段）
                response_data["description"] = window.get("description", "暂无文本描述")
                
            elif window_type == "text" or window_type == "markdown":
                response_data["content"] = content
                response_data["content_length"] = len(content)
                
            elif window_type == "pdf":
                response_data["file_path"] = window.get("file_path") or content
                response_data["message"] = "这是PDF窗口。请使用 read_pdf_text 工具读取内容，或 generate_pdf_annotation 工具生成注释。"
                
            else:
                # 其他类型（web, video, etc.）
                response_data["content"] = content
            
            info(f"[工具] 读取窗口成功: {window_id} @ {board_id} (Type: {window_type})")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_window",
                status=ToolStatus.SUCCESS,
                data=response_data
            )
            
        except Exception as e:
            error(f"[工具] 读取窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_window",
                status=ToolStatus.ERROR,
                error=f"读取窗口失败: {str(e)}"
            )
    
    async def update_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """更新窗口内容"""
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            new_content = args["content"]
            mode = args.get("mode", "replace")
            
            # 如果是追加或前置，需要先读取原内容
            if mode in ["append", "prepend"]:
                windows = self.content_manager.get_board_windows(board_id)
                window = next((w for w in windows if w.get("id") == window_id), None)
                
                if not window:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="update_window",
                        status=ToolStatus.ERROR,
                        error=f"窗口不存在: {window_id}"
                    )
                
                old_content = window.get("content", "")
                
                if mode == "append":
                    new_content = old_content + "\n\n" + new_content
                else:  # prepend
                    new_content = new_content + "\n\n" + old_content
            
            # 更新内容（此方法无返回值，通过异常来判断失败）
            try:
                self.content_manager.update_window_content_only(
                    board_id, 
                    window_id, 
                    new_content
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_window",
                    status=ToolStatus.ERROR,
                    error=f"更新失败: {str(e)}"
                )
            
            info(f"[工具] 更新窗口成功: {window_id} @ {board_id}, 模式: {mode}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_id,
                    "mode": mode,
                    "content_length": len(new_content),
                    "message": f"成功更新窗口内容（{mode} 模式）"
                }
            )
            
        except Exception as e:
            error(f"[工具] 更新窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_window",
                status=ToolStatus.ERROR,
                error=f"更新窗口失败: {str(e)}"
            )
    
    async def edit_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """精细编辑窗口内容"""
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            operation = args["operation"]
            target = args.get("target", "")
            new_content = args.get("content", "")
            position = args.get("position", "after")
            replace_all = args.get("all", False)
            
            # 读取当前内容
            windows = self.content_manager.get_board_windows(board_id)
            window = next((w for w in windows if w.get("id") == window_id), None)
            
            if not window:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="edit_window",
                    status=ToolStatus.ERROR,
                    error=f"窗口不存在: {window_id}"
                )
            
            old_content = window.get("content", "")
            result_content = old_content
            operation_desc = ""
            
            # 根据操作类型处理
            if operation == "replace_text":
                # 替换文本
                if not target:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error="replace_text 操作需要指定 target 参数"
                    )
                
                if target not in old_content:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error=f"未找到目标文本: {target[:50]}..."
                    )
                
                if replace_all:
                    count = old_content.count(target)
                    result_content = old_content.replace(target, new_content)
                    operation_desc = f"替换了 {count} 处文本"
                else:
                    result_content = old_content.replace(target, new_content, 1)
                    operation_desc = "替换了第一处匹配的文本"
            
            elif operation == "delete_text":
                # 删除文本
                if not target:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error="delete_text 操作需要指定 target 参数"
                    )
                
                if target not in old_content:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error=f"未找到目标文本: {target[:50]}..."
                    )
                
                if replace_all:
                    count = old_content.count(target)
                    result_content = old_content.replace(target, "")
                    operation_desc = f"删除了 {count} 处文本"
                else:
                    result_content = old_content.replace(target, "", 1)
                    operation_desc = "删除了第一处匹配的文本"
            
            elif operation == "insert":
                # 在指定文本位置插入
                if not target:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error="insert 操作需要指定 target 参数（查找位置）"
                    )
                
                if target not in old_content:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error=f"未找到目标文本: {target[:50]}..."
                    )
                
                idx = old_content.find(target)
                if position == "before":
                    result_content = old_content[:idx] + new_content + old_content[idx:]
                    operation_desc = "在目标文本之前插入了内容"
                elif position == "after":
                    idx += len(target)
                    result_content = old_content[:idx] + new_content + old_content[idx:]
                    operation_desc = "在目标文本之后插入了内容"
                else:  # at
                    result_content = old_content[:idx] + new_content + old_content[idx + len(target):]
                    operation_desc = "替换了目标文本"
            
            elif operation in ["insert_line", "replace_line", "delete_line"]:
                # 按行操作
                lines = old_content.split('\n')
                
                # 解析行号或行号范围
                try:
                    if '-' in target:
                        # 行号范围: "5-10"
                        start_str, end_str = target.split('-')
                        start_line = int(start_str.strip()) - 1  # 转为0索引
                        end_line = int(end_str.strip()) - 1
                        
                        if start_line < 0 or end_line >= len(lines) or start_line > end_line:
                            return ToolResult(
                                tool_call_id=context.get("call_id", ""),
                                tool_name="edit_window",
                                status=ToolStatus.ERROR,
                                error=f"无效的行号范围: {target}（总共 {len(lines)} 行）"
                            )
                    else:
                        # 单行号: "5"
                        line_num = int(target) - 1  # 转为0索引
                        if line_num < 0 or line_num >= len(lines):
                            return ToolResult(
                                tool_call_id=context.get("call_id", ""),
                                tool_name="edit_window",
                                status=ToolStatus.ERROR,
                                error=f"无效的行号: {target}（总共 {len(lines)} 行）"
                            )
                        start_line = end_line = line_num
                except ValueError:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="edit_window",
                        status=ToolStatus.ERROR,
                        error=f"无效的行号格式: {target}（应该是数字或范围，如 '5' 或 '5-10'）"
                    )
                
                # 执行行操作
                if operation == "insert_line":
                    if position == "before":
                        lines.insert(start_line, new_content)
                        operation_desc = f"在第 {start_line + 1} 行之前插入了新行"
                    elif position == "after":
                        lines.insert(end_line + 1, new_content)
                        operation_desc = f"在第 {end_line + 1} 行之后插入了新行"
                    else:  # at
                        lines[start_line] = new_content
                        operation_desc = f"替换了第 {start_line + 1} 行"
                
                elif operation == "replace_line":
                    for i in range(start_line, end_line + 1):
                        lines[i] = new_content if i == start_line else ""
                    # 移除空行
                    lines = [l for l in lines if l or lines.index(l) == start_line]
                    if start_line == end_line:
                        operation_desc = f"替换了第 {start_line + 1} 行"
                    else:
                        operation_desc = f"替换了第 {start_line + 1}-{end_line + 1} 行"
                
                elif operation == "delete_line":
                    del lines[start_line:end_line + 1]
                    if start_line == end_line:
                        operation_desc = f"删除了第 {start_line + 1} 行"
                    else:
                        operation_desc = f"删除了第 {start_line + 1}-{end_line + 1} 行"
                
                result_content = '\n'.join(lines)
            
            else:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="edit_window",
                    status=ToolStatus.ERROR,
                    error=f"未知的操作类型: {operation}"
                )
            
            # 更新内容
            try:
                self.content_manager.update_window_content_only(
                    board_id, 
                    window_id, 
                    result_content
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="edit_window",
                    status=ToolStatus.ERROR,
                    error=f"更新失败: {str(e)}"
                )
            
            info(f"[工具] 编辑窗口成功: {window_id} @ {board_id}, 操作: {operation}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="edit_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_id,
                    "operation": operation,
                    "operation_desc": operation_desc,
                    "old_length": len(old_content),
                    "new_length": len(result_content),
                    "message": f"成功{operation_desc}"
                }
            )
            
        except Exception as e:
            error(f"[工具] 编辑窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="edit_window",
                status=ToolStatus.ERROR,
                error=f"编辑窗口失败: {str(e)}"
            )

    async def update_web_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """更新网页窗口URL或元数据"""
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            raw_url = args["url"]
            normalized_url = normalize_web_url(raw_url)
            
            if not normalized_url:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_web_window",
                    status=ToolStatus.ERROR,
                    error="URL 无效，请提供 http 或 https 链接"
                )
            
            windows = self.content_manager.get_board_windows(board_id)
            window = next((w for w in windows if w.get("id") == window_id), None)
            
            if not window:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_web_window",
                    status=ToolStatus.ERROR,
                    error=f"窗口不存在: {window_id}"
                )
            
            updated_window = {**window}
            updated_window["type"] = "web"
            updated_window["content"] = normalized_url
            updated_window["web_url"] = normalized_url
            updated_window["file_path"] = None
            updated_window["updated_at"] = datetime.now().isoformat()
            
            if args.get("title"):
                updated_window["title"] = args["title"]
            
            position_args = args.get("position")
            current_position = updated_window.get("position") or {
                "x": updated_window.get("x", 100),
                "y": updated_window.get("y", 100)
            }
            if position_args:
                current_position["x"] = position_args.get("x", current_position.get("x", 100))
                current_position["y"] = position_args.get("y", current_position.get("y", 100))
            updated_window["position"] = current_position
            updated_window["x"] = current_position.get("x", 100)
            updated_window["y"] = current_position.get("y", 100)
            
            size_args = args.get("size")
            current_size = updated_window.get("size") or {
                "width": updated_window.get("width", 600),
                "height": updated_window.get("height", 400)
            }
            if size_args:
                current_size["width"] = size_args.get("width", current_size.get("width", 600))
                current_size["height"] = size_args.get("height", current_size.get("height", 400))
            updated_window["size"] = current_size
            updated_window["width"] = current_size.get("width", 600)
            updated_window["height"] = current_size.get("height", 400)
            
            success = self.content_manager.save_window_content(board_id, updated_window)
            
            if not success:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_web_window",
                    status=ToolStatus.ERROR,
                    error="保存网页窗口失败，展板可能不存在"
                )
            
            info(f"[工具] 更新网页窗口成功: {window_id} @ {board_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_web_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_id,
                    "board_id": board_id,
                    "title": updated_window.get("title"),
                    "url": normalized_url,
                    "position": updated_window.get("position"),
                    "size": updated_window.get("size")
                }
            )
            
        except Exception as e:
            error(f"[工具] 更新网页窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_web_window",
                status=ToolStatus.ERROR,
                error=f"更新网页窗口失败: {str(e)}"
            )
    
    async def delete_window(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """删除窗口"""
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            permanent = args.get("permanent", False)
            
            if permanent:
                success = self.content_manager.delete_window_content(board_id, window_id)
                message = "永久删除窗口成功"
            else:
                success = self.content_manager.move_window_to_trash(board_id, window_id)
                message = "窗口已移动到回收站"
            
            if not success:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="delete_window",
                    status=ToolStatus.ERROR,
                    error=f"删除失败，窗口可能不存在: {window_id}"
                )
            
            info(f"[工具] {message}: {window_id} @ {board_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="delete_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_id,
                    "permanent": permanent,
                    "message": message
                }
            )
            
        except Exception as e:
            error(f"[工具] 删除窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="delete_window",
                status=ToolStatus.ERROR,
                error=f"删除窗口失败: {str(e)}"
            )
    
    async def search_windows(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """搜索窗口"""
        try:
            board_id = args["board_id"]
            query = args["query"].lower()
            search_in = args.get("search_in", "both")
            limit = args.get("limit", 10)
            
            # 获取所有窗口
            windows = self.content_manager.get_board_windows(board_id)
            
            # 搜索匹配
            matches = []
            for window in windows:
                title = window.get("title", "").lower()
                content = window.get("content", "").lower()
                
                matched = False
                match_in = []
                
                if search_in in ["title", "both"] and query in title:
                    matched = True
                    match_in.append("title")
                
                if search_in in ["content", "both"] and query in content:
                    matched = True
                    match_in.append("content")
                
                if matched:
                    matches.append({
                        "id": window.get("id"),
                        "title": window.get("title"),
                        "type": window.get("type"),
                        "matched_in": match_in,
                        "updated_at": window.get("updated_at")
                    })
                
                if len(matches) >= limit:
                    break
            
            info(f"[工具] 搜索窗口: '{query}' @ {board_id}, 找到 {len(matches)} 个结果")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="search_windows",
                status=ToolStatus.SUCCESS,
                data={
                    "query": query,
                    "board_id": board_id,
                    "count": len(matches),
                    "results": matches
                }
            )
            
        except Exception as e:
            error(f"[工具] 搜索窗口失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="search_windows",
                status=ToolStatus.ERROR,
                error=f"搜索失败: {str(e)}"
            )


class PDFToolHandlers:
    """PDF内容读取相关工具处理器"""

    def __init__(self, content_manager: ContentManager):
        self.content_manager = content_manager

    async def read_pdf_text(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        try:
            board_id = args["board_id"]
            window_id = args["window_id"]
            source = args.get("source", "auto")
            page = args.get("page")
            end_page = args.get("end_page")

            result = self.content_manager.get_pdf_text(
                board_id=board_id,
                window_id=window_id,
                page=page,
                end_page=end_page,
                source=source
            )

            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="read_pdf_text",
                    status=ToolStatus.ERROR,
                    error=result.get("error", "读取PDF内容失败"),
                    data={
                        "board_id": board_id,
                        "window_id": window_id,
                        "details": result
                    }
                )

            info(
                f"[工具] 读取PDF内容成功: board={board_id}, window={window_id}, "
                f"mode={result.get('mode')}, pages={result.get('start_page')}-{result.get('end_page')}, "
                f"source={result.get('sources_used')}"
            )

            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_pdf_text",
                status=ToolStatus.SUCCESS,
                data=result
            )

        except KeyError as e:
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_pdf_text",
                status=ToolStatus.ERROR,
                error=f"缺少必需参数: {e}"
            )
        except Exception as e:
            error(f"[工具] 读取PDF内容失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_pdf_text",
                status=ToolStatus.ERROR,
                error=f"读取PDF内容时发生错误: {str(e)}"
            )
    
    async def generate_pdf_annotation(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """生成PDF注释"""
        try:
            
            board_id = args.get("board_id")
            window_id = args.get("window_id")
            pages = args.get("pages")
            style = args.get("style", "detailed")
            custom_prompt = args.get("custom_prompt", "")
            
            # 注释风格提示词映射
            style_prompts = {
                "detailed": "请为第{page}页生成详细的注释，包括：\n1. 页面主要内容概要\n2. 重要知识点详解\n3. 需要注意的细节\n4. 相关概念说明\n\n请用Markdown格式输出。",
                "simple": "请为第{page}页生成简洁的注释，只包括：\n1. 核心内容概括（1-2句话）\n2. 关键知识点（列表形式）\n\n请用Markdown格式输出。",
                "academic": "请为第{page}页生成学术风格的注释，包括：\n1. 内容摘要\n2. 主要论点和证据\n3. 方法论说明\n4. 关键术语解释\n\n请用Markdown格式输出。",
                "qanda": "请为第{page}页生成问答式注释：\n1. 这页讲了什么？\n2. 核心概念是什么？\n3. 需要记住什么？\n4. 如何应用？\n\n请用Markdown格式输出。"
            }
            
            # 确定使用的提示词模板
            if style == "custom":
                if not custom_prompt:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="generate_pdf_annotation",
                        status=ToolStatus.ERROR,
                        error="当style为custom时，必须提供custom_prompt参数"
                    )
                prompt_template = custom_prompt
            else:
                prompt_template = style_prompts.get(style, style_prompts["detailed"])
            
            # 获取窗口信息以确定PDF总页数
            windows = self.content_manager.get_board_windows(board_id)
            target_window = None
            for window in windows:
                if window.get('id') == window_id:
                    target_window = window
                    break
            
            if not target_window:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_annotation",
                    status=ToolStatus.ERROR,
                    error=f"窗口不存在: {window_id}"
                )
            
            if target_window.get('type') != 'pdf':
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_annotation",
                    status=ToolStatus.ERROR,
                    error=f"窗口类型不是PDF: {target_window.get('type')}"
                )
            
            is_full_batch = isinstance(pages, str) and pages.lower() == "all"
            
            # 全流程批量注释（大纲 -> 细分 -> 逐页注释 -> 融合）
            if is_full_batch:
                batch_result = await self._run_full_annotation_pipeline(
                    board_id=board_id,
                    window_id=window_id,
                    style=style,
                    prompt_template=prompt_template,
                    tool_call_id=context.get("call_id", "")
                )
                
                if not batch_result["success"]:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="generate_pdf_annotation",
                        status=ToolStatus.ERROR,
                        error=batch_result["error"],
                        data=batch_result.get("data")
                    )
                
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_annotation",
                    status=ToolStatus.SUCCESS,
                    data=batch_result["data"]
                )
            
            # 确定要注释的页码列表（非全流程时）
            if isinstance(pages, int):
                page_list = [pages]
            elif isinstance(pages, list):
                page_list = pages
            else:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_annotation",
                    status=ToolStatus.ERROR,
                    error=f"无效的pages参数: {pages}"
                )
            
            # 调用后端API生成注释
            results = []
            errors = []
            
            timeout = aiohttp.ClientTimeout(total=120, sock_connect=30, sock_read=110)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for page_num in page_list:
                    try:
                        url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/{page_num}/generate"
                        payload = {
                            "promptTemplate": prompt_template.replace("{page}", str(page_num))
                        }
                        
                        async with session.post(url, json=payload) as response:
                            if response.status == 200:
                                # 检查响应类型
                                content_type = response.headers.get('Content-Type', '')
                                
                                if 'text/event-stream' in content_type:
                                    # SSE流式响应，需要累积所有chunk
                                    accumulated_content = ""
                                    
                                    # 使用aiohttp的iter_lines方法逐行读取SSE流
                                    async for line_bytes in response.content:
                                        if not line_bytes:
                                            continue
                                        
                                        line = line_bytes.decode('utf-8', errors='ignore').strip()
                                        
                                        # SSE格式: data: {...}\n\n
                                        if line.startswith('data: '):
                                            data_str = line[6:]  # 移除 "data: " 前缀
                                            
                                            # 检查结束标记
                                            if data_str == '[DONE]':
                                                break
                                            
                                            try:
                                                chunk_data = json.loads(data_str)
                                                
                                                # 累积content类型的chunk
                                                if chunk_data.get('type') == 'content':
                                                    chunk_content = chunk_data.get('content', '')
                                                    if chunk_content:
                                                        accumulated_content += chunk_content
                                                
                                                # 检查done标记
                                                elif chunk_data.get('type') == 'done':
                                                    break
                                                
                                                # 忽略其他类型的消息（如status, notification等）
                                                
                                            except json.JSONDecodeError as e:
                                                # 如果JSON解析失败，可能是纯文本数据
                                                # 尝试直接使用
                                                if data_str and data_str != '[DONE]':
                                                    info(f"[工具] SSE数据不是JSON格式，尝试直接使用: {data_str[:50]}...")
                                                    accumulated_content += data_str
                                    
                                    if accumulated_content:
                                        results.append({
                                            "page": page_num,
                                            "status": "success",
                                            "annotation": accumulated_content
                                        })
                                        info(f"[工具] PDF注释生成成功: 第{page_num}页 (流式响应，长度: {len(accumulated_content)} 字符)")
                                    else:
                                        errors.append(f"第{page_num}页: 流式响应未收到任何内容")
                                        info(f"[工具] PDF注释生成失败: 第{page_num}页 - 未收到内容")
                                else:
                                    # 标准JSON响应
                                    result_data = await response.json(content_type=None)
                                    results.append({
                                        "page": page_num,
                                        "status": "success",
                                        "annotation": result_data.get("annotation", "")
                                    })
                                    info(f"[工具] PDF注释生成成功: 第{page_num}页")
                            else:
                                error_text = await response.text()
                                errors.append(f"第{page_num}页: HTTP {response.status} - {error_text}")
                                info(f"[工具] PDF注释生成失败: 第{page_num}页 - {error_text}")
                    except Exception as e:
                        errors.append(f"第{page_num}页: {str(e)}")
                        error(f"[工具] PDF注释生成异常: 第{page_num}页 - {e}")
                        import traceback
                        error(traceback.format_exc())
            
            if errors:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_annotation",
                    status=ToolStatus.ERROR,
                    error=f"部分页面注释生成失败:\n" + "\n".join(errors),
                    data={
                        "successful": results,
                        "failed": errors
                    }
                )
            
            info(f"[工具] PDF注释生成完成: 共{len(results)}页")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="generate_pdf_annotation",
                status=ToolStatus.SUCCESS,
                data={
                    "total_pages": len(page_list),
                    "completed": len(results),
                    "style": style,
                    "results": results
                }
            )
            
        except Exception as e:
            error(f"[工具] 生成PDF注释失败: {e}")
            import traceback
            error(traceback.format_exc())
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="generate_pdf_annotation",
                status=ToolStatus.ERROR,
                error=f"生成PDF注释时发生异常: {str(e)}"
            )

    async def generate_pdf_summary_note(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """生成PDF全文档笔记"""
        try:
            board_id = args.get("board_id")
            window_id = args.get("window_id")
            style = args.get("style", "detailed")
            custom_prompt = args.get("custom_prompt", "")
            
            if style == "custom" and not custom_prompt:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="generate_pdf_summary_note",
                    status=ToolStatus.ERROR,
                    error="当style为custom时，必须提供custom_prompt参数"
                )
            
            # 调用后端API生成笔记
            # 设置较长的超时时间，因为生成笔记可能需要较长时间（尤其是大文件）
            timeout = aiohttp.ClientTimeout(total=600, sock_connect=30, sock_read=550)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/batch/summary-note"
                payload = {
                    "summary_style": style,
                    "custom_prompt": custom_prompt
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        # 处理SSE流式响应
                        accumulated_content = ""
                        saved_path = ""
                        
                        async for line_bytes in response.content:
                            if not line_bytes:
                                continue
                            
                            line = line_bytes.decode('utf-8', errors='ignore').strip()
                            if line.startswith('data: '):
                                data_str = line[6:]
                                try:
                                    chunk_data = json.loads(data_str)
                                    msg_type = chunk_data.get('type')
                                    
                                    if msg_type in ['content', 'merge_content']:
                                        accumulated_content += chunk_data.get('content', '')
                                    elif msg_type == 'saved':
                                        saved_path = chunk_data.get('path', '')
                                    elif msg_type == 'error':
                                        return ToolResult(
                                            tool_call_id=context.get("call_id", ""),
                                            tool_name="generate_pdf_summary_note",
                                            status=ToolStatus.ERROR,
                                            error=f"生成过程中出错: {chunk_data.get('error')}"
                                        )
                                except json.JSONDecodeError:
                                    pass
                        
                        if accumulated_content:
                            info(f"[工具] 全文档笔记生成成功: {len(accumulated_content)} 字符")
                            return ToolResult(
                                tool_call_id=context.get("call_id", ""),
                                tool_name="generate_pdf_summary_note",
                                status=ToolStatus.SUCCESS,
                                data={
                                    "note_content": accumulated_content,
                                    "saved_path": saved_path,
                                    "message": "全文档笔记生成成功"
                                }
                            )
                        else:
                            return ToolResult(
                                tool_call_id=context.get("call_id", ""),
                                tool_name="generate_pdf_summary_note",
                                status=ToolStatus.ERROR,
                                error="未收到笔记内容"
            )
                    else:
                        error_text = await response.text()
                        return ToolResult(
                            tool_call_id=context.get("call_id", ""),
                            tool_name="generate_pdf_summary_note",
                            status=ToolStatus.ERROR,
                            error=f"API请求失败 (HTTP {response.status}): {error_text}"
                        )
                        
        except Exception as e:
            error(f"[工具] 生成全文档笔记失败: {e}")
            import traceback
            error(traceback.format_exc())
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="generate_pdf_summary_note",
                status=ToolStatus.ERROR,
                error=f"生成全文档笔记时发生异常: {str(e)}"
            )
            

    async def _collect_sse_events(self, response) -> List[Dict[str, Any]]:
        """从SSE响应中收集事件"""
        events: List[Dict[str, Any]] = []
        buffer = ""
        
        async for chunk in response.content.iter_any():
            buffer += chunk.decode("utf-8", errors="ignore")
            
            while "\n\n" in buffer:
                segment, buffer = buffer.split("\n\n", 1)
                segment = segment.strip()
                if not segment:
                    continue
                
                for line in segment.splitlines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    if data_str == "[DONE]":
                        return events
                    
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        if event.get("type") == "done":
                            return events
                    except json.JSONDecodeError:
                        info(f"[工具] SSE事件JSON解析失败，原始数据: {data_str[:100]}")
                        events.append({"type": "raw", "data": data_str})
        
        # 处理剩余缓冲
        if buffer.strip():
            for line in buffer.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str and data_str != "[DONE]":
                        try:
                            events.append(json.loads(data_str))
                        except json.JSONDecodeError:
                            events.append({"type": "raw", "data": data_str})
        
        return events

    async def _post_sse_request(
        self,
        session: "aiohttp.ClientSession",
        url: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """发送POST请求并解析SSE事件"""
        try:
            async with session.post(url, json=payload) as response:
                if response.status >= 400:
                    text = await response.text()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {text}"
                    }
                
                content_type = (response.headers.get("Content-Type") or "").lower()
                if "text/event-stream" in content_type:
                    events = await self._collect_sse_events(response)
                    return {"success": True, "mode": "sse", "events": events}
                
                # 尝试解析JSON
                try:
                    data = await response.json(content_type=None)
                except Exception:
                    data = await response.text()
                
                return {"success": True, "mode": "json", "data": data}
        except Exception as e:
            import traceback
            error(f"[工具] SSE请求失败 ({url}): {e}")
            error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    def _extract_event(self, events: List[Dict[str, Any]], event_type: str) -> Optional[Dict[str, Any]]:
        """从事件列表中提取指定类型的事件"""
        for event in events:
            if event.get("type") == event_type:
                return event
        return None

    async def _run_outline_stage(
        self,
        session: "aiohttp.ClientSession",
        board_id: str,
        window_id: str,
    ) -> Dict[str, Any]:
        """执行批量注释第一阶段：生成大纲"""
        url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/batch/outline"
        result = await self._post_sse_request(session, url)
        if not result["success"]:
            return {"success": False, "error": f"生成大纲失败: {result.get('error')}"}
        
        outline_data = None
        status_log: List[str] = []
        events = result.get("events", [])
        
        for event in events:
            event_type = event.get("type")
            if event_type in {"status", "info"} and event.get("message"):
                status_log.append(event["message"])
            elif event_type == "outline":
                outline_data = event.get("outline")
            elif event_type == "error":
                return {"success": False, "error": event.get("error", "生成大纲时发生错误")}
        
        if not outline_data:
            return {"success": False, "error": "生成大纲失败，未收到outline数据"}
        
        return {"success": True, "outline": outline_data, "status_log": status_log, "events": events}

    async def _run_subdivide_stage(
        self,
        session: "aiohttp.ClientSession",
        board_id: str,
        window_id: str,
    ) -> Dict[str, Any]:
        """执行批量注释第二阶段：细分大纲"""
        url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/batch/subdivide"
        result = await self._post_sse_request(session, url)
        if not result["success"]:
            return {"success": False, "error": f"细分大纲失败: {result.get('error')}"}
        
        subdivision_data = None
        status_log: List[str] = []
        events = result.get("events", [])
        
        for event in events:
            event_type = event.get("type")
            if event_type == "status" and event.get("message"):
                status_log.append(event["message"])
            elif event_type == "error":
                return {"success": False, "error": event.get("message", "细分大纲时发生错误")}
            elif event_type == "complete":
                subdivision_data = event.get("data")
        
        if not subdivision_data:
            return {"success": False, "error": "细分大纲失败，未收到完整数据"}
        
        return {"success": True, "subdivisions": subdivision_data, "status_log": status_log, "events": events}

    async def _run_section_generation_stage(
        self,
        session: "aiohttp.ClientSession",
        board_id: str,
        window_id: str,
        section_index: int,
        section_data: Dict[str, Any],
        subdivision_data: Dict[str, Any],
        annotation_style: str,
        prompt_template: str,
    ) -> Dict[str, Any]:
        """执行批量注释第三阶段：逐分段生成注释"""
        url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-section"
        payload = {
            "section_index": section_index,
            "section_data": section_data,
            "subdivision_data": subdivision_data,
            "annotation_style": annotation_style,
            "promptTemplate": prompt_template
        }
        
        result = await self._post_sse_request(session, url, payload)
        if not result["success"]:
            return {"success": False, "error": f"分段{section_index}注释失败: {result.get('error')}"}
        
        events = result.get("events", [])
        page_annotations: Dict[int, str] = {}
        status_log: List[str] = []
        completed_pages = 0
        total_pages = (section_data.get("page_end", 0) - section_data.get("page_start", 0) + 1) or 0
        
        for event in events:
            event_type = event.get("type")
            if event_type == "status" and event.get("message"):
                status_log.append(event["message"])
            elif event_type == "page_done":
                page = event.get("page")
                annotation = event.get("annotation")
                if page and annotation:
                    page_annotations[int(page)] = annotation
                completed_pages = event.get("completed", completed_pages)
            elif event_type == "error":
                return {"success": False, "error": event.get("error", f"分段{section_index}注释失败")}
            elif event_type == "complete":
                completed_pages = event.get("completed_pages", completed_pages)
                total_pages = event.get("total_pages", total_pages)
        
        return {
            "success": True,
            "page_annotations": page_annotations,
            "status_log": status_log,
            "completed_pages": completed_pages,
            "total_pages": total_pages,
            "events": events
        }

    async def _run_merge_stage(
        self,
        session: "aiohttp.ClientSession",
        board_id: str,
        window_id: str,
    ) -> Dict[str, Any]:
        """执行批量注释第四阶段：融合重叠页"""
        url = f"http://localhost:8081/api/boards/{board_id}/windows/{window_id}/annotations/batch/merge-overlapping"
        result = await self._post_sse_request(session, url)
        if not result["success"]:
            return {"success": False, "error": f"融合重叠页失败: {result.get('error')}"}
        
        events = result.get("events", [])
        status_log: List[str] = []
        merged_pages = 0
        total_pages = 0
        
        for event in events:
            event_type = event.get("type")
            if event_type in {"status", "info"} and event.get("message"):
                status_log.append(event["message"])
            elif event_type in {"merge_done", "merge_skip"}:
                merged_pages = event.get("completed", merged_pages)
                total_pages = event.get("total", total_pages)
            elif event_type == "complete":
                total_pages = event.get("total_pages", total_pages)
            elif event_type == "error":
                return {"success": False, "error": event.get("error", "融合重叠页失败")}
        
        return {
            "success": True,
            "merged_pages": merged_pages,
            "total_pages": total_pages,
            "status_log": status_log,
            "events": events
        }

    async def _run_full_annotation_pipeline(
        self,
        board_id: str,
        window_id: str,
        style: str,
        prompt_template: str,
        tool_call_id: str
    ) -> Dict[str, Any]:
        """执行完整的批量注释流程"""
        
        status_log: List[str] = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=120, sock_connect=30, sock_read=110)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 阶段1：生成大纲
                outline_result = await self._run_outline_stage(session, board_id, window_id)
                if not outline_result["success"]:
                    return outline_result
                
                outline_data = outline_result["outline"]
                status_log.extend(outline_result.get("status_log", []))
                
                sections = outline_data.get("outline", [])
                if not sections:
                    return {"success": False, "error": "生成的大纲为空，无法继续批量注释"}
                
                page_analysis = outline_data.get("page_analysis", {})
                overlapping_pages = page_analysis.get("statistics", {}).get("multi_annotated_pages", [])
                
                # 阶段2：细分大纲
                subdivision_result = await self._run_subdivide_stage(session, board_id, window_id)
                if not subdivision_result["success"]:
                    return subdivision_result
                
                subdivision_data = subdivision_result["subdivisions"]
                status_log.extend(subdivision_result.get("status_log", []))
                subdivisions_list = subdivision_data.get("subdivisions", [])
                if not subdivisions_list or len(subdivisions_list) != len(sections):
                    return {"success": False, "error": "细分数据不完整，请重试批量注释"}
                
                # 阶段3：逐分段生成注释
                all_page_annotations: Dict[int, str] = {}
                section_summaries: List[Dict[str, Any]] = []
                for idx, section in enumerate(sections):
                    subdivision = subdivisions_list[idx]
                    if subdivision is None:
                        status_log.append(f"分段 {idx + 1} 缺少细分数据，已跳过")
                        continue
                    section_result = await self._run_section_generation_stage(
                        session=session,
                        board_id=board_id,
                        window_id=window_id,
                        section_index=idx,
                        section_data=section,
                        subdivision_data=subdivision,
                        annotation_style=style,
                        prompt_template=prompt_template
                    )
                    if not section_result["success"]:
                        return section_result
                    status_log.extend(section_result.get("status_log", []))
                    for page, annotation in section_result["page_annotations"].items():
                        all_page_annotations[page] = annotation
                    section_summaries.append({
                        "section_index": idx,
                        "title": section.get("title") or section.get("section_title") or f"分段{idx + 1}",
                        "page_start": section.get("page_start"),
                        "page_end": section.get("page_end"),
                        "generated_pages": section_result.get("completed_pages"),
                        "total_pages": section_result.get("total_pages")
                    })
                
                # 阶段4：融合重叠页（如有需要）
                merge_info = None
                if overlapping_pages:
                    merge_result = await self._run_merge_stage(session, board_id, window_id)
                    if not merge_result["success"]:
                        return merge_result
                    status_log.extend(merge_result.get("status_log", []))
                    merge_info = {
                        "merged_pages": merge_result.get("merged_pages"),
                        "total_pages": merge_result.get("total_pages")
                    }
                
                # 汇总全部页码
                all_pages: List[int] = []
                for section in sections:
                    start = section.get("page_start")
                    end = section.get("page_end")
                    if start is not None and end is not None:
                        all_pages.extend(range(start, end + 1))
                unique_pages = sorted(set(all_pages))
                
                # 读取最终注释内容（文件系统已保存最新结果）
                final_annotations: Dict[int, str] = {}
                for page in unique_pages:
                    try:
                        annotation_text = self.content_manager.get_pdf_annotation(board_id, window_id, page)
                    except Exception:
                        annotation_text = ""
                    if annotation_text:
                        final_annotations[page] = annotation_text
                    elif page in all_page_annotations:
                        final_annotations[page] = all_page_annotations[page]
                    else:
                        final_annotations[page] = ""
                
                data = {
                    "mode": "batch_full",
                    "total_sections": len(sections),
                    "total_pages": len(unique_pages),
                    "style": style,
                    "outline_sections": [
                        {
                            "section_number": section.get("section_number", idx + 1),
                            "title": section.get("title") or section.get("section_title") or f"分段{idx + 1}",
                            "page_start": section.get("page_start"),
                            "page_end": section.get("page_end")
                        }
                        for idx, section in enumerate(sections)
                    ],
                    "subdivision_summary": [
                        {
                            "section_index": idx,
                            "section_number": (sections[idx] or {}).get("section_number", idx + 1),
                            "section_title": (sections[idx] or {}).get("title") or (sections[idx] or {}).get("section_title") or f"分段{idx + 1}",
                            "has_data": subdivisions_list[idx] is not None,
                            "subdivision_count": len((subdivisions_list[idx] or {}).get("subdivisions", [])) if subdivisions_list[idx] else 0
                        }
                        for idx in range(len(sections))
                    ],
                    "overlapping_pages": overlapping_pages,
                    "merge_info": merge_info,
                    "annotations": final_annotations,
                    "section_results": section_summaries,
                    "status_log": status_log
                }
                
                return {"success": True, "data": data}
        except Exception as e:
            import traceback
            error(f"[工具] 全流程批量注释失败: {e}")
            error(traceback.format_exc())
            return {"success": False, "error": f"批量注释流程失败: {str(e)}"}


# ==================== 课程和展板工具定义 ====================

# 创建课程
CREATE_COURSE_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "create_course",
        "description": "创建一个新的课程",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "课程名称"
                },
                "description": {
                    "type": "string",
                    "description": "课程描述（可选）",
                    "default": ""
                }
            },
            "required": ["name"]
        }
    }
)

# 创建展板
CREATE_BOARD_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "create_board",
        "description": "在指定课程下创建一个新的展板",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "课程ID"
                },
                "board_name": {
                    "type": "string",
                    "description": "展板名称"
                }
            },
            "required": ["course_id", "board_name"]
        }
    }
)


# ==================== 课程和展板工具处理器 ====================

class CourseToolHandlers:
    """课程和展板工具处理器"""
    
    def __init__(self, file_manager: FileSystemManager):
        self.file_manager = file_manager
    
    async def create_course(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """创建新课程"""
        try:
            name = arguments.get("name")
            description = arguments.get("description", "")
            
            if not name:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_course",
                    status=ToolStatus.ERROR,
                    error="课程名称不能为空"
                )
            
            # 调用文件管理器创建课程
            course = self.file_manager.create_course(name, description)
            
            info(f"[工具] 创建课程: {name} (ID: {course['id']})")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_course",
                status=ToolStatus.SUCCESS,
                data={
                    "course_id": course["id"],
                    "name": course["name"],
                    "description": course.get("description", ""),
                    "created_at": course.get("created_at")
                }
            )
            
        except Exception as e:
            error(f"[工具] 创建课程失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_course",
                status=ToolStatus.ERROR,
                error=f"创建课程失败: {str(e)}"
            )
    
    async def create_board(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """创建新展板"""
        try:
            course_id = arguments.get("course_id")
            board_name = arguments.get("board_name")
            
            if not course_id or not board_name:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_board",
                    status=ToolStatus.ERROR,
                    error="课程ID和展板名称不能为空"
                )
            
            # 调用文件管理器创建展板
            board = self.file_manager.create_board(course_id, board_name)
            
            info(f"[工具] 创建展板: {board_name} (ID: {board['id']}) @ {course_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_board",
                status=ToolStatus.SUCCESS,
                data={
                    "board_id": board["id"],
                    "name": board["name"],
                    "course_id": course_id,
                    "created_at": board.get("created_at")
                }
            )
            
        except Exception as e:
            error(f"[工具] 创建展板失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_board",
                status=ToolStatus.ERROR,
                error=f"创建展板失败: {str(e)}"
            )


# ==================== 工具注册函数 ====================

def register_builtin_tools(tool_registry, content_manager: ContentManager, file_manager: FileSystemManager = None, data_dir: Path = None):
    """注册所有内置工具到工具注册表"""
    
    # 窗口工具
    window_handlers = WindowToolHandlers(content_manager)
    window_tools = [
        (CREATE_WINDOW_TOOL, ToolHandler(executor=window_handlers.create_window)),
        (CREATE_WEB_WINDOW_TOOL, ToolHandler(executor=window_handlers.create_web_window)),
        (GET_WINDOWS_TOOL, ToolHandler(executor=window_handlers.get_windows)),
        (READ_WINDOW_TOOL, ToolHandler(executor=window_handlers.read_window)),
        (UPDATE_WINDOW_TOOL, ToolHandler(executor=window_handlers.update_window)),
        (UPDATE_WEB_WINDOW_TOOL, ToolHandler(executor=window_handlers.update_web_window)),
        (EDIT_WINDOW_TOOL, ToolHandler(executor=window_handlers.edit_window)),
        (DELETE_WINDOW_TOOL, ToolHandler(executor=window_handlers.delete_window)),
        (SEARCH_WINDOWS_TOOL, ToolHandler(executor=window_handlers.search_windows)),
    ]
    
    for tool_def, handler in window_tools:
        tool_registry.register_tool(tool_def, handler, category="window")
    
    info(f"✅ 已注册 {len(window_tools)} 个窗口工具")
    
    # PDF工具
    pdf_handlers = PDFToolHandlers(content_manager)
    pdf_tools = [
        (READ_PDF_TEXT_TOOL, ToolHandler(executor=pdf_handlers.read_pdf_text, timeout=120)),
        (GENERATE_PDF_ANNOTATION_TOOL, ToolHandler(executor=pdf_handlers.generate_pdf_annotation, timeout=600)),
        (GENERATE_PDF_SUMMARY_NOTE_TOOL, ToolHandler(executor=pdf_handlers.generate_pdf_summary_note, timeout=600)),
    ]
    
    for tool_def, handler in pdf_tools:
        tool_registry.register_tool(tool_def, handler, category="pdf")
    
    info(f"✅ 已注册 {len(pdf_tools)} 个PDF工具")
    
    # 课程和展板工具
    if file_manager:
        course_handlers = CourseToolHandlers(file_manager)
        course_tools = [
            (CREATE_COURSE_TOOL, ToolHandler(executor=course_handlers.create_course)),
            (CREATE_BOARD_TOOL, ToolHandler(executor=course_handlers.create_board)),
        ]
        
        for tool_def, handler in course_tools:
            tool_registry.register_tool(tool_def, handler, category="course")
        
        info(f"✅ 已注册 {len(course_tools)} 个课程工具")
    
    # 日历工具
    if data_dir:
        from .calendar_tools import register_calendar_tools
        register_calendar_tools(tool_registry, data_dir)

