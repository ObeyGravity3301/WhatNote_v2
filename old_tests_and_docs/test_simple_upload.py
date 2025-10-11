#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试：创建窗口并上传文件
"""
import requests
import json
import time
import tempfile
from pathlib import Path

BASE_URL = "http://localhost:8081"

def create_test_file(filename, content="测试内容"):
    """创建测试文件"""
    temp_dir = Path(tempfile.gettempdir()) / "whatnote_test"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return file_path

def simple_upload_test():
    print("🧪 简单上传测试")
    
    # 获取展板ID
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    print(f"使用展板: {board_id}")
    
    # 创建窗口
    window_data = {
        "type": "image",
        "title": "测试窗口123",
        "content": "",
        "position": {"x": 100, "y": 100},
        "size": {"width": 400, "height": 300}
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/boards/{board_id}/windows",
        headers={"Content-Type": "application/json"},
        json=window_data
    )
    
    window_id = create_response.json()["id"]
    print(f"创建窗口: {window_id}")
    
    time.sleep(1)
    
    # 上传文件
    test_file = create_test_file("上传图片123.jpg", "测试图片内容")
    
    with open(test_file, "rb") as f:
        files = {"file": ("上传图片123.jpg", f, "image/jpeg")}
        data = {
            "file_type": "images",
            "window_id": window_id
        }
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data
        )
    
    if upload_response.ok:
        print("✅ 上传成功")
        result = upload_response.json()
        print(f"返回: {result}")
    else:
        print(f"❌ 上传失败: {upload_response.status_code}")
        print(f"错误: {upload_response.text}")
    
    test_file.unlink()
    
    # 等待处理
    time.sleep(3)
    
    # 检查窗口状态
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows = windows_response.json().get("windows", [])
    
    for window in windows:
        if window.get("id") == window_id:
            print(f"\n窗口信息:")
            print(f"  ID: {window.get('id')}")
            print(f"  标题: {window.get('title')}")
            print(f"  文件路径: {window.get('file_path')}")
            print(f"  内容: {window.get('content', '')[:100]}...")
            break

if __name__ == "__main__":
    simple_upload_test()

