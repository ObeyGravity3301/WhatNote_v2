#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件扩展名动态适配功能
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
    
    if filename.endswith(('.jpg', '.png', '.gif', '.bmp', '.webp')):
        # 创建假的图片文件
        with open(file_path, "wb") as f:
            f.write(b"fake image data " + content.encode())
    elif filename.endswith(('.mp4', '.avi', '.mov', '.webm')):
        # 创建假的视频文件
        with open(file_path, "wb") as f:
            f.write(b"fake video data " + content.encode())
    elif filename.endswith(('.mp3', '.wav', '.flac', '.aac')):
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

def test_dynamic_file_extension():
    print("🎯 测试文件扩展名动态适配功能")
    print("="*80)
    
    # 获取测试环境
    courses_response = requests.get(f"{BASE_URL}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    print(f"使用展板: {board_id}")
    
    # 测试场景：创建图片窗口，但上传不同格式的文件
    test_scenarios = [
        {
            "window_type": "image",
            "window_title": "我的图片",
            "upload_file": "动物照片.gif",  # 上传GIF而不是JPG
            "expected_extension": ".gif"
        },
        {
            "window_type": "video", 
            "window_title": "我的视频",
            "upload_file": "风景视频.webm",  # 上传WEBM而不是MP4
            "expected_extension": ".webm"
        },
        {
            "window_type": "audio",
            "window_title": "我的音乐", 
            "upload_file": "背景音乐.flac",  # 上传FLAC而不是MP3
            "expected_extension": ".flac"
        }
    ]
    
    random_id = random.randint(10000, 99999)
    results = []
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n📋 测试场景 {i+1}: {scenario['window_type']} 窗口上传 {scenario['expected_extension']} 文件")
        print("-" * 60)
        
        window_type = scenario["window_type"]
        window_title = f"{scenario['window_title']}{random_id}"
        upload_filename = f"{Path(scenario['upload_file']).stem}{random_id}{Path(scenario['upload_file']).suffix}"
        expected_extension = scenario["expected_extension"]
        
        # 1. 创建窗口
        print(f"1️⃣ 创建 {window_type} 窗口: {window_title}")
        window_data = {
            "type": window_type,
            "title": window_title,
            "content": "",
            "position": {"x": 100 + i * 50, "y": 100 + i * 50},
            "size": {"width": 400, "height": 300}
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            headers={"Content-Type": "application/json"},
            json=window_data
        )
        
        if not create_response.ok:
            print(f"   ❌ 窗口创建失败: {create_response.status_code}")
            results.append({"scenario": i+1, "success": False, "error": "窗口创建失败"})
            continue
        
        window_id = create_response.json()["id"]
        print(f"   ✅ 窗口创建成功: {window_id}")
        
        time.sleep(1)
        
        # 2. 检查初始状态
        print(f"2️⃣ 检查窗口初始状态")
        windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
        if windows_response.ok:
            windows = windows_response.json().get("windows", [])
            initial_window = None
            for window in windows:
                if window.get("id") == window_id:
                    initial_window = window
                    break
            
            if initial_window:
                initial_title = initial_window.get("title", "")
                initial_file_path = initial_window.get("file_path", "")
                print(f"   初始标题: {initial_title}")
                print(f"   初始路径: {initial_file_path}")
                
                # 验证初始状态不包含固定扩展名
                has_fixed_extension = (
                    initial_title.endswith('.jpg') or 
                    initial_title.endswith('.mp4') or 
                    initial_title.endswith('.mp3')
                )
                print(f"   {'✅' if not has_fixed_extension else '❌'} 初始标题无固定扩展名: {not has_fixed_extension}")
        
        # 3. 上传文件
        print(f"3️⃣ 上传 {expected_extension} 文件: {upload_filename}")
        temp_file = create_test_file(upload_filename, f"测试{window_type}内容")
        file_type = get_file_type_by_extension(upload_filename)
        
        try:
            with open(temp_file, "rb") as f:
                files = {"file": (upload_filename, f, f"application/{window_type}")}
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
                print(f"   ✅ 文件上传成功")
                temp_file.unlink()
                
                # 等待处理
                time.sleep(3)
                
                # 4. 检查最终状态
                print(f"4️⃣ 检查上传后的状态")
                windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
                if windows_response.ok:
                    windows = windows_response.json().get("windows", [])
                    final_window = None
                    
                    for window in windows:
                        if window.get("id") == window_id:
                            final_window = window
                            break
                    
                    if final_window:
                        final_title = final_window.get("title", "")
                        final_file_path = final_window.get("file_path", "")
                        
                        print(f"   最终标题: {final_title}")
                        print(f"   最终路径: {final_file_path}")
                        
                        # 验证结果
                        title_correct = final_title == upload_filename
                        path_correct = final_file_path == f"files/{upload_filename}"
                        extension_matches = final_title.endswith(expected_extension)
                        
                        print(f"   {'✅' if title_correct else '❌'} 标题正确: {title_correct}")
                        print(f"   {'✅' if path_correct else '❌'} 路径正确: {path_correct}")
                        print(f"   {'✅' if extension_matches else '❌'} 扩展名匹配: {extension_matches}")
                        
                        success = title_correct and path_correct and extension_matches
                        results.append({
                            "scenario": i+1,
                            "window_type": window_type,
                            "expected_ext": expected_extension,
                            "final_title": final_title,
                            "final_path": final_file_path,
                            "success": success,
                            "title_correct": title_correct,
                            "path_correct": path_correct,
                            "extension_matches": extension_matches
                        })
                        
                        # 5. 检查文件系统
                        print(f"5️⃣ 检查文件系统状态")
                        files_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/files?file_type={file_type}")
                        if files_response.ok:
                            files = files_response.json().get("files", [])
                            related_files = [f for f in files if upload_filename in f or window_title in f]
                            
                            actual_files = [f for f in related_files if not f.endswith('.json')]
                            json_files = [f for f in related_files if f.endswith('.json')]
                            
                            print(f"   实际文件: {actual_files}")
                            print(f"   JSON文件: {json_files}")
                            
                            # 验证只有正确的文件
                            correct_file_exists = upload_filename in actual_files
                            no_wrong_extensions = not any(f.endswith('.jpg') and not upload_filename.endswith('.jpg') for f in actual_files)
                            
                            print(f"   {'✅' if correct_file_exists else '❌'} 正确文件存在: {correct_file_exists}")
                            print(f"   {'✅' if no_wrong_extensions else '❌'} 无错误扩展名: {no_wrong_extensions}")
                    
                    else:
                        print(f"   ❌ 未找到目标窗口")
                        results.append({"scenario": i+1, "success": False, "error": "未找到窗口"})
                else:
                    print(f"   ❌ 获取窗口列表失败")
                    results.append({"scenario": i+1, "success": False, "error": "获取窗口失败"})
            else:
                print(f"   ❌ 上传失败: {upload_response.status_code}")
                print(f"   错误: {upload_response.text}")
                temp_file.unlink()
                results.append({"scenario": i+1, "success": False, "error": f"上传失败: {upload_response.status_code}"})
                
        except Exception as e:
            print(f"   ❌ 上传异常: {e}")
            if temp_file.exists():
                temp_file.unlink()
            results.append({"scenario": i+1, "success": False, "error": f"异常: {e}"})
    
    # 汇总结果
    print(f"\n" + "="*80)
    print("📊 文件扩展名动态适配测试结果")
    print("="*80)
    
    success_count = sum(1 for r in results if r.get("success", False))
    total_count = len(results)
    
    print(f"\n总体结果: {success_count}/{total_count} 通过")
    
    for result in results:
        scenario_num = result["scenario"]
        success = result.get("success", False)
        status = "✅ 通过" if success else "❌ 失败"
        
        print(f"\n场景 {scenario_num}: {status}")
        if success:
            print(f"  窗口类型: {result.get('window_type', 'N/A')}")
            print(f"  期望扩展名: {result.get('expected_ext', 'N/A')}")
            print(f"  最终标题: {result.get('final_title', 'N/A')}")
            print(f"  最终路径: {result.get('final_path', 'N/A')}")
        else:
            print(f"  错误: {result.get('error', '未知错误')}")
    
    print(f"\n{'🎉 所有测试通过！文件扩展名动态适配功能正常！' if success_count == total_count else '💥 部分测试失败，需要进一步调试'}")
    
    return success_count == total_count

if __name__ == "__main__":
    try:
        success = test_dynamic_file_extension()
        
        if success:
            print(f"\n🎯 修复效果:")
            print("✅ 窗口创建时不再使用固定扩展名")
            print("✅ 上传文件时根据实际格式确定扩展名")
            print("✅ 支持 GIF、WEBM、FLAC 等多种格式")
            print("✅ 前端显示与实际文件格式一致")
        else:
            print(f"\n💡 需要进一步调试的问题:")
            print("- 检查窗口创建逻辑")
            print("- 检查文件上传处理逻辑")
            print("- 验证扩展名识别逻辑")
        
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

