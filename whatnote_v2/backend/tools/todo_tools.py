"""
任务追踪工具 - 简化版
用于 LLM 在复杂多步骤任务中追踪进度和判断完成状态

设计原则：
1. 单一数据源：Todo 状态只存储在 ConversationManager 的对话 JSON 中
2. 无内存缓存：每次工具调用时从磁盘读取，执行后立即写回
3. 简单可靠：减少状态同步复杂度，避免不一致问题
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus
from logger import info, error
from typing import Dict, Any, List, Optional
from datetime import datetime


# ==================== 工具定义 ====================

CREATE_TODO_LIST_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "create_todo_list",
        "description": "在开始执行复杂的多步骤任务前，创建待办事项列表来追踪执行进度。这有助于确保所有步骤都被完成，不会遗漏",
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "待办事项列表，按执行顺序排列。每一项应该是明确的操作或输出说明"
                },
                "description": {
                    "type": "string",
                    "description": "整体任务的简短描述（可选）"
                }
            },
            "required": ["items"]
        }
    }
)

COMPLETE_TODO_ITEM_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "complete_todo_item",
        "description": "标记某个待办项为已完成。每完成一个步骤（工具调用或文本输出）后，必须调用此工具更新进度",
        "parameters": {
            "type": "object",
            "properties": {
                "item_index": {
                    "type": "integer",
                    "description": "待办项的索引（从0开始）"
                },
                "note": {
                    "type": "string",
                    "description": "完成备注（可选）"
                }
            },
            "required": ["item_index"]
        }
    }
)

COMPLETE_TODO_ITEMS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "complete_todo_items",
        "description": "一次性标记多个待办项为已完成。当你连续完成了多个步骤后，可以使用此工具批量标记，比逐个调用 complete_todo_item 更高效，节省时间和 token",
        "parameters": {
            "type": "object",
            "properties": {
                "item_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "待办项的索引列表（从0开始），例如 [0, 1, 2] 表示同时完成前3项"
                },
                "notes": {
                    "type": "object",
                    "description": "可选的备注字典，键为索引，值为备注内容，例如 {\"0\": \"已完成\", \"1\": \"已确认\"}",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["item_indices"]
        }
    }
)

GET_TODO_STATUS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "get_todo_status",
        "description": "查看当前待办列表的完成情况，包括总数、已完成数量、剩余数量等",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
)

ADD_TODO_ITEM_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "add_todo_item",
        "description": "在执行过程中发现需要额外步骤时，动态添加新的待办项",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "新增的待办项"
                },
                "position": {
                    "type": "integer",
                    "description": "插入位置（索引），不提供则追加到末尾"
                }
            },
            "required": ["item"]
        }
    }
)

SKIP_TODO_ITEM_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "skip_todo_item",
        "description": "跳过某个待办项（标记为已完成但注明跳过原因）",
        "parameters": {
            "type": "object",
            "properties": {
                "item_index": {
                    "type": "integer",
                    "description": "待办项的索引（从0开始）"
                },
                "reason": {
                    "type": "string",
                    "description": "跳过的原因"
                }
            },
            "required": ["item_index", "reason"]
        }
    }
)

PAUSE_EXECUTION_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "pause_execution",
        "description": "暂停当前任务的执行。当你需要中途暂停执行（例如：等待用户确认、需要更多信息、或已完成部分工作想先展示给用户），可以调用此工具。暂停后，待办列表会保留，用户可以稍后继续。",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "暂停的原因（可选），例如：'等待用户确认'、'已完成部分工作，先展示给用户'、'需要更多信息'等"
                }
            },
            "required": []
        }
    }
)


# ==================== TodoState 数据结构 ====================

class TodoState:
    """
    Todo 状态数据结构
    设计为纯数据类，不持有任何外部引用
    """
    
    def __init__(self, data: Optional[Dict] = None):
        if data:
            self.todos: List[str] = data.get("todos", [])
            self.completed: set = set(data.get("completed", []))
            self.skipped: Dict[int, str] = {int(k): v for k, v in data.get("skipped", {}).items()}
            self.notes: Dict[int, str] = {int(k): v for k, v in data.get("notes", {}).items()}
            self.description: str = data.get("description", "")
            self.created_at: Optional[str] = data.get("created_at")
        else:
            self.todos = []
            self.completed = set()
            self.skipped = {}
            self.notes = {}
            self.description = ""
            self.created_at = None
    
    def to_dict(self) -> Optional[Dict]:
        """导出为可序列化的字典"""
        if not self.todos:
            return None
        return {
            "todos": self.todos,
            "completed": list(self.completed),
            "skipped": self.skipped,
            "notes": self.notes,
            "description": self.description,
            "created_at": self.created_at
        }
    
    def get_status(self) -> Dict:
        """获取状态摘要（用于前端显示）"""
        total = len(self.todos)
        completed_count = len(self.completed)
        remaining = total - completed_count
        
        return {
            "has_todos": total > 0,
            "description": self.description,
            "total": total,
            "completed_count": completed_count,
            "remaining_count": remaining,
            "all_completed": completed_count == total and total > 0,
            "items": [
                {
                    "index": i,
                    "task": task,
                    "completed": i in self.completed,
                    "skipped": i in self.skipped,
                    "skip_reason": self.skipped.get(i),
                    "note": self.notes.get(i)
                }
                for i, task in enumerate(self.todos)
            ]
        }
    
    def has_todos(self) -> bool:
        return len(self.todos) > 0
    
    def is_all_completed(self) -> bool:
        return len(self.todos) > 0 and len(self.completed) == len(self.todos)
    
    def create_list(self, items: List[str], description: str = "") -> Dict:
        """创建新的待办列表（完全重置）"""
        self.todos = list(items)
        self.completed = set()
        self.skipped = {}
        self.notes = {}
        self.description = description
        self.created_at = datetime.now().isoformat()
        
        status = self.get_status()
        return {
            "success": True,
            "total": len(items),
            "description": description,
            "items": status["items"],
            **status  # 包含 has_todos, completed_count 等
        }
    
    def complete_item(self, index: int, note: str = "") -> Dict:
        """完成待办项"""
        if index < 0 or index >= len(self.todos):
            return {"success": False, "error": f"索引 {index} 超出范围 (0-{len(self.todos)-1})"}
        
        self.completed.add(index)
        if note:
            self.notes[index] = note
        
        remaining = len(self.todos) - len(self.completed)
        return {
            "success": True,
            "completed_index": index,
            "completed_task": self.todos[index],
            "remaining": remaining,
            "all_completed": remaining == 0
        }
    
    def complete_items(self, indices: List[int], notes: Optional[Dict[int, str]] = None) -> Dict:
        """一次性完成多个待办项"""
        if not indices:
            return {"success": False, "error": "索引列表不能为空"}
        
        invalid_indices = [idx for idx in indices if idx < 0 or idx >= len(self.todos)]
        if invalid_indices:
            return {"success": False, "error": f"无效的索引: {invalid_indices}，有效范围 (0-{len(self.todos)-1})"}
        
        # 完成所有项
        completed_tasks = []
        for index in indices:
            self.completed.add(index)
            completed_tasks.append({
                "index": index,
                "task": self.todos[index]
            })
            # 如果有对应的备注，添加备注
            if notes and index in notes:
                self.notes[index] = notes[index]
        
        remaining = len(self.todos) - len(self.completed)
        return {
            "success": True,
            "completed_count": len(indices),
            "completed_indices": indices,
            "completed_tasks": completed_tasks,
            "remaining": remaining,
            "all_completed": remaining == 0
        }
    
    def skip_item(self, index: int, reason: str) -> Dict:
        """跳过待办项"""
        if index < 0 or index >= len(self.todos):
            return {"success": False, "error": f"索引 {index} 超出范围"}
        
        self.completed.add(index)
        self.skipped[index] = reason
        
        remaining = len(self.todos) - len(self.completed)
        return {
            "success": True,
            "skipped_index": index,
            "skipped_task": self.todos[index],
            "reason": reason,
            "remaining": remaining
        }
    
    def add_item(self, item: str, position: Optional[int] = None) -> Dict:
        """添加待办项"""
        if position is None or position >= len(self.todos):
            self.todos.append(item)
            new_index = len(self.todos) - 1
        else:
            self.todos.insert(position, item)
            new_index = position
            # 更新已完成索引
            new_completed = set()
            for idx in self.completed:
                new_completed.add(idx + 1 if idx >= position else idx)
            self.completed = new_completed
        
        return {
            "success": True,
            "added_index": new_index,
            "added_task": item,
            "total": len(self.todos)
        }


# ==================== 工具处理器 ====================

class TodoToolHandlers:
    """
    待办工具处理器 - 简化版
    
    设计原则：
    - 不持有任何状态，每次调用从 context 获取 conversation_manager
    - 每次操作都从磁盘读取最新状态，操作后立即写回
    - 通过 context 传递 board_id 和 conversation_id
    """
    
    def __init__(self):
        pass  # 不再需要任何初始化参数
    
    def _get_conversation_manager(self, context: Optional[Dict]) -> Optional[Any]:
        """从 context 获取 conversation_manager"""
        if not context:
            return None
        return context.get("conversation_manager")
    
    def _get_ids(self, context: Optional[Dict]) -> tuple:
        """从 context 获取 board_id 和 conversation_id"""
        if not context:
            return None, None
        return context.get("board_id"), context.get("conversation_id")
    
    def _load_state(self, context: Optional[Dict]) -> TodoState:
        """从 ConversationManager 加载状态"""
        conv_manager = self._get_conversation_manager(context)
        board_id, conv_id = self._get_ids(context)
        
        if not conv_manager or not board_id or not conv_id:
            info("[TodoTools] 缺少必要的上下文信息，使用空状态")
            return TodoState()
        
        try:
            data = conv_manager.get_todo_state(board_id, conv_id)
            if data and data.get("state"):
                info(f"[TodoTools] 从磁盘加载状态: {board_id}/{conv_id}")
                return TodoState(data.get("state"))
        except Exception as e:
            error(f"[TodoTools] 加载状态失败: {e}")
        
        return TodoState()
    
    def _save_state(self, state: TodoState, context: Optional[Dict]) -> bool:
        """保存状态到 ConversationManager"""
        conv_manager = self._get_conversation_manager(context)
        board_id, conv_id = self._get_ids(context)
        
        if not conv_manager or not board_id or not conv_id:
            info("[TodoTools] 缺少必要的上下文信息，无法保存状态")
            return False
        
        try:
            state_dict = state.to_dict()
            status_dict = state.get_status()
            success = conv_manager.save_todo_state(board_id, conv_id, state_dict, status_dict)
            if success:
                info(f"[TodoTools] 状态已保存: {board_id}/{conv_id}, total={status_dict['total']}, completed={status_dict['completed_count']}")
            else:
                error(f"[TodoTools] 保存状态失败: 对话不存在 {board_id}/{conv_id}")
            return success
        except Exception as e:
            error(f"[TodoTools] 保存状态失败: {e}")
            return False
    
    async def create_todo_list(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """创建待办列表"""
        try:
            items = arguments.get("items", [])
            description = arguments.get("description", "")
            
            if not items:
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="create_todo_list",
                    status=ToolStatus.ERROR,
                    error="待办项列表不能为空"
                )
            
            # 创建新状态（不需要加载旧状态，直接覆盖）
            state = TodoState()
            result = state.create_list(items, description)
            
            # 保存到磁盘
            saved = self._save_state(state, context)
            
            info(f"[TodoTools] 创建待办列表: {len(items)} 项, saved={saved}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="create_todo_list",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 创建待办列表失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="create_todo_list",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def complete_todo_item(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """完成待办项"""
        try:
            item_index = arguments.get("item_index")
            note = arguments.get("note", "")
            
            if item_index is None:
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index"
                )
            
            # 加载当前状态
            state = self._load_state(context)
            
            if not state.has_todos():
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error="当前没有待办列表"
                )
            
            # 执行操作
            result = state.complete_item(item_index, note)
            
            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error=result.get("error")
                )
            
            # 保存状态
            self._save_state(state, context)
            
            info(f"[TodoTools] 完成待办项 {item_index}, 剩余 {result['remaining']} 项")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="complete_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 完成待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="complete_todo_item",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def complete_todo_items(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """批量完成待办项"""
        try:
            item_indices = arguments.get("item_indices", [])
            notes_raw = arguments.get("notes", {})
            
            if not item_indices:
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_items",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_indices 数组"
                )
            
            # 转换 notes 字典的键为整数（JSON 中的键可能是字符串）
            notes = {}
            if notes_raw:
                for key, value in notes_raw.items():
                    try:
                        notes[int(key)] = str(value)
                    except (ValueError, TypeError):
                        pass  # 忽略无效的键
            
            # 加载当前状态
            state = self._load_state(context)
            
            if not state.has_todos():
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_items",
                    status=ToolStatus.ERROR,
                    error="当前没有待办列表"
                )
            
            # 执行操作
            result = state.complete_items(item_indices, notes if notes else None)
            
            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="complete_todo_items",
                    status=ToolStatus.ERROR,
                    error=result.get("error")
                )
            
            # 保存状态
            self._save_state(state, context)
            
            info(f"[TodoTools] 批量完成待办项 {len(item_indices)} 项: {item_indices}, 剩余 {result['remaining']} 项")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="complete_todo_items",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 批量完成待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="complete_todo_items",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def get_todo_status(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """获取待办状态"""
        try:
            state = self._load_state(context)
            result = state.get_status()
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="get_todo_status",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 获取待办状态失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="get_todo_status",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def add_todo_item(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """添加待办项"""
        try:
            item = arguments.get("item")
            position = arguments.get("position")
            
            if not item:
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="add_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供待办项内容"
                )
            
            # 加载当前状态
            state = self._load_state(context)
            
            # 如果没有待办列表，创建一个空的
            if not state.has_todos():
                state.todos = []
                state.created_at = datetime.now().isoformat()
            
            # 执行操作
            result = state.add_item(item, position)
            
            # 保存状态
            saved = self._save_state(state, context)
            
            info(f"[TodoTools] 添加待办项: {item}, 位置={position}, 总数={result['total']}, 保存结果={saved}")
            
            # 验证保存后的状态
            verify_state = self._load_state(context)
            info(f"[TodoTools] 验证保存后状态: todos={len(verify_state.todos)}, items={[t[:15] for t in verify_state.todos]}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="add_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 添加待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="add_todo_item",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def skip_todo_item(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """跳过待办项"""
        try:
            item_index = arguments.get("item_index")
            reason = arguments.get("reason")
            
            if item_index is None or not reason:
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index 和 reason"
                )
            
            # 加载当前状态
            state = self._load_state(context)
            
            if not state.has_todos():
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error="当前没有待办列表"
                )
            
            # 执行操作
            result = state.skip_item(item_index, reason)
            
            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", "") if context else "",
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error=result.get("error")
                )
            
            # 保存状态
            self._save_state(state, context)
            
            info(f"[TodoTools] 跳过待办项 {item_index}: {reason}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="skip_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[TodoTools] 跳过待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="skip_todo_item",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def pause_execution(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """暂停执行"""
        try:
            reason = arguments.get("reason", "")
            
            info(f"[TodoTools] 暂停执行，原因: {reason if reason else '未指定'}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="pause_execution",
                status=ToolStatus.SUCCESS,
                data={
                    "success": True,
                    "paused": True,
                    "reason": reason,
                    "message": "执行已暂停"
                }
            )
            
        except Exception as e:
            error(f"[TodoTools] 暂停执行失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", "") if context else "",
                tool_name="pause_execution",
                status=ToolStatus.ERROR,
                error=str(e)
            )


# ==================== 工具注册函数 ====================

_TODO_HANDLERS_INSTANCE: Optional[TodoToolHandlers] = None


def get_todo_handlers() -> TodoToolHandlers:
    """获取全局唯一的 TodoToolHandlers 实例"""
    global _TODO_HANDLERS_INSTANCE
    if _TODO_HANDLERS_INSTANCE is None:
        _TODO_HANDLERS_INSTANCE = TodoToolHandlers()
    return _TODO_HANDLERS_INSTANCE


def register_todo_tools(tool_registry):
    """注册待办工具到工具注册表"""
    handlers = get_todo_handlers()
    
    todo_tools = [
        (CREATE_TODO_LIST_TOOL, ToolHandler(executor=handlers.create_todo_list)),
        (COMPLETE_TODO_ITEM_TOOL, ToolHandler(executor=handlers.complete_todo_item)),
        (COMPLETE_TODO_ITEMS_TOOL, ToolHandler(executor=handlers.complete_todo_items)),
        (GET_TODO_STATUS_TOOL, ToolHandler(executor=handlers.get_todo_status)),
        (ADD_TODO_ITEM_TOOL, ToolHandler(executor=handlers.add_todo_item)),
        (SKIP_TODO_ITEM_TOOL, ToolHandler(executor=handlers.skip_todo_item)),
        (PAUSE_EXECUTION_TOOL, ToolHandler(executor=handlers.pause_execution)),
    ]
    
    for tool_def, handler in todo_tools:
        tool_registry.register_tool(tool_def, handler, category="todo")
    
    info(f"✅ 已注册 {len(todo_tools)} 个待办工具")


# ==================== 辅助函数 ====================

def load_todo_state_from_context(context: Optional[Dict]) -> TodoState:
    """从 context 加载 Todo 状态（供 llm_service 使用）"""
    handlers = get_todo_handlers()
    return handlers._load_state(context)


def get_todo_status_from_context(context: Optional[Dict]) -> Dict:
    """从 context 获取 Todo 状态摘要（供 llm_service 使用）"""
    state = load_todo_state_from_context(context)
    status = state.get_status()
    info(f"[TodoTools] get_todo_status_from_context: total={status.get('total')}, items_count={len(status.get('items', []))}")
    return status
