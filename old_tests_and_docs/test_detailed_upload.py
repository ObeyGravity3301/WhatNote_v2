#!/usr/bin/env python3
"""
详细日志上传测试
"""

import requests
import json
from PIL import Image
import os
import time

# 服务器配置
BASE_URL = "http://127.0.0.1:8081"

def main():
    print("=" * 80)
    print("🧪 详细日志上传测试")
    print("=" * 80)
    
    try:
        # 1. 获取课程列表
        print("\n1️⃣ 获取课程列表...")
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_response.raise_for_status()
        courses = courses_response.json()["courses"]
        
        if not courses:
            print("❌ 没有找到课程")
            return
            
        course_id = courses[0]["id"]
        print(f"✅ 使用课程: {course_id}")
        
        # 2. 获取板块列表
        print(f"\n2️⃣ 获取板块列表...")
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_response.raise_for_status()
        boards = boards_response.json()["boards"]
        
        if not boards:
            print("❌ 没有找到板块")
            return
            
        board_id = boards[0]["id"]
        print(f"✅ 使用板块: {board_id}")
        
        # 3. 获取窗口列表
        print(f"\n3️⃣ 获取窗口列表...")
        windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        windows_response.raise_for_status()
        windows = windows_response.json()["windows"]
        
        if not windows:
            print("❌ 没有找到窗口")
            return
        
        # 找一个图片类型的窗口
        target_window = None
        for window in windows:
            if window.get("type") == "image":
                target_window = window
                break
                
        if not target_window:
            print("❌ 没有找到图片类型的窗口")
            return
            
        window_id = target_window["id"]
        window_title = target_window.get("title", "未知")
        print(f"✅ 使用窗口: {window_id}")
        print(f"   当前标题: {window_title}")
        
        # 4. 创建测试文件
        print(f"\n4️⃣ 创建测试GIF文件...")
        test_filename = f"detailed_test_{int(time.time())}.gif"
        
        # 创建一个简单的GIF图片
        img = Image.new('RGB', (100, 100), color='green')
        img.save(test_filename, 'GIF')
        print(f"✅ 创建测试文件: {test_filename}")
        
        # 5. 上传文件
        print(f"\n5️⃣ 上传GIF文件到窗口 {window_id}...")
        print("=" * 60)
        print("🚀 开始上传，观察后端日志...")
        print("=" * 60)
        
        with open(test_filename, 'rb') as f:
            files = {'file': (test_filename, f, 'image/gif')}
            data = {'file_type': 'images'}
            params = {'window_id': window_id}
            
            upload_response = requests.post(
                f"{BASE_URL}/api/boards/{board_id}/upload",
                files=files,
                data=data,
                params=params
            )
        
        print("=" * 60)
        print(f"📊 上传响应状态: {upload_response.status_code}")
        if upload_response.status_code == 200:
            print("✅ 上传成功")
            response_data = upload_response.json()
            print(f"📄 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 上传失败: {upload_response.text}")
        
        # 6. 清理测试文件
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print(f"🗑️ 清理测试文件: {test_filename}")
            
        print("\n" + "=" * 80)
        print("🎯 测试完成！请检查后端日志中的详细信息")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
