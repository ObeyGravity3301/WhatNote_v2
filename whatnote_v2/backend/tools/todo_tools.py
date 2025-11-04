"""
任务追踪工具
用于 LLM 在复杂多步骤任务中追踪进度和判断完成状态
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus
from logger import info, error
from typing import Dict, Any, List
from datetime import datetime


# ==================== 工具定义 ====================

# 1. 创建待办列表
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

# 2. 完成待办项
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

# 3. 获取待办状态
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

# 4. 添加待办项
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

# 5. 跳过待办项
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


# ==================== TodoTracker 类 ====================

class TodoTracker:
    """任务追踪器 - 每个对话会话一个实例"""
    
    def __init__(self):
        self.todos = []  # 待办项列表
        self.completed = set()  # 已完成的索引集合
        self.skipped = {}  # 跳过的项 {index: reason}
        self.notes = {}  # 完成备注 {index: note}
        self.description = ""  # 整体描述
        self.created_at = None
    
    def create_list(self, items: List[str], description: str = ""):
        """创建待办列表"""
        self.todos = items
        self.completed = set()
        self.skipped = {}
        self.notes = {}
        self.description = description
        self.created_at = datetime.now().isoformat()
        
        info(f"[TodoTracker] 创建待办列表: {len(items)} 项")
        
        return {
            "success": True,
            "total": len(items),
            "description": description,
            "items": [
                {
                    "index": i,
                    "task": task,
                    "completed": False
                }
                for i, task in enumerate(items)
            ]
        }
    
    def complete_item(self, item_index: int, note: str = ""):
        """完成待办项"""
        if item_index < 0 or item_index >= len(self.todos):
            return {
                "success": False,
                "error": f"索引 {item_index} 超出范围 (0-{len(self.todos)-1})"
            }
        
        self.completed.add(item_index)
        if note:
            self.notes[item_index] = note
        
        remaining = len(self.todos) - len(self.completed)
        
        info(f"[TodoTracker] 完成项 {item_index}: {self.todos[item_index]}, 剩余 {remaining} 项")
        
        return {
            "success": True,
            "completed_index": item_index,
            "completed_task": self.todos[item_index],
            "remaining": remaining,
            "all_completed": remaining == 0
        }
    
    def skip_item(self, item_index: int, reason: str):
        """跳过待办项"""
        if item_index < 0 or item_index >= len(self.todos):
            return {
                "success": False,
                "error": f"索引 {item_index} 超出范围"
            }
        
        self.completed.add(item_index)  # 也标记为已完成
        self.skipped[item_index] = reason
        
        remaining = len(self.todos) - len(self.completed)
        
        info(f"[TodoTracker] 跳过项 {item_index}: {reason}")
        
        return {
            "success": True,
            "skipped_index": item_index,
            "skipped_task": self.todos[item_index],
            "reason": reason,
            "remaining": remaining
        }
    
    def add_item(self, item: str, position: int = None):
        """添加待办项"""
        if position is None or position >= len(self.todos):
            # 追加到末尾
            self.todos.append(item)
            new_index = len(self.todos) - 1
        else:
            # 插入到指定位置
            self.todos.insert(position, item)
            new_index = position
            
            # 更新已完成索引（因为插入导致后面的索引变化）
            new_completed = set()
            for idx in self.completed:
                if idx >= position:
                    new_completed.add(idx + 1)
                else:
                    new_completed.add(idx)
            self.completed = new_completed
        
        info(f"[TodoTracker] 添加项 {new_index}: {item}")
        
        return {
            "success": True,
            "added_index": new_index,
            "added_task": item,
            "total": len(self.todos)
        }
    
    def get_status(self):
        """获取当前状态"""
        completed_count = len(self.completed)
        total = len(self.todos)
        remaining = total - completed_count
        
        return {
            "has_todos": len(self.todos) > 0,
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
    
    def has_todos(self):
        """是否有待办列表"""
        return len(self.todos) > 0
    
    def is_all_completed(self):
        """是否全部完成"""
        return len(self.todos) > 0 and len(self.completed) == len(self.todos)


# ==================== 工具处理器 ====================

class TodoToolHandlers:
    """待办工具处理器"""
    
    def __init__(self, tracker: TodoTracker):
        self.tracker = tracker
    
    async def create_todo_list(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """创建待办列表"""
        try:
            items = arguments.get("items", [])
            description = arguments.get("description", "")
            
            if not items:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_todo_list",
                    status=ToolStatus.ERROR,
                    error="待办项列表不能为空"
                )
            
            result = self.tracker.create_list(items, description)
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_todo_list",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[工具] 创建待办列表失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
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
                    tool_call_id=context.get("call_id", ""),
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index"
                )
            
            result = self.tracker.complete_item(item_index, note)
            
            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error=result.get("error")
                )
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="complete_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[工具] 完成待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="complete_todo_item",
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def get_todo_status(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """获取待办状态"""
        try:
            result = self.tracker.get_status()
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="get_todo_status",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[工具] 获取待办状态失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
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
                    tool_call_id=context.get("call_id", ""),
                    tool_name="add_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供待办项内容"
                )
            
            result = self.tracker.add_item(item, position)
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="add_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[工具] 添加待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
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
                    tool_call_id=context.get("call_id", ""),
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index 和 reason"
                )
            
            result = self.tracker.skip_item(item_index, reason)
            
            if not result.get("success"):
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error=result.get("error")
                )
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="skip_todo_item",
                status=ToolStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            error(f"[工具] 跳过待办项失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="skip_todo_item",
                status=ToolStatus.ERROR,
                error=str(e)
            )


# ==================== 工具注册函数 ====================

def register_todo_tools(tool_registry, tracker: TodoTracker):
    """注册待办工具到工具注册表"""
    
    handlers = TodoToolHandlers(tracker)
    
    todo_tools = [
        (CREATE_TODO_LIST_TOOL, ToolHandler(executor=handlers.create_todo_list)),
        (COMPLETE_TODO_ITEM_TOOL, ToolHandler(executor=handlers.complete_todo_item)),
        (GET_TODO_STATUS_TOOL, ToolHandler(executor=handlers.get_todo_status)),
        (ADD_TODO_ITEM_TOOL, ToolHandler(executor=handlers.add_todo_item)),
        (SKIP_TODO_ITEM_TOOL, ToolHandler(executor=handlers.skip_todo_item)),
    ]
    
    for tool_def, handler in todo_tools:
        tool_registry.register_tool(tool_def, handler, category="todo")
    
    info(f"✅ 已注册 {len(todo_tools)} 个待办工具")

