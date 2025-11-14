"""
任务追踪工具
用于 LLM 在复杂多步骤任务中追踪进度和判断完成状态
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus
from logger import info, error
from typing import Dict, Any, List, Optional
from datetime import datetime
from difflib import SequenceMatcher


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

# 6. 暂停执行
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
        """创建待办列表（会完全重置所有状态）"""
        # 记录旧状态（用于日志）
        old_total = len(self.todos)
        old_completed = len(self.completed)
        
        # 完全重置所有状态
        self.todos = list(items)  # 确保是新的列表对象
        self.completed = set()  # 清空已完成状态
        self.skipped = {}  # 清空跳过状态
        self.notes = {}  # 清空备注
        self.description = description
        self.created_at = datetime.now().isoformat()
        
        info(
            f"[TodoTracker] 创建新待办列表: {len(items)} 项 "
            f"(已清空旧列表: {old_total} 项, 其中 {old_completed} 项已完成)"
        )
        
        # 验证状态确实被重置
        status = self.get_status()
        info(
            f"[TodoTracker] 新列表状态验证: total={status['total']}, "
            f"completed={status['completed_count']}, remaining={status['remaining_count']}"
        )
        
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

    def get_state(self) -> Optional[Dict]:
        """导出当前待办状态，便于持久化"""
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

    def load_state(self, state: Optional[Dict]):
        """从持久化状态恢复待办列表"""
        if not state:
            self.todos = []
            self.completed = set()
            self.skipped = {}
            self.notes = {}
            self.description = ""
            self.created_at = None
            info("[TodoTracker] 已从空状态恢复，当前无待办")
            return

        self.todos = state.get("todos", [])
        completed = state.get("completed", [])
        self.completed = set(int(idx) for idx in completed)

        skipped = state.get("skipped", {})
        self.skipped = {int(k): v for k, v in skipped.items()}

        notes = state.get("notes", {})
        self.notes = {int(k): v for k, v in notes.items()}

        self.description = state.get("description", "")
        self.created_at = state.get("created_at")
        info(
            f"[TodoTracker] 从持久化状态恢复: total={len(self.todos)}, completed={len(self.completed)}, "
            f"remaining={len(self.todos) - len(self.completed)}"
        )


# ==================== 工具处理器 ====================

class TodoToolHandlers:
    """待办工具处理器"""
    
    def __init__(self, tracker: Optional[TodoTracker] = None):
        self.tracker = tracker

    def _resolve_tracker(self, context: Optional[Dict[str, Any]] = None) -> TodoTracker:
        """从上下文获取当前待办追踪器"""
        tracker = None
        if isinstance(context, dict):
            tracker = context.get("todo_tracker") or context.get("tracker") or context.get("todoTracker")
        if tracker is None:
            tracker = self.tracker
        if tracker is None:
            raise ValueError("todo_tracker 未提供，无法执行待办工具")
        return tracker

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        return ''.join(ch.lower() for ch in text if ch.isalnum() or ch.isspace()).strip()

    def _should_drop_leading_summary(self, first_item: str, description: str) -> bool:
        if not first_item or not description:
            return False
        normalized_item = self._normalize_text(first_item)
        normalized_desc = self._normalize_text(description)
        if not normalized_item or not normalized_desc:
            return False
        if normalized_item == normalized_desc:
            return True
        if normalized_item.startswith(normalized_desc) or normalized_desc.startswith(normalized_item):
            return True
        similarity = SequenceMatcher(None, normalized_item, normalized_desc).ratio()
        return similarity >= 0.72
    
    async def create_todo_list(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """创建待办列表（会完全重置旧列表）"""
        try:
            tracker = self._resolve_tracker(context)
            items = arguments.get("items", [])
            description = arguments.get("description", "")
            
            if not items:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="create_todo_list",
                    status=ToolStatus.ERROR,
                    error="待办项列表不能为空"
                )
            
            # 记录创建前的状态（用于日志）
            old_status = tracker.get_status() if tracker.has_todos() else None
            if old_status:
                info(
                    f"[TodoToolHandlers] 创建新待办列表前，旧列表状态: "
                    f"total={old_status['total']}, completed={old_status['completed_count']}"
                )
            
            cleaned_items = list(items)
            if description and len(cleaned_items) > 1 and self._should_drop_leading_summary(cleaned_items[0], description):
                removed_item = cleaned_items.pop(0)
                info(f"[TodoTracker] 自动移除了重复的总览项: \"{removed_item}\"")
            
            # 创建新列表（会完全重置所有状态）
            result = tracker.create_list(cleaned_items, description)
            
            # 验证新状态
            new_status = tracker.get_status()
            info(
                f"[TodoToolHandlers] 创建新待办列表后，状态验证: "
                f"total={new_status['total']}, completed={new_status['completed_count']}, "
                f"remaining={new_status['remaining_count']}, has_todos={new_status['has_todos']}"
            )
            
            # 确保返回的数据包含完整的状态信息
            result_with_status = {
                **result,
                "has_todos": new_status['has_todos'],
                "completed_count": new_status['completed_count'],
                "remaining_count": new_status['remaining_count'],
                "all_completed": new_status['all_completed']
            }
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="create_todo_list",
                status=ToolStatus.SUCCESS,
                data=result_with_status
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
            tracker = self._resolve_tracker(context)
            item_index = arguments.get("item_index")
            note = arguments.get("note", "")
            
            if item_index is None:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="complete_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index"
                )
            
            result = tracker.complete_item(item_index, note)
            
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
            tracker = self._resolve_tracker(context)
            result = tracker.get_status()
            
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
            tracker = self._resolve_tracker(context)
            item = arguments.get("item")
            position = arguments.get("position")
            
            if not item:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="add_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供待办项内容"
                )
            
            result = tracker.add_item(item, position)
            
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
            tracker = self._resolve_tracker(context)
            item_index = arguments.get("item_index")
            reason = arguments.get("reason")
            
            if item_index is None or not reason:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="skip_todo_item",
                    status=ToolStatus.ERROR,
                    error="必须提供 item_index 和 reason"
                )
            
            result = tracker.skip_item(item_index, reason)
            
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
    
    async def pause_execution(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """暂停执行"""
        try:
            tracker = self._resolve_tracker(context)
            reason = arguments.get("reason", "")
            
            info(f"[工具] 暂停执行，原因: {reason if reason else '未指定'}")
            
            # 返回特殊标记，让 llm_service 知道要暂停
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
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
            error(f"[工具] 暂停执行失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="pause_execution",
                status=ToolStatus.ERROR,
                error=str(e)
            )


# ==================== 工具注册函数 ====================

_TODO_TOOLS_REGISTERED = False


def register_todo_tools(tool_registry, tracker: Optional[TodoTracker] = None, force: bool = False):
    """注册待办工具到工具注册表（默认只注册一次）"""
    global _TODO_TOOLS_REGISTERED
    
    if _TODO_TOOLS_REGISTERED and not force:
        info("ℹ️ 待办工具已注册，跳过重复注册")
        return
    
    handlers = TodoToolHandlers(tracker or TodoTracker())
    
    todo_tools = [
        (CREATE_TODO_LIST_TOOL, ToolHandler(executor=handlers.create_todo_list)),
        (COMPLETE_TODO_ITEM_TOOL, ToolHandler(executor=handlers.complete_todo_item)),
        (GET_TODO_STATUS_TOOL, ToolHandler(executor=handlers.get_todo_status)),
        (ADD_TODO_ITEM_TOOL, ToolHandler(executor=handlers.add_todo_item)),
        (SKIP_TODO_ITEM_TOOL, ToolHandler(executor=handlers.skip_todo_item)),
        (PAUSE_EXECUTION_TOOL, ToolHandler(executor=handlers.pause_execution)),
    ]
    
    for tool_def, handler in todo_tools:
        tool_registry.register_tool(tool_def, handler, category="todo")
    
    _TODO_TOOLS_REGISTERED = True
    info(f"✅ 已注册 {len(todo_tools)} 个待办工具")

