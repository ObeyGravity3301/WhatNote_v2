#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试应用中的键盘输入问题
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def create_test_window_for_input_test():
    print("🧪 创建专门用于键盘输入测试的窗口...")
    
    # 获取测试数据
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    # 创建一个专门用于键盘输入测试的窗口
    window_data = {
        "type": "text",
        "title": "键盘输入测试窗口",
        "content": "请在浏览器中右键点击这个图标，选择重命名，然后测试键盘输入",
        "position": {"x": 50, "y": 50},
        "size": {"width": 300, "height": 150}
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/boards/{board_id}/windows",
        headers={"Content-Type": "application/json"},
        json=window_data
    )
    
    if create_response.ok:
        new_window = create_response.json()
        print(f"✅ 创建测试窗口成功: {new_window['id']}")
        print(f"📍 窗口位置: ({new_window['position']['x']}, {new_window['position']['y']})")
        print()
        print("📋 测试步骤:")
        print("1. 在浏览器中打开 http://localhost:3000")
        print("2. 找到标题为 '键盘输入测试窗口' 的桌面图标")
        print("3. 右键点击该图标，选择 '重命名'")
        print("4. 使用英文输入法，逐个字符输入测试文本")
        print("5. 观察是否出现每次只显示一个字符的问题")
        print()
        print("🔍 预期行为:")
        print("- 输入框应该能正常接受连续的字符输入")
        print("- 高度应该根据内容长度自动调整")
        print("- 不应该出现输入被截断或重置的问题")
        print()
        print("⚠️ 如果发现问题:")
        print("- 请注意观察每次按键后输入框的内容变化")
        print("- 检查浏览器控制台是否有错误信息")
        print("- 尝试不同长度的文本输入")
        
        return True
    else:
        print(f"❌ 创建测试窗口失败: {create_response.status_code}")
        return False

def show_debugging_tips():
    print("\n" + "="*60)
    print("🛠️ 调试提示:")
    print("="*60)
    print()
    print("如果遇到输入问题，可能的原因和解决方案:")
    print()
    print("1. 高度调整干扰输入:")
    print("   - 检查 adjustTextareaHeight 函数是否过于频繁调用")
    print("   - 确保防抖机制正常工作")
    print()
    print("2. CSS样式冲突:")
    print("   - 检查 textarea 的样式是否稳定")
    print("   - 确保没有transition动画干扰")
    print()
    print("3. React状态更新问题:")
    print("   - 检查 onChange 事件处理是否正确")
    print("   - 确保状态更新不会导致组件重新渲染")
    print()
    print("4. 浏览器兼容性:")
    print("   - 在不同浏览器中测试")
    print("   - 检查开发者工具中的错误信息")

if __name__ == "__main__":
    try:
        success = create_test_window_for_input_test()
        if success:
            show_debugging_tips()
        print(f"\n{'✅ 测试窗口创建完成' if success else '❌ 测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 创建测试窗口时发生异常: {e}")

