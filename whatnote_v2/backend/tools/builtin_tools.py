"""
WhatNote 内置工具集
提供窗口管理、内容操作等基础功能
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus, ToolCall
from storage.content_manager import ContentManager
from storage.file_manager import FileSystemManager
from logger import info, error
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


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
                    "enum": ["text", "image", "video", "audio", "pdf", "document"],
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
            
            info(f"[工具] 读取窗口成功: {window_id} @ {board_id}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="read_window",
                status=ToolStatus.SUCCESS,
                data={
                    "window_id": window_id,
                    "title": title,
                    "type": window_type,
                    "content": content,
                    "content_length": len(content),
                    "created_at": window.get("created_at"),
                    "updated_at": window.get("updated_at")
                }
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
        (GET_WINDOWS_TOOL, ToolHandler(executor=window_handlers.get_windows)),
        (READ_WINDOW_TOOL, ToolHandler(executor=window_handlers.read_window)),
        (UPDATE_WINDOW_TOOL, ToolHandler(executor=window_handlers.update_window)),
        (EDIT_WINDOW_TOOL, ToolHandler(executor=window_handlers.edit_window)),
        (DELETE_WINDOW_TOOL, ToolHandler(executor=window_handlers.delete_window)),
        (SEARCH_WINDOWS_TOOL, ToolHandler(executor=window_handlers.search_windows)),
    ]
    
    for tool_def, handler in window_tools:
        tool_registry.register_tool(tool_def, handler, category="window")
    
    info(f"✅ 已注册 {len(window_tools)} 个窗口工具")
    
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

