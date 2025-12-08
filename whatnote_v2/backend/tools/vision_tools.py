"""
视觉能力工具集
将 VL 模型能力封装为 Tool，供纯文本模型调用
"""

from .schemas import ToolDefinition, ToolHandler, ToolResult, ToolStatus
from logger import info, error
from typing import Dict, Any
import aiohttp
import json
import base64
import mimetypes
from pathlib import Path

# ==================== 工具定义 ====================

ANALYZE_IMAGE_TOOL = ToolDefinition(
    type="function",
    function={
        "name": "analyze_image",
        "description": "使用视觉模型分析图片内容。当需要识别图片中的文字、物体、场景或回答关于图片的问题时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "图片的完整文件路径（通常通过 read_window 获取）"
                },
                "query": {
                    "type": "string",
                    "description": "关于图片的具体问题或指令。例如：'这张图里有什么？', '图中的红色物体是什么？', '提取图中的文字'",
                    "default": "请详细描述这张图片的内容"
                }
            },
            "required": ["image_path"]
        }
    }
)

# ==================== 工具处理器 ====================

class VisionToolHandlers:
    """视觉工具处理器"""
    
    def __init__(self, api_config_manager):
        self.api_config_manager = api_config_manager
    
    async def analyze_image(self, args: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """分析图片"""
        try:
            image_path = args["image_path"]
            query = args.get("query", "请详细描述这张图片的内容")
            
            # 1. 验证图片文件
            path = Path(image_path)
            if not path.exists():
                # 尝试相对路径修正
                if (Path("data") / image_path).exists():
                    path = Path("data") / image_path
                elif (Path("../data") / image_path).exists():
                    path = Path("../data") / image_path
                else:
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="analyze_image",
                        status=ToolStatus.ERROR,
                        error=f"图片文件不存在: {image_path}"
                    )
            
            # 2. 读取并编码图片
            try:
                with open(path, "rb") as f:
                    image_data = f.read()
                    
                mime_type, _ = mimetypes.guess_type(str(path))
                if not mime_type:
                    mime_type = "image/jpeg"
                    
                base64_data = base64.b64encode(image_data).decode("utf-8")
                data_url = f"data:{mime_type};base64,{base64_data}"
                
            except Exception as e:
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="analyze_image",
                    status=ToolStatus.ERROR,
                    error=f"读取图片失败: {str(e)}"
                )
            
            # 3. 获取 API 配置 (强制使用 qwen-vl-max)
            # 我们暂时硬编码使用 Qwen VL，因为它是最强的
            # 也可以从配置中读取，但要确保是 VL 模型
            qwen_config = self.api_config_manager.get_provider_config("qwen")
            if not qwen_config or not qwen_config.get("apiKey"):
                return ToolResult(
                    tool_call_id=context.get("call_id", ""),
                    tool_name="analyze_image",
                    status=ToolStatus.ERROR,
                    error="未配置 Qwen API，无法使用视觉能力"
                )
            
            api_key = qwen_config["apiKey"]
            base_url = qwen_config["baseUrl"]
            model = "qwen-vl-max"  # 强制使用 VL 模型
            
            # 4. 调用 VL 模型
            info(f"[Vision Tool] 调用 {model} 分析图片: {path.name}")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": query}
                    ]
                }
            ]
            
            async with aiohttp.ClientSession() as session:
                url = f"{base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ToolResult(
                            tool_call_id=context.get("call_id", ""),
                            tool_name="analyze_image",
                            status=ToolStatus.ERROR,
                            error=f"VL 模型调用失败: {error_text}"
                        )
                    
                    result = await response.json()
                    description = result["choices"][0]["message"]["content"]
                    
                    info(f"[Vision Tool] 分析完成，描述长度: {len(description)}")
                    
                    return ToolResult(
                        tool_call_id=context.get("call_id", ""),
                        tool_name="analyze_image",
                        status=ToolStatus.SUCCESS,
                        data={
                            "description": description,
                            "image_name": path.name,
                            "model_used": model
                        }
                    )
                    
        except Exception as e:
            error(f"[Vision Tool] 分析失败: {e}")
            import traceback
            error(traceback.format_exc())
            return ToolResult(
                tool_call_id=context.get("call_id", ""),
                tool_name="analyze_image",
                status=ToolStatus.ERROR,
                error=f"分析过程发生异常: {str(e)}"
            )

def register_vision_tools(tool_registry, api_config_manager):
    """注册视觉工具"""
    handlers = VisionToolHandlers(api_config_manager)
    
    tool_registry.register_tool(
        ANALYZE_IMAGE_TOOL, 
        ToolHandler(executor=handlers.analyze_image),
        category="vision"
    )
    
    info("✅ 已注册视觉工具")


