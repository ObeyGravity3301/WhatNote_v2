#!/usr/bin/env python3
"""
调试上传过程
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def debug_upload_process():
    print("=== 调试上传过程 ===\n")
    
    # 获取课程和板块信息
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses_data = courses_response.json()
    course_id = courses_data["courses"][0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards_data = boards_response.json()
    board_id = boards_data["boards"][0]["id"]
    
    print(f"使用板块: {board_id}")
    
    # 1. 清理现有文件
    print("\n1. 清理现有文件...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.status_code == 200:
        windows_data = windows_response.json()
        windows = windows_data.get("windows", [])
        
        for window in windows:
            if "debug" in window.get("title", "").lower():
                print(f"删除调试窗口: {window['id']}")
                requests.delete(f"{BASE_URL}/api/boards/{board_id}/windows/{window['id']}", params={"permanent": "true"})
    
    time.sleep(1)
    
    # 2. 创建新窗口
    print("\n2. 创建新窗口...")
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 100,
        "y": 100,
        "width": 300,
        "height": 200,
        "title": "调试图片窗口"
    })
    
    window_data = create_response.json()
    window_id = window_data["id"]
    print(f"创建窗口: {window_id}")
    print(f"初始标题: {window_data.get('title', '未知')}")
    
    time.sleep(2)
    
    # 3. 检查初始状态
    print("\n3. 检查初始状态...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_windows = [w for w in windows if w["id"] == window_id]
    print(f"找到匹配窗口数量: {len(debug_windows)}")
    
    if debug_windows:
        window = debug_windows[0]
        print(f"窗口标题: {window.get('title')}")
        print(f"文件路径: {window.get('file_path')}")
    
    # 检查文件系统
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    files_found = []
    
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        for file_path in files_dir.iterdir():
                            if file_path.is_file() and '调试' in file_path.name:
                                files_found.append(file_path.name)
    
    print(f"文件系统中的文件: {files_found}")
    
    # 4. 创建测试文件
    print("\n4. 创建测试文件...")
    test_png_path = Path("debug_test.png")
    with open(test_png_path, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 5. 上传文件
    print("\n5. 上传文件...")
    print(f"目标窗口ID: {window_id}")
    
    with open(test_png_path, "rb") as f:
        files = {"file": ("debug_test.png", f, "image/png")}
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
    
    # 6. 立即检查状态（避免文件监控器干扰）
    print("\n6. 立即检查状态...")
    time.sleep(1)
    
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_windows = [w for w in windows if "debug" in w.get("title", "").lower()]
    print(f"找到调试相关窗口数量: {len(debug_windows)}")
    
    for i, window in enumerate(debug_windows):
        print(f"窗口{i+1}: ID={window['id'][:12]}..., 标题='{window.get('title')}', 文件路径='{window.get('file_path')}'")
    
    # 检查文件系统
    files_found = []
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        for file_path in files_dir.iterdir():
                            if file_path.is_file() and 'debug' in file_path.name.lower():
                                files_found.append(file_path.name)
    
    print(f"文件系统中的debug文件: {files_found}")
    
    # 7. 等待文件监控器处理
    print("\n7. 等待文件监控器处理...")
    time.sleep(3)
    
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_windows = [w for w in windows if "debug" in w.get("title", "").lower()]
    print(f"最终调试相关窗口数量: {len(debug_windows)}")
    
    for i, window in enumerate(debug_windows):
        print(f"最终窗口{i+1}: ID={window['id'][:12]}..., 标题='{window.get('title')}', 文件路径='{window.get('file_path')}'")
    
    # 最终文件检查
    files_found = []
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        for file_path in files_dir.iterdir():
                            if file_path.is_file() and 'debug' in file_path.name.lower():
                                files_found.append(file_path.name)
    
    print(f"最终文件系统中的debug文件: {files_found}")
    
    # 清理
    if test_png_path.exists():
        test_png_path.unlink()

if __name__ == "__main__":
    try:
        debug_upload_process()
    except Exception as e:
        print(f"调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
