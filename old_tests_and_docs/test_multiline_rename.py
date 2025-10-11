#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多行重命名功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_multiline_rename():
    print("📝 开始测试多行重命名功能...")
    
    # 1. 获取测试数据
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
    
    # 2. 创建测试窗口
    test_cases = [
        {
            "name": "短名称",
            "title": "短名称测试"
        },
        {
            "name": "中等长度名称", 
            "title": "这是一个中等长度的文件名称测试"
        },
        {
            "name": "长名称",
            "title": "这是一个非常非常长的文件名称，用来测试多行显示功能是否正常工作，应该会自动换行显示"
        },
        {
            "name": "包含特殊字符",
            "title": "测试文件 - 包含特殊字符 & 符号 (2024)"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 测试用例 {i+1}: {test_case['name']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"测试窗口{i+1}",
            "content": "测试内容",
            "position": {"x": 100 + i*50, "y": 100 + i*50},
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
        
        # 测试重命名为长名称
        rename_data = {"new_name": test_case["title"]}
        rename_response = requests.put(
            f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
            headers={"Content-Type": "application/json"},
            json=rename_data
        )
        
        if rename_response.ok:
            result = rename_response.json()
            print(f"✅ 重命名成功: {test_case['title']}")
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
                        "status": "✅ 成功"
                    })
                else:
                    test_results.append({
                        "case": test_case["name"], 
                        "title": test_case["title"],
                        "title_length": len(test_case["title"]),
                        "status": "❌ 验证失败"
                    })
            else:
                test_results.append({
                    "case": test_case["name"],
                    "title": test_case["title"], 
                    "title_length": len(test_case["title"]),
                    "status": "❌ 验证请求失败"
                })
        else:
            error_text = rename_response.text
            print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "status": f"❌ 重命名失败: {rename_response.status_code}"
            })
    
    # 3. 输出测试结果总结
    print("\n" + "="*60)
    print("📊 多行重命名功能测试结果总结:")
    print("="*60)
    
    success_count = 0
    for result in test_results:
        print(f"{result['status']} {result['case']}")
        print(f"   标题: {result['title']}")
        print(f"   长度: {result['title_length']} 字符")
        print(f"   预期行数: {max(1, len(result['title']) // 20)}")  # 估算行数
        print()
        
        if "成功" in result['status']:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试用例通过")
    
    if success_count == len(test_results):
        print("🎉 所有多行重命名测试通过!")
        return True
    else:
        print("💥 部分测试失败!")
        return False

if __name__ == "__main__":
    try:
        success = test_multiline_rename()
        print(f"\n{'🎉 测试通过' if success else '💥 测试失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

