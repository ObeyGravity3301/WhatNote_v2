"""
控制台命令处理器
处理用户的控制台命令，调用工具并返回格式化的结果
"""

import json
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
from .tool_registry import tool_registry
from .tool_executor import tool_executor
from .schemas import ToolCall, ToolStatus
from logger import info, error


class ConsoleHandler:
    """控制台命令处理器"""
    
    def __init__(self, file_manager=None):
        self.history: List[str] = []
        self.current_board: Optional[str] = None
        self.current_course: Optional[str] = None
        self.current_path: str = "/"  # 当前路径
        self.file_manager = file_manager  # 用于获取课程/展板信息
        
    async def handle_command(self, command: str) -> Dict[str, Any]:
        """
        处理控制台命令
        
        Args:
            command: 用户输入的命令
            
        Returns:
            响应字典，包含 type, content, data 等字段
        """
        command = command.strip()
        
        # 空命令
        if not command:
            return {"type": "empty"}
        
        # 记录历史
        self.history.append(command)
        
        # 解析命令
        parts = command.split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 命令别名
        command_aliases = {
            # 注意：course 和 board 用于创建，不设置别名
            'dir': 'ls',
            'list': 'ls',
            'tool': 'tools',
            '?': 'help',
            'cls': 'clear',
            'quit': 'exit',
            'q': 'exit',
            # 简化命令别名
            'new': 'create',
            'cat': 'read',
            'rm': 'delete',
            'find': 'search',
            'pdf': 'window',
            'pdfread': 'window',
            'view': 'window',
            'win': 'window',
            'annotate': 'generate_pdf_annotation',
            'annot': 'generate_pdf_annotation',
            'summary': 'generate_pdf_summary_note',
            'note': 'generate_pdf_summary_note'
        }
        
        # 应用别名
        if cmd in command_aliases:
            cmd = command_aliases[cmd]
        
        # 处理简化命令（位置参数风格）
        simplified_result = await self._try_simplified_command(cmd, args)
        if simplified_result:
            return simplified_result
        
        # 处理内置命令
        if cmd == "help":
            return self._handle_help(args)
        elif cmd == "tools":
            return self._handle_tools()
        elif cmd == "clear":
            return {"type": "clear"}
        elif cmd == "history":
            return self._handle_history()
        elif cmd == "use":
            return self._handle_use(args)
        elif cmd == "pwd":
            return self._handle_pwd()
        elif cmd == "courses":
            return self._handle_courses()
        elif cmd == "boards":
            return self._handle_boards()
        elif cmd == "cd":
            return self._handle_cd(args)
        elif cmd == "ls":
            return self._handle_ls()
        elif cmd == "exit":
            return {"type": "exit"}
        else:
            # 尝试作为工具调用
            return await self._handle_tool_call(command)
    
    def _handle_help(self, args: str) -> Dict[str, Any]:
        """显示帮助信息"""
        if not args:
            # 通用帮助
            lines = [
                "WhatNote Tool Console - 命令帮助",
                "=" * 60,
                "",
                "导航命令:",
                "  pwd                 - 显示当前路径",
                "  courses             - 列出所有课程",
                "  boards              - 列出当前课程的展板",
                "  ls (或 dir, list)   - 列出当前位置的内容",
                "  cd COURSE_NAME      - 进入课程",
                "  cd BOARD_NAME       - 进入展板",
                "  cd ..               - 返回上一级",
                "  cd /                - 返回根目录",
                "",
                "创建命令:",
                "  course \"名称\" [\"描述\"]  - 创建新课程",
                "  board \"名称\"             - 创建新展板(需在课程中)",
                "  create \"标题\" [\"内容\"]  - 创建窗口(需在展板中)",
                "",
                "窗口命令 (需在展板中):",
                "  ls (或 dir)         - 列出所有窗口",
                "  window \"标题或ID\" - 自动查看窗口内容（文本/PDF/其他）",
                "    ▸ 支持选项: page=2 end=3 source=llm meta raw all",
                "    ▸ 别名: pdf, pdfread, view, win",
                "  read \"标题或ID\"    - 快速读取文本窗口内容",
                "  edit \"标题\" \"内容\" - 编辑窗口(追加/替换/插入等)",
                "  delete \"标题或ID\"  - 删除窗口",
                "  search \"关键词\"    - 搜索窗口",
                "  annotate \"窗口ID\" pages=1 style=detailed  - 生成PDF注释",
                "    ▸ pages: 页码(数字/数组/all), style: detailed/simple/academic/qanda/custom",
                "    ▸ 别名: annot",
                "    ▸ 示例: annotate \"window_123\" pages=[1,2,3] style=simple",
                "    ▸ 示例: annotate \"window_123\" pages=all style=custom custom_prompt=\"请为第{page}页生成注释...\"",
                "  summary \"窗口ID\" style=detailed  - 生成PDF全文档笔记",
                "    ▸ style: detailed/concise/academic/outline/custom",
                "    ▸ 别名: note",
                "    ▸ 示例: summary \"window_123\" style=academic",
                "    ▸ 示例: summary \"window_123\" style=custom custom_prompt=\"请以XXX视角总结...\"",
                "",
                "日历命令:",
                "  task \"标题\" \"时间\" [\"日期\"]    - 添加任务(默认今日)",
                "  tasks [\"日期\"]                    - 列出任务(默认今日)",
                "  edittask <任务ID> \"标题\" [\"时间\"] [日期] - 修改任务",
                "  done <任务ID> [日期]               - 切换完成状态(默认今日)",
                "",
                "系统命令:",
                "  help (或 ?)         - 显示此帮助信息",
                "  help TOOL_NAME      - 显示工具详细说明",
                "  tools (或 tool)     - 列出所有可用工具",
                "  history             - 显示命令历史",
                "  clear (或 cls)      - 清屏",
                "  exit (或 quit, q)   - 退出控制台",
                "",
                "快速开始:",
                "  1. course \"生态学\"   -> 创建新课程",
                "  2. cd \"生态学\"       -> 进入课程",
                "  3. board \"第一章\"    -> 创建展板",
                "  4. cd \"第一章\"       -> 进入展板",
                "  5. create \"笔记\" \"# 内容\" -> 创建窗口",
                "",
                "提示: 括号中是命令别名,功能相同"
            ]
            return {
                "type": "text",
                "content": "\n".join(lines)
            }
        else:
            # 工具特定帮助
            tool_name = args.strip()
            tools = tool_registry.get_all_tools()
            tool = next((t for t in tools if t['function']['name'] == tool_name), None)
            
            if not tool:
                return {
                    "type": "error",
                    "content": f"工具不存在: {tool_name}\n使用 'tools' 查看可用工具列表"
                }
            
            func = tool['function']
            lines = [
                f"{func['name']} - {func['description']}",
                "=" * 60,
                "",
                "参数:"
            ]
            
            params = func.get('parameters', {}).get('properties', {})
            required = func.get('parameters', {}).get('required', [])
            
            for param_name, param_info in params.items():
                req_flag = "(必需)" if param_name in required else "(可选)"
                param_type = param_info.get('type', 'string')
                param_desc = param_info.get('description', '无描述')
                lines.append(f"  {param_name} {req_flag}")
                lines.append(f"    类型: {param_type}")
                lines.append(f"    说明: {param_desc}")
                
                if 'enum' in param_info:
                    lines.append(f"    可选值: {', '.join(param_info['enum'])}")
                if 'default' in param_info:
                    lines.append(f"    默认值: {param_info['default']}")
                lines.append("")
            
            # 示例 - 提供具体的示例值
            lines.append("示例:")
            
            # 为常见工具提供具体示例
            tool_examples = {
                'create_window': 'create_window board_id="board-1234567890" title="我的笔记" content="# 标题\\n内容"',
                'get_windows': 'get_windows board_id="board-1234567890"',
                'read_window': 'read_window board_id="board-1234567890" window_id="window_1234567890"',
                'update_window': 'update_window board_id="board-1234567890" window_id="window_1234567890" content="新内容" mode="append"',
                'delete_window': 'delete_window board_id="board-1234567890" window_id="window_1234567890"',
                'search_windows': 'search_windows board_id="board-1234567890" query="搜索词" limit=10',
                'read_pdf_text': 'read_pdf_text board_id="board-1234567890" window_id="window_1234567890" source="auto" page=1 end_page=2',
                'generate_pdf_annotation': 'generate_pdf_annotation board_id="board-1234567890" window_id="window_1234567890" pages=[1,2,3] style="detailed"',
                'annotate': 'annotate board_id="board-1234567890" window_id="window_1234567890" pages=all style="simple"'
            }
            
            if func['name'] in tool_examples:
                lines.append(f"  {tool_examples[func['name']]}")
            else:
                # 默认示例
                example_params = []
                for param_name in required:
                    if 'board_id' in param_name:
                        example_params.append(f'{param_name}="board-1234567890"')
                    elif 'window_id' in param_name:
                        example_params.append(f'{param_name}="window_1234567890"')
                    elif 'title' in param_name:
                        example_params.append(f'{param_name}="标题"')
                    else:
                        example_params.append(f'{param_name}="值"')
                
                example = f"  {func['name']} {' '.join(example_params)}"
                lines.append(example)
            
            lines.append("")
            lines.append("提示: 使用实际的 board_id 和 window_id 替换示例中的值")
            
            return {
                "type": "text",
                "content": "\n".join(lines)
            }
    
    def _handle_tools(self) -> Dict[str, Any]:
        """列出所有工具"""
        tools = tool_registry.get_all_tools()
        
        lines = [
            f"可用工具 (共 {len(tools)} 个):",
            "=" * 60,
            ""
        ]
        
        for i, tool in enumerate(tools, 1):
            func = tool['function']
            lines.append(f"{i:2d}. {func['name']}")
            lines.append(f"    {func['description']}")
            lines.append("")
        
        lines.append("使用 'help TOOL_NAME' 查看工具详细说明（例如: help get_windows）")
        
        return {
            "type": "text",
            "content": "\n".join(lines)
        }
    
    def _handle_history(self) -> Dict[str, Any]:
        """显示命令历史"""
        if not self.history:
            return {
                "type": "text",
                "content": "暂无命令历史"
            }
        
        lines = [
            "命令历史:",
            "=" * 60,
            ""
        ]
        
        for i, cmd in enumerate(self.history[-20:], 1):  # 最近20条
            lines.append(f"{i:2d}. {cmd}")
        
        return {
            "type": "text",
            "content": "\n".join(lines)
        }
    
    def _handle_use(self, board_id: str) -> Dict[str, Any]:
        """切换当前展板"""
        board_id = board_id.strip().strip('"\'')
        
        if not board_id:
            if self.current_board:
                return {
                    "type": "text",
                    "content": f"当前展板: {self.current_board}"
                }
            else:
                return {
                    "type": "text",
                    "content": "未设置当前展板\n使用 'use <board_id>' 设置"
                }
        
        self.current_board = board_id
        return {
            "type": "success",
            "content": f"已切换到展板: {board_id}"
        }
    
    def _handle_pwd(self) -> Dict[str, Any]:
        """显示当前路径"""
        path_parts = ["/"]
        
        if self.current_course:
            # 获取课程名称
            if self.file_manager:
                courses = self.file_manager.get_courses()
                course = next((c for c in courses if c['id'] == self.current_course), None)
                if course:
                    path_parts.append(course['name'])
                else:
                    path_parts.append(f"[{self.current_course}]")
            else:
                path_parts.append(f"[{self.current_course}]")
        
        if self.current_board:
            # 获取展板名称
            if self.file_manager and self.current_course:
                boards = self.file_manager.get_boards(self.current_course)
                board = next((b for b in boards if b['id'] == self.current_board), None)
                if board:
                    path_parts.append(board['name'])
                else:
                    path_parts.append(f"[{self.current_board}]")
            else:
                path_parts.append(f"[{self.current_board}]")
        
        path = "/".join(path_parts) if len(path_parts) > 1 else "/"
        
        return {
            "type": "text",
            "content": f"当前路径: {path}"
        }
    
    def _handle_courses(self) -> Dict[str, Any]:
        """列出所有课程"""
        if not self.file_manager:
            return {
                "type": "error",
                "content": "文件管理器未初始化"
            }
        
        try:
            courses = self.file_manager.get_courses()
            
            if not courses:
                return {
                    "type": "text",
                    "content": "暂无课程\n提示: 在前端界面创建课程"
                }
            
            lines = [
                f"课程列表 (共 {len(courses)} 个):",
                "=" * 60,
                ""
            ]
            
            for i, course in enumerate(courses, 1):
                name = course.get('name', '无标题')
                course_id = course.get('id', '')
                desc = course.get('description', '')
                
                lines.append(f"{i:2d}. {name}")
                if desc:
                    lines.append(f"    描述: {desc}")
                lines.append(f"    ID: {course_id}")
                lines.append("")
            
            lines.append("使用 'cd \"课程名\"' 进入课程")
            
            return {
                "type": "text",
                "content": "\n".join(lines)
            }
        except Exception as e:
            error(f"获取课程列表失败: {e}")
            return {
                "type": "error",
                "content": f"获取课程列表失败: {str(e)}"
            }
    
    def _handle_boards(self) -> Dict[str, Any]:
        """列出当前课程的展板"""
        if not self.file_manager:
            return {
                "type": "error",
                "content": "文件管理器未初始化"
            }
        
        if not self.current_course:
            return {
                "type": "error",
                "content": "请先进入课程\n提示: 使用 'courses' 查看课程列表, 使用 'cd \"课程名\"' 进入"
            }
        
        try:
            boards = self.file_manager.get_boards(self.current_course)
            
            if not boards:
                return {
                    "type": "text",
                    "content": "当前课程暂无展板\n提示: 在前端界面创建展板"
                }
            
            lines = [
                f"展板列表 (共 {len(boards)} 个):",
                "=" * 60,
                ""
            ]
            
            for i, board in enumerate(boards, 1):
                name = board.get('name', '无标题')
                board_id = board.get('id', '')
                
                current_marker = " <- 当前" if board_id == self.current_board else ""
                lines.append(f"{i:2d}. {name}{current_marker}")
                lines.append(f"    ID: {board_id}")
                lines.append("")
            
            lines.append("使用 'cd \"展板名\"' 进入展板")
            
            return {
                "type": "text",
                "content": "\n".join(lines)
            }
        except Exception as e:
            error(f"获取展板列表失败: {e}")
            return {
                "type": "error",
                "content": f"获取展板列表失败: {str(e)}"
            }
    
    def _handle_cd(self, args: str) -> Dict[str, Any]:
        """切换目录"""
        target = args.strip().strip('"\'')
        
        if not target:
            return {
                "type": "error",
                "content": "用法: cd DIRECTORY\n示例: cd \"高等数学\" 或 cd \"高等数学/第一章\" 或 cd .. 或 cd /"
            }
        
        # 返回根目录
        if target == "/":
            self.current_course = None
            self.current_board = None
            return {
                "type": "success",
                "content": "已返回根目录"
            }
        
        # 返回上一级
        if target == "..":
            if self.current_board:
                self.current_board = None
                return {
                    "type": "success",
                    "content": "已返回课程目录"
                }
            elif self.current_course:
                self.current_course = None
                return {
                    "type": "success",
                    "content": "已返回根目录"
                }
            else:
                return {
                    "type": "text",
                    "content": "已在根目录"
                }
        
        # 进入目录
        if not self.file_manager:
            return {
                "type": "error",
                "content": "文件管理器未初始化"
            }
        
        try:
            # 检查是否是路径形式 (课程/展板)
            if "/" in target:
                parts = [p.strip() for p in target.split("/") if p.strip()]
                
                if len(parts) == 2:
                    course_name, board_name = parts
                    
                    # 先找课程
                    courses = self.file_manager.get_courses()
                    course = next((c for c in courses if c['name'] == course_name or c['id'] == course_name), None)
                    
                    if not course:
                        return {
                            "type": "error",
                            "content": f"课程不存在: {course_name}\n使用 'courses' 查看可用课程"
                        }
                    
                    # 再找展板
                    boards = self.file_manager.get_boards(course['id'])
                    board = next((b for b in boards if b['name'] == board_name or b['id'] == board_name), None)
                    
                    if not board:
                        return {
                            "type": "error",
                            "content": f"展板不存在: {board_name}\n使用 'boards' 查看可用展板"
                        }
                    
                    # 设置当前课程和展板
                    self.current_course = course['id']
                    self.current_board = board['id']
                    
                    return {
                        "type": "success",
                        "content": f"已进入展板: {course['name']}/{board['name']}\n现在可以使用窗口工具了",
                        "action": {
                            "type": "switch_board",
                            "course_id": course['id'],
                            "board_id": board['id']
                        }
                    }
                else:
                    return {
                        "type": "error",
                        "content": "路径格式错误\n示例: cd \"课程名/展板名\""
                    }
            
            # 单层导航
            # 如果在根目录，尝试进入课程
            if not self.current_course:
                courses = self.file_manager.get_courses()
                course = next((c for c in courses if c['name'] == target or c['id'] == target), None)
                
                if course:
                    self.current_course = course['id']
                    return {
                        "type": "success",
                        "content": f"已进入课程: {course['name']}\n使用 'boards' 查看展板列表",
                        "action": {
                            "type": "switch_course",
                            "course_id": course['id']
                        }
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"课程不存在: {target}\n使用 'courses' 查看可用课程"
                    }
            
            # 如果在课程目录，尝试进入展板
            elif self.current_course and not self.current_board:
                boards = self.file_manager.get_boards(self.current_course)
                board = next((b for b in boards if b['name'] == target or b['id'] == target), None)
                
                if board:
                    self.current_board = board['id']
                    return {
                        "type": "success",
                        "content": f"已进入展板: {board['name']}\n现在可以使用窗口工具了",
                        "action": {
                            "type": "switch_board",
                            "course_id": self.current_course,
                            "board_id": board['id']
                        }
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"展板不存在: {target}\n使用 'boards' 查看可用展板"
                    }
            
            # 已在展板中
            else:
                return {
                    "type": "error",
                    "content": "已在展板中\n使用 'cd ..' 返回上一级"
                }
                
        except Exception as e:
            error(f"切换目录失败: {e}")
            return {
                "type": "error",
                "content": f"切换目录失败: {str(e)}"
            }
    
    def _handle_ls(self) -> Dict[str, Any]:
        """列出当前位置内容"""
        # 在根目录，列出课程
        if not self.current_course:
            return self._handle_courses()
        
        # 在课程中，列出展板
        elif not self.current_board:
            return self._handle_boards()
        
        # 在展板中，列出窗口（调用 get_windows 工具）
        else:
            return {
                "type": "text",
                "content": "已在展板中\n使用 'get_windows' 查看窗口列表"
            }
    
    async def _handle_tool_call(self, command: str) -> Dict[str, Any]:
        """处理工具调用"""
        try:
            # 解析命令: tool_name param1="value1" param2="value2"
            parts = command.split(None, 1)
            tool_name = parts[0]
            args_str = parts[1] if len(parts) > 1 else ""
            
            # 检查工具是否存在
            tools = tool_registry.get_all_tools()
            tool = next((t for t in tools if t['function']['name'] == tool_name), None)
            
            if not tool:
                # 提供智能建议
                suggestions = []
                
                # 检查是否是常见的拼写错误
                similar_commands = {
                    'course': 'courses',
                    'board': 'boards',
                    'tool': 'tools',
                    'window': 'get_windows',
                    'pdf': 'window',
                    'pdfread': 'window',
                    'create': 'create_window',
                    'delete': 'delete_window',
                    'search': 'search_windows',
                    'read': 'read_window',
                    'update': 'update_window',
                    'annotate': 'generate_pdf_annotation',
                    'annot': 'generate_pdf_annotation'
                }
                
                if tool_name in similar_commands:
                    suggestions.append(f"你是否想输入: {similar_commands[tool_name]}")
                
                # 检查是否是工具名的一部分
                for t in tools:
                    t_name = t['function']['name']
                    if tool_name in t_name or t_name in tool_name:
                        suggestions.append(f"相似工具: {t_name}")
                
                error_msg = f"未知命令或工具: {tool_name}\n"
                if suggestions:
                    error_msg += "\n".join(suggestions) + "\n"
                error_msg += "\n使用 'help' 查看所有命令\n使用 'tools' 查看所有工具"
                
                return {
                    "type": "error",
                    "content": error_msg
                }
            
            # 解析参数
            arguments = self._parse_arguments(args_str)
            
            # 如果设置了当前展板且参数中没有 board_id，自动填充
            if self.current_board and 'board_id' not in arguments:
                params = tool['function'].get('parameters', {}).get('properties', {})
                if 'board_id' in params:
                    arguments['board_id'] = self.current_board
            
            # 构建工具调用
            tool_call = ToolCall(
                id=f"console_{int(datetime.now().timestamp() * 1000)}",
                type="function",
                function={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            
            # 执行工具
            info(f"[控制台] 执行工具: {tool_name} {arguments}")
            result = await tool_executor.execute_tool_call(tool_call, context={})
            
            # 格式化输出
            if result.status == ToolStatus.SUCCESS:
                # 为不同工具提供定制化输出格式
                if tool_name == "create_window":
                    data = result.data or {}
                    lines = [
                        f"成功创建窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        f"标题: {data.get('title', 'N/A')}",
                        f"类型: {data.get('type', 'N/A')}",
                        "",
                        "提示: 使用 'read_window window_id=\"...\"' 查看窗口内容"
                    ]
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                elif tool_name == "get_windows":
                    data = result.data or {}
                    windows = data.get('windows', [])
                    lines = [
                        f"窗口列表 (共 {data.get('count', 0)} 个)",
                        "=" * 60,
                        ""
                    ]
                    
                    for i, w in enumerate(windows, 1):
                        lines.append(f"{i:2d}. {w.get('title', '无标题')} [{w.get('type', 'text')}]")
                        lines.append(f"    ID: {w.get('id', 'N/A')}")
                        lines.append(f"    创建: {w.get('created_at', 'N/A')}")
                        if w.get('updated_at') != w.get('created_at'):
                            lines.append(f"    更新: {w.get('updated_at', 'N/A')}")
                        lines.append("")
                    
                    if not windows:
                        lines.append("当前展板没有窗口")
                        lines.append("使用 'create_window title=\"标题\" content=\"内容\"' 创建新窗口")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data
                    }
                
                elif tool_name == "read_window":
                    data = result.data or {}
                    content = data.get('content', '')
                    lines = [
                        f"窗口内容",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        f"标题: {data.get('title', 'N/A')}",
                        f"类型: {data.get('type', 'N/A')}",
                        f"内容长度: {data.get('content_length', 0)} 字符",
                        f"创建时间: {data.get('created_at', 'N/A')}",
                        f"更新时间: {data.get('updated_at', 'N/A')}",
                        "",
                        "内容:",
                        "-" * 60
                    ]
                    
                    # 限制显示内容长度（控制台显示）
                    if len(content) > 500:
                        lines.append(content[:500])
                        lines.append("")
                        lines.append(f"... (还有 {len(content) - 500} 个字符)")
                        lines.append("提示: 完整内容请在前端窗口查看")
                    else:
                        lines.append(content if content else "(空内容)")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data
                    }
                
                elif tool_name == "update_window":
                    data = result.data or {}
                    lines = [
                        f"成功更新窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        f"更新模式: {data.get('mode', 'N/A')}",
                        f"新内容长度: {data.get('content_length', 0)} 字符",
                        "",
                        "提示: 使用 'read_window' 查看更新后的内容"
                    ]
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                elif tool_name == "edit_window":
                    data = result.data or {}
                    lines = [
                        f"成功编辑窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        f"操作: {data.get('operation', 'N/A')}",
                        f"结果: {data.get('operation_desc', 'N/A')}",
                        "",
                        f"原内容长度: {data.get('old_length', 0)} 字符",
                        f"新内容长度: {data.get('new_length', 0)} 字符",
                        f"变化: {data.get('new_length', 0) - data.get('old_length', 0):+d} 字符",
                        "",
                        "提示: 使用 'read_window' 查看编辑后的内容"
                    ]
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                elif tool_name == "delete_window":
                    data = result.data or {}
                    lines = [
                        f"成功删除窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        "",
                        "窗口已移至回收站"
                    ]
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                elif tool_name == "search_windows":
                    data = result.data or {}
                    windows = data.get('windows', [])
                    lines = [
                        f"搜索结果 (共 {data.get('count', 0)} 个)",
                        "=" * 60,
                        f"关键词: {data.get('query', 'N/A')}",
                        ""
                    ]
                    
                    for i, w in enumerate(windows, 1):
                        lines.append(f"{i:2d}. {w.get('title', '无标题')}")
                        lines.append(f"    ID: {w.get('id', 'N/A')}")
                        if w.get('matched_in'):
                            lines.append(f"    匹配位置: {', '.join(w['matched_in'])}")
                        lines.append("")
                    
                    if not windows:
                        lines.append("未找到匹配的窗口")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data
                    }
                
                elif tool_name == "read_pdf_text":
                    data = result.data or {}
                    lines = [
                        "PDF内容读取成功",
                        "=" * 60,
                        ""
                    ]
                    
                    if data.get('mode') == 'single':
                        lines.append(f"页码: {data.get('start_page', 'N/A')}")
                        lines.append(f"来源: {', '.join(data.get('sources_used', []))}")
                        lines.append("")
                        lines.append("内容:")
                        lines.append("-" * 60)
                        content = data.get('content', '')
                        if len(content) > 1000:
                            lines.append(content[:1000] + f"\n\n... (内容已截断，总长度: {len(content)} 字符)")
                        else:
                            lines.append(content)
                    elif data.get('mode') == 'range':
                        lines.append(f"页码范围: {data.get('start_page', 'N/A')} - {data.get('end_page', 'N/A')}")
                        lines.append(f"来源: {', '.join(data.get('sources_used', []))}")
                        lines.append("")
                        lines.append("内容:")
                        lines.append("-" * 60)
                        content = data.get('content', '')
                        if len(content) > 2000:
                            lines.append(content[:2000] + f"\n\n... (内容已截断，总长度: {len(content)} 字符)")
                        else:
                            lines.append(content)
                    else:
                        lines.append(json.dumps(data, indent=2, ensure_ascii=False))
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data
                    }
                
                elif tool_name == "generate_pdf_annotation":
                    data = result.data or {}
                    lines = [
                        "PDF注释生成完成",
                        "=" * 60,
                        ""
                    ]
                    
                    total = data.get('total_pages', 0)
                    completed = data.get('completed', 0)
                    style = data.get('style', 'detailed')
                    results = data.get('results', [])
                    
                    lines.append(f"注释风格: {style}")
                    lines.append(f"总页数: {total}")
                    lines.append(f"已完成: {completed}")
                    lines.append("")
                    
                    if results:
                        lines.append("生成结果:")
                        lines.append("-" * 60)
                        for r in results[:10]:  # 只显示前10页
                            page = r.get('page', 'N/A')
                            status = r.get('status', 'unknown')
                            annotation = r.get('annotation', '')
                            if annotation:
                                preview = annotation[:200] + "..." if len(annotation) > 200 else annotation
                                lines.append(f"第{page}页 ({status}):")
                                lines.append(f"  {preview}")
                                lines.append("")
                        
                        if len(results) > 10:
                            lines.append(f"... 还有 {len(results) - 10} 页注释已生成")
                    
                    lines.append("")
                    lines.append("提示: 在PDF窗口中查看生成的注释")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                elif tool_name == "generate_pdf_summary_note":
                    data = result.data or {}
                    lines = [
                        "全文档笔记生成完成",
                        "=" * 60,
                        ""
                    ]
                    
                    message = data.get('message', '')
                    saved_path = data.get('saved_path', '')
                    content = data.get('note_content', '')
                    
                    lines.append(message)
                    if saved_path:
                        lines.append(f"保存路径: {saved_path}")
                    lines.append("")
                    
                    if content:
                        lines.append("笔记预览:")
                        lines.append("-" * 60)
                        preview = content[:500] + "..." if len(content) > 500 else content
                        lines.append(preview)
                        if len(content) > 500:
                            lines.append(f"\n... (还有 {len(content) - 500} 个字符)")
                    
                    lines.append("")
                    lines.append("提示: 请在前端大纲侧栏查看完整笔记")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data,
                        "action": {
                            "type": "refresh_board"
                        }
                    }
                
                # 默认格式（JSON）
                else:
                    lines = [
                        f"执行成功: {tool_name}",
                        "-" * 60,
                        ""
                    ]
                    
                    if result.data:
                        lines.append(json.dumps(result.data, indent=2, ensure_ascii=False))
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "data": result.data
                    }
            else:
                return {
                    "type": "error",
                    "content": f"执行失败: {result.error}"
                }
                
        except Exception as e:
            error(f"[控制台] 命令执行错误: {e}")
            return {
                "type": "error",
                "content": f"命令执行错误: {str(e)}\n{traceback.format_exc()}"
            }
    
    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """
        解析参数字符串
        支持格式: param1="value1" param2=123 param3=true param4=[1,2,3] param5="all"
        """
        arguments = {}
        
        if not args_str.strip():
            return arguments
        
        # 简单的参数解析（支持引号包裹的值和数组）
        import re
        import json
        
        # 先处理数组格式 [1,2,3] 或 ["a","b"]
        array_pattern = r'(\w+)=\[([^\]]+)\]'
        array_matches = re.findall(array_pattern, args_str)
        for key, array_content in array_matches:
            try:
                # 尝试解析为JSON数组
                array_value = json.loads(f"[{array_content}]")
                arguments[key] = array_value
                # 从原始字符串中移除已处理的数组
                args_str = re.sub(rf'{re.escape(key)}=\[[^\]]+\]', '', args_str)
            except:
                # 如果JSON解析失败，尝试按逗号分割
                try:
                    array_value = [int(x.strip()) if x.strip().isdigit() else x.strip().strip('"\'') 
                                 for x in array_content.split(',')]
                    arguments[key] = array_value
                    args_str = re.sub(rf'{re.escape(key)}=\[[^\]]+\]', '', args_str)
                except:
                    pass
        
        # 匹配 key="value" 或 key=value
        pattern = r'(\w+)=(?:"((?:\\.|[^"])*)"|\'((?:\\.|[^\'])*)\'|([^\s]+))'
        matches = re.findall(pattern, args_str)
        
        for match in matches:
            key = match[0]
            value = match[1] or match[2] or match[3]
            
            # 跳过已处理的数组参数
            if key in arguments:
                continue
            
            # 处理转义字符（将 \n, \t 等转换为实际的换行、制表符）
            if isinstance(value, str):
                # 处理常见的转义字符
                value = value.replace('\\n', '\n')  # 换行
                value = value.replace('\\t', '\t')  # 制表符
                value = value.replace('\\r', '\r')  # 回车
                value = value.replace('\\\\', '\\')  # 反斜杠本身
                value = value.replace('\\"', '"')   # 引号
                value = value.replace("\\'", "'")   # 单引号
            
            # 尝试转换类型
            if value.lower() == 'true':
                arguments[key] = True
            elif value.lower() == 'false':
                arguments[key] = False
            elif value.lower() == 'all':
                arguments[key] = 'all'  # 特殊值，保持字符串
            elif value.isdigit():
                arguments[key] = int(value)
            else:
                try:
                    arguments[key] = float(value)
                except ValueError:
                    arguments[key] = value
        
        return arguments
    
    def _resolve_window_id(self, identifier: str) -> Optional[str]:
        """
        解析窗口标识符（可以是窗口ID或标题）
        返回实际的窗口ID，如果找不到返回 None
        """
        if not self.current_board:
            return None
        
        # 如果已经是 window_xxx 格式，直接返回
        if identifier.startswith('window_'):
            return identifier
        
        # 否则尝试通过标题查找
        try:
            from storage.content_manager import ContentManager
            from storage.file_manager import FileSystemManager
            from config import DATA_DIR
            
            file_manager = FileSystemManager(DATA_DIR)
            content_manager = ContentManager(file_manager)
            
            windows = content_manager.get_board_windows(self.current_board)
            
            # 精确匹配标题
            for window in windows:
                if window.get('title') == identifier:
                    return window.get('id')
            
            # 如果精确匹配失败，尝试部分匹配（不区分大小写）
            identifier_lower = identifier.lower()
            for window in windows:
                if identifier_lower in window.get('title', '').lower():
                    return window.get('id')
            
            return None
        except Exception as e:
            error(f"解析窗口标识符失败: {e}")
            return None
    
    def _get_window_data(self, window_id: str) -> Optional[Dict[str, Any]]:
        """获取当前展板指定窗口的完整数据"""
        if not self.current_board:
            return None
        
        try:
            from storage.content_manager import ContentManager
            from storage.file_manager import FileSystemManager
            from config import DATA_DIR
            
            file_manager = FileSystemManager(DATA_DIR)
            content_manager = ContentManager(file_manager)
            
            windows = content_manager.get_board_windows(self.current_board)
            for window in windows:
                if window.get('id') == window_id:
                    return window
        except Exception as e:
            error(f"获取窗口数据失败: {e}")
        
        return None
    
    def _parse_positive_int(self, value: str) -> Optional[int]:
        """解析正整数，失败时返回 None"""
        try:
            number = int(value)
            return number if number > 0 else None
        except ValueError:
            return None
    
    def _parse_window_view_options(self, tokens: List[str]) -> Dict[str, Any]:
        """
        解析 window 命令的可选参数
        返回包含解析结果或错误信息的字典
        """
        options = {
            "source": "auto",
            "page": None,
            "end_page": None,
            "all": False,
            "meta": False,
            "raw": False,
            "explicit_page": False,
            "error": None
        }
        
        for token in tokens:
            lower = token.lower()
            
            if lower in {"meta", "info"}:
                options["meta"] = True
                continue
            if lower == "raw":
                options["raw"] = True
                continue
            if lower in {"all", "full"}:
                options["all"] = True
                continue
            if lower.startswith("source="):
                value = lower.split("=", 1)[1] or "auto"
                options["source"] = value
                continue
            if lower in {"auto", "pypdf", "llm"}:
                options["source"] = lower
                continue
            if lower.startswith("page="):
                parsed = self._parse_positive_int(lower.split("=", 1)[1])
                if parsed is None:
                    options["error"] = f"页码无效: {token}"
                    return options
                options["page"] = parsed
                options["explicit_page"] = True
                continue
            if lower.startswith("end_page=") or lower.startswith("end="):
                parsed = self._parse_positive_int(lower.split("=", 1)[1])
                if parsed is None:
                    options["error"] = f"结束页无效: {token}"
                    return options
                options["end_page"] = parsed
                options["explicit_page"] = True
                continue
            
            parsed = self._parse_positive_int(lower)
            if parsed is not None:
                if options["page"] is None:
                    options["page"] = parsed
                    options["explicit_page"] = True
                    continue
                if options["end_page"] is None:
                    options["end_page"] = parsed
                    options["explicit_page"] = True
                    continue
            
            options["error"] = f"无法识别的参数: {token}"
            return options
        
        return options
    
    def _format_window_metadata(self, window_data: Dict[str, Any]) -> List[str]:
        """格式化窗口通用元数据"""
        lines = [
            f"窗口ID: {window_data.get('id', 'N/A')}",
            f"标题: {window_data.get('title', 'N/A')}",
            f"类型: {window_data.get('type', 'N/A')}",
            f"创建时间: {window_data.get('created_at', '未知')}",
            f"更新时间: {window_data.get('updated_at', '未知')}",
        ]
        
        file_path = window_data.get('file_path')
        if file_path:
            lines.append(f"文件路径: {file_path}")
        content = window_data.get('content')
        if isinstance(content, str) and content and window_data.get('type') != 'text':
            lines.append(f"内容字段: {content}")
        
        return lines
    
    def _format_text_window_output(self, window_data: Dict[str, Any], content: str, raw: bool = False, include_meta: bool = False) -> str:
        """格式化文本窗口的输出"""
        lines = [
            "窗口内容",
            "=" * 60,
            ""
        ]
        
        if include_meta:
            lines.extend(self._format_window_metadata(window_data))
            lines.append("")
        
        content_length = len(content)
        lines.append(f"内容长度: {content_length} 字符")
        lines.append("")
        lines.append("内容预览:")
        lines.append("-" * 60)
        
        if not content:
            lines.append("(空内容)")
        else:
            preview_limit = None if raw else 800
            if preview_limit and content_length > preview_limit:
                lines.append(content[:preview_limit])
                lines.append("")
                lines.append(f"... (还有 {content_length - preview_limit} 个字符)")
            else:
                lines.append(content)
        
        return "\n".join(lines)
    
    def _format_pdf_output(
        self,
        window_id: str,
        window_title: str,
        source: str,
        options: Dict[str, Any],
        result: Dict[str, Any]
    ) -> str:
        """格式化 PDF 窗口的输出"""
        pages = result.get("pages", [])
        sources_used = result.get("sources_used", [])
        combined_text = result.get("combined_text")
        partial_errors = result.get("partial_errors", [])
        
        lines = [
            "PDF内容预览",
            "=" * 60,
            "",
            f"窗口ID: {window_id}",
            f"标题: {window_title}",
            f"请求来源: {source}",
            f"实际来源: {', '.join(sources_used) if sources_used else 'N/A'}",
            f"页码范围: 第 {result.get('start_page')} - 第 {result.get('end_page')} 页 (模式: {result.get('mode')})",
            f"PDF总页数: {result.get('total_pages', '未知')}",
        ]
        
        if options.get("meta"):
            window_data = result.get("window_data")
            if isinstance(window_data, dict):
                lines.append("")
                lines.append("窗口信息:")
                lines.append("-" * 60)
                lines.extend(self._format_window_metadata(window_data))
        
        if options.get("all") and combined_text:
            preview = combined_text if len(combined_text) <= 800 else combined_text[:800] + f"... (剩余 {len(combined_text) - 800} 字符)"
            lines.extend([
                "",
                "合并文本预览:",
                "-" * 60,
                preview
            ])
        
        for page_info in pages:
            page_num = page_info.get("page")
            page_source = page_info.get("source", "未知")
            content_type = page_info.get("content_type", "text")
            heading = page_info.get("heading")
            metadata = page_info.get("metadata", [])
            content = page_info.get("content")
            
            lines.extend([
                "",
                f"- 第 {page_num} 页 | 来源: {page_source} | 类型: {content_type}"
            ])
            
            if heading:
                lines.append(f"  标题: {heading}")
            for meta in metadata:
                lines.append(f"  {meta}")
            
            if isinstance(content, dict):
                content_str = json.dumps(content, ensure_ascii=False, indent=2)
            else:
                content_str = str(content or "")
            
            if content_str:
                preview_text = content_str
                preview_limit = None if options.get("raw") else 800
                if preview_limit and len(content_str) > preview_limit:
                    preview_text = content_str[:preview_limit] + f"... (剩余 {len(content_str) - preview_limit} 字符)"
                
                lines.append("  内容预览:")
                for line in preview_text.splitlines():
                    lines.append(f"    {line}")
            else:
                lines.append("  内容为空")
        
        if partial_errors:
            lines.extend([
                "",
                "[Warning] 部分页面出现错误:",
                "-" * 60
            ])
            lines.extend([f"- {err}" for err in partial_errors])
        
        lines.append("")
        lines.append("提示: 使用 'window <ID> page=2 source=llm' 可读取其他页面或来源")
        
        return "\n".join(lines)
    
    async def _handle_window_text(self, window_id: str, window_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本窗口查看"""
        tool_call = ToolCall(
            id=f"console_{int(datetime.now().timestamp() * 1000)}",
            type="function",
            function={
                "name": "read_window",
                "arguments": {
                    "board_id": self.current_board,
                    "window_id": window_id
                }
            }
        )
        
        result = await tool_executor.execute_tool_call(tool_call, context={})
        if result.status != ToolStatus.SUCCESS:
            return {
                "type": "error",
                "content": f"读取窗口失败: {result.error}"
            }
        
        data = result.data or {}
        content = data.get("content", "")
        output = self._format_text_window_output(window_data or data, content, raw=options.get("raw", False), include_meta=options.get("meta", False))
        return {
            "type": "success",
            "content": output
        }
    
    async def _handle_window_pdf(self, window_id: str, window_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """处理 PDF 窗口查看"""
        source = options.get("source", "auto").lower()
        if source not in {"auto", "pypdf", "llm"}:
            return {
                "type": "error",
                "content": f"来源无效: {source}\n可选: auto, pypdf, llm"
            }
        
        page = options.get("page")
        end_page = options.get("end_page")
        
        if not options.get("explicit_page") and not options.get("all"):
            page = page or 1
            end_page = end_page or page
        elif options.get("explicit_page") and page and end_page and end_page < page:
            page, end_page = end_page, page
        
        tool_args = {
            "board_id": self.current_board,
            "window_id": window_id,
            "source": source
        }
        
        if options.get("all"):
            pass  # 不指定页码，获取整本
        else:
            if page:
                tool_args["page"] = page
            if end_page:
                tool_args["end_page"] = end_page
        
        tool_call = ToolCall(
            id=f"console_{int(datetime.now().timestamp() * 1000)}",
            type="function",
            function={
                "name": "read_pdf_text",
                "arguments": tool_args
            }
        )
        
        result = await tool_executor.execute_tool_call(tool_call, context={})
        if result.status != ToolStatus.SUCCESS:
            return {
                "type": "error",
                "content": f"读取PDF失败: {result.error}"
            }
        
        data = result.data or {}
        data["window_data"] = window_data
        output = self._format_pdf_output(window_id, window_data.get("title", window_id), source, options, data)
        return {
            "type": "success",
            "content": output
        }
    
    def _handle_window_other(self, window_id: str, window_data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """处理非文本/非PDF窗口查看"""
        lines = [
            "窗口信息",
            "=" * 60,
            ""
        ]
        lines.extend(self._format_window_metadata(window_data))
        
        window_type = window_data.get("type", "unknown")
        content = window_data.get("content", "")
        lines.append("")
        lines.append(f"当前暂未支持直接预览 {window_type} 类型的窗口内容。")
        if content:
            lines.append(f"相关资源: {content}")
        lines.append("请在前端界面查看该窗口，或等待后续指令扩展。")
        
        return {
            "type": "info",
            "content": "\n".join(lines)
        }
    
    async def _try_simplified_command(self, cmd: str, args: str) -> Optional[Dict[str, Any]]:
        """
        尝试解析简化命令格式（位置参数）
        返回 None 表示不是简化命令，应该继续尝试其他解析方式
        """
        import re
        import shlex
        
        # 定义简化命令的格式
        
        # course "课程名" ["描述"]  - 创建新课程
        if cmd == "course":
            try:
                parts = shlex.split(args)
                if len(parts) < 1:
                    return {
                        "type": "error",
                        "content": "用法: course \"课程名\" [\"描述\"]\n示例: course \"生态学\" \"生态学基础课程\""
                    }
                
                name = parts[0]
                description = parts[1] if len(parts) > 1 else ""
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "create_course",
                        "arguments": {
                            "name": name,
                            "description": description
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    course_id = data.get('course_id', '')
                    
                    return {
                        "type": "success",
                        "content": f"成功创建课程\n"
                                   f"{'=' * 60}\n\n"
                                   f"课程名: {name}\n"
                                   f"课程ID: {course_id}\n"
                                   f"描述: {description if description else '(无)'}\n\n"
                                   f"提示: 使用 'cd \"{name}\"' 进入课程",
                        "action": {"type": "refresh_courses"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"创建课程失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 使用引号包裹包含空格的参数"
                }
        
        # board "展板名"  - 在当前课程下创建展板
        elif cmd == "board":
            if not self.current_course:
                return {
                    "type": "error",
                    "content": "请先进入课程\n提示: 使用 'cd' 命令进入课程"
                }
            
            try:
                parts = shlex.split(args)
                if len(parts) < 1:
                    return {
                        "type": "error",
                        "content": "用法: board \"展板名\"\n示例: board \"第一章\""
                    }
                
                board_name = parts[0]
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "create_board",
                        "arguments": {
                            "course_id": self.current_course,
                            "board_name": board_name
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    board_id = data.get('board_id', '')
                    
                    return {
                        "type": "success",
                        "content": f"成功创建展板\n"
                                   f"{'=' * 60}\n\n"
                                   f"展板名: {board_name}\n"
                                   f"展板ID: {board_id}\n"
                                   f"所属课程: {self.current_course}\n\n"
                                   f"提示: 使用 'cd \"{board_name}\"' 进入展板",
                        "action": {"type": "refresh_boards", "course_id": self.current_course}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"创建展板失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 使用引号包裹包含空格的参数"
                }
        
        # create "标题" "内容"
        elif cmd == "create":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板\n提示: 使用 'cd' 命令进入展板"
                }
            
            try:
                # 使用 shlex 解析带引号的参数
                parts = shlex.split(args)
                if len(parts) < 1:
                    return {
                        "type": "error",
                        "content": "用法: create \"标题\" [\"内容\"]\n示例: create \"我的笔记\" \"# 标题\\n\\n内容\""
                    }
                
                title = parts[0]
                content = parts[1] if len(parts) > 1 else ""
                
                # 处理转义字符
                content = content.replace('\\n', '\n').replace('\\t', '\t')
                
                # 构造工具调用
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "create_window",
                        "arguments": {
                            "board_id": self.current_board,
                            "title": title,
                            "content": content
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    lines = [
                        f"成功创建窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {data.get('window_id', 'N/A')}",
                        f"标题: {data.get('title', 'N/A')}",
                        "",
                        "提示: 使用 'read {窗口ID}' 查看内容"
                    ]
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "action": {"type": "refresh_board"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"创建失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 使用引号包裹包含空格的参数"
                }
        
        # window <窗口ID或标题> [参数]
        elif cmd == "window":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板"
                }
            
            import shlex
            try:
                parts = shlex.split(args)
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 使用引号包裹包含空格的参数"
                }
            
            if not parts:
                usage = [
                    "用法: window <窗口ID或标题> [选项]",
                    "示例:",
                    "  window window_1234567890",
                    "  window \"课程讲义\" page=2 source=llm",
                    "  window \"课程讲义\" all",
                    "",
                    "可选参数:",
                    "  page=<数字>      指定起始页（适用于PDF）",
                    "  end=<数字>       指定结束页（适用于PDF）",
                    "  source=auto|pypdf|llm  指定PDF读取来源",
                    "  all               读取整个PDF（可能较长）",
                    "  meta / info       显示窗口元信息",
                    "  raw               取消内容截断，输出完整内容"
                ]
                return {
                    "type": "error",
                    "content": "\n".join(usage)
                }
            
            identifier = parts[0]
            options = self._parse_window_view_options(parts[1:])
            if options.get("error"):
                return {
                    "type": "error",
                    "content": options["error"]
                }
            
            window_id = self._resolve_window_id(identifier)
            if not window_id:
                return {
                    "type": "error",
                    "content": f"未找到窗口: {identifier}\n提示: 使用 'ls' 查看所有窗口"
                }
            
            window_data = self._get_window_data(window_id)
            if not window_data:
                return {
                    "type": "error",
                    "content": f"未能加载窗口数据: {window_id}\n提示: 先执行 'ls' 或 'get_windows' 更新缓存"
                }
            
            window_type = (window_data.get("type") or "text").lower()
            if window_type in {"text", "document", "markdown"}:
                return await self._handle_window_text(window_id, window_data, options)
            elif window_type == "pdf":
                return await self._handle_window_pdf(window_id, window_data, options)
            else:
                return self._handle_window_other(window_id, window_data, options)
        
        # read <window_id_or_title>
        elif cmd == "read":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板"
                }
            
            identifier = args.strip()
            if not identifier:
                return {
                    "type": "error",
                    "content": "用法: read <窗口ID或标题>\n示例: read window_1762160636035 或 read \"我的笔记\""
                }
            
            # 解析窗口标识符（可能是ID或标题）
            window_id = self._resolve_window_id(identifier)
            if not window_id:
                return {
                    "type": "error",
                    "content": f"未找到窗口: {identifier}\n提示: 使用 'ls' 查看所有窗口"
                }
            
            tool_call = ToolCall(
                id=f"console_{int(datetime.now().timestamp() * 1000)}",
                type="function",
                function={
                    "name": "read_window",
                    "arguments": {
                        "board_id": self.current_board,
                        "window_id": window_id
                    }
                }
            )
            
            result = await tool_executor.execute_tool_call(tool_call, context={})
            
            if result.status == ToolStatus.SUCCESS:
                data = result.data or {}
                content = data.get('content', '')
                lines = [
                    f"窗口内容",
                    "=" * 60,
                    "",
                    f"窗口ID: {data.get('window_id', 'N/A')}",
                    f"标题: {data.get('title', 'N/A')}",
                    f"类型: {data.get('type', 'N/A')}",
                    f"内容长度: {data.get('content_length', 0)} 字符",
                    "",
                    "内容:",
                    "-" * 60
                ]
                
                if len(content) > 500:
                    lines.append(content[:500])
                    lines.append("")
                    lines.append(f"... (还有 {len(content) - 500} 个字符)")
                else:
                    lines.append(content if content else "(空内容)")
                
                return {
                    "type": "success",
                    "content": "\n".join(lines)
                }
            else:
                return {
                    "type": "error",
                    "content": f"读取失败: {result.error}"
                }
        # edit <window_id> "新内容" [操作] ["目标"] [选项]
        # 文本操作:
        #   edit window_xxx "新内容"  -> append
        #   edit window_xxx "新内容" replace "旧文本" [all]
        #   edit window_xxx "新内容" insert "位置文本" [before|after]
        #   edit window_xxx "" delete "文本" [all]
        # 行操作:
        #   edit window_xxx "新内容" insert-line "5" [before|after]
        #   edit window_xxx "新内容" replace-line "5"
        #   edit window_xxx "" delete-line "5-10"
        elif cmd == "edit":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板"
                }
            
            try:
                parts = shlex.split(args)
                if len(parts) < 1:
                    return {
                        "type": "error",
                        "content": "用法: edit <窗口ID> [\"新内容\"] [操作] [\"目标\"] [选项]\n\n"
                                   "文本操作:\n"
                                   "  edit window_xxx \"新内容\"  # 追加到末尾\n"
                                   "  edit window_xxx \"新文本\" replace \"旧文本\" [all]  # 替换\n"
                                   "  edit window_xxx \"插入\" insert \"位置\" [before|after]  # 插入\n"
                                   "  edit window_xxx \"\" delete \"文本\" [all]  # 删除\n\n"
                                   "行操作:\n"
                                   "  edit window_xxx \"新行\" insert-line \"5\" [before|after]  # 插入行\n"
                                   "  edit window_xxx \"新内容\" replace-line \"5\"  # 替换行\n"
                                   "  edit window_xxx \"\" delete-line \"5-10\"  # 删除行\n\n"
                                   "示例:\n"
                                   "  edit window_xxx \"\\n\\n新章节\"  # 追加\n"
                                   "  edit window_xxx \"新\" replace \"旧\" all  # 替换所有\n"
                                   "  edit window_xxx \"注释\" insert \"代码\" before  # 之前插入\n"
                                   "  edit window_xxx \"\" delete-line \"10\"  # 删除第10行"
                    }
                
                identifier = parts[0]
                
                # 如果只有窗口标识符，显示帮助
                if len(parts) == 1:
                    return {
                        "type": "error",
                        "content": f"请指定编辑内容或操作\n\n用法: edit {identifier} \"新内容\" [操作] [\"目标\"]"
                    }
                
                # 解析窗口标识符（可能是ID或标题）
                window_id = self._resolve_window_id(identifier)
                if not window_id:
                    return {
                        "type": "error",
                        "content": f"未找到窗口: {identifier}\n提示: 使用 'ls' 查看所有窗口"
                    }
                
                content = parts[1].replace('\\n', '\n').replace('\\t', '\t') if len(parts) > 1 else ""
                operation_type = parts[2].lower() if len(parts) > 2 else "append"
                target = parts[3] if len(parts) > 3 else ""
                option = parts[4].lower() if len(parts) > 4 else ""
                
                # 解析操作类型和参数
                tool_name = "update_window"
                tool_args = {
                    "board_id": self.current_board,
                    "window_id": window_id
                }
                
                # 根据操作类型构造工具调用
                if operation_type == "append":
                    # 追加模式
                    tool_name = "update_window"
                    tool_args.update({
                        "content": content,
                        "mode": "append"
                    })
                    operation_desc = "追加内容"
                
                elif operation_type == "replace":
                    # 替换文本
                    if not target:
                        return {
                            "type": "error",
                            "content": "replace 操作需要指定目标文本\n用法: edit window_xxx \"新文本\" replace \"旧文本\" [all]"
                        }
                    tool_name = "edit_window"
                    tool_args.update({
                        "operation": "replace_text",
                        "target": target,
                        "content": content,
                        "all": (option == "all")
                    })
                    operation_desc = f"替换文本 ({option if option == 'all' else '仅首个'})"
                
                elif operation_type == "insert":
                    # 插入文本
                    if not target:
                        return {
                            "type": "error",
                            "content": "insert 操作需要指定位置文本\n用法: edit window_xxx \"新内容\" insert \"位置\" [before|after]"
                        }
                    tool_name = "edit_window"
                    position = option if option in ["before", "after", "at"] else "after"
                    tool_args.update({
                        "operation": "insert",
                        "target": target,
                        "content": content,
                        "position": position
                    })
                    operation_desc = f"在指定位置{position}插入"
                
                elif operation_type == "delete":
                    # 删除文本
                    if not target:
                        return {
                            "type": "error",
                            "content": "delete 操作需要指定要删除的文本\n用法: edit window_xxx \"\" delete \"文本\" [all]"
                        }
                    tool_name = "edit_window"
                    tool_args.update({
                        "operation": "delete_text",
                        "target": target,
                        "all": (option == "all")
                    })
                    operation_desc = f"删除文本 ({option if option == 'all' else '仅首个'})"
                
                elif operation_type == "insert-line":
                    # 插入行
                    if not target:
                        return {
                            "type": "error",
                            "content": "insert-line 操作需要指定行号\n用法: edit window_xxx \"新行\" insert-line \"5\" [before|after]"
                        }
                    tool_name = "edit_window"
                    position = option if option in ["before", "after", "at"] else "after"
                    tool_args.update({
                        "operation": "insert_line",
                        "target": target,
                        "content": content,
                        "position": position
                    })
                    operation_desc = f"在第 {target} 行{position}插入"
                
                elif operation_type == "replace-line":
                    # 替换行
                    if not target:
                        return {
                            "type": "error",
                            "content": "replace-line 操作需要指定行号\n用法: edit window_xxx \"新内容\" replace-line \"5\""
                        }
                    tool_name = "edit_window"
                    tool_args.update({
                        "operation": "replace_line",
                        "target": target,
                        "content": content
                    })
                    operation_desc = f"替换第 {target} 行"
                
                elif operation_type == "delete-line":
                    # 删除行
                    if not target:
                        return {
                            "type": "error",
                            "content": "delete-line 操作需要指定行号\n用法: edit window_xxx \"\" delete-line \"5\" 或 \"5-10\""
                        }
                    tool_name = "edit_window"
                    tool_args.update({
                        "operation": "delete_line",
                        "target": target
                    })
                    operation_desc = f"删除第 {target} 行"
                
                else:
                    return {
                        "type": "error",
                        "content": f"未知的操作类型: {operation_type}\n\n支持的操作:\n"
                                   "  文本: append, replace, insert, delete\n"
                                   "  行: insert-line, replace-line, delete-line"
                    }
                
                # 构造工具调用
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": tool_name,
                        "arguments": tool_args
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    lines = [
                        f"成功编辑窗口",
                        "=" * 60,
                        "",
                        f"窗口ID: {window_id}",
                        f"操作: {operation_desc}",
                    ]
                    
                    # 显示变化信息
                    if 'old_length' in data and 'new_length' in data:
                        change = data['new_length'] - data['old_length']
                        lines.append(f"内容变化: {change:+d} 字符")
                    
                    lines.append("")
                    lines.append("提示: 使用 'read {窗口ID}' 查看结果")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines),
                        "action": {"type": "refresh_board"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"编辑失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 使用引号包裹参数"
                }
            except Exception as e:
                return {
                    "type": "error",
                    "content": f"执行错误: {str(e)}"
                }
        
        # delete <window_id_or_title>
        elif cmd == "delete":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板"
                }
            
            identifier = args.strip()
            if not identifier:
                return {
                    "type": "error",
                    "content": "用法: delete <窗口ID或标题>\n示例: delete window_1762160636035 或 delete \"我的笔记\""
                }
            
            # 解析窗口标识符（可能是ID或标题）
            window_id = self._resolve_window_id(identifier)
            if not window_id:
                return {
                    "type": "error",
                    "content": f"未找到窗口: {identifier}\n提示: 使用 'ls' 查看所有窗口"
                }
            
            tool_call = ToolCall(
                id=f"console_{int(datetime.now().timestamp() * 1000)}",
                type="function",
                function={
                    "name": "delete_window",
                    "arguments": {
                        "board_id": self.current_board,
                        "window_id": window_id
                    }
                }
            )
            
            result = await tool_executor.execute_tool_call(tool_call, context={})
            
            if result.status == ToolStatus.SUCCESS:
                lines = [
                    f"成功删除窗口",
                    "=" * 60,
                    "",
                    f"窗口ID: {window_id}",
                    "",
                    "窗口已移至回收站"
                ]
                return {
                    "type": "success",
                    "content": "\n".join(lines),
                    "action": {"type": "refresh_board"}
                }
            else:
                return {
                    "type": "error",
                    "content": f"删除失败: {result.error}"
                }
        
        # search "关键词"
        elif cmd == "search":
            if not self.current_board:
                return {
                    "type": "error",
                    "content": "请先进入展板"
                }
            
            try:
                query = shlex.split(args)[0] if args.strip() else ""
                if not query:
                    return {
                        "type": "error",
                        "content": "用法: search \"关键词\"\n示例: search \"生态系统\""
                    }
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "search_windows",
                        "arguments": {
                            "board_id": self.current_board,
                            "query": query
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    windows = data.get('windows', [])
                    lines = [
                        f"搜索结果 (共 {data.get('count', 0)} 个)",
                        "=" * 60,
                        f"关键词: {data.get('query', 'N/A')}",
                        ""
                    ]
                    
                    for i, w in enumerate(windows, 1):
                        lines.append(f"{i:2d}. {w.get('title', '无标题')}")
                        lines.append(f"    ID: {w.get('id', 'N/A')}")
                        lines.append("")
                    
                    if not windows:
                        lines.append("未找到匹配的窗口")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines)
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"搜索失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}"
                }
        
        # task "标题" "时间" ["日期"]  - 添加任务
        elif cmd == "task":
            try:
                parts = shlex.split(args)
                if len(parts) < 2:
                    return {
                        "type": "error",
                        "content": "用法: task \"标题\" \"时间\" [\"日期\"]\n示例: task \"开会\" \"14:30\" \"2024-11-05\""
                    }
                
                title = parts[0]
                time = parts[1]
                date = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d")
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "add_task",
                        "arguments": {
                            "date": date,
                            "title": title,
                            "time": time
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    return {
                        "type": "success",
                        "content": f"成功添加任务\n{'=' * 60}\n\n"
                                   f"日期: {date}\n"
                                   f"时间: {time}\n"
                                   f"标题: {title}\n\n"
                                   f"提示: 使用 'tasks {date}' 查看该日任务",
                        "action": {"type": "refresh_calendar"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"添加任务失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}"
                }
        
        # tasks ["日期"]  - 列出任务
        elif cmd == "tasks":
            try:
                date = shlex.split(args)[0] if args.strip() else datetime.now().strftime("%Y-%m-%d")
                info(f"[Console] 查询任务日期: {date}")
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "list_tasks",
                        "arguments": {
                            "date": date
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    tasks = data.get("tasks", [])
                    
                    lines = [
                        f"任务列表 ({date})",
                        "=" * 60,
                        ""
                    ]
                    
                    if tasks:
                        for i, task in enumerate(tasks, 1):
                            status = "✓" if task.get("completed") else " "
                            lines.append(f" [{status}] {task['time']} {task['title']} (ID: {task['id']})")
                        lines.append("")
                        lines.append(f"共 {len(tasks)} 个任务")
                        lines.append("")
                        lines.append("提示: 使用 'done <任务ID> <日期>' 标记完成")
                    else:
                        lines.append("该日期暂无任务")
                        lines.append("")
                        lines.append("提示: 使用 'task \"标题\" \"时间\"' 添加任务")
                    
                    return {
                        "type": "success",
                        "content": "\n".join(lines)
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"获取任务失败: {result.error}"
                    }
                    
            except Exception as e:
                return {
                    "type": "error",
                    "content": f"执行错误: {str(e)}"
                }
        
        # edittask <任务ID> ["新标题"] ["新时间"] [日期]  - 修改任务
        elif cmd == "edittask":
            try:
                parts = shlex.split(args)
                if len(parts) < 2:
                    return {
                        "type": "error",
                        "content": "用法: edittask <任务ID> \"新标题\" [\"新时间\"] [日期]\n示例:\n"
                                   "  edittask 1730800000000 \"开会讨论\"           # 修改今日任务标题\n"
                                   "  edittask 1730800000000 \"\" \"15:30\"        # 修改今日任务时间\n"
                                   "  edittask 1730800000000 \"会议\" \"16:00\"    # 同时修改标题和时间\n"
                                   "  edittask 1730800000000 \"会议\" \"\" 2024-11-06  # 修改明天任务标题"
                    }
                
                task_id = int(parts[0])
                new_title = parts[1] if parts[1] else None
                new_time = parts[2] if len(parts) > 2 and parts[2] else None
                date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")
                
                # 验证时间格式
                if new_time:
                    try:
                        datetime.strptime(new_time, "%H:%M")
                    except ValueError:
                        return {
                            "type": "error",
                            "content": f"时间格式错误: {new_time}\n应为 HH:MM 格式，例如 14:30"
                        }
                
                # 构建参数
                tool_args = {
                    "date": date,
                    "task_id": task_id
                }
                if new_title:
                    tool_args["title"] = new_title
                if new_time:
                    tool_args["time"] = new_time
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "update_task",
                        "arguments": tool_args
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    changes = []
                    if new_title:
                        changes.append(f"标题: {new_title}")
                    if new_time:
                        changes.append(f"时间: {new_time}")
                    
                    return {
                        "type": "success",
                        "content": f"成功修改任务\n{'=' * 60}\n\n"
                                   f"任务ID: {task_id}\n"
                                   f"日期: {date}\n"
                                   f"修改: {', '.join(changes)}\n\n"
                                   f"提示: 使用 'tasks {date}' 查看任务列表",
                        "action": {"type": "refresh_calendar"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"修改任务失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 任务ID应为数字"
                }
        
        # done <任务ID> [日期]  - 切换任务完成状态
        elif cmd == "done":
            try:
                parts = shlex.split(args)
                if len(parts) < 1:
                    return {
                        "type": "error",
                        "content": "用法: done <任务ID> [日期]\n示例:\n  done 1730800000000           # 今日任务\n  done 1730800000000 2024-11-05  # 指定日期"
                    }
                
                task_id = int(parts[0])
                date = parts[1] if len(parts) > 1 else datetime.now().strftime("%Y-%m-%d")
                
                tool_call = ToolCall(
                    id=f"console_{int(datetime.now().timestamp() * 1000)}",
                    type="function",
                    function={
                        "name": "toggle_task",
                        "arguments": {
                            "date": date,
                            "task_id": task_id
                        }
                    }
                )
                
                result = await tool_executor.execute_tool_call(tool_call, context={})
                
                if result.status == ToolStatus.SUCCESS:
                    data = result.data or {}
                    completed = data.get("completed", False)
                    status_text = "已完成" if completed else "未完成"
                    
                    return {
                        "type": "success",
                        "content": f"任务状态已更新\n{'=' * 60}\n\n"
                                   f"任务ID: {task_id}\n"
                                   f"状态: {status_text}\n\n"
                                   f"提示: 使用 'tasks {date}' 查看任务列表",
                        "action": {"type": "refresh_calendar"}
                    }
                else:
                    return {
                        "type": "error",
                        "content": f"切换任务状态失败: {result.error}"
                    }
                    
            except ValueError as e:
                return {
                    "type": "error",
                    "content": f"参数解析错误: {str(e)}\n提示: 任务ID应为数字"
                }
        
        # 不是简化命令，返回 None
        return None

