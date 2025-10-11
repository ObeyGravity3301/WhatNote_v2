#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终演示：窗口上传功能修复效果
"""
import requests
import json
import time
import tempfile
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

def demo_upload_fix():
    print("🎬 WhatNote V2 - 窗口上传功能修复演示")
    print("="*80)
    
    # 获取测试环境
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    print(f"📁 使用展板: {board_id}")
    
    # 场景演示
    random_id = random.randint(10000, 99999)
    
    print(f"\n🎯 场景：用户创建图片窗口并上传文件")
    print("="*80)
    
    print("1️⃣ 用户在前端创建了一个新的图片窗口...")
    
    # 创建窗口
    window_data = {
        "type": "image",
        "title": f"我的照片{random_id}",
        "content": "",
        "position": {"x": 200, "y": 150},
        "size": {"width": 500, "height": 400}
    }
    
    create_response = requests.post(
        f"{BASE_URL}/api/boards/{board_id}/windows",
        headers={"Content-Type": "application/json"},
        json=window_data
    )
    
    window_id = create_response.json()["id"]
    print(f"   ✅ 窗口创建成功: {window_id}")
    print(f"   📝 初始标题: {window_data['title']}")
    
    time.sleep(1)
    
    print(f"\n2️⃣ 系统自动创建了占位文件...")
    files_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/files?file_type=images")
    if files_response.ok:
        files = files_response.json().get("files", [])
        placeholder_files = [f for f in files if f"我的照片{random_id}" in f]
        print(f"   📄 占位文件: {placeholder_files}")
    
    print(f"\n3️⃣ 用户上传真实图片文件...")
    
    # 上传文件
    actual_filename = f"美丽风景{random_id}.jpg"
    temp_file = create_test_file(actual_filename, f"这是一张美丽的风景照片 {random_id}")
    
    with open(temp_file, "rb") as f:
        files = {"file": (actual_filename, f, "image/jpeg")}
        data = {
            "file_type": "images",
            "window_id": window_id  # 关键：指定要替换的窗口
        }
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data
        )
    
    if upload_response.ok:
        print(f"   ✅ 文件上传成功: {actual_filename}")
        temp_file.unlink()
    
    time.sleep(3)  # 等待文件处理完成
    
    print(f"\n4️⃣ 检查修复后的结果...")
    print("-" * 50)
    
    # 检查文件系统状态
    files_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/files?file_type=images")
    if files_response.ok:
        files = files_response.json().get("files", [])
        related_files = [f for f in files if (f"我的照片{random_id}" in f or f"美丽风景{random_id}" in f)]
        
        jpg_files = [f for f in related_files if f.endswith('.jpg')]
        json_files = [f for f in related_files if f.endswith('.json')]
        
        print(f"📂 files目录中的相关文件:")
        print(f"   📄 JPG文件: {jpg_files}")
        print(f"   📄 JSON文件: {json_files}")
        
        # 分析结果
        print(f"\n✅ 修复效果验证:")
        
        if len(jpg_files) == 1 and jpg_files[0] == actual_filename:
            print(f"   ✅ 只有一个JPG文件，名称正确: {actual_filename}")
        else:
            print(f"   ❌ JPG文件异常: {jpg_files}")
        
        expected_json = f"{actual_filename}.json"
        if len(json_files) == 1 and json_files[0] == expected_json:
            print(f"   ✅ 只有一个JSON文件，名称正确: {expected_json}")
        else:
            print(f"   ❌ JSON文件异常: {json_files}")
        
        # 检查占位文件是否清理
        placeholder_remaining = [f for f in related_files if f"我的照片{random_id}" in f]
        if not placeholder_remaining:
            print(f"   ✅ 占位文件已清理，无残留")
        else:
            print(f"   ❌ 仍有占位文件残留: {placeholder_remaining}")
    
    # 检查窗口数据更新
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    if windows_response.ok:
        windows = windows_response.json().get("windows", [])
        target_window = None
        
        for window in windows:
            if window.get("id") == window_id:
                target_window = window
                break
        
        if target_window:
            title = target_window.get("title", "")
            file_path = target_window.get("file_path", "")
            content = target_window.get("content", "")
            
            print(f"\n📋 窗口数据更新:")
            print(f"   标题: {title}")
            print(f"   文件路径: {file_path}")
            print(f"   内容URL: {content[:80]}...")
            
            # 验证更新正确性
            title_correct = title == actual_filename
            path_correct = file_path == f"files/{actual_filename}"
            content_has_url = "http" in content and actual_filename in content
            
            print(f"\n✅ 数据验证:")
            print(f"   {'✅' if title_correct else '❌'} 标题更新正确: {title_correct}")
            print(f"   {'✅' if path_correct else '❌'} 路径更新正确: {path_correct}")
            print(f"   {'✅' if content_has_url else '❌'} 内容URL正确: {content_has_url}")
            
            all_correct = title_correct and path_correct and content_has_url
            
            print(f"\n{'🎉' if all_correct else '💥'} 总体结果: {'修复成功！' if all_correct else '需要进一步调试'}")
            
            return all_correct
    
    return False

def show_fix_benefits():
    print(f"\n" + "="*80)
    print("🎯 修复前后对比")
    print("="*80)
    
    print(f"\n❌ 修复前的问题:")
    print("1. 占位文件不会被删除，导致files目录中有多个文件")
    print("2. JSON文件重复创建，如: 新建图片.jpg.json + 上传图片.jpg.json")
    print("3. 文件路径错误，如: files/上传图片.jpg.jpg (重复扩展名)")
    print("4. 窗口标题与实际文件名不一致")
    print("5. 前端显示的文件名与后端存储不匹配")
    
    print(f"\n✅ 修复后的效果:")
    print("1. 占位文件被正确替换，只保留上传的真实文件")
    print("2. 只有一个JSON文件: 真实文件名.json")
    print("3. 文件路径正确: files/真实文件名")
    print("4. 窗口标题自动更新为真实文件名（包含扩展名）")
    print("5. 前端显示与后端存储完全一致")
    
    print(f"\n🔧 技术改进:")
    print("- save_file_to_board(): 添加占位文件删除逻辑")
    print("- _update_window_json_file(): 新增JSON文件更新方法")
    print("- update_window_content_only(): 避免重复处理文件路径")
    print("- 优化上传API，分离内容更新和文件处理逻辑")
    
    print(f"\n📁 文件结构示例:")
    print("修复前:")
    print("  files/")
    print("    ├── 新建图片.jpg          (占位文件)")
    print("    ├── 新建图片.jpg.json     (占位JSON)")
    print("    ├── 上传图片.jpg          (真实文件)")
    print("    └── 上传图片.jpg.json     (真实JSON)")
    print("修复后:")
    print("  files/")
    print("    ├── 上传图片.jpg          (只有真实文件)")
    print("    └── 上传图片.jpg.json     (只有对应JSON)")

if __name__ == "__main__":
    try:
        print("🚀 开始演示...")
        success = demo_upload_fix()
        show_fix_benefits()
        
        print(f"\n{'🎉 演示完成！修复功能正常工作。' if success else '💥 演示发现问题，需要进一步调试。'}")
        
        print(f"\n📋 用户使用建议:")
        print("1. 创建窗口后，直接上传文件即可自动替换占位内容")
        print("2. 文件名会自动更新到窗口标题，包含完整扩展名")
        print("3. 支持图片、视频、音频、PDF等多种文件类型")
        print("4. 不再需要担心文件重复或命名冲突问题")
        
    except Exception as e:
        print(f"\n💥 演示过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

