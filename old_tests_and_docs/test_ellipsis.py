#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试长文件名省略号显示功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_ellipsis_functionality():
    print("✂️ 开始测试长文件名省略号显示功能...")
    
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
    
    # 测试用例：不同长度的文件名
    test_cases = [
        {
            "name": "短文件名",
            "title": "短文件",
            "expected": "不截断"
        },
        {
            "name": "中等长度",
            "title": "这是一个中等长度的文件名",
            "expected": "不截断或轻微截断"
        },
        {
            "name": "长文件名（中文）",
            "title": "这是一个非常非常长的中文文件名，应该会被截断并显示省略号，不会覆盖图标",
            "expected": "截断并显示省略号"
        },
        {
            "name": "长文件名（英文）",
            "title": "This is a very very long English filename that should be truncated with ellipsis and not cover the icon",
            "expected": "截断并显示省略号"
        },
        {
            "name": "超长文件名（混合）",
            "title": "这是一个超级超级超级长的混合语言文件名 This filename is extremely long with mixed languages 应该被正确截断处理",
            "expected": "截断并显示省略号"
        },
        {
            "name": "包含特殊字符",
            "title": "长文件名_with-special.characters@and#symbols$that%should^be&handled*properly(2024)",
            "expected": "在合适的位置截断"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 测试用例 {i+1}: {test_case['name']}")
        print(f"   原始标题: {test_case['title']}")
        print(f"   标题长度: {len(test_case['title'])} 字符")
        print(f"   预期效果: {test_case['expected']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"测试{i+1}",  # 先用短名称创建
            "content": "省略号显示测试",
            "position": {"x": 100 + i*70, "y": 100 + (i//4)*100},  # 网格排列
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
        
        # 重命名为长文件名
        rename_data = {"new_name": test_case["title"]}
        rename_response = requests.put(
            f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
            headers={"Content-Type": "application/json"},
            json=rename_data
        )
        
        if rename_response.ok:
            result = rename_response.json()
            print(f"✅ 重命名成功")
            print(f"   新文件名: {result.get('new_filename', 'N/A')}")
            
            # 验证重命名结果
            verify_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
            if verify_response.ok:
                windows = verify_response.json().get("windows", [])
                renamed_window = next((w for w in windows if w["id"] == window_id), None)
                
                if renamed_window and renamed_window["title"] == test_case["title"]:
                    test_results.append({
                        "case": test_case["name"],
                        "title": test_case["title"],
                        "title_length": len(test_case["title"]),
                        "window_id": window_id,
                        "status": "✅ 创建成功"
                    })
                    print(f"✅ 验证成功")
                else:
                    test_results.append({
                        "case": test_case["name"],
                        "title": test_case["title"],
                        "title_length": len(test_case["title"]),
                        "window_id": window_id,
                        "status": "❌ 验证失败"
                    })
                    print(f"❌ 验证失败")
            else:
                test_results.append({
                    "case": test_case["name"],
                    "title": test_case["title"],
                    "title_length": len(test_case["title"]),
                    "window_id": window_id,
                    "status": "❌ 验证请求失败"
                })
        else:
            error_text = rename_response.text
            print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "window_id": None,
                "status": f"❌ 重命名失败: {rename_response.status_code}"
            })
    
    # 输出测试结果总结
    print("\n" + "="*80)
    print("📊 省略号显示功能测试结果总结:")
    print("="*80)
    
    success_count = 0
    for result in test_results:
        print(f"{result['status']} {result['case']}")
        print(f"   标题长度: {result['title_length']} 字符")
        if result['window_id']:
            print(f"   窗口ID: {result['window_id']}")
        print()
        
        if "成功" in result['status']:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试用例创建成功")
    print()
    print("📋 手动验证步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 观察桌面图标的文件名显示效果")
    print("3. 检查长文件名是否正确显示省略号")
    print("4. 悬停鼠标查看是否显示完整文件名")
    print("5. 确认文字没有覆盖图标")
    
    return success_count == len(test_results)

def show_ellipsis_algorithm_info():
    print("\n" + "="*80)
    print("🔧 省略号算法说明:")
    print("="*80)
    print()
    print("算法参数:")
    print("- 图标宽度: 64px")
    print("- 字体大小: 11px")
    print("- 预估字符宽度: 6px")
    print("- 每行字符数: ~10个")
    print("- 最大行数: 3行")
    print("- 最大字符数: ~30个")
    print()
    print("截断策略:")
    print("1. 如果文本长度 ≤ 最大字符数，不截断")
    print("2. 否则截断到(最大字符数-3)位置，添加'...'")
    print("3. 尝试在单词边界或标点符号处截断（英文）")
    print("4. 如果边界截断点合理（>70%最大长度），使用边界截断")
    print()
    print("显示特性:")
    print("- CSS限制最大高度为39px（3行）")
    print("- 使用-webkit-line-clamp限制行数")
    print("- 悬停显示完整标题")
    print("- 防止文字覆盖图标")

if __name__ == "__main__":
    try:
        success = test_ellipsis_functionality()
        show_ellipsis_algorithm_info()
        print(f"\n{'🎉 测试完成，请在浏览器中验证显示效果' if success else '💥 部分测试失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

