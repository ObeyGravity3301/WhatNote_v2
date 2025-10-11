#!/usr/bin/env python3
"""
测试真实占位文件系统
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def test_real_placeholder_system():
    print("=== 测试真实占位文件系统 ===\n")
    
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
    
    # 2. 创建图片窗口（应该创建新建图片.jpg占位文件）
    print("\n2. 创建图片窗口...")
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 150,
        "y": 150,
        "width": 300,
        "height": 200,
        "title": "测试真实占位文件"
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
    
    # 3. 验证占位文件创建
    print("\n3. 验证占位文件创建...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.status_code == 200:
        windows_data = windows_response.json()
        windows = windows_data.get("windows", [])
        
        target_window = None
        for window in windows:
            if window["id"] == window_id:
                target_window = window
                break
        
        if target_window:
            print(f"窗口标题: {target_window.get('title', '未知')}")
            print(f"文件路径: {target_window.get('file_path', '未知')}")
            
            # 检查是否有扩展名
            title = target_window.get('title', '')
            if '.jpg' in title:
                print("✅ 成功：占位文件包含扩展名")
            else:
                print(f"❌ 失败：占位文件不包含扩展名，标题：{title}")
    
    # 4. 创建测试PNG文件
    print("\n4. 创建测试PNG文件...")
    test_png_path = Path("test_replacement.png")
    # 创建一个简单的PNG文件内容（1x1像素的PNG）
    with open(test_png_path, "wb") as f:
        # 写入PNG文件头和最小内容
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 5. 上传PNG文件替换占位文件
    print("\n5. 上传PNG文件替换占位文件...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("test_replacement.png", f, "image/png")}
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
    
    # 6. 验证替换结果
    print("\n6. 验证替换结果...")
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
        print(f"更新后窗口标题: {target_window.get('title', '未知')}")
        print(f"更新后内容URL: {target_window.get('content', '无')}")
        
        # 检查标题是否包含.png扩展名
        title = target_window.get('title', '')
        if title.endswith('.png'):
            print("✅ 成功：窗口标题更新为PNG扩展名")
        else:
            print(f"❌ 失败：窗口标题未正确更新，当前标题：{title}")
        
        # 检查内容URL是否指向png文件
        content_url = target_window.get('content', '')
        if '.png' in content_url:
            print("✅ 成功：内容URL包含PNG扩展名")
        else:
            print(f"❌ 失败：内容URL不包含PNG扩展名，当前URL：{content_url}")
    else:
        print("❌ 失败：找不到目标窗口")
    
    # 7. 检查文件系统（确保只有一对文件）
    print("\n7. 检查文件系统...")
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    if backend_data_path.exists():
        for course_dir in backend_data_path.iterdir():
            if course_dir.is_dir() and course_dir.name.startswith("course-"):
                for board_dir in course_dir.iterdir():
                    if board_dir.is_dir() and board_dir.name.startswith("board-"):
                        files_dir = board_dir / "files"
                        if files_dir.exists():
                            print(f"检查文件夹: {files_dir}")
                            replacement_files = []
                            for file_path in files_dir.iterdir():
                                if file_path.is_file() and 'replacement' in file_path.name.lower():
                                    replacement_files.append(file_path.name)
                            
                            print(f"  找到相关文件: {replacement_files}")
                            
                            # 检查是否只有一对文件（.png和.png.json）
                            png_files = [f for f in replacement_files if f.endswith('.png') and not f.endswith('.json')]
                            json_files = [f for f in replacement_files if f.endswith('.png.json')]
                            
                            if len(png_files) == 1 and len(json_files) == 1:
                                print("  ✅ 成功：只有一对文件存在")
                            else:
                                print(f"  ❌ 失败：文件数量不正确，PNG文件: {len(png_files)}, JSON文件: {len(json_files)}")
    
    # 清理测试文件
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")

if __name__ == "__main__":
    try:
        test_real_placeholder_system()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
