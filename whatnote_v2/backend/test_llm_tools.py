"""
测试 LLM 工具调用功能
"""

import asyncio
import json
from llm_service import LLMService
from storage.api_config_manager import APIConfigManager
from storage.content_manager import ContentManager
from storage.file_manager import FileSystemManager
from tools import tool_registry, register_builtin_tools
from config import DATA_DIR


async def test_llm_tools():
    """测试LLM工具调用"""
    
    # 初始化服务
    api_config_manager = APIConfigManager(DATA_DIR)
    
    # 临时修改模型为 qwen-plus（支持工具调用）
    current_config = api_config_manager.get_current_config()
    original_model = current_config.get('model')
    current_config['model'] = 'qwen-plus'
    print(f"使用模型: {current_config['model']} (原: {original_model})\n")
    
    file_manager = FileSystemManager(DATA_DIR)
    content_manager = ContentManager(file_manager)
    llm_service = LLMService(api_config_manager, content_manager)
    
    # 注册工具
    if len(tool_registry.get_all_tools()) == 0:
        register_builtin_tools(tool_registry, content_manager, file_manager, DATA_DIR)
    
    print(f"[Success] 已注册 {len(tool_registry.get_all_tools())} 个工具")
    print("\n可用工具列表:")
    for tool in tool_registry.get_all_tools():
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    
    print("\n" + "="*60)
    print("开始测试...")
    print("="*60 + "\n")
    
    # 测试消息
    messages = [
        {
            "role": "system",
            "content": "你是 WhatNote 智能助手。你可以使用提供的工具来帮助用户管理笔记、课程、展板和日历任务。"
                       "当用户询问任务、笔记或需要创建内容时，请主动使用相应的工具。"
                       "例如：用户问'今天有什么任务'时，使用 list_tasks 工具查询。"
        },
        {
            "role": "user",
            "content": "请使用 list_tasks 工具查看 2025-11-04 的任务"
        }
    ]
    
    print(f"用户: {messages[1]['content']}\n")
    print("AI响应:")
    print("-" * 60)
    
    # 调用工具增强的对话
    async for event in llm_service.chat_with_tools(messages):
        event_type = event.get('type')
        content = event.get('content', '')
        
        if event_type == 'tool_call':
            print(f"\n🔧 {content}")
            print(f"   工具: {event.get('tool_name')}")
            print(f"   参数: {json.dumps(event.get('arguments', {}), ensure_ascii=False)}")
            
        elif event_type == 'tool_result':
            print(f"[Success] {content}")
            result = event.get('tool_result', {})
            print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)[:200]}...")
            
        elif event_type == 'final':
            print(f"\n💬 AI最终回复:")
            print(f"{content}")
            
        elif event_type == 'error':
            print(f"\n[Error] 错误: {content}")
            
        elif event_type == 'warning':
            print(f"\n[Warning]  {content}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_llm_tools())

