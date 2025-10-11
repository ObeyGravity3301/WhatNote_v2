#!/usr/bin/env python3
"""
测试最终修复：真实占位文件 + 竞态条件修复
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def test_final_fix():
    print("=== 测试最终修复效果 ===\n")
    
    # 1. 获取课程和板块信息
    print("1. 获取课程信息...")
    try:
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
        
    except Exception as e:
        print(f"连接服务失败: {e}")
        return
    
    # 2. 创建图片窗口（测试真实占位文件）
    print("\n2. 创建图片窗口...")
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 100,
        "y": 100,
        "width": 300,
        "height": 200,
        "title": "最终测试图片"
    })
    
    if create_response.status_code != 200:
        print(f"创建窗口失败: {create_response.status_code}")
        return
    
    window_data = create_response.json()
    window_id = window_data["id"]
    print(f"创建窗口成功: {window_id}")
    print(f"初始标题: {window_data.get('title', '未知')}")
    
    # 等待窗口创建完成
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
            title = target_window.get('title', '未知')
            print(f"占位文件标题: {title}")
            
            if title.endswith('.jpg'):
                print("✅ 占位文件包含正确扩展名")
            else:
                print(f"❌ 占位文件扩展名不正确: {title}")
        else:
            print("❌ 找不到创建的窗口")
    
    # 4. 检查文件系统状态
    print("\n4. 检查占位文件...")
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    files_found = []
    
    if backend_data_path.exists():
        for course_dir in backend_data_path.iterdir():
            if course_dir.is_dir() and course_dir.name.startswith("course-"):
                for board_dir in course_dir.iterdir():
                    if board_dir.is_dir() and board_dir.name.startswith("board-"):
                        files_dir = board_dir / "files"
                        if files_dir.exists():
                            for file_path in files_dir.iterdir():
                                if file_path.is_file() and '最终测试' in file_path.name:
                                    files_found.append(file_path.name)
    
    print(f"找到文件: {files_found}")
    
    expected_files = ['最终测试图片.jpg', '最终测试图片.jpg.json']
    if set(files_found) == set(expected_files):
        print("✅ 占位文件创建正确：只有一对文件")
    else:
        print(f"❌ 占位文件创建异常，期望: {expected_files}, 实际: {files_found}")
    
    # 5. 创建测试PNG文件
    print("\n5. 创建测试PNG文件...")
    test_png_path = Path("final_test.png")
    with open(test_png_path, "wb") as f:
        # 写入PNG文件头和最小内容
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 6. 上传PNG文件（测试竞态条件修复）
    print("\n6. 上传PNG文件...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("final_test.png", f, "image/png")}
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
    
    # 7. 验证最终结果
    print("\n7. 验证最终结果...")
    
    # 检查窗口信息
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.status_code == 200:
        windows_data = windows_response.json()
        windows = windows_data.get("windows", [])
        
        target_windows = [w for w in windows if w["id"] == window_id]
        
        print(f"找到匹配窗口数量: {len(target_windows)}")
        
        if len(target_windows) == 1:
            window = target_windows[0]
            title = window.get('title', '未知')
            content = window.get('content', '未知')
            
            print(f"✅ 只有一个窗口，标题: {title}")
            
            if title.endswith('.png'):
                print("✅ 窗口标题更新为PNG扩展名")
            else:
                print(f"❌ 窗口标题未正确更新: {title}")
                
            if '.png' in content:
                print("✅ 窗口内容指向PNG文件")
            else:
                print(f"❌ 窗口内容未正确更新: {content}")
        else:
            print(f"❌ 窗口数量异常: {len(target_windows)}")
            for i, w in enumerate(target_windows):
                print(f"  窗口{i+1}: {w.get('title', '未知')}")
    
    # 检查文件系统
    files_found = []
    if backend_data_path.exists():
        for course_dir in backend_data_path.iterdir():
            if course_dir.is_dir() and course_dir.name.startswith("course-"):
                for board_dir in course_dir.iterdir():
                    if board_dir.is_dir() and board_dir.name.startswith("board-"):
                        files_dir = board_dir / "files"
                        if files_dir.exists():
                            for file_path in files_dir.iterdir():
                                if file_path.is_file() and 'final' in file_path.name.lower():
                                    files_found.append(file_path.name)
    
    print(f"\n最终文件列表: {files_found}")
    
    # 期望只有一对PNG文件
    expected_final = ['final_test.png', 'final_test.png.json']
    png_files = [f for f in files_found if f.endswith('.png') and not f.endswith('.json')]
    json_files = [f for f in files_found if f.endswith('.png.json')]
    
    if len(png_files) == 1 and len(json_files) == 1:
        print("✅ 最终结果正确：只有一对PNG文件")
    else:
        print(f"❌ 最终结果异常，PNG文件: {len(png_files)}, JSON文件: {len(json_files)}")
    
    # 清理测试文件
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")

if __name__ == "__main__":
    try:
        test_final_fix()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
