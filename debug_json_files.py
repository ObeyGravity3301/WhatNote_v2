#!/usr/bin/env python3
"""
调试JSON文件内容
"""

import json
from pathlib import Path

def debug_json_files():
    print("=== 调试JSON文件内容 ===\n")
    
    # 查找最新的测试文件
    backend_data_path = Path("whatnote_v2/backend/whatnote_data/courses")
    
    if not backend_data_path.exists():
        print(f"数据目录不存在: {backend_data_path}")
        return
    
    for course_dir in backend_data_path.iterdir():
        if course_dir.is_dir() and course_dir.name.startswith("course-"):
            print(f"课程目录: {course_dir.name}")
            
            for board_dir in course_dir.iterdir():
                if board_dir.is_dir() and board_dir.name.startswith("board-"):
                    print(f"  板块目录: {board_dir.name}")
                    
                    files_dir = board_dir / "files"
                    if files_dir.exists():
                        print(f"    文件目录: {files_dir}")
                        
                        # 列出所有文件
                        print("    所有文件:")
                        for file_path in files_dir.iterdir():
                            if file_path.is_file():
                                print(f"      {file_path.name}")
                        
                        # 查找包含test_image的文件
                        print("\n    包含'test_image'的JSON文件:")
                        for json_file in files_dir.glob("*.json"):
                            if "test_image" in json_file.name.lower():
                                try:
                                    with open(json_file, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                    
                                    print(f"      文件: {json_file.name}")
                                    print(f"        ID: {data.get('id', '未知')}")
                                    print(f"        标题: {data.get('title', '未知')}")
                                    print(f"        文件路径: {data.get('file_path', '未知')}")
                                    print(f"        内容: {data.get('content', '未知')[:50]}...")
                                    print(f"        更新时间: {data.get('updated_at', '未知')}")
                                    print()
                                    
                                except Exception as e:
                                    print(f"      读取失败: {json_file.name}, 错误: {e}")
                        
                        # 查找最新创建的窗口
                        print("    最新的5个JSON文件:")
                        json_files = list(files_dir.glob("*.json"))
                        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        
                        for json_file in json_files[:5]:
                            try:
                                with open(json_file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                
                                print(f"      文件: {json_file.name}")
                                print(f"        ID: {data.get('id', '未知')}")
                                print(f"        标题: {data.get('title', '未知')}")
                                print(f"        类型: {data.get('type', '未知')}")
                                print(f"        文件路径: {data.get('file_path', '未知')}")
                                print(f"        创建时间: {data.get('created_at', '未知')}")
                                print(f"        更新时间: {data.get('updated_at', '未知')}")
                                print()
                                
                            except Exception as e:
                                print(f"      读取失败: {json_file.name}, 错误: {e}")

if __name__ == "__main__":
    debug_json_files()
