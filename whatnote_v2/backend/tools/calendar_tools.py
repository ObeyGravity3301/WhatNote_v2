"""
日历和任务管理工具
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus
from logger import info, error
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
from pathlib import Path


# ==================== 工具定义 ====================

# 1. 添加任务
ADD_TASK_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "add_task",
        "description": "添加任务到指定日期的日历中。如果用户未指定日期，默认使用今天",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期，格式 YYYY-MM-DD，例如 '2025-11-05'。如果不提供，默认为今天"
                },
                "title": {
                    "type": "string",
                    "description": "任务标题"
                },
                "time": {
                    "type": "string",
                    "description": "任务时间，格式 HH:MM，例如 '14:30'"
                }
            },
            "required": ["title", "time"]
        }
    }
)

# 2. 列出任务
LIST_TASKS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "list_tasks",
        "description": "列出指定日期的所有任务",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "日期，格式 YYYY-MM-DD。不提供则返回今日任务"
                }
            },
            "required": []
        }
    }
)

# 3. 切换任务完成状态
TOGGLE_TASK_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "toggle_task",
        "description": "切换任务的完成状态（已完成 ↔ 未完成）",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "任务所在日期，格式 YYYY-MM-DD"
                },
                "task_id": {
                    "type": "integer",
                    "description": "任务ID"
                }
            },
            "required": ["date", "task_id"]
        }
    }
)

# 4. 更新任务
UPDATE_TASK_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "update_task",
        "description": "更新任务的标题或时间",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "任务所在日期，格式 YYYY-MM-DD"
                },
                "task_id": {
                    "type": "integer",
                    "description": "任务ID"
                },
                "title": {
                    "type": "string",
                    "description": "新的任务标题（可选）"
                },
                "time": {
                    "type": "string",
                    "description": "新的任务时间，格式 HH:MM（可选）"
                }
            },
            "required": ["date", "task_id"]
        }
    }
)

# 5. 删除任务
DELETE_TASK_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "delete_task",
        "description": "删除指定的任务",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "任务所在日期，格式 YYYY-MM-DD"
                },
                "task_id": {
                    "type": "integer",
                    "description": "任务ID"
                }
            },
            "required": ["date", "task_id"]
        }
    }
)

# 6. 搜索任务
SEARCH_TASKS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "search_tasks",
        "description": "搜索任务，支持按标题关键词和日期范围搜索",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词（标题）"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD"
                },
                "completed": {
                    "type": "boolean",
                    "description": "筛选完成状态：true=已完成，false=未完成，不提供=全部"
                }
            },
            "required": []
        }
    }
)

# 7. 获取即将到来的任务
GET_UPCOMING_TASKS_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "get_upcoming_tasks",
        "description": "获取未来N天内的任务",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "未来天数，默认为7天",
                    "default": 7
                },
                "include_completed": {
                    "type": "boolean",
                    "description": "是否包含已完成的任务，默认为false",
                    "default": False
                }
            },
            "required": []
        }
    }
)


# ==================== 工具处理器 ====================

class CalendarToolHandlers:
    """日历工具处理器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.calendar_file = self.data_dir / "calendar_tasks.json"
        self._ensure_calendar_file()
    
    def _ensure_calendar_file(self):
        """确保日历文件存在"""
        if not self.calendar_file.exists():
            self.calendar_file.parent.mkdir(parents=True, exist_ok=True)
            self._save_calendar_data({})
    
    def _load_calendar_data(self) -> Dict:
        """加载日历数据"""
        try:
            if self.calendar_file.exists():
                with open(self.calendar_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            error(f"加载日历数据失败: {e}")
        return {}
    
    def _save_calendar_data(self, data: Dict):
        """保存日历数据"""
        try:
            with open(self.calendar_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error(f"保存日历数据失败: {e}")
            raise
    
    async def add_task(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """添加任务"""
        try:
            # 如果没有提供日期，使用今天
            date = arguments.get("date")
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
                info(f"[工具] 未提供日期，使用今天: {date}")
            
            title = arguments.get("title")
            time = arguments.get("time")
            
            # 验证日期格式
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="add_task",
                    status=ToolStatus.ERROR,
                    error="日期格式错误，应为 YYYY-MM-DD"
                )
            
            # 验证时间格式
            try:
                datetime.strptime(time, "%H:%M")
            except ValueError:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="add_task",
                    status=ToolStatus.ERROR,
                    error="时间格式错误，应为 HH:MM"
                )
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            # 创建新任务
            task_id = int(datetime.now().timestamp() * 1000)
            new_task = {
                "id": task_id,
                "title": title,
                "time": time,
                "completed": False,
                "createdAt": datetime.now().isoformat()
            }
            
            # 添加到指定日期
            if date not in calendar_data:
                calendar_data[date] = []
            calendar_data[date].append(new_task)
            
            # 保存
            self._save_calendar_data(calendar_data)
            
            info(f"[工具] 添加任务: {title} @ {date} {time}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="add_task",
                status=ToolStatus.SUCCESS,
                data={
                    "task_id": task_id,
                    "date": date,
                    "title": title,
                    "time": time
                }
            )
            
        except Exception as e:
            error(f"[工具] 添加任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="add_task",
                status=ToolStatus.ERROR,
                error=f"添加任务失败: {str(e)}"
            )
    
    async def list_tasks(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """列出任务"""
        try:
            date = arguments.get("date")
            
            # 如果没有提供日期，使用今天
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            info(f"[工具] 日历数据包含的日期: {list(calendar_data.keys())}")
            tasks = calendar_data.get(date, [])
            info(f"[工具] 日期 {date} 的任务: {tasks}")
            
            # 排序：未完成在前，按时间排序
            tasks_sorted = sorted(tasks, key=lambda t: (t.get("completed", False), t.get("time", "")))
            
            info(f"[工具] 列出任务: {date}, 共 {len(tasks_sorted)} 个")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="list_tasks",
                status=ToolStatus.SUCCESS,
                data={
                    "date": date,
                    "count": len(tasks_sorted),
                    "tasks": tasks_sorted
                }
            )
            
        except Exception as e:
            error(f"[工具] 列出任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="list_tasks",
                status=ToolStatus.ERROR,
                error=f"列出任务失败: {str(e)}"
            )
    
    async def toggle_task(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """切换任务完成状态"""
        try:
            date = arguments.get("date")
            task_id = arguments.get("task_id")
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            if date not in calendar_data:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="toggle_task",
                    status=ToolStatus.ERROR,
                    error=f"日期 {date} 没有任务"
                )
            
            # 查找并切换任务
            tasks = calendar_data[date]
            task_found = False
            
            for task in tasks:
                if task["id"] == task_id:
                    task["completed"] = not task.get("completed", False)
                    if task["completed"]:
                        task["completedAt"] = datetime.now().isoformat()
                    else:
                        task.pop("completedAt", None)
                    task_found = True
                    break
            
            if not task_found:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="toggle_task",
                    status=ToolStatus.ERROR,
                    error=f"未找到任务 ID: {task_id}"
                )
            
            # 保存
            self._save_calendar_data(calendar_data)
            
            info(f"[工具] 切换任务状态: {task_id} @ {date}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="toggle_task",
                status=ToolStatus.SUCCESS,
                data={
                    "task_id": task_id,
                    "date": date,
                    "completed": task["completed"]
                }
            )
            
        except Exception as e:
            error(f"[工具] 切换任务状态失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="toggle_task",
                status=ToolStatus.ERROR,
                error=f"切换任务状态失败: {str(e)}"
            )
    
    async def update_task(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """更新任务"""
        try:
            date = arguments.get("date")
            task_id = arguments.get("task_id")
            new_title = arguments.get("title")
            new_time = arguments.get("time")
            
            if not new_title and not new_time:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_task",
                    status=ToolStatus.ERROR,
                    error="请至少提供 title 或 time 其中一个参数"
                )
            
            # 验证时间格式（如果提供了）
            if new_time:
                try:
                    datetime.strptime(new_time, "%H:%M")
                except ValueError:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="update_task",
                        status=ToolStatus.ERROR,
                        error="时间格式错误，应为 HH:MM"
                    )
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            if date not in calendar_data:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_task",
                    status=ToolStatus.ERROR,
                    error=f"日期 {date} 没有任务"
                )
            
            # 查找并更新任务
            tasks = calendar_data[date]
            task_found = False
            updated_task = None
            
            for task in tasks:
                if task["id"] == task_id:
                    if new_title:
                        task["title"] = new_title
                    if new_time:
                        task["time"] = new_time
                    task["updatedAt"] = datetime.now().isoformat()
                    task_found = True
                    updated_task = task
                    break
            
            if not task_found:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="update_task",
                    status=ToolStatus.ERROR,
                    error=f"未找到任务 ID: {task_id}"
                )
            
            # 保存
            self._save_calendar_data(calendar_data)
            
            info(f"[工具] 更新任务: {task_id} @ {date}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_task",
                status=ToolStatus.SUCCESS,
                data={
                    "task_id": task_id,
                    "date": date,
                    "title": updated_task["title"],
                    "time": updated_task["time"]
                }
            )
            
        except Exception as e:
            error(f"[工具] 更新任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="update_task",
                status=ToolStatus.ERROR,
                error=f"更新任务失败: {str(e)}"
            )
    
    async def delete_task(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """删除任务"""
        try:
            date = arguments.get("date")
            task_id = arguments.get("task_id")
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            if date not in calendar_data:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="delete_task",
                    status=ToolStatus.ERROR,
                    error=f"日期 {date} 没有任务"
                )
            
            # 删除任务
            tasks = calendar_data[date]
            original_count = len(tasks)
            calendar_data[date] = [t for t in tasks if t["id"] != task_id]
            
            if len(calendar_data[date]) == original_count:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="delete_task",
                    status=ToolStatus.ERROR,
                    error=f"未找到任务 ID: {task_id}"
                )
            
            # 保存
            self._save_calendar_data(calendar_data)
            
            info(f"[工具] 删除任务: {task_id} @ {date}")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="delete_task",
                status=ToolStatus.SUCCESS,
                data={
                    "task_id": task_id,
                    "date": date
                }
            )
            
        except Exception as e:
            error(f"[工具] 删除任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="delete_task",
                status=ToolStatus.ERROR,
                error=f"删除任务失败: {str(e)}"
            )
    
    async def search_tasks(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """搜索任务"""
        try:
            query = arguments.get("query", "")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            completed = arguments.get("completed")
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            results = []
            
            for date, tasks in calendar_data.items():
                # 日期范围筛选
                if start_date and date < start_date:
                    continue
                if end_date and date > end_date:
                    continue
                
                for task in tasks:
                    # 关键词筛选
                    if query and query.lower() not in task.get("title", "").lower():
                        continue
                    
                    # 完成状态筛选
                    if completed is not None and task.get("completed", False) != completed:
                        continue
                    
                    results.append({
                        "date": date,
                        **task
                    })
            
            # 按日期和时间排序
            results.sort(key=lambda t: (t["date"], t.get("time", "")))
            
            info(f"[工具] 搜索任务: '{query}', 找到 {len(results)} 个")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="search_tasks",
                status=ToolStatus.SUCCESS,
                data={
                    "query": query,
                    "count": len(results),
                    "tasks": results
                }
            )
            
        except Exception as e:
            error(f"[工具] 搜索任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="search_tasks",
                status=ToolStatus.ERROR,
                error=f"搜索任务失败: {str(e)}"
            )
    
    async def get_upcoming_tasks(self, arguments: Dict[str, Any], context: Dict[str, Any] = None) -> ToolResult:
        """获取即将到来的任务"""
        try:
            days = arguments.get("days", 7)
            include_completed = arguments.get("include_completed", False)
            
            # 计算日期范围
            today = datetime.now()
            end_date = today + timedelta(days=days)
            
            start_str = today.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # 加载数据
            calendar_data = self._load_calendar_data()
            
            results = []
            
            for date, tasks in calendar_data.items():
                if start_str <= date <= end_str:
                    for task in tasks:
                        # 是否包含已完成的任务
                        if not include_completed and task.get("completed", False):
                            continue
                        
                        results.append({
                            "date": date,
                            **task
                        })
            
            # 按日期和时间排序
            results.sort(key=lambda t: (t["date"], t.get("time", "")))
            
            info(f"[工具] 获取未来{days}天任务: 共 {len(results)} 个")
            
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="get_upcoming_tasks",
                status=ToolStatus.SUCCESS,
                data={
                    "days": days,
                    "start_date": start_str,
                    "end_date": end_str,
                    "count": len(results),
                    "tasks": results
                }
            )
            
        except Exception as e:
            error(f"[工具] 获取即将到来的任务失败: {e}")
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="get_upcoming_tasks",
                status=ToolStatus.ERROR,
                error=f"获取任务失败: {str(e)}"
            )


# ==================== 工具注册函数 ====================

def register_calendar_tools(tool_registry, data_dir: Path):
    """注册日历工具到工具注册表"""
    
    handlers = CalendarToolHandlers(data_dir)
    
    calendar_tools = [
        (ADD_TASK_TOOL, ToolHandler(executor=handlers.add_task)),
        (LIST_TASKS_TOOL, ToolHandler(executor=handlers.list_tasks)),
        (TOGGLE_TASK_TOOL, ToolHandler(executor=handlers.toggle_task)),
        (UPDATE_TASK_TOOL, ToolHandler(executor=handlers.update_task)),
        (DELETE_TASK_TOOL, ToolHandler(executor=handlers.delete_task)),
        (SEARCH_TASKS_TOOL, ToolHandler(executor=handlers.search_tasks)),
        (GET_UPCOMING_TASKS_TOOL, ToolHandler(executor=handlers.get_upcoming_tasks)),
    ]
    
    for tool_def, handler in calendar_tools:
        tool_registry.register_tool(tool_def, handler, category="calendar")
    
    info(f"[Success] 已注册 {len(calendar_tools)} 个日历工具")

