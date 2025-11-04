"""
工具注册中心

管理所有可用工具的定义和处理器
"""

from typing import Dict, List, Optional, Any
from .schemas import ToolDefinition, ToolHandler
from logger import info, error


class ToolRegistry:
    """
    工具注册中心
    
    负责管理所有可用工具的定义和执行器
    采用单例模式，确保全局唯一
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: Dict[str, ToolDefinition] = {}  # 工具定义
        self._handlers: Dict[str, ToolHandler] = {}  # 工具处理器
        self._categories: Dict[str, List[str]] = {  # 工具分类
            'window': [],      # 窗口管理
            'file': [],        # 文件操作
            'planner': [],     # 日历待办
            'pdf': [],         # PDF 操作
            'search': [],      # 搜索功能
            'system': []       # 系统功能
        }
        self._initialized = True
        
        info("🔧 工具注册中心初始化完成")
    
    def register_tool(
        self,
        definition: ToolDefinition,
        handler: ToolHandler,
        category: str = 'system'
    ) -> None:
        """
        注册工具
        
        Args:
            definition: 工具定义（OpenAI 格式）
            handler: 工具处理器
            category: 工具分类
        """
        tool_name = definition.name
        
        if tool_name in self._tools:
            error(f"⚠️ 工具已存在，将被覆盖: {tool_name}")
        
        self._tools[tool_name] = definition
        self._handlers[tool_name] = handler
        
        # 添加到分类
        if category in self._categories:
            if tool_name not in self._categories[category]:
                self._categories[category].append(tool_name)
        else:
            error(f"⚠️ 未知的工具分类: {category}，使用默认分类 'system'")
            self._categories['system'].append(tool_name)
        
        info(f"✅ 工具注册成功: {tool_name} (分类: {category})")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否成功
        """
        if tool_name not in self._tools:
            error(f"⚠️ 工具不存在: {tool_name}")
            return False
        
        del self._tools[tool_name]
        del self._handlers[tool_name]
        
        # 从分类中移除
        for category_tools in self._categories.values():
            if tool_name in category_tools:
                category_tools.remove(tool_name)
        
        info(f"✅ 工具注销成功: {tool_name}")
        return True
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        获取工具定义
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[ToolDefinition]: 工具定义，不存在则返回 None
        """
        return self._tools.get(tool_name)
    
    def get_tool_handler(self, tool_name: str) -> Optional[ToolHandler]:
        """
        获取工具处理器
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[ToolHandler]: 工具处理器，不存在则返回 None
        """
        return self._handlers.get(tool_name)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有工具定义（OpenAI 格式）
        
        Returns:
            List[Dict]: 工具定义列表，可直接传递给 LLM API
        """
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        获取指定分类的工具定义
        
        Args:
            category: 工具分类
            
        Returns:
            List[Dict]: 工具定义列表
        """
        if category not in self._categories:
            error(f"⚠️ 未知的工具分类: {category}")
            return []
        
        tool_names = self._categories[category]
        return [
            self._tools[name].to_openai_format() 
            for name in tool_names 
            if name in self._tools
        ]
    
    def list_tools(self) -> Dict[str, List[str]]:
        """
        列出所有工具及其分类
        
        Returns:
            Dict[str, List[str]]: {分类: [工具名称列表]}
        """
        return {
            category: list(tools)
            for category, tools in self._categories.items()
        }
    
    def tool_exists(self, tool_name: str) -> bool:
        """
        检查工具是否存在
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否存在
        """
        return tool_name in self._tools
    
    def get_tool_count(self) -> int:
        """
        获取已注册工具总数
        
        Returns:
            int: 工具数量
        """
        return len(self._tools)
    
    def clear_all(self) -> None:
        """清空所有已注册的工具（用于测试）"""
        self._tools.clear()
        self._handlers.clear()
        for category in self._categories:
            self._categories[category].clear()
        info("🔧 已清空所有工具注册")


# 全局单例
tool_registry = ToolRegistry()





