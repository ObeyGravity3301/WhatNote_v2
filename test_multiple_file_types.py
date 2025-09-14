#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多种文件类型的窗口上传功能
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
    if filename.endswith(('.jpg', '.png', '.gif')):
        # 创建假的图片文件
        with open(file_path, "wb") as f:
            f.write(b"fake image data " + content.encode())
    elif filename.endswith(('.mp4', '.avi', '.mov')):
        # 创建假的视频文件
        with open(file_path, "wb") as f:
            f.write(b"fake video data " + content.encode())
    elif filename.endswith(('.mp3', '.wav', '.flac')):
        # 创建假的音频文件
        with open(file_path, "wb") as f:
            f.write(b"fake audio data " + content.encode())
    else:
        # 文本文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    return file_path

def get_file_type_by_extension(filename):
    """根据文件扩展名确定文件类型"""
    ext = Path(filename).suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return 'images'
    elif ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
        return 'videos'
    elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
        return 'audios'
    elif ext in ['.pdf']:
        return 'pdfs'
    else:
        return 'images'  # 默认

def test_multiple_file_types():
    print("🎯 测试多种文件类型的窗口上传")
    
    # 获取测试数据
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    print(f"使用展板: {board_id}")
    
    # 测试不同类型的文件
    test_files = [
        ("测试图片.jpg", "image"),
        ("测试视频.mp4", "video"), 
        ("测试音频.mp3", "audio"),
        ("测试文档.pdf", "pdf")
    ]
    
    random_id = random.randint(10000, 99999)
    results = []
    
    for filename, window_type in test_files:
        print(f"\n📁 测试 {window_type} 类型文件: {filename}")
        print("-" * 50)
        
        # 创建窗口
        actual_filename = f"{Path(filename).stem}{random_id}{Path(filename).suffix}"
        window_data = {
            "type": window_type,
            "title": f"上传测试_{window_type}_{random_id}",
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
            results.append({"type": window_type, "success": False, "error": "创建窗口失败"})
            continue
        
        window_id = create_response.json()["id"]
        print(f"   ✅ 窗口创建成功: {window_id}")
        
        time.sleep(1)
        
        # 上传文件
        temp_file = create_test_file(actual_filename, f"测试{window_type}内容")
        file_type = get_file_type_by_extension(actual_filename)
        
        try:
            with open(temp_file, "rb") as f:
                files = {"file": (actual_filename, f, f"application/{window_type}")}
                data = {
                    "file_type": file_type,
                    "window_id": window_id
                }
                upload_response = requests.post(
                    f"{BASE_URL}/api/boards/{board_id}/upload",
                    files=files,
                    data=data
                )
            
            if upload_response.ok:
                print(f"   ✅ 上传成功")
                temp_file.unlink()
                
                # 等待处理
                time.sleep(2)
                
                # 检查窗口状态
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
                        
                        # 验证结果
                        title_correct = title == actual_filename
                        path_correct = file_path == f"files/{actual_filename}"
                        
                        print(f"   窗口标题: {title}")
                        print(f"   文件路径: {file_path}")
                        print(f"   {'✅' if title_correct else '❌'} 标题正确: {title_correct}")
                        print(f"   {'✅' if path_correct else '❌'} 路径正确: {path_correct}")
                        
                        success = title_correct and path_correct
                        results.append({
                            "type": window_type,
                            "filename": actual_filename,
                            "success": success,
                            "title_correct": title_correct,
                            "path_correct": path_correct,
                            "actual_title": title,
                            "actual_path": file_path
                        })
                    else:
                        print(f"   ❌ 未找到目标窗口")
                        results.append({"type": window_type, "success": False, "error": "未找到窗口"})
                else:
                    print(f"   ❌ 获取窗口列表失败")
                    results.append({"type": window_type, "success": False, "error": "获取窗口失败"})
            else:
                print(f"   ❌ 上传失败: {upload_response.status_code}")
                print(f"   错误: {upload_response.text}")
                temp_file.unlink()
                results.append({"type": window_type, "success": False, "error": f"上传失败: {upload_response.status_code}"})
                
        except Exception as e:
            print(f"   ❌ 上传异常: {e}")
            if temp_file.exists():
                temp_file.unlink()
            results.append({"type": window_type, "success": False, "error": f"异常: {e}"})
    
    # 汇总结果
    print(f"\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    
    print(f"\n总体结果: {success_count}/{total_count} 通过")
    
    for result in results:
        file_type = result["type"]
        success = result.get("success", False)
        status = "✅ 通过" if success else "❌ 失败"
        
        print(f"\n{file_type.upper()}: {status}")
        if success:
            print(f"  文件名: {result.get('filename', 'N/A')}")
            print(f"  标题: {result.get('actual_title', 'N/A')}")
            print(f"  路径: {result.get('actual_path', 'N/A')}")
        else:
            print(f"  错误: {result.get('error', '未知错误')}")
    
    print(f"\n{'🎉 所有测试通过！' if success_count == total_count else '💥 部分测试失败，需要进一步调试'}")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        success = test_multiple_file_types()
        print(f"\n📋 测试完成，结果: {'成功' if success else '需要改进'}")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

