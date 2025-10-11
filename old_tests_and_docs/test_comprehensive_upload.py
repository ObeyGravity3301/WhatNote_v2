#!/usr/bin/env python3
"""
全面的上传测试 - 包含文件清理和详细诊断
"""

import requests
import json
from PIL import Image
import os
import time

# 服务器配置
BASE_URL = "http://127.0.0.1:8081"

def clean_test_files():
    """清理测试文件"""
    print("=" * 60)
    print("清理测试文件")
    print("=" * 60)
    
    test_files_dir = "whatnote_v2/backend/whatnote_data/courses/course-1756987907632/board-1756987954946/files/"
    
    # 删除所有测试相关文件
    import glob
    patterns = [
        "detailed_test*",
        "_temp_*",
        "*河津桜*",
        "test_*",
        "debug_*",
        "final_*"
    ]
    
    for pattern in patterns:
        for file_path in glob.glob(test_files_dir + pattern):
            try:
                os.remove(file_path)
                print(f"删除文件: {file_path}")
            except Exception as e:
                print(f"删除失败: {file_path}, 错误: {e}")

def create_new_window():
    """创建一个新的测试窗口"""
    print("\n" + "=" * 60)
    print("创建新测试窗口")
    print("=" * 60)
    
    try:
        # 获取课程和板块信息
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_response.raise_for_status()
        courses = courses_response.json()["courses"]
        course_id = courses[0]["id"]
        
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_response.raise_for_status()
        boards = boards_response.json()["boards"]
        board_id = boards[0]["id"]
        
        # 创建新窗口
        window_data = {
            "type": "image",
            "title": "测试图片窗口",
            "x": 200,
            "y": 200,
            "width": 400,
            "height": 300
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            json=window_data
        )
        create_response.raise_for_status()
        
        window_info = create_response.json()
        window_id = window_info["id"]
        print(f"✅ 创建新窗口成功: {window_id}")
        print(f"   标题: {window_info.get('title')}")
        
        return course_id, board_id, window_id
        
    except Exception as e:
        print(f"❌ 创建窗口失败: {e}")
        return None, None, None

def test_upload(board_id, window_id):
    """测试上传文件"""
    print("\n" + "=" * 60)
    print("测试文件上传")
    print("=" * 60)
    
    # 创建测试GIF文件
    test_filename = f"comprehensive_test_{int(time.time())}.gif"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(test_filename, 'GIF')
    print(f"✅ 创建测试文件: {test_filename}")
    
    try:
        # 上传文件
        with open(test_filename, 'rb') as f:
            files = {'file': (test_filename, f, 'image/gif')}
            data = {'file_type': 'images'}
            params = {'window_id': window_id}
            
            print("开始上传...")
            print("-" * 40)
            
            upload_response = requests.post(
                f"{BASE_URL}/api/boards/{board_id}/upload",
                files=files,
                data=data,
                params=params
            )
        
        print("-" * 40)
        print(f"上传响应状态: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            print("✅ 上传成功")
            response_data = upload_response.json()
            print(f"响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 上传失败: {upload_response.text}")
            
    except Exception as e:
        print(f"❌ 上传过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理测试文件
        if os.path.exists(test_filename):
            os.remove(test_filename)
            print(f"🗑️ 清理测试文件: {test_filename}")

def check_final_state(board_id):
    """检查最终状态"""
    print("\n" + "=" * 60)
    print("检查最终文件状态")
    print("=" * 60)
    
    try:
        # 获取窗口列表
        windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        windows_response.raise_for_status()
        windows = windows_response.json()["windows"]
        
        print(f"当前窗口数量: {len(windows)}")
        for i, window in enumerate(windows):
            print(f"窗口{i+1}:")
            print(f"  ID: {window.get('id')}")
            print(f"  标题: {window.get('title')}")
            print(f"  类型: {window.get('type')}")
            print(f"  文件路径: {window.get('file_path')}")
            print(f"  内容URL: {window.get('content', '')[:80]}...")
            print()
        
        # 检查文件系统
        files_dir = "whatnote_v2/backend/whatnote_data/courses/course-1756987907632/board-1756987954946/files/"
        print("文件系统状态:")
        
        import glob
        all_files = glob.glob(files_dir + "*")
        for file_path in sorted(all_files):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            print(f"  {file_name} ({file_size} bytes)")
            
    except Exception as e:
        print(f"❌ 检查状态失败: {e}")

def main():
    print("=" * 80)
    print("🧪 全面上传测试 - 包含清理和诊断")
    print("=" * 80)
    
    # 步骤1: 清理测试文件
    clean_test_files()
    
    # 步骤2: 创建新窗口
    course_id, board_id, window_id = create_new_window()
    if not all([course_id, board_id, window_id]):
        print("❌ 无法继续测试")
        return
    
    # 步骤3: 测试上传
    test_upload(board_id, window_id)
    
    # 步骤4: 检查最终状态
    check_final_state(board_id)
    
    print("\n" + "=" * 80)
    print("🎯 测试完成！请检查后端日志")
    print("=" * 80)

if __name__ == "__main__":
    main()
