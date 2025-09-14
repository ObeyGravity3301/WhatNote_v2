#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试maxHeight错误修复
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_error_fix():
    print("🔧 开始测试maxHeight错误修复...")
    
    # 获取测试数据
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    if not courses_response.ok:
        print(f"❌ 获取课程失败: {courses_response.status_code}")
        return False
    
    courses = courses_response.json().get("courses", [])
    if not courses:
        print("❌ 没有找到课程")
        return False
    
    course_id = courses[0]["id"]
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    if not boards_response.ok:
        print(f"❌ 获取展板失败: {boards_response.status_code}")
        return False
    
    boards = boards_response.json().get("boards", [])
    if not boards:
        print("❌ 没有找到展板")
        return False
    
    board_id = boards[0]["id"]
    print(f"✅ 使用展板: {board_id}")
    
    # 创建一个测试文件来验证错误修复
    test_case = {
        "name": "错误修复测试",
        "title": "这是一个用来测试maxHeight错误修复的长文件名，应该不会再出现JavaScript运行时错误",
        "description": "测试JavaScript错误修复"
    }
    
    print(f"\n🧪 创建测试用例: {test_case['name']}")
    print(f"   文件名: {test_case['title']}")
    print(f"   文件名长度: {len(test_case['title'])} 字符")
    print(f"   测试目的: {test_case['description']}")
    
    # 创建测试窗口
    window_data = {
        "type": "text",
        "title": "错误修复测试",
        "content": f"{test_case['description']}的测试内容",
        "position": {"x": 100, "y": 100},
        "size": {"width": 300, "height": 200}
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/boards/{board_id}/windows",
        headers={"Content-Type": "application/json"},
        json=window_data
    )
    
    if not create_response.ok:
        print(f"❌ 创建窗口失败: {create_response.status_code}")
        return False
    
    new_window = create_response.json()
    window_id = new_window["id"]
    
    # 重命名为测试文件名
    rename_data = {"new_name": test_case["title"]}
    rename_response = requests.put(
        f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
        headers={"Content-Type": "application/json"},
        json=rename_data
    )
    
    if rename_response.ok:
        result = rename_response.json()
        print(f"✅ 测试窗口创建成功")
        print(f"   窗口ID: {window_id}")
        print(f"   新文件名: {result.get('new_name', '未知')}")
        return True
    else:
        error_text = rename_response.text
        print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
        return False

def show_error_fix_guide():
    print("\n" + "="*80)
    print("🔧 maxHeight错误修复指南:")
    print("="*80)
    print()
    print("❌ 修复前的错误:")
    print("- ReferenceError: maxHeight is not defined")
    print("- 错误位置: adjustTextareaHeight函数")
    print("- 错误原因: 移除了maxHeight变量定义，但保留了引用")
    print()
    print("✅ 修复内容:")
    print("- 移除了对未定义maxHeight变量的引用")
    print("- 将 textarea.style.overflowY = newHeight >= maxHeight ? 'auto' : 'hidden'")
    print("- 改为 textarea.style.overflowY = 'visible'")
    print("- 确保不显示滚动条，让内容完全可见")
    print()
    print("📋 测试步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 右键点击测试图标，选择'重命名'")
    print("3. 观察浏览器控制台是否还有错误")
    print("4. 尝试输入长文件名")
    print("5. 确认重命名功能正常工作")
    print()
    print("🎯 预期结果:")
    print("- 无JavaScript运行时错误")
    print("- 重命名功能正常")
    print("- 高度自动调整")
    print("- 无滚动条出现")
    print("- 所有文字完整显示")

def show_technical_details():
    print("\n" + "="*80)
    print("🔧 技术修复详情:")
    print("="*80)
    print()
    print("📝 问题分析:")
    print("- 在adjustTextareaHeight函数中移除了maxHeight变量定义")
    print("- 但在函数末尾仍然引用了maxHeight变量")
    print("- 导致ReferenceError: maxHeight is not defined")
    print()
    print("🛠️ 修复方案:")
    print("- 方案1: 重新定义maxHeight变量（保留限制）")
    print("- 方案2: 移除maxHeight引用（选择的方案）")
    print("- 方案3: 使用条件判断避免引用")
    print()
    print("✅ 实施的修复:")
    print("```javascript")
    print("// 修复前:")
    print("textarea.style.overflowY = newHeight >= maxHeight ? 'auto' : 'hidden';")
    print("")
    print("// 修复后:")
    print("textarea.style.overflowY = 'visible';")
    print("```")
    print()
    print("🎯 修复优势:")
    print("- 彻底解决了maxHeight未定义错误")
    print("- 简化了代码逻辑")
    print("- 确保内容始终完全可见")
    print("- 符合我们移除高度限制的设计目标")

if __name__ == "__main__":
    try:
        success = test_error_fix()
        show_error_fix_guide()
        show_technical_details()
        print(f"\n{'🎉 错误修复测试完成，请在浏览器中验证重命名功能' if success else '💥 测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

