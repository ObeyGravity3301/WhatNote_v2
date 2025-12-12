"""
工具调用相关数据模型

定义工具定义、工具调用、工具结果的数据结构
"""

from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class ToolStatus(Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"  # 部分成功


@dataclass
class ToolDefinition:
    """
    工具定义
    
    遵循 OpenAI Function Calling 格式
    参考: https://platform.openai.com/docs/guides/function-calling
    """
    type: str = "function"  # 固定为 "function"
    function: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证必需字段"""
        if not self.function:
            raise ValueError("function 字段不能为空")
        
        required_fields = ['name', 'description', 'parameters']
        for field_name in required_fields:
            if field_name not in self.function:
                raise ValueError(f"function 缺少必需字段: {field_name}")
        
        # 验证 parameters 是否为有效的 JSON Schema
        params = self.function['parameters']
        if not isinstance(params, dict):
            raise ValueError("parameters 必须是字典类型")
        
        if params.get('type') != 'object':
            raise ValueError("parameters.type 必须是 'object'")
    
    @property
    def name(self) -> str:
        """工具名称"""
        return self.function['name']
    
    @property
    def description(self) -> str:
        """工具描述"""
        return self.function['description']
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """参数 schema"""
        return self.function['parameters']
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI API 格式"""
        return {
            "type": self.type,
            "function": self.function
        }


@dataclass
class ToolCall:
    """
    工具调用请求
    
    LLM 返回的工具调用信息
    """
    id: str  # 工具调用唯一ID，由 LLM 生成
    type: str = "function"  # 固定为 "function"
    function: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def name(self) -> str:
        """工具名称"""
        return self.function.get('name', '')
    
    @property
    def arguments(self) -> Dict[str, Any]:
        """工具参数（已解析为字典）"""
        args = self.function.get('arguments', {})
        # 如果是字符串，尝试解析为字典
        if isinstance(args, str):
            import json
            try:
                return json.loads(args)
            except json.JSONDecodeError:
                return {}
        return args
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function
        }


@dataclass
class ToolResult:
    """
    工具执行结果
    
    包含执行状态、返回数据、错误信息等
    """
    tool_call_id: str  # 对应的 tool_call.id
    tool_name: str  # 工具名称
    status: ToolStatus  # 执行状态
    data: Optional[Any] = None  # 返回数据
    error: Optional[str] = None  # 错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def to_llm_message(self) -> Dict[str, Any]:
        """
        转换为 LLM 可理解的消息格式
        
        根据 OpenAI 规范，工具结果需要以 role="tool" 的消息返回
        """
        content = {
            "status": self.status.value,
            "tool_name": self.tool_name
        }
        
        if self.status == ToolStatus.SUCCESS:
            content["result"] = self.data
        elif self.status == ToolStatus.ERROR:
            content["error"] = self.error
        else:  # PARTIAL
            content["result"] = self.data
            content["warning"] = self.error
        
        if self.metadata:
            content["metadata"] = self.metadata
        
        import json
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "content": json.dumps(content, ensure_ascii=False)
        }
    
    def is_success(self) -> bool:
        """是否执行成功"""
        return self.status == ToolStatus.SUCCESS
    
    def get_summary(self) -> str:
        """获取执行摘要（用于日志）"""
        if self.status == ToolStatus.SUCCESS:
            return f"✅ {self.tool_name}: 成功"
        elif self.status == ToolStatus.ERROR:
            return f"❌ {self.tool_name}: {self.error}"
        else:
            return f"⚠️ {self.tool_name}: 部分成功"


@dataclass
class ToolHandler:
    """
    工具处理器
    
    封装工具的执行函数及相关配置
    """
    executor: Callable[[Dict[str, Any], Any], Awaitable[ToolResult]]  # 异步执行函数
    requires_confirmation: bool = False  # 是否需要用户确认
    is_dangerous: bool = False  # 是否为危险操作（删除等）
    timeout: int = 120  # 超时时间（秒）
    
    async def execute(self, arguments: Dict[str, Any], context: Any = None) -> ToolResult:
        """
        执行工具
        
        Args:
            arguments: 工具参数
            context: 执行上下文（如 board_id, user_id 等）
            
        Returns:
            ToolResult: 执行结果
        """
        return await self.executor(arguments, context)





