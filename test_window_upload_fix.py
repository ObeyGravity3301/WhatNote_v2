#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试窗口上传修复：占位文件替换和JSON文件处理
"""
import requests
import json
import time
import tempfile
import os
from pathlib import Path
import random

BASE_URL = "http://localhost:8081"

def create_test_file(filename, content="测试内容"):
    """创建测试文件"""
    temp_dir = Path(tempfile.gettempdir()) / "whatnote_test"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return file_path

def test_window_upload_fix():
    print("🔧 开始测试窗口上传修复...")
    
    # 获取测试数据
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    if not courses_response.ok:
        print(f"❌ 获取课程失败: {courses_response.status_code}")
        return False
    
    courses = courses_response.json().get("courses", [])
    if not courses:
        print("❌ 没有找到课程")
        return False
    
    course_id = courses[0]["id"]
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    if not boards_response.ok:
        print(f"❌ 获取展板失败: {boards_response.status_code}")
        return False
    
    boards = boards_response.json().get("boards", [])
    if not boards:
        print("❌ 没有找到展板")
        return False
    
    board_id = boards[0]["id"]
    print(f"✅ 使用展板: {board_id}")
    
    # 使用随机数避免冲突
    random_id = random.randint(10000, 99999)
    
    print(f"\n🧪 测试场景：创建窗口后上传文件")
    print("-" * 50)
    
    # 步骤1：创建一个新的图片窗口（会创建占位文件）
    print("📝 步骤1：创建新图片窗口")
    window_data = {
        "type": "image",
        "title": f"上传测试{random_id}",
        "content": "",
        "position": {"x": 100, "y": 100},
        "size": {"width": 400, "height": 300}
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/boards/{board_id}/windows",
        headers={"Content-Type": "application/json"},
        json=window_data
    )
    
    if not create_response.ok:
        print(f"❌ 创建窗口失败: {create_response.status_code}")
        return False
    
    new_window = create_response.json()
    window_id = new_window["id"]
    print(f"   ✅ 窗口创建成功: {window_id}")
    
    # 等待文件系统操作完成
    time.sleep(2)
    
    # 检查创建后的文件状态
    print("📋 检查创建后的文件状态:")
    files_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/files?file_type=images")
    if files_response.ok:
        files = files_response.json().get("files", [])
        placeholder_files = [f for f in files if f"上传测试{random_id}" in f]
        print(f"   占位文件: {placeholder_files}")
    
    # 步骤2：向该窗口上传真实图片
    print(f"\n📤 步骤2：上传真实图片到窗口 {window_id}")
    test_image_name = f"真实图片{random_id}.jpg"
    temp_file = create_test_file(test_image_name, f"这是真实图片内容 {random_id}")
    
    try:
        with open(temp_file, "rb") as f:
            files = {"file": (test_image_name, f, "image/jpeg")}
            data = {
                "file_type": "images",
                "window_id": window_id  # 关键：指定window_id
            }
            upload_response = requests.post(
                f"{BASE_URL}/api/boards/{board_id}/upload",
                files=files,
                data=data
            )
        
        if upload_response.ok:
            upload_result = upload_response.json()
            print(f"   ✅ 上传成功: {upload_result.get('filename', '未知')}")
        else:
            print(f"   ❌ 上传失败: {upload_response.status_code}")
            print(f"   错误信息: {upload_response.text}")
            return False
        
        temp_file.unlink()
        
    except Exception as e:
        print(f"   ❌ 上传异常: {e}")
        return False
    
    # 等待文件处理完成
    time.sleep(3)
    
    # 步骤3：检查最终文件状态
    print(f"\n📋 步骤3：检查上传后的文件状态")
    
    # 检查files目录中的文件
    files_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/files?file_type=images")
    if files_response.ok:
        files = files_response.json().get("files", [])
        related_files = [f for f in files if (f"上传测试{random_id}" in f or f"真实图片{random_id}" in f)]
        print(f"   相关文件: {related_files}")
        
        # 分析文件类型
        jpg_files = [f for f in related_files if f.endswith('.jpg')]
        json_files = [f for f in related_files if f.endswith('.json')]
        
        print(f"   📄 JPG文件 ({len(jpg_files)}): {jpg_files}")
        print(f"   📄 JSON文件 ({len(json_files)}): {json_files}")
        
        # 检查是否有重复或错误的文件
        issues = []
        if len(jpg_files) > 1:
            issues.append(f"JPG文件重复: {len(jpg_files)} 个")
        if len(json_files) > 1:
            issues.append(f"JSON文件重复: {len(json_files)} 个")
        
        # 检查文件名是否正确
        expected_jpg = f"真实图片{random_id}.jpg"
        expected_json = f"真实图片{random_id}.jpg.json"
        
        if expected_jpg not in jpg_files:
            issues.append(f"预期JPG文件不存在: {expected_jpg}")
        if expected_json not in json_files:
            issues.append(f"预期JSON文件不存在: {expected_json}")
        
        # 检查是否还有占位文件
        placeholder_files = [f for f in related_files if f"上传测试{random_id}" in f and not f"真实图片{random_id}" in f]
        if placeholder_files:
            issues.append(f"占位文件未清理: {placeholder_files}")
        
        if issues:
            print(f"   ❌ 发现问题:")
            for issue in issues:
                print(f"      - {issue}")
            return False
        else:
            print(f"   ✅ 文件状态正常")
    
    # 步骤4：检查窗口数据
    print(f"\n📋 步骤4：检查窗口数据更新")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.ok:
        windows_data = windows_response.json()
        windows = windows_data.get("windows", [])
        
        target_window = None
        for window in windows:
            if window.get("id") == window_id:
                target_window = window
                break
        
        if target_window:
            window_title = target_window.get("title", "")
            file_path = target_window.get("file_path", "")
            
            print(f"   窗口标题: {window_title}")
            print(f"   文件路径: {file_path}")
            
            # 检查标题和路径是否正确更新
            expected_title = f"真实图片{random_id}.jpg"
            expected_path = f"files/真实图片{random_id}.jpg"
            
            title_correct = window_title == expected_title
            path_correct = file_path == expected_path
            
            print(f"   {'✅' if title_correct else '❌'} 标题正确: {title_correct}")
            print(f"   {'✅' if path_correct else '❌'} 路径正确: {path_correct}")
            
            if title_correct and path_correct:
                print(f"   ✅ 窗口数据更新正确")
                return True
            else:
                print(f"   ❌ 窗口数据更新有误")
                return False
        else:
            print(f"   ❌ 未找到目标窗口")
            return False
    
    return False

def show_fix_summary():
    print("\n" + "="*80)
    print("📋 窗口上传修复总结:")
    print("="*80)
    print()
    print("🎯 修复的问题:")
    print("1. ✅ 占位文件正确替换：上传文件时删除占位文件")
    print("2. ✅ JSON文件正确更新：避免重复JSON文件")
    print("3. ✅ 窗口数据同步：title和file_path正确更新")
    print("4. ✅ 文件命名一致：前端显示与后端存储一致")
    print()
    print("🔧 技术实现:")
    print("- save_file_to_board(): 修复占位文件替换逻辑")
    print("- _update_window_json_file(): 新增JSON文件更新方法")
    print("- 删除旧的占位文件，避免文件重复")
    print("- 正确更新窗口的title和file_path字段")
    print()
    print("📁 预期结果:")
    print("- files/目录中只有: 真实文件.jpg + 真实文件.jpg.json")
    print("- 窗口title显示: 真实文件.jpg（包含扩展名）")
    print("- 不再有占位文件残留")
    print("- 不再有重复的JSON文件")

if __name__ == "__main__":
    try:
        success = test_window_upload_fix()
        show_fix_summary()
        
        print(f"\n{'🎉 窗口上传修复测试通过！' if success else '💥 窗口上传修复需要进一步调试'}")
        print("\n📋 建议测试:")
        print("1. 在浏览器中创建新的图片/视频/音频窗口")
        print("2. 向窗口上传文件")
        print("3. 检查files目录中的文件是否正确")
        print("4. 验证前端显示的文件名是否正确")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

