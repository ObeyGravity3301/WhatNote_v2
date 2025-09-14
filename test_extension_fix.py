#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试扩展名显示修复
"""
import requests
import json
import time
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8081"

def create_test_file(filename, content="测试内容"):
    """创建测试文件"""
    temp_dir = Path(tempfile.gettempdir()) / "whatnote_test"
    temp_dir.mkdir(exist_ok=True)
    
    file_path = temp_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return file_path

def test_extension_display():
    print("🔧 开始测试扩展名显示修复...")
    
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
    
    # 测试不同扩展名的文件
    test_files = [
        {"name": "扩展名测试.txt", "type": "images", "expected": "扩展名测试.txt"},
        {"name": "图片测试.jpg", "type": "images", "expected": "图片测试.jpg"},
        {"name": "音频测试.mp3", "type": "audios", "expected": "音频测试.mp3"},
        {"name": "PDF测试.pdf", "type": "pdfs", "expected": "PDF测试.pdf"}
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
                    
                    # 查找匹配的窗口
                    matching_window = None
                    for window in windows:
                        window_title = window.get("title", "")
                        if test_file["name"] in window_title:
                            matching_window = window
                            break
                    
                    if matching_window:
                        actual_title = matching_window.get("title", "未知")
                        expected_title = test_file["expected"]
                        success = actual_title == expected_title
                        
                        print(f"   {'✅' if success else '❌'} 窗口标题: {actual_title}")
                        print(f"   {'✅' if success else '❌'} 预期标题: {expected_title}")
                        
                        results.append({
                            "filename": test_file["name"],
                            "expected": expected_title,
                            "actual": actual_title,
                            "success": success
                        })
                    else:
                        print(f"   ❌ 未找到对应的窗口")
                        results.append({
                            "filename": test_file["name"],
                            "expected": test_file["expected"],
                            "actual": "未找到窗口",
                            "success": False
                        })
                else:
                    print(f"   ❌ 获取窗口列表失败")
                    results.append({
                        "filename": test_file["name"],
                        "expected": test_file["expected"],
                        "actual": "获取失败",
                        "success": False
                    })
            else:
                print(f"   ❌ 上传失败: {upload_response.status_code}")
                results.append({
                    "filename": test_file["name"],
                    "expected": test_file["expected"],
                    "actual": "上传失败",
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
                "success": False
            })
    
    # 输出测试结果
    print("\n" + "="*80)
    print("📊 扩展名显示修复测试结果:")
    print("="*80)
    
    success_count = 0
    for result in results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{status} {result['filename']}")
        print(f"   预期: {result['expected']}")
        print(f"   实际: {result['actual']}")
        print()
        
        if result["success"]:
            success_count += 1
    
    print(f"总计: {success_count}/{len(results)} 个测试通过")
    
    return success_count == len(results)

if __name__ == "__main__":
    try:
        success = test_extension_display()
        print(f"\n{'🎉 扩展名显示修复测试完成' if success else '💥 部分测试失败'}!")
        print("\n📋 请在浏览器中验证:")
        print("1. 打开 http://localhost:3000")
        print("2. 观察桌面图标是否显示完整文件名（包含扩展名）")
        print("3. 验证文件名冲突时的编号后缀显示")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

