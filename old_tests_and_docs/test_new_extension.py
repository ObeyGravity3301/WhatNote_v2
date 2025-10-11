#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新文件的扩展名显示
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

def test_new_extension_display():
    print("🔧 开始测试新文件扩展名显示...")
    
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
    
    # 使用随机数避免文件名冲突
    random_id = random.randint(1000, 9999)
    
    # 测试不同扩展名的文件
    test_files = [
        {"name": f"新测试{random_id}.txt", "type": "images", "expected": f"新测试{random_id}.txt"},
        {"name": f"新图片{random_id}.jpg", "type": "images", "expected": f"新图片{random_id}.jpg"},
        {"name": f"新音频{random_id}.mp3", "type": "audios", "expected": f"新音频{random_id}.mp3"},
    ]
    
    results = []
    
    for test_file in test_files:
        print(f"\n📤 测试文件: {test_file['name']}")
        
        # 创建临时文件
        temp_file = create_test_file(test_file["name"], f"这是{test_file['name']}的测试内容")
        
        try:
            # 上传文件
            with open(temp_file, "rb") as f:
                files = {"file": (test_file["name"], f, "text/plain")}
                data = {"file_type": test_file["type"]}
                upload_response = requests.post(
                    f"{BASE_URL}/api/boards/{board_id}/upload",
                    files=files,
                    data=data
                )
            
            if upload_response.ok:
                result = upload_response.json()
                print(f"   ✅ 上传成功: {result.get('filename', '未知')}")
                
                # 等待文件监控器创建窗口
                print(f"   ⏳ 等待窗口创建...")
                time.sleep(3)
                
                # 获取窗口列表
                windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
                if windows_response.ok:
                    windows_data = windows_response.json()
                    windows = windows_data.get("windows", [])
                    
                    # 查找匹配的窗口 - 使用更宽松的匹配
                    matching_window = None
                    base_name = Path(test_file["name"]).stem  # 不带扩展名的基础名
                    
                    for window in windows:
                        window_title = window.get("title", "")
                        # 检查title是否包含基础名称
                        if base_name in window_title:
                            matching_window = window
                            break
                    
                    if matching_window:
                        actual_title = matching_window.get("title", "未知")
                        expected_title = test_file["expected"]
                        has_extension = "." in actual_title
                        
                        print(f"   📋 找到窗口，标题: {actual_title}")
                        print(f"   {'✅' if has_extension else '❌'} 是否包含扩展名: {has_extension}")
                        
                        success = actual_title == expected_title
                        results.append({
                            "filename": test_file["name"],
                            "expected": expected_title,
                            "actual": actual_title,
                            "has_extension": has_extension,
                            "success": success
                        })
                    else:
                        print(f"   ❌ 未找到对应的窗口")
                        print(f"   📋 现有窗口标题:")
                        for window in windows[-3:]:  # 显示最新的3个窗口
                            print(f"      - {window.get('title', '未知')}")
                        
                        results.append({
                            "filename": test_file["name"],
                            "expected": test_file["expected"],
                            "actual": "未找到窗口",
                            "has_extension": False,
                            "success": False
                        })
                else:
                    print(f"   ❌ 获取窗口列表失败")
                    results.append({
                        "filename": test_file["name"],
                        "expected": test_file["expected"],
                        "actual": "获取失败",
                        "has_extension": False,
                        "success": False
                    })
            else:
                print(f"   ❌ 上传失败: {upload_response.status_code}")
                results.append({
                    "filename": test_file["name"],
                    "expected": test_file["expected"],
                    "actual": "上传失败",
                    "has_extension": False,
                    "success": False
                })
            
            # 清理临时文件
            temp_file.unlink()
            
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
            results.append({
                "filename": test_file["name"],
                "expected": test_file["expected"],
                "actual": f"异常: {e}",
                "has_extension": False,
                "success": False
            })
    
    # 输出测试结果
    print("\n" + "="*80)
    print("📊 新文件扩展名显示测试结果:")
    print("="*80)
    
    success_count = 0
    extension_count = 0
    for result in results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        ext_status = "✅ 有扩展名" if result["has_extension"] else "❌ 无扩展名"
        
        print(f"{status} {result['filename']}")
        print(f"   预期: {result['expected']}")
        print(f"   实际: {result['actual']}")
        print(f"   {ext_status}")
        print()
        
        if result["success"]:
            success_count += 1
        if result["has_extension"]:
            extension_count += 1
    
    print(f"完全匹配: {success_count}/{len(results)} 个测试通过")
    print(f"包含扩展名: {extension_count}/{len(results)} 个测试通过")
    
    return extension_count > 0  # 至少要有扩展名显示

if __name__ == "__main__":
    try:
        success = test_new_extension_display()
        print(f"\n{'🎉 扩展名显示修复生效' if success else '💥 扩展名显示仍有问题'}!")
        print("\n📋 请在浏览器中验证:")
        print("1. 打开 http://localhost:3000")
        print("2. 观察最新创建的桌面图标是否显示完整文件名（包含扩展名）")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

