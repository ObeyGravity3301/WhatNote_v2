"""
工具执行引擎

负责解析 LLM 返回的工具调用并执行对应的处理器
"""

from typing import Dict, List, Any, Optional
import asyncio
import json
from .schemas import ToolCall, ToolResult, ToolStatus, ToolHandler
from .tool_registry import tool_registry
from logger import info, error


class ToolExecutor:
    """
    工具执行引擎
    
    负责：
    1. 解析 LLM 响应中的 tool_calls
    2. 验证参数
    3. 调用对应的工具处理器
    4. 返回结构化结果
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
        
        self.max_concurrent = 3  # 最大并发执行数
        self.default_timeout = 120  # 默认超时（秒）
        self._initialized = True
        
        info("[System] 工具执行引擎初始化完成")
    
    async def execute_tool_call(
        self,
        tool_call: ToolCall,
        context: Optional[Any] = None
    ) -> ToolResult:
        """
        执行单个工具调用
        
        Args:
            tool_call: 工具调用对象
            context: 执行上下文（如 board_id, conversation_id 等）
            
        Returns:
            ToolResult: 执行结果
        """
        tool_name = tool_call.name
        
        info(f"🔧 开始执行工具: {tool_name}")
        info(f"   工具调用ID: {tool_call.id}")
        info(f"   参数: {json.dumps(tool_call.arguments, ensure_ascii=False)}")
        
        # 检查工具是否存在
        if not tool_registry.tool_exists(tool_name):
            error(f"[Error] 工具不存在: {tool_name}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=f"工具 '{tool_name}' 未注册"
            )
        
        # 获取工具处理器
        handler = tool_registry.get_tool_handler(tool_name)
        if not handler:
            error(f"[Error] 工具处理器不存在: {tool_name}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=f"工具 '{tool_name}' 缺少处理器"
            )
        
        # 验证参数（基于 JSON Schema）
        tool_definition = tool_registry.get_tool_definition(tool_name)
        validation_error = self._validate_arguments(
            tool_call.arguments,
            tool_definition.parameters
        )
        
        if validation_error:
            error(f"[Error] 参数验证失败: {validation_error}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=f"参数验证失败: {validation_error}"
            )
        
        # 执行工具（带超时控制）
        try:
            timeout = handler.timeout or self.default_timeout
            result = await asyncio.wait_for(
                handler.execute(tool_call.arguments, context),
                timeout=timeout
            )
            
            info(f"[Success] 工具执行成功: {tool_name}")
            return result
            
        except asyncio.TimeoutError:
            error(f"[Timeout] 工具执行超时: {tool_name} (超时: {timeout}秒)")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=f"执行超时（>{timeout}秒）"
            )
        except Exception as e:
            error(f"[Error] 工具执行异常: {tool_name} - {str(e)}")
            return ToolResult(
                tool_call_id=tool_call.id,
                tool_name=tool_name,
                status=ToolStatus.ERROR,
                error=f"执行异常: {str(e)}"
            )
    
    async def execute_tool_calls(
        self,
        tool_calls: List[ToolCall],
        context: Optional[Any] = None,
        parallel: bool = False
    ) -> List[ToolResult]:
        """
        批量执行工具调用
        
        Args:
            tool_calls: 工具调用列表
            context: 执行上下文
            parallel: 是否并行执行（默认串行）
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        if not tool_calls:
            return []
        
        info(f"🔧 开始批量执行 {len(tool_calls)} 个工具调用 (并行: {parallel})")
        
        if parallel:
            # 并行执行（限制并发数）
            tasks = [
                self.execute_tool_call(call, context)
                for call in tool_calls
            ]
            
            results = []
            for i in range(0, len(tasks), self.max_concurrent):
                batch = tasks[i:i + self.max_concurrent]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                
                # 处理异常
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        call_idx = i + j
                        results.append(ToolResult(
                            tool_call_id=tool_calls[call_idx].id,
                            tool_name=tool_calls[call_idx].name,
                            status=ToolStatus.ERROR,
                            error=f"执行异常: {str(result)}"
                        ))
                    else:
                        results.append(result)
            
            return results
        else:
            # 串行执行
            results = []
            for call in tool_calls:
                result = await self.execute_tool_call(call, context)
                results.append(result)
            
            return results
    
    def _validate_arguments(
        self,
        arguments: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Optional[str]:
        """
        验证参数是否符合 JSON Schema
        
        Args:
            arguments: 实际参数
            schema: JSON Schema
            
        Returns:
            Optional[str]: 错误信息，验证通过则返回 None
        """
        # 检查必需参数
        required = schema.get('required', [])
        for field in required:
            if field not in arguments:
                return f"缺少必需参数: {field}"
        
        # 检查参数类型（简化版本，只检查基本类型）
        properties = schema.get('properties', {})
        for key, value in arguments.items():
            if key not in properties:
                # 允许额外参数（宽松模式）
                continue
            
            expected_type = properties[key].get('type')
            if expected_type:
                if not self._check_type(value, expected_type):
                    return f"参数 '{key}' 类型错误，期望 {expected_type}，实际 {type(value).__name__}"
            
            # 检查枚举值
            enum_values = properties[key].get('enum')
            if enum_values and value not in enum_values:
                return f"参数 '{key}' 值不在允许范围内: {enum_values}"
            
            # 检查数值范围
            if expected_type in ['integer', 'number']:
                minimum = properties[key].get('minimum')
                maximum = properties[key].get('maximum')
                
                if minimum is not None and value < minimum:
                    return f"参数 '{key}' 小于最小值 {minimum}"
                
                if maximum is not None and value > maximum:
                    return f"参数 '{key}' 大于最大值 {maximum}"
            
            # 检查字符串模式
            if expected_type == 'string':
                pattern = properties[key].get('pattern')
                if pattern:
                    import re
                    if not re.match(pattern, value):
                        return f"参数 '{key}' 不匹配格式要求: {pattern}"
        
        return None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        检查值是否匹配指定的 JSON Schema 类型
        
        Args:
            value: 待检查的值
            expected_type: 期望的类型（JSON Schema 类型）
            
        Returns:
            bool: 是否匹配
        """
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return True  # 未知类型，跳过检查
        
        return isinstance(value, expected_python_type)
    
    def parse_tool_calls_from_response(
        self,
        response_data: Dict[str, Any]
    ) -> List[ToolCall]:
        """
        从 LLM 响应中解析工具调用
        
        Args:
            response_data: LLM API 返回的响应数据
            
        Returns:
            List[ToolCall]: 工具调用列表
        """
        tool_calls = []
        
        # OpenAI / 通义千问格式
        if 'choices' in response_data:
            for choice in response_data['choices']:
                message = choice.get('message', {})
                raw_tool_calls = message.get('tool_calls', [])
                
                for call_data in raw_tool_calls:
                    try:
                        tool_call = ToolCall(
                            id=call_data.get('id', f"call_{len(tool_calls)}"),
                            type=call_data.get('type', 'function'),
                            function=call_data.get('function', {})
                        )
                        tool_calls.append(tool_call)
                        info(f"🔍 解析到工具调用: {tool_call.name}")
                    except Exception as e:
                        error(f"[Warning] 解析工具调用失败: {e}")
        
        return tool_calls
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取工具注册统计信息
        
        Returns:
            Dict: 统计数据
        """
        return {
            "total_tools": len(self._tools),
            "categories": {
                category: len(tools)
                for category, tools in self._categories.items()
            },
            "tools_by_category": {
                category: list(tools)
                for category, tools in self._categories.items()
            }
        }


# 全局单例
tool_executor = ToolExecutor()





