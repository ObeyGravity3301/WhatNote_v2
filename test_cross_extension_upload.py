#!/usr/bin/env python3
"""
测试跨扩展名上传功能
演示：JPG占位文件 → 上传PNG文件，MP4占位文件 → 上传AVI文件等
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def create_test_files():
    """创建各种格式的测试文件"""
    test_files = {}
    
    # 创建PNG文件（1x1像素）
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    png_path = Path("test_cross.png")
    with open(png_path, "wb") as f:
        f.write(png_data)
    test_files["png"] = png_path
    
    # 创建GIF文件（最小的GIF）
    gif_data = (
        b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00'
        b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
    )
    
    gif_path = Path("test_cross.gif")
    with open(gif_path, "wb") as f:
        f.write(gif_data)
    test_files["gif"] = gif_path
    
    # 创建文本文件
    txt_path = Path("test_cross.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("这是一个测试文本文件\n包含中文内容\n用于测试跨扩展名上传")
    test_files["txt"] = txt_path
    
    # 创建Markdown文件
    md_path = Path("test_cross.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 测试Markdown文件\n\n这是一个**Markdown**文档，用于测试跨扩展名上传功能。\n\n- 列表项1\n- 列表项2")
    test_files["md"] = md_path
    
    return test_files

def test_cross_extension_upload():
    print("=== 测试跨扩展名上传功能 ===\n")
    
    # 创建测试文件
    test_files = create_test_files()
    print(f"创建了测试文件: {list(test_files.keys())}")
    
    # 1. 获取课程和板块信息
    print("\n1. 获取课程信息...")
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
        
    except Exception as e:
        print(f"连接服务失败: {e}")
        return
    
    # 2. 测试场景1：JPG占位文件 → 上传PNG文件
    print("\n2. 测试场景1：JPG占位文件 → 上传PNG文件")
    
    # 创建图片窗口（默认JPG占位文件）
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 200,
        "y": 100,
        "width": 300,
        "height": 200,
        "title": "跨扩展名测试图片"
    })
    
    if create_response.status_code != 200:
        print(f"创建窗口失败: {create_response.status_code}")
        return
    
    window1_data = create_response.json()
    window1_id = window1_data["id"]
    print(f"创建图片窗口: {window1_id}")
    
    time.sleep(1)
    
    # 上传PNG文件替换JPG占位文件
    with open(test_files["png"], "rb") as f:
        files = {"file": ("test_cross.png", f, "image/png")}
        data = {"file_type": "images"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data,
            params={"window_id": window1_id}
        )
    
    if upload_response.status_code == 200:
        print("✅ PNG文件成功替换JPG占位文件")
    else:
        print(f"❌ PNG上传失败: {upload_response.status_code} - {upload_response.text}")
    
    # 3. 测试场景2：JPG占位文件 → 上传GIF文件
    print("\n3. 测试场景2：JPG占位文件 → 上传GIF文件")
    
    # 创建另一个图片窗口
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "image",
        "x": 200,
        "y": 350,
        "width": 300,
        "height": 200,
        "title": "GIF测试图片"
    })
    
    if create_response.status_code != 200:
        print(f"创建窗口失败: {create_response.status_code}")
        return
    
    window2_data = create_response.json()
    window2_id = window2_data["id"]
    print(f"创建图片窗口: {window2_id}")
    
    time.sleep(1)
    
    # 上传GIF文件
    with open(test_files["gif"], "rb") as f:
        files = {"file": ("test_cross.gif", f, "image/gif")}
        data = {"file_type": "images"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data,
            params={"window_id": window2_id}
        )
    
    if upload_response.status_code == 200:
        print("✅ GIF文件成功替换JPG占位文件")
    else:
        print(f"❌ GIF上传失败: {upload_response.status_code} - {upload_response.text}")
    
    # 4. 测试场景3：TXT占位文件 → 上传Markdown文件
    print("\n4. 测试场景3：TXT占位文件 → 上传Markdown文件")
    
    # 创建文本窗口（默认TXT占位文件）
    create_response = requests.post(f"{BASE_URL}/api/boards/{board_id}/windows", json={
        "type": "text",
        "x": 550,
        "y": 100,
        "width": 400,
        "height": 300,
        "title": "Markdown测试文档"
    })
    
    if create_response.status_code != 200:
        print(f"创建窗口失败: {create_response.status_code}")
        return
    
    window3_data = create_response.json()
    window3_id = window3_data["id"]
    print(f"创建文本窗口: {window3_id}")
    
    time.sleep(1)
    
    # 上传Markdown文件
    with open(test_files["md"], "rb") as f:
        files = {"file": ("test_cross.md", f, "text/markdown")}
        data = {"file_type": "texts"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data,
            params={"window_id": window3_id}
        )
    
    if upload_response.status_code == 200:
        print("✅ Markdown文件成功替换TXT占位文件")
    else:
        print(f"❌ Markdown上传失败: {upload_response.status_code} - {upload_response.text}")
    
    # 5. 验证最终结果
    print("\n5. 验证最终结果...")
    time.sleep(2)
    
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.status_code == 200:
        windows_data = windows_response.json()
        windows = windows_data.get("windows", [])
        
        for window in windows:
            if window["id"] in [window1_id, window2_id, window3_id]:
                title = window.get('title', '未知')
                file_path = window.get('file_path', '未知')
                print(f"窗口 {window['id'][:12]}...: 标题='{title}', 文件路径='{file_path}'")
                
                # 检查扩展名是否正确
                if window["id"] == window1_id and title.endswith('.png'):
                    print("  ✅ JPG→PNG 替换成功")
                elif window["id"] == window2_id and title.endswith('.gif'):
                    print("  ✅ JPG→GIF 替换成功")
                elif window["id"] == window3_id and title.endswith('.md'):
                    print("  ✅ TXT→MD 替换成功")
    
    # 清理测试文件
    print("\n6. 清理测试文件...")
    for file_path in test_files.values():
        if file_path.exists():
            file_path.unlink()
            print(f"删除: {file_path.name}")

if __name__ == "__main__":
    try:
        test_cross_extension_upload()
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
