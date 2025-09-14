#!/usr/bin/env python3
"""
测试动态文件扩展名处理功能
验证上传的文件类型能正确保存和显示
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:8081"

def test_dynamic_extension_handling():
    print("=== 测试动态文件扩展名处理功能 ===\n")
    
    # 1. 获取课程和板块信息
    print("1. 获取课程信息...")
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    if courses_response.status_code != 200:
        print(f"获取课程失败: {courses_response.status_code}")
        return
    
    courses_data = courses_response.json()
    courses = courses_data.get("courses", [])
    if not courses:
        print("没有找到课程")
        return
    
    course_id = courses[0]["id"]
    print(f"使用课程: {course_id}")
    
    # 获取板块信息
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    if boards_response.status_code != 200:
        print(f"获取板块失败: {boards_response.status_code}")
        return
    
    boards_data = boards_response.json()
    boards = boards_data.get("boards", [])
    if not boards:
        print("没有找到板块")
        return
    
    board_id = boards[0]["id"]
    print(f"使用板块: {board_id}")
    
    # 2. 创建测试图片窗口（默认为jpg）
    print("\n2. 创建图片窗口...")
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 100,
        "y": 100,
        "width": 300,
        "height": 200,
        "title": "测试图片窗口"
    })
    
    if create_response.status_code != 200:
        print(f"创建窗口失败: {create_response.status_code}")
        return
    
    window_data = create_response.json()
    window_id = window_data["id"]
    print(f"创建窗口成功: {window_id}")
    print(f"初始标题: {window_data.get('title', '未知')}")
    
    # 等待文件系统创建完成
    time.sleep(2)
    
    # 3. 创建测试PNG文件
    print("\n3. 创建测试PNG文件...")
    test_png_path = Path("test_image.png")
    # 创建一个简单的PNG文件内容（1x1像素的PNG）
    with open(test_png_path, "wb") as f:
        # 写入PNG文件头和最小内容
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 4. 上传PNG文件到图片窗口
    print("\n4. 上传PNG文件到图片窗口...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("test_image.png", f, "image/png")}
        data = {"file_type": "images"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data,
            params={"window_id": window_id}
        )
    
    print(f"上传响应状态: {upload_response.status_code}")
    if upload_response.status_code == 200:
        upload_result = upload_response.json()
        print(f"上传结果: {json.dumps(upload_result, ensure_ascii=False, indent=2)}")
    else:
        print(f"上传失败: {upload_response.text}")
        return
    
    # 等待文件处理完成
    time.sleep(3)
    
    # 5. 验证窗口信息更新
    print("\n5. 验证窗口信息...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.status_code != 200:
        print(f"获取窗口列表失败: {windows_response.status_code}")
        return
    
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    target_window = None
    for window in windows:
        if window["id"] == window_id:
            target_window = window
            break
    
    if target_window:
        print(f"窗口标题: {target_window.get('title', '未知')}")
        print(f"窗口内容URL: {target_window.get('content', '无')}")
        
        # 检查标题是否包含.png扩展名
        title = target_window.get('title', '')
        if title.endswith('.png'):
            print("✅ 成功：窗口标题包含正确的.png扩展名")
        else:
            print(f"❌ 失败：窗口标题不包含.png扩展名，当前标题：{title}")
        
        # 检查内容URL是否指向png文件
        content_url = target_window.get('content', '')
        if '.png' in content_url:
            print("✅ 成功：内容URL包含.png扩展名")
        else:
            print(f"❌ 失败：内容URL不包含.png扩展名，当前URL：{content_url}")
    else:
        print("❌ 失败：找不到目标窗口")
    
    # 6. 检查文件系统
    print("\n6. 检查文件系统...")
    backend_data_path = Path("backend/whatnote_data/courses")
    if backend_data_path.exists():
        for course_dir in backend_data_path.iterdir():
            if course_dir.is_dir() and course_dir.name.startswith("course-"):
                for board_dir in course_dir.iterdir():
                    if board_dir.is_dir() and board_dir.name.startswith("board-"):
                        files_dir = board_dir / "files"
                        if files_dir.exists():
                            print(f"检查文件夹: {files_dir}")
                            for file_path in files_dir.iterdir():
                                if file_path.is_file():
                                    print(f"  文件: {file_path.name}")
                                    if file_path.name.endswith('.png'):
                                        print("  ✅ 找到.png文件")
                                    elif file_path.name.endswith('.jpg') and 'test' in file_path.name.lower():
                                        print("  ❌ 发现多余的.jpg文件")
    
    # 清理测试文件
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")

if __name__ == "__main__":
    try:
        test_dynamic_extension_handling()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
