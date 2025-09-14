#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件名同步和扩展名显示功能
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

def test_filename_sync():
    print("🔄 开始测试文件名同步和扩展名显示功能...")
    
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
    
    test_results = []
    
    # 测试用例：文件名冲突和扩展名显示
    test_cases = [
        {
            "name": "基础文件名测试",
            "files": [
                {"name": "测试文档.txt", "content": "这是一个测试文档"},
                {"name": "测试图片.jpg", "content": "假装这是图片内容"},
                {"name": "测试音频.mp3", "content": "假装这是音频内容"}
            ],
            "rename_tests": [
                {"old": "测试文档.txt", "new": "重命名文档", "expected": "重命名文档.txt"},
                {"old": "测试图片.jpg", "new": "新图片", "expected": "新图片.jpg"}
            ]
        },
        {
            "name": "文件名冲突测试",
            "files": [
                {"name": "冲突测试.txt", "content": "第一个文件"},
                {"name": "冲突测试.txt", "content": "第二个文件，应该变成冲突测试(1).txt"},
                {"name": "冲突测试.txt", "content": "第三个文件，应该变成冲突测试(2).txt"}
            ],
            "expected_names": ["冲突测试.txt", "冲突测试(1).txt", "冲突测试(2).txt"]
        },
        {
            "name": "重命名冲突测试",
            "files": [
                {"name": "原文件1.txt", "content": "原文件1内容"},
                {"name": "原文件2.txt", "content": "原文件2内容"},
                {"name": "目标文件.txt", "content": "目标文件内容"}
            ],
            "rename_tests": [
                {"old": "原文件1.txt", "new": "目标文件", "expected": "目标文件(1).txt"},
                {"old": "原文件2.txt", "new": "目标文件", "expected": "目标文件(2).txt"}
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 执行测试用例: {test_case['name']}")
        
        case_results = {
            "name": test_case["name"],
            "files_created": [],
            "rename_results": [],
            "success": True
        }
        
        # 上传测试文件
        for file_info in test_case["files"]:
            print(f"   📤 上传文件: {file_info['name']}")
            
            # 创建临时文件
            temp_file = create_test_file(file_info["name"], file_info["content"])
            
            try:
                # 上传文件 - 根据扩展名确定文件类型
                file_ext = Path(file_info["name"]).suffix.lower()
                if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    file_type = "images"
                elif file_ext in ['.mp4', '.avi', '.mkv', '.mov']:
                    file_type = "videos"
                elif file_ext in ['.mp3', '.wav', '.flac', '.ogg']:
                    file_type = "audios"
                elif file_ext == '.pdf':
                    file_type = "pdfs"
                else:
                    file_type = "images"  # 默认使用images类型
                
                with open(temp_file, "rb") as f:
                    files = {"file": (file_info["name"], f, "text/plain")}
                    data = {"file_type": file_type}
                    upload_response = requests.post(
                        f"{BASE_URL}/api/boards/{board_id}/upload",
                        files=files,
                        data=data
                    )
                
                if upload_response.ok:
                    result = upload_response.json()
                    print(f"   ✅ 上传成功: {result.get('filename', '未知')}")
                    
                    # 等待文件监控器创建窗口（异步过程）
                    print(f"   ⏳ 等待窗口创建...")
                    time.sleep(2)
                    
                    # 获取最新的窗口列表来找到创建的窗口
                    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
                    if windows_response.ok:
                        windows_data = windows_response.json()
                        windows = windows_data.get("windows", [])
                        
                        # 查找匹配的窗口（按文件名或时间排序找最新的）
                        matching_window = None
                        expected_filename = result.get("filename", file_info["name"])
                        
                        for window in windows:
                            window_title = window.get("title", "")
                            # 检查是否匹配原始文件名或生成的唯一文件名
                            if (window_title == expected_filename or 
                                window_title.startswith(Path(expected_filename).stem)):
                                matching_window = window
                                break
                        
                        if matching_window:
                            actual_title = matching_window.get("title", "未知")
                            print(f"   📋 窗口创建成功，显示文件名: {actual_title}")
                            case_results["files_created"].append({
                                "original": file_info["name"],
                                "actual": actual_title,
                                "window_id": matching_window.get("id")
                            })
                        else:
                            print(f"   ❌ 未找到对应的窗口")
                            case_results["success"] = False
                    else:
                        print(f"   ❌ 获取窗口列表失败")
                        case_results["success"] = False
                else:
                    print(f"   ❌ 上传失败: {upload_response.status_code}")
                    case_results["success"] = False
                    
                # 清理临时文件
                temp_file.unlink()
                
            except Exception as e:
                print(f"   ❌ 上传异常: {e}")
                case_results["success"] = False
        
        # 执行重命名测试
        if "rename_tests" in test_case:
            print(f"   🔄 执行重命名测试...")
            for rename_test in test_case["rename_tests"]:
                # 查找对应的窗口ID
                window_id = None
                for created_file in case_results["files_created"]:
                    if created_file["actual"] == rename_test["old"]:
                        window_id = created_file["window_id"]
                        break
                
                if not window_id:
                    print(f"   ❌ 未找到文件 {rename_test['old']} 对应的窗口")
                    continue
                
                # 执行重命名
                rename_data = {"new_name": rename_test["new"]}
                rename_response = requests.put(
                    f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
                    headers={"Content-Type": "application/json"},
                    json=rename_data
                )
                
                if rename_response.ok:
                    result = rename_response.json()
                    actual_name = result.get("new_name", "未知")
                    expected_name = rename_test["expected"]
                    success = actual_name == expected_name
                    
                    print(f"   {'✅' if success else '❌'} 重命名: {rename_test['old']} -> {rename_test['new']}")
                    print(f"       预期: {expected_name}")
                    print(f"       实际: {actual_name}")
                    
                    case_results["rename_results"].append({
                        "old_name": rename_test["old"],
                        "new_input": rename_test["new"],
                        "expected": expected_name,
                        "actual": actual_name,
                        "success": success
                    })
                    
                    if not success:
                        case_results["success"] = False
                else:
                    print(f"   ❌ 重命名失败: {rename_response.status_code}")
                    case_results["success"] = False
        
        # 检查预期文件名（用于冲突测试）
        if "expected_names" in test_case:
            print(f"   🔍 检查文件名冲突处理...")
            expected_names = test_case["expected_names"]
            actual_names = [f["actual"] for f in case_results["files_created"]]
            
            for i, expected in enumerate(expected_names):
                if i < len(actual_names):
                    actual = actual_names[i]
                    success = actual == expected
                    print(f"   {'✅' if success else '❌'} 文件 {i+1}: 预期 {expected}, 实际 {actual}")
                    if not success:
                        case_results["success"] = False
                else:
                    print(f"   ❌ 缺少文件 {i+1}: 预期 {expected}")
                    case_results["success"] = False
        
        test_results.append(case_results)
    
    # 输出测试结果
    print("\n" + "="*80)
    print("📊 文件名同步和扩展名显示测试结果:")
    print("="*80)
    
    success_count = 0
    for result in test_results:
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{status} {result['name']}")
        
        if result["files_created"]:
            print("   📁 创建的文件:")
            for file_info in result["files_created"]:
                print(f"      {file_info['original']} -> {file_info['actual']}")
        
        if result["rename_results"]:
            print("   🔄 重命名结果:")
            for rename_info in result["rename_results"]:
                status = "✅" if rename_info["success"] else "❌"
                print(f"      {status} {rename_info['old_name']} -> {rename_info['new_input']} = {rename_info['actual']}")
        
        print()
        
        if result["success"]:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试用例通过")
    
    return success_count == len(test_results)

def show_testing_guide():
    print("\n" + "="*80)
    print("📋 文件名同步和扩展名显示测试指南:")
    print("="*80)
    print()
    print("🎯 测试目标:")
    print("1. 前端显示的文件名与后端存储的文件名完全一致")
    print("2. 文件名包含完整的扩展名")
    print("3. 文件名冲突时正确添加(1)、(2)等后缀")
    print("4. 重命名时保持文件名同步")
    print()
    print("📋 验证步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 观察桌面图标显示的文件名")
    print("3. 验证文件名包含扩展名（如 .txt, .jpg 等）")
    print("4. 验证冲突文件名包含编号后缀（如 文件(1).txt）")
    print("5. 尝试重命名文件，观察结果")
    print()
    print("✅ 预期效果:")
    print("- 显示完整文件名（包含扩展名）")
    print("- 冲突文件自动添加(1)、(2)后缀")
    print("- 前端显示与后端存储完全一致")
    print("- 重命名后文件名正确更新")
    print()
    print("🔧 技术实现:")
    print("- 后端：title字段使用完整文件名")
    print("- 后端：_generate_unique_filename处理冲突")
    print("- 前端：直接显示window.title字段")
    print("- 同步：前后端文件名保持一致")

if __name__ == "__main__":
    try:
        success = test_filename_sync()
        show_testing_guide()
        print(f"\n{'🎉 所有测试通过，文件名同步功能正常' if success else '💥 部分测试失败，请检查实现'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
