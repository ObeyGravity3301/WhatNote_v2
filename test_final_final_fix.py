#!/usr/bin/env python3
"""
测试最终修复方案
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def test_final_final_fix():
    print("=== 测试最终修复方案 ===\n")
    
    # 获取课程和板块信息
    try:
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_data = courses_response.json()
        course_id = courses_data["courses"][0]["id"]
        
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_data = boards_response.json()
        board_id = boards_data["boards"][0]["id"]
        
        print(f"使用板块: {board_id}")
    except Exception as e:
        print(f"连接服务失败: {e}")
        return
    
    # 获取现有的调试窗口
    print("\n1. 获取现有调试窗口...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_window = None
    for window in windows:
        if "调试" in window.get("title", ""):
            debug_window = window
            break
    
    if not debug_window:
        print("没有找到调试窗口")
        return
    
    window_id = debug_window["id"]
    print(f"使用窗口: {window_id}")
    print(f"当前标题: {debug_window.get('title', '未知')}")
    
    # 创建测试PNG文件
    print("\n2. 创建测试PNG文件...")
    test_png_path = Path("final_final_test.png")
    with open(test_png_path, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 上传PNG文件
    print(f"\n3. 上传PNG文件...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("final_final_test.png", f, "image/png")}
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
    print("\n4. 等待处理完成...")
    time.sleep(3)
    
    # 验证结果
    print("\n5. 验证结果...")
    
    # 检查窗口数量和内容
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    final_windows = [w for w in windows if "final" in w.get("title", "").lower() or "调试" in w.get("title", "")]
    
    print(f"相关窗口数量: {len(final_windows)}")
    
    success_count = 0
    for i, window in enumerate(final_windows):
        title = window.get('title', '')
        window_id_check = window.get('id', '')
        
        print(f"窗口{i+1}: ID={window_id_check[:12]}..., 标题='{title}'")
        
        if window_id_check == window_id:
            if title.endswith('.png'):
                print(f"  ✅ 目标窗口标题正确更新: {title}")
                success_count += 1
            else:
                print(f"  ❌ 目标窗口标题未正确更新: {title}")
        elif "final" in title.lower():
            print(f"  ❌ 发现重复窗口: {title}")
    
    # 检查文件系统
    print("\n6. 检查文件系统...")
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    files_found = []
    
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        for file_path in files_dir.iterdir():
                            if file_path.is_file() and 'final' in file_path.name.lower():
                                files_found.append(file_path.name)
    
    print(f"找到final相关文件: {files_found}")
    
    # 分析结果
    correct_png_files = [f for f in files_found if f.endswith('.png') and not f.endswith('.json') and not '.jpg' in f]
    correct_json_files = [f for f in files_found if f.endswith('.png.json')]
    incorrect_files = [f for f in files_found if '.png.jpg' in f]
    
    print(f"\n结果分析:")
    print(f"正确PNG文件: {correct_png_files}")
    print(f"正确JSON文件: {correct_json_files}")
    print(f"错误文件: {incorrect_files}")
    
    if (len(correct_png_files) == 1 and 
        len(correct_json_files) == 1 and 
        len(incorrect_files) == 0 and 
        success_count == 1):
        print("\n🎉 最终修复成功！")
        print("✅ 只有一个窗口被正确更新")
        print("✅ 只有一对正确的文件")
        print("✅ 没有重复扩展名问题")
    else:
        print("\n❌ 修复仍有问题")
    
    # 清理
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")

if __name__ == "__main__":
    try:
        test_final_final_fix()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
