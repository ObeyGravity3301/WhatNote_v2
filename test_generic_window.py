#!/usr/bin/env python3
"""
测试通用窗口创建
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8081"

def test_generic_window_creation():
    print("=" * 60)
    print("测试通用窗口创建")
    print("=" * 60)
    
    try:
        # 获取课程和板块信息
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_response.raise_for_status()
        courses = courses_response.json()["courses"]
        course_id = courses[0]["id"]
        
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_response.raise_for_status()
        boards = boards_response.json()["boards"]
        board_id = boards[0]["id"]
        
        print(f"使用课程: {course_id}")
        print(f"使用板块: {board_id}")
        
        # 创建通用窗口
        window_data = {
            "type": "generic",
            "title": "测试通用窗口",
            "x": 100,
            "y": 100,
            "width": 300,
            "height": 200
        }
        
        print(f"\n创建通用窗口...")
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            json=window_data
        )
        
        print(f"创建响应状态: {create_response.status_code}")
        
        if create_response.status_code == 200:
            print("✅ 通用窗口创建成功")
            window_info = create_response.json()
            print(f"窗口ID: {window_info['id']}")
            print(f"窗口标题: {window_info['title']}")
            print(f"窗口类型: {window_info['type']}")
            print(f"文件路径: {window_info.get('file_path', 'None')}")
        else:
            print(f"❌ 创建失败: {create_response.text}")
            
        # 检查窗口列表
        print(f"\n检查窗口列表...")
        windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        windows_response.raise_for_status()
        windows = windows_response.json()["windows"]
        
        print(f"当前窗口总数: {len(windows)}")
        for window in windows:
            if window.get('type') == 'generic':
                print(f"  通用窗口: {window['id']} - {window['title']}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generic_window_creation()
