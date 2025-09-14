#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件名显示和交互改进
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_filename_display_improvements():
    print("🔧 开始测试文件名显示和交互改进...")
    
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
    
    # 创建测试用例：专门用于测试显示改进的文件
    test_cases = [
        {
            "name": "垂直对齐测试",
            "title": "测试第一行显示完整性",
            "description": "测试文件名第一行是否完整显示"
        },
        {
            "name": "单击显示测试",
            "title": "这是一个用于测试单击显示完整文件名功能的长文件名",
            "description": "测试单击后是否显示完整文件名"
        },
        {
            "name": "重命名显示测试", 
            "title": "重命名时应该显示完整的原始文件名而不是截断后的名称",
            "description": "测试重命名时是否显示完整文件名"
        },
        {
            "name": "交互测试",
            "title": "用于测试各种交互功能的综合测试文件名_包含特殊字符@符号#和数字123",
            "description": "测试各种交互功能"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 创建测试用例 {i+1}: {test_case['name']}")
        print(f"   文件名: {test_case['title']}")
        print(f"   用途: {test_case['description']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"临时{i+1}",  # 先用短名称创建
            "content": f"用于{test_case['description']}的测试内容",
            "position": {"x": 50 + i*80, "y": 50 + i*60},
            "size": {"width": 300, "height": 200}
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            headers={"Content-Type": "application/json"},
            json=window_data
        )
        
        if not create_response.ok:
            print(f"❌ 创建窗口失败: {create_response.status_code}")
            continue
        
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
            print(f"✅ 创建成功")
            print(f"   窗口ID: {window_id}")
            print(f"   新文件名: {result.get('new_filename', 'N/A')}")
            
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "window_id": window_id,
                "status": "✅ 创建成功"
            })
        else:
            error_text = rename_response.text
            print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "window_id": None,
                "status": f"❌ 失败: {rename_response.status_code}"
            })
    
    # 输出测试结果和使用说明
    print("\n" + "="*80)
    print("📊 文件名显示改进测试结果:")
    print("="*80)
    
    success_count = 0
    for result in test_results:
        print(f"{result['status']} {result['case']}")
        if result['window_id']:
            print(f"   窗口ID: {result['window_id']}")
        print()
        
        if "成功" in result['status']:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试窗口创建成功")
    
    return success_count == len(test_results)

def show_testing_instructions():
    print("\n" + "="*80)
    print("📋 手动测试说明:")
    print("="*80)
    print()
    print("🔍 测试项目1: 文件名垂直对齐")
    print("- 在浏览器中打开 http://localhost:3000")
    print("- 观察桌面图标的文件名显示")
    print("- 检查第一行文字是否完整显示（不应该被截断上半部分）")
    print()
    print("🔍 测试项目2: 单击显示完整文件名")
    print("- 单击任何长文件名的图标")
    print("- 应该在图标下方弹出黑色背景的完整文件名")
    print("- 再次单击同一图标应该隐藏完整文件名")
    print("- 单击其他地方应该自动隐藏完整文件名")
    print()
    print("🔍 测试项目3: 重命名时显示完整文件名")
    print("- 右键点击长文件名图标，选择'重命名'")
    print("- 输入框中应该显示完整的原始文件名")
    print("- 输入框应该能根据内容自动调整高度")
    print("- 按Enter确认或Esc取消")
    print()
    print("✅ 预期效果:")
    print("- 文字不再覆盖图标")
    print("- 第一行文字完整显示")
    print("- 单击可查看完整文件名")
    print("- 重命名时操作完整文件名")
    print("- 交互流畅，无显示问题")

def show_css_improvements():
    print("\n" + "="*80)
    print("🎨 CSS改进说明:")
    print("="*80)
    print()
    print("垂直对齐修复:")
    print("- align-items: flex-start (顶部对齐)")
    print("- padding-top: 1px (确保第一行完整)")
    print("- overflow: visible (允许完整文件名超出)")
    print()
    print("完整文件名显示:")
    print("- position: absolute (绝对定位)")
    print("- background: rgba(0,0,0,0.8) (半透明黑色背景)")
    print("- z-index: 1000 (确保在最上层)")
    print("- max-width: 200px (限制最大宽度)")
    print("- box-shadow: 阴影效果")
    print()
    print("交互改进:")
    print("- 点击显示/隐藏完整文件名")
    print("- 重命名时自动隐藏完整文件名显示")
    print("- 点击空白区域自动隐藏")

if __name__ == "__main__":
    try:
        success = test_filename_display_improvements()
        show_testing_instructions()
        show_css_improvements()
        print(f"\n{'🎉 测试窗口创建完成，请按说明进行手动测试' if success else '💥 部分测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

