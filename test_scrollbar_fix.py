#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重命名时滚动条修复
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_scrollbar_fix():
    print("🔧 开始测试重命名滚动条修复...")
    
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
    
    # 创建专门用于测试滚动条修复的文件
    test_cases = [
        {
            "name": "极短文件名",
            "title": "短",
            "lines": 1,
            "description": "测试单字符文件名"
        },
        {
            "name": "两行文件名",
            "title": "这是一个两行显示的文件名测试",
            "lines": 2,
            "description": "测试两行文件名的滚动条"
        },
        {
            "name": "三行文件名",
            "title": "这是一个需要三行显示的比较长的文件名测试，用来验证滚动条修复",
            "lines": 3,
            "description": "测试三行文件名的滚动条"
        },
        {
            "name": "四行文件名",
            "title": "这是一个需要四行显示的很长很长的文件名测试，专门用来验证重命名时不会出现滚动条的问题修复效果",
            "lines": 4,
            "description": "测试四行文件名的滚动条"
        },
        {
            "name": "超长英文文件名",
            "title": "This is an extremely long English filename that should span multiple lines to test the scrollbar fix functionality in the renaming textarea component",
            "lines": 4,
            "description": "测试超长英文文件名的滚动条"
        },
        {
            "name": "混合超长文件名",
            "title": "中英文混合的超长文件名 Mixed very long filename with Chinese and English characters 用来测试滚动条修复功能是否正常工作 for testing scrollbar fix",
            "lines": 5,
            "description": "测试混合超长文件名的滚动条"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 创建测试用例 {i+1}: {test_case['name']}")
        print(f"   文件名: {test_case['title']}")
        print(f"   文件名长度: {len(test_case['title'])} 字符")
        print(f"   预期行数: {test_case['lines']} 行")
        print(f"   测试目的: {test_case['description']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"滚动条测试{i+1}",
            "content": f"{test_case['description']}的测试内容",
            "position": {"x": 50 + (i % 3) * 120, "y": 50 + (i // 3) * 150},  # 网格布局
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
            
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "expected_lines": test_case["lines"],
                "window_id": window_id,
                "status": "✅ 创建成功"
            })
        else:
            error_text = rename_response.text
            print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "expected_lines": test_case["lines"],
                "window_id": None,
                "status": f"❌ 失败: {rename_response.status_code}"
            })
    
    # 输出测试结果
    print("\n" + "="*80)
    print("📊 滚动条修复测试结果:")
    print("="*80)
    
    success_count = 0
    for result in test_results:
        print(f"{result['status']} {result['case']}")
        print(f"   文件名长度: {result['title_length']} 字符")
        print(f"   预期行数: {result['expected_lines']} 行")
        if result['window_id']:
            print(f"   窗口ID: {result['window_id']}")
        print()
        
        if "成功" in result['status']:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试用例创建成功")
    
    return success_count == len(test_results)

def show_scrollbar_fix_testing_guide():
    print("\n" + "="*80)
    print("🔧 滚动条修复测试指南:")
    print("="*80)
    print()
    print("📋 测试步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 右键点击任意测试图标，选择'重命名'")
    print("3. 观察重命名输入框是否出现滚动条")
    print("4. 尝试输入更长的文件名")
    print("5. 观察高度是否自动调整")
    print("6. 确认所有文字都完整可见")
    print()
    print("✅ 修复后的预期效果:")
    print("- 重命名输入框：无滚动条")
    print("- 高度调整：自动适应文本内容")
    print("- 文字显示：完整可见，无裁剪")
    print("- 背景样式：透明，融入选中框")
    print("- 边框样式：无独立边框")
    print()
    print("❌ 修复前的问题:")
    print("- 出现垂直滚动条")
    print("- 文字被裁剪或隐藏")
    print("- 高度限制过严格")
    print("- 用户体验不佳")
    print()
    print("🔧 技术修复要点:")
    print("- CSS: overflow: visible (而不是 hidden)")
    print("- CSS: height: auto (允许自动调整)")
    print("- JS: 移除最大高度限制")
    print("- JS: 使用实际宽度计算高度")
    print("- JS: 复制完整的计算样式")

def show_height_calculation_improvements():
    print("\n" + "="*80)
    print("📐 高度计算改进:")
    print("="*80)
    print()
    print("🔧 修复前的问题:")
    print("- 固定宽度: 64px (对长文件名不够)")
    print("- 最大高度限制: 3行 (无法显示更长文件名)")
    print("- 样式不完整: 缺少实际的计算样式")
    print("- 溢出处理: overflow: hidden (导致滚动条)")
    print()
    print("✅ 修复后的改进:")
    print("- 动态宽度: window.getComputedStyle(textarea).width")
    print("- 无高度限制: 移除maxHeight约束")
    print("- 完整样式复制: fontSize, fontFamily, lineHeight等")
    print("- 溢出处理: overflow: visible (允许内容显示)")
    print()
    print("📊 计算逻辑:")
    print("1. 创建隐藏的测试textarea")
    print("2. 复制原textarea的所有计算样式")
    print("3. 设置相同的内容和宽度")
    print("4. 测量scrollHeight获得实际需要的高度")
    print("5. 应用到原textarea，无最大高度限制")
    print()
    print("🎯 预期结果:")
    print("- 任意长度文件名都能完整显示")
    print("- 高度自动适应内容")
    print("- 无滚动条出现")
    print("- 保持Windows桌面风格")

if __name__ == "__main__":
    try:
        success = test_scrollbar_fix()
        show_scrollbar_fix_testing_guide()
        show_height_calculation_improvements()
        print(f"\n{'🎉 滚动条修复测试窗口创建完成，请按指南进行测试' if success else '💥 部分测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

