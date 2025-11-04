"""
测试内置工具功能
"""

import asyncio
import json
from tools import tool_registry, tool_executor, register_builtin_tools, ToolCall
from storage.file_manager import FileSystemManager
from storage.content_manager import ContentManager
from config import DATA_DIR

async def main():
    print("=" * 60)
    print("🧪 测试 WhatNote 内置工具")
    print("=" * 60)
    
    # 初始化管理器
    file_manager = FileSystemManager(DATA_DIR)
    content_manager = ContentManager(file_manager)
    
    # 注册内置工具
    register_builtin_tools(tool_registry, content_manager)
    
    # 显示已注册的工具
    tools = tool_registry.get_all_tools()
    print(f"\n✅ 已注册 {len(tools)} 个工具:")
    for tool in tools:
        print(f"   - {tool['function']['name']}: {tool['function']['description']}")
    
    # 获取第一个展板ID（用于测试）
    courses = file_manager.get_courses()
    if not courses:
        print("\n❌ 没有找到任何课程，无法测试")
        return
    
    # 找到第一个有展板的课程
    test_board_id = None
    for course in courses:
        boards = file_manager.get_boards(course['id'])
        if boards:
            test_board_id = boards[0]['id']
            break
    
    if not test_board_id:
        print("\n❌ 没有找到任何展板，无法测试")
        return
    
    print(f"\n📍 使用测试展板: {test_board_id}")
    
    # ========== 测试 1: 获取窗口列表 ==========
    print("\n" + "=" * 60)
    print("测试 1: 获取窗口列表")
    print("=" * 60)
    
    result = await tool_executor.execute_tool_call(
        ToolCall(
            id="call_test_001",
            type="function",
            function={
                "name": "get_windows",
                "arguments": {
                    "board_id": test_board_id
                }
            }
        ),
        context={}
    )
    
    print(f"状态: {result.status.value}")
    print(f"数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    # ========== 测试 2: 创建新窗口 ==========
    print("\n" + "=" * 60)
    print("测试 2: 创建新窗口")
    print("=" * 60)
    
    result = await tool_executor.execute_tool_call(
        ToolCall(
            id="call_test_002",
            type="function",
            function={
                "name": "create_window",
                "arguments": {
                    "board_id": test_board_id,
                    "title": "LLM 工具测试窗口",
                    "content": "# 这是一个测试窗口\n\n由 LLM 工具系统自动创建。\n\n- 测试项 1\n- 测试项 2\n- 测试项 3",
                    "position": {"x": 200, "y": 200},
                    "size": {"width": 500, "height": 400}
                }
            }
        ),
        context={}
    )
    
    print(f"状态: {result.status.value}")
    print(f"数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    if result.is_success():
        test_window_id = result.data.get("window_id")
        
        # ========== 测试 3: 读取窗口内容 ==========
        print("\n" + "=" * 60)
        print("测试 3: 读取窗口内容")
        print("=" * 60)
        
        result = await tool_executor.execute_tool_call(
            ToolCall(
                id="call_test_003",
                type="function",
                function={
                    "name": "read_window",
                    "arguments": {
                        "board_id": test_board_id,
                        "window_id": test_window_id
                    }
                }
            ),
            context={}
        )
        
        print(f"状态: {result.status.value}")
        if result.is_success():
            print(f"标题: {result.data.get('title')}")
            print(f"类型: {result.data.get('type')}")
            print(f"内容长度: {result.data.get('content_length')} 字符")
            print(f"内容预览:\n{result.data.get('content')[:200]}...")
        
        # ========== 测试 4: 更新窗口内容（追加） ==========
        print("\n" + "=" * 60)
        print("测试 4: 更新窗口内容（追加模式）")
        print("=" * 60)
        
        result = await tool_executor.execute_tool_call(
            ToolCall(
                id="call_test_004",
                type="function",
                function={
                    "name": "update_window",
                    "arguments": {
                        "board_id": test_board_id,
                        "window_id": test_window_id,
                        "content": "## 追加的内容\n\n这是通过 `append` 模式添加的新内容。\n\n当前时间: " + str(asyncio.get_event_loop().time()),
                        "mode": "append"
                    }
                }
            ),
            context={}
        )
        
        print(f"状态: {result.status.value}")
        print(f"数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
        
        # ========== 测试 5: 搜索窗口 ==========
        print("\n" + "=" * 60)
        print("测试 5: 搜索窗口")
        print("=" * 60)
        
        result = await tool_executor.execute_tool_call(
            ToolCall(
                id="call_test_005",
                type="function",
                function={
                    "name": "search_windows",
                    "arguments": {
                        "board_id": test_board_id,
                        "query": "测试",
                        "search_in": "both",
                        "limit": 5
                    }
                }
            ),
            context={}
        )
        
        print(f"状态: {result.status.value}")
        print(f"数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
        
        # ========== 测试 6: 删除窗口（移到回收站） ==========
        print("\n" + "=" * 60)
        print("测试 6: 删除窗口（移到回收站）")
        print("=" * 60)
        
        result = await tool_executor.execute_tool_call(
            ToolCall(
                id="call_test_006",
                type="function",
                function={
                    "name": "delete_window",
                    "arguments": {
                        "board_id": test_board_id,
                        "window_id": test_window_id,
                        "permanent": False
                    }
                }
            ),
            context={}
        )
        
        print(f"状态: {result.status.value}")
        print(f"数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

