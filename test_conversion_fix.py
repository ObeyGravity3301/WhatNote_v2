#!/usr/bin/env python3
"""
测试转换修复
"""
import requests
import json
import time

def test_conversion_fix():
    print("=== 测试转换修复 ===\n")
    
    base_url = "http://localhost:8081"
    
    # 1. 获取现有板块
    print("1. 获取现有板块...")
    courses_response = requests.get(f"{base_url}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{base_url}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    print(f"使用板块: {board_id}\n")
    
    # 2. 创建通用窗口
    print("2. 创建通用窗口...")
    window_data = {
        "title": "转换测试窗口",
        "type": "generic",
        "position": {"x": 100, "y": 100},
        "size": {"width": 400, "height": 300}
    }
    
    create_response = requests.post(
        f"{base_url}/api/boards/{board_id}/windows",
        json=window_data
    )
    
    window = create_response.json()
    window_id = window["id"]
    print(f"✅ 创建窗口: {window_id}\n")
    
    # 3. 等待一下确保文件系统稳定
    print("3. 等待文件系统稳定...")
    time.sleep(2)
    
    # 4. 检查窗口状态
    print("4. 检查转换前状态...")
    windows_response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    before_window = None
    for w in windows:
        if w["id"] == window_id:
            before_window = w
            break
    
    if before_window:
        print(f"转换前窗口类型: {before_window.get('type')}")
        print(f"转换前窗口标题: {before_window.get('title')}")
    else:
        print("❌ 找不到窗口")
        return
    
    # 5. 转换为文本窗口
    print("\n5. 转换为文本窗口...")
    convert_response = requests.post(
        f"{base_url}/api/windows/{window_id}/convert-to-text"
    )
    
    if convert_response.ok:
        print("✅ 转换请求成功")
    else:
        print(f"❌ 转换请求失败: {convert_response.status_code}")
        print(convert_response.text)
        return
    
    # 6. 等待转换完成
    print("\n6. 等待转换完成...")
    time.sleep(3)
    
    # 7. 检查转换结果
    print("7. 检查转换结果...")
    final_windows_response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
    if not final_windows_response.ok:
        print(f"❌ 获取窗口失败: {final_windows_response.status_code}")
        return
    
    final_windows_data = final_windows_response.json()
    final_windows = final_windows_data.get("windows", [])
    
    converted_window = None
    for w in final_windows:
        if w["id"] == window_id:
            converted_window = w
            break
    
    if converted_window:
        print(f"✅ 窗口仍然存在！")
        print(f"转换后窗口类型: {converted_window.get('type')}")
        print(f"转换后窗口标题: {converted_window.get('title')}")
        print(f"文件路径: {converted_window.get('file_path')}")
        
        if converted_window.get('type') == 'text':
            print("🎉 转换成功！窗口类型正确")
        else:
            print(f"⚠️ 窗口类型不对: {converted_window.get('type')}")
    else:
        print("❌ 窗口消失了！修复失败")
        print("现有窗口:")
        for w in final_windows:
            print(f"  - {w.get('id')}: {w.get('title')} ({w.get('type')})")

if __name__ == "__main__":
    test_conversion_fix()
