#!/usr/bin/env python3
"""
测试上传修复
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def test_upload_fix():
    print("=== 测试上传修复 ===\n")
    
    # 获取课程和板块信息
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses_data = courses_response.json()
    course_id = courses_data["courses"][0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards_data = boards_response.json()
    board_id = boards_data["boards"][0]["id"]
    
    print(f"使用板块: {board_id}")
    
    # 获取现有的调试窗口
    print("\n1. 查找现有调试窗口...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_window = None
    for window in windows:
        if "调试" in window.get("title", ""):
            debug_window = window
            break
    
    if not debug_window:
        print("没有找到调试窗口，创建新窗口...")
        create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
            "type": "image",
            "x": 100,
            "y": 100,
            "width": 300,
            "height": 200,
            "title": "修复测试图片"
        })
        debug_window = create_response.json()
        time.sleep(2)
    
    window_id = debug_window["id"]
    print(f"使用窗口: {window_id}")
    print(f"当前标题: {debug_window.get('title', '未知')}")
    
    # 创建测试PNG文件
    print("\n2. 创建测试PNG文件...")
    test_png_path = Path("upload_fix_test.png")
    with open(test_png_path, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 上传PNG文件
    print(f"\n3. 上传PNG文件到窗口 {window_id}...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("upload_fix_test.png", f, "image/png")}
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
        print(f"上传成功: {upload_result.get('filename', '未知')}")
    else:
        print(f"上传失败: {upload_response.text}")
        return
    
    # 等待处理完成
    time.sleep(3)
    
    # 验证结果
    print("\n4. 验证结果...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    # 查找所有相关窗口
    related_windows = []
    for window in windows:
        title = window.get("title", "")
        if "fix" in title.lower() or "修复" in title or "调试" in title:
            related_windows.append(window)
    
    print(f"找到相关窗口数量: {len(related_windows)}")
    
    for i, window in enumerate(related_windows):
        print(f"窗口{i+1}: ID={window['id'][:12]}..., 标题='{window.get('title')}', 文件路径='{window.get('file_path')}'")
        
        # 检查是否是我们的目标窗口
        if window['id'] == window_id:
            title = window.get('title', '')
            if title.endswith('.png'):
                print(f"  ✅ 目标窗口标题正确更新为PNG: {title}")
            else:
                print(f"  ❌ 目标窗口标题未正确更新: {title}")
    
    # 检查文件系统
    print("\n5. 检查文件系统...")
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    files_found = []
    
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        for file_path in files_dir.iterdir():
                            if file_path.is_file() and ('fix' in file_path.name.lower() or '修复' in file_path.name or '调试' in file_path.name):
                                files_found.append(file_path.name)
    
    print(f"找到相关文件: {files_found}")
    
    # 分析文件
    png_files = [f for f in files_found if f.endswith('.png') and not f.endswith('.json')]
    json_files = [f for f in files_found if f.endswith('.png.json')]
    incorrect_files = [f for f in files_found if '.png.jpg' in f]
    
    print(f"PNG文件: {png_files}")
    print(f"PNG JSON文件: {json_files}")
    print(f"错误文件(.png.jpg): {incorrect_files}")
    
    if len(png_files) == 1 and len(json_files) == 1 and len(incorrect_files) == 0:
        print("✅ 文件系统检查通过：只有一对正确的PNG文件")
    else:
        print("❌ 文件系统检查失败：存在错误或多余的文件")
    
    # 清理
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")

if __name__ == "__main__":
    try:
        test_upload_fix()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
