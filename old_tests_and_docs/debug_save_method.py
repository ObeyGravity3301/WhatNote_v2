#!/usr/bin/env python3
"""
调试save_file_to_board方法调用
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8081"

def debug_save_method():
    print("=== 调试save_file_to_board方法调用 ===\n")
    
    # 在上传前添加调试输出到content_manager.py
    content_manager_path = Path("whatnote_v2/backend/storage/content_manager.py")
    
    # 读取当前文件内容
    with open(content_manager_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否已经有调试输出
    if "DEBUG_UPLOAD_START" not in content:
        # 在save_file_to_board方法开头添加调试输出
        old_line = 'def save_file_to_board(self, board_id: str, file_type: str, file_path: str, filename: str, window_id: str = None) -> str:'
        new_line = '''def save_file_to_board(self, board_id: str, file_type: str, file_path: str, filename: str, window_id: str = None) -> str:
        print("DEBUG_UPLOAD_START: save_file_to_board called")
        print(f"DEBUG_UPLOAD: board_id={board_id}, filename={filename}, window_id={window_id}")'''
        
        content = content.replace(old_line, new_line)
        
        # 在临时文件逻辑处添加调试输出
        old_temp_line = '# 如果有window_id，使用两步法避免文件监控器干扰'
        new_temp_line = '''# 如果有window_id，使用两步法避免文件监控器干扰
        print("DEBUG_UPLOAD: 开始两步法上传")'''
        
        content = content.replace(old_temp_line, new_temp_line)
        
        # 保存修改后的文件
        with open(content_manager_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print("已添加调试输出到content_manager.py")
        print("请重启服务后重新运行测试")
        return
    
    print("调试输出已存在，开始测试...")
    
    # 获取课程和板块信息
    try:
        courses_response = requests.get(f"{BASE_URL}/api/courses")
        courses_data = courses_response.json()
        course_id = courses_data["courses"][0]["id"]
        
        boards_response = requests.get(f"{BASE_URL}/api/courses/{course_id}/boards")
        boards_data = boards_response.json()
        board_id = boards_data["boards"][0]["id"]
        
        print(f"使用板块: {board_id}")
    except Exception as e:
        print(f"连接服务失败: {e}")
        return
    
    # 获取现有的调试窗口
    print("\n1. 获取现有调试窗口...")
    windows_response = requests.get(f"{BASE_URL}/api/boards/{board_id}/windows")
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    debug_window = None
    for window in windows:
        if "调试" in window.get("title", ""):
            debug_window = window
            break
    
    if not debug_window:
        print("没有找到调试窗口")
        return
    
    window_id = debug_window["id"]
    print(f"使用窗口: {window_id}")
    
    # 创建测试PNG文件
    print("\n2. 创建测试PNG文件...")
    test_png_path = Path("debug_save_test.png")
    with open(test_png_path, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"创建测试文件: {test_png_path}")
    
    # 上传PNG文件
    print(f"\n3. 上传PNG文件（注意后端调试输出）...")
    with open(test_png_path, "rb") as f:
        files = {"file": ("debug_save_test.png", f, "image/png")}
        data = {"file_type": "images"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/upload",
            files=files,
            data=data,
            params={"window_id": window_id}
        )
    
    print(f"上传响应状态: {upload_response.status_code}")
    if upload_response.status_code == 200:
        upload_result = upload_response.json()
        print(f"上传结果: {json.dumps(upload_result, ensure_ascii=False, indent=2)}")
    else:
        print(f"上传失败: {upload_response.text}")
    
    # 清理
    if test_png_path.exists():
        test_png_path.unlink()
        print(f"\n清理测试文件: {test_png_path}")
    
    print("\n请检查后端控制台输出，查看是否有DEBUG_UPLOAD相关信息")

if __name__ == "__main__":
    debug_save_method()
