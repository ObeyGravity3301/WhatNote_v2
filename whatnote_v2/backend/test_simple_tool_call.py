"""
简单测试工具调用 - 直接调用API
"""

import asyncio
import aiohttp
import json


async def test_simple_call():
    """测试基本的工具调用"""
    
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    import os
    api_key = os.getenv("QWEN_API_KEY", "")
    
    # 简单的工具定义
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前时间",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": "列出指定日期的所有任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "日期，格式 YYYY-MM-DD"
                        }
                    },
                    "required": []
                }
            }
        }
    ]
    
    messages = [
        {
            "role": "system",
            "content": "你是一个助手，可以使用工具来帮助用户。当用户询问任务时，使用 list_tasks 工具查询。"
        },
        {
            "role": "user",
            "content": "今天有什么任务？"
        }
    ]
    
    payload = {
        "model": "qwen-plus",
        "messages": messages,
        "tools": tools,
        "stream": False
    }
    
    print("发送请求到通义千问...")
    print(f"工具数: {len(tools)}")
    print(f"消息数: {len(messages)}")
    print()
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f"错误 ({response.status}): {error_text}")
                return
            
            data = await response.json()
            
            print("响应:")
            print("="*60)
            
            message = data['choices'][0]['message']
            finish_reason = data['choices'][0].get('finish_reason')
            
            print(f"finish_reason: {finish_reason}")
            print()
            
            if message.get('tool_calls'):
                print("✅ 检测到工具调用:")
                for tool_call in message['tool_calls']:
                    print(f"  - {tool_call['function']['name']}")
                    print(f"    参数: {tool_call['function']['arguments']}")
            elif message.get('content'):
                print(f"内容: {message['content']}")
            else:
                print("没有内容或工具调用")


if __name__ == "__main__":
    asyncio.run(test_simple_call())

