#!/usr/bin/env python3
"""
最终全面测试 - 修复所有问题后的验证
"""

import requests
import json
from PIL import Image
import os
import time
import glob

# 服务器配置
BASE_URL = "http://127.0.0.1:8081"

def clean_all_test_files():
    """彻底清理所有测试文件"""
    print("=" * 60)
    print("彻底清理所有测试文件")
    print("=" * 60)
    
    files_dir = "whatnote_v2/backend/whatnote_data/courses/course-1756987907632/board-1756987954946/files/"
    
    # 删除所有测试相关文件
    patterns = [
        "*test*",
        "_temp_*", 
        "*河津*",
        "*comprehensive*",
        "*debug*",
        "*final*"
    ]
    
    deleted_count = 0
    for pattern in patterns:
        for file_path in glob.glob(files_dir + pattern):
            try:
                os.remove(file_path)
                print(f"删除: {os.path.basename(file_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"删除失败: {file_path}, 错误: {e}")
    
    print(f"总共删除了 {deleted_count} 个文件")

def test_template_system():
    """测试模板系统是否工作"""
    print("\n" + "=" * 60)
    print("测试模板系统")
    print("=" * 60)
    
    try:
        # 获取基本信息
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_response.raise_for_status()
        courses = courses_response.json()["courses"]
        course_id = courses[0]["id"]
        
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_response.raise_for_status()
        boards = boards_response.json()["boards"]
        board_id = boards[0]["id"]
        
        # 创建不同类型的窗口
        window_types = [
            {"type": "image", "title": "模板测试图片"},
            {"type": "text", "title": "模板测试文本"},
            {"type": "video", "title": "模板测试视频"}
        ]
        
        created_windows = []
        for window_data in window_types:
            window_data.update({
                "x": 100,
                "y": 100,
                "width": 300,
                "height": 200
            })
            
            create_response = requests.post(
                f"{BASE_URL}/api/boards/{board_id}/windows",
                json=window_data
            )
            create_response.raise_for_status()
            
            window_info = create_response.json()
            created_windows.append(window_info)
            print(f"✅ 创建 {window_data['type']} 窗口: {window_info['id']}")
            print(f"   标题: {window_info.get('title')}")
        
        return course_id, board_id, created_windows
        
    except Exception as e:
        print(f"❌ 测试模板系统失败: {e}")
        return None, None, None

def test_upload_to_window(board_id, window_id, window_type):
    """测试上传文件到指定窗口"""
    print(f"\n--- 测试上传到 {window_type} 窗口 ---")
    
    # 创建对应类型的测试文件
    if window_type == "image":
        test_filename = f"final_test_{int(time.time())}.png"
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(test_filename, 'PNG')
        file_type = 'images'
        mime_type = 'image/png'
    elif window_type == "text":
        test_filename = f"final_test_{int(time.time())}.txt"
        with open(test_filename, 'w', encoding='utf-8') as f:
            f.write("这是测试文本内容")
        file_type = 'texts'
        mime_type = 'text/plain'
    elif window_type == "video":
        # 创建一个假的视频文件
        test_filename = f"final_test_{int(time.time())}.mp4"
        with open(test_filename, 'wb') as f:
            f.write(b'fake video content')
        file_type = 'videos'
        mime_type = 'video/mp4'
    
    print(f"创建测试文件: {test_filename}")
    
    try:
        # 上传文件
        with open(test_filename, 'rb') as f:
            files = {'file': (test_filename, f, mime_type)}
            data = {'file_type': file_type}
            params = {'window_id': window_id}
            
            upload_response = requests.post(
                f"{BASE_URL}/api/boards/{board_id}/upload",
                files=files,
                data=data,
                params=params
            )
        
        print(f"上传状态: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            print("✅ 上传成功")
            response_data = upload_response.json()
            print(f"文件路径: {response_data.get('file_path')}")
            print(f"文件名: {response_data.get('filename')}")
        else:
            print(f"❌ 上传失败: {upload_response.text}")
            
    except Exception as e:
        print(f"❌ 上传过程出错: {e}")
    finally:
        # 清理测试文件
        if os.path.exists(test_filename):
            os.remove(test_filename)

def check_final_results(board_id):
    """检查最终结果"""
    print("\n" + "=" * 60)
    print("检查最终结果")
    print("=" * 60)
    
    try:
        # 获取窗口列表
        windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        windows_response.raise_for_status()
        windows = windows_response.json()["windows"]
        
        print(f"当前窗口总数: {len(windows)}")
        print()
        
        for i, window in enumerate(windows, 1):
            print(f"窗口 {i}:")
            print(f"  ID: {window.get('id')}")
            print(f"  标题: {window.get('title')}")
            print(f"  类型: {window.get('type')}")
            print(f"  文件路径: {window.get('file_path')}")
            if window.get('content'):
                print(f"  内容URL: {window.get('content')[:50]}...")
            print()
        
        # 检查文件系统
        files_dir = "whatnote_v2/backend/whatnote_data/courses/course-1756987907632/board-1756987954946/files/"
        print("文件系统状态:")
        
        all_files = sorted(glob.glob(files_dir + "*"))
        for file_path in all_files:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            print(f"  {file_name} ({file_size} bytes)")
            
        # 统计分析
        content_files = [f for f in all_files if not f.endswith('.json')]
        json_files = [f for f in all_files if f.endswith('.json')]
        temp_files = [f for f in all_files if '_temp_' in os.path.basename(f)]
        
        print(f"\n统计:")
        print(f"  内容文件: {len(content_files)} 个")
        print(f"  JSON文件: {len(json_files)} 个")
        print(f"  临时文件: {len(temp_files)} 个")
        print(f"  窗口数量: {len(windows)} 个")
        
        if len(temp_files) > 0:
            print("⚠️ 发现临时文件未清理!")
        
        if len(content_files) != len(json_files):
            print("⚠️ 内容文件与JSON文件数量不匹配!")
        
        if len(windows) != len(json_files):
            print("⚠️ 窗口数量与JSON文件数量不匹配!")
            
    except Exception as e:
        print(f"❌ 检查结果失败: {e}")

def main():
    print("=" * 80)
    print("🧪 最终全面测试 - 验证所有修复")
    print("=" * 80)
    
    # 步骤1: 彻底清理
    clean_all_test_files()
    
    # 步骤2: 测试模板系统
    course_id, board_id, windows = test_template_system()
    if not all([course_id, board_id, windows]):
        print("❌ 无法继续测试")
        return
    
    # 步骤3: 测试上传到不同类型窗口
    for window in windows:
        test_upload_to_window(board_id, window['id'], window['type'])
        time.sleep(1)  # 避免并发问题
    
    # 步骤4: 检查最终结果
    check_final_results(board_id)
    
    print("\n" + "=" * 80)
    print("🎯 最终测试完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
