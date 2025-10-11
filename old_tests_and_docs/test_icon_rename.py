#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试桌面图标重命名功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_icon_rename_functionality():
    print("🖱️ 开始测试桌面图标重命名功能...")
    
    # 1. 获取所有课程
    print("\n📚 获取课程列表...")
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    if not courses_response.ok:
        print(f"❌ 获取课程失败: {courses_response.status_code}")
        return False
    
    courses = courses_response.json().get("courses", [])
    if not courses:
        print("❌ 没有找到课程")
        return False
    
    course_id = courses[0]["id"]
    print(f"✅ 找到课程: {course_id}")
    
    # 2. 获取课程的展板
    print(f"\n📋 获取课程 {course_id} 的展板列表...")
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    if not boards_response.ok:
        print(f"❌ 获取展板失败: {boards_response.status_code}")
        return False
    
    boards = boards_response.json().get("boards", [])
    if not boards:
        print("❌ 没有找到展板")
        return False
    
    board_id = boards[0]["id"]
    print(f"✅ 找到展板: {board_id}")
    
    # 3. 获取展板的窗口（桌面图标）
    print(f"\n🪟 获取展板 {board_id} 的窗口列表...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if not windows_response.ok:
        print(f"❌ 获取窗口失败: {windows_response.status_code}")
        return False
    
    windows = windows_response.json().get("windows", [])
    if not windows:
        print("ℹ️ 展板没有窗口，创建一个测试窗口...")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": "图标重命名测试",
            "content": "这是一个测试图标重命名的窗口",
            "position": {"x": 100, "y": 100},
            "size": {"width": 400, "height": 300}
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            headers={"Content-Type": "application/json"},
            json=window_data
        )
        
        if not create_response.ok:
            print(f"❌ 创建测试窗口失败: {create_response.status_code}")
            return False
        
        new_window = create_response.json()
        window_id = new_window["id"]
        original_title = new_window["title"]
        print(f"✅ 创建了测试窗口: {window_id}")
    else:
        window_id = windows[0]["id"]
        original_title = windows[0]["title"]
        print(f"✅ 找到窗口: {window_id} (标题: {original_title})")
    
    # 4. 测试重命名功能（模拟右键菜单重命名）
    print(f"\n🔄 测试图标重命名 {window_id}...")
    new_name = f"重命名图标_{int(time.time())}"
    
    rename_data = {"new_name": new_name}
    rename_response = requests.put(
        f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
        headers={"Content-Type": "application/json"},
        json=rename_data
    )
    
    if rename_response.ok:
        result = rename_response.json()
        print(f"✅ 图标重命名成功!")
        print(f"   新文件名: {result.get('new_filename', 'N/A')}")
        print(f"   响应消息: {result.get('message', 'N/A')}")
        
        # 5. 验证重命名结果
        print(f"\n🔍 验证重命名结果...")
        verify_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        if verify_response.ok:
            updated_windows = verify_response.json().get("windows", [])
            renamed_window = next((w for w in updated_windows if w["id"] == window_id), None)
            
            if renamed_window and renamed_window["title"] == new_name:
                print(f"✅ 验证成功! 图标标题已更新为: {renamed_window['title']}")
                print(f"   文件路径: {renamed_window.get('file_path', 'N/A')}")
                
                # 6. 测试命名冲突处理
                print(f"\n🔄 测试命名冲突处理...")
                conflict_rename_response = requests.put(
                    f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
                    headers={"Content-Type": "application/json"},
                    json={"new_name": new_name}  # 使用相同的名称
                )
                
                if conflict_rename_response.ok:
                    conflict_result = conflict_rename_response.json()
                    print(f"✅ 命名冲突处理成功!")
                    print(f"   新文件名: {conflict_result.get('new_filename', 'N/A')}")
                    
                    # 验证冲突处理结果
                    verify2_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
                    if verify2_response.ok:
                        final_windows = verify2_response.json().get("windows", [])
                        final_window = next((w for w in final_windows if w["id"] == window_id), None)
                        
                        if final_window and "(1)" in final_window["title"]:
                            print(f"✅ 命名冲突验证成功! 最终标题: {final_window['title']}")
                            return True
                        else:
                            print(f"❌ 命名冲突验证失败! 标题: {final_window['title'] if final_window else 'N/A'}")
                            return False
                    else:
                        print(f"❌ 冲突验证请求失败: {verify2_response.status_code}")
                        return False
                else:
                    print(f"❌ 命名冲突处理失败: {conflict_rename_response.status_code}")
                    return False
                
            else:
                print(f"❌ 验证失败! 图标标题未正确更新")
                print(f"   期望: {new_name}")
                print(f"   实际: {renamed_window['title'] if renamed_window else 'N/A'}")
                return False
        else:
            print(f"❌ 验证请求失败: {verify_response.status_code}")
            return False
    else:
        error_text = rename_response.text
        print(f"❌ 图标重命名失败: {rename_response.status_code}")
        print(f"   错误信息: {error_text}")
        return False

if __name__ == "__main__":
    try:
        success = test_icon_rename_functionality()
        if success:
            print("\n🎉 桌面图标重命名功能测试通过!")
        else:
            print("\n💥 桌面图标重命名功能测试失败!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

