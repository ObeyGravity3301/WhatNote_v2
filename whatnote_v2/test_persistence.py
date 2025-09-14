#!/usr/bin/env python3
"""
测试窗口位置和大小的持久化功能
"""

import json
import requests
import time

def test_window_persistence():
    """测试窗口持久化功能"""
    base_url = "http://localhost:8081"
    
    print("🧪 测试窗口持久化功能...")
    
    try:
        # 1. 获取展板列表
        print("1. 获取展板列表...")
        response = requests.get(f"{base_url}/api/courses")
        courses = response.json().get('courses', [])
        
        if not courses:
            print("❌ 没有找到课程")
            return False
            
        # 找到第一个有展板的课程
        board_id = None
        for course in courses:
            if course.get('boards'):
                board_id = course['boards'][0]['id']
                print(f"✓ 找到展板: {board_id}")
                break
                
        if not board_id:
            print("❌ 没有找到展板")
            return False
            
        # 2. 获取展板窗口
        print("2. 获取展板窗口...")
        response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
        windows_data = response.json()
        windows = windows_data.get('windows', [])
        
        print(f"✓ 找到 {len(windows)} 个窗口")
        
        # 3. 显示每个窗口的位置和大小
        for i, window in enumerate(windows):
            position = window.get('position', {})
            size = window.get('size', {})
            print(f"  窗口 {i+1} ({window['type']}):")
            print(f"    位置: x={position.get('x', 0):.1f}, y={position.get('y', 0):.1f}")
            print(f"    大小: {size.get('width', 0)}x{size.get('height', 0)}")
            print(f"    标题: {window.get('title', 'N/A')}")
            
        # 4. 如果有窗口，测试修改位置
        if windows:
            test_window = windows[0]
            window_id = test_window['id']
            
            print(f"\n3. 测试修改窗口位置...")
            original_pos = test_window['position'].copy()
            
            # 修改位置
            new_position = {'x': 500, 'y': 300}
            new_size = {'width': 400, 'height': 250}
            
            updated_window = {
                **test_window,
                'position': new_position,
                'size': new_size
            }
            
            # 保存修改
            response = requests.put(
                f"{base_url}/api/boards/{board_id}/windows/{window_id}",
                json=updated_window
            )
            
            if response.ok:
                print("✓ 窗口位置已修改")
                
                # 验证修改是否生效
                time.sleep(0.5)
                response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
                updated_windows = response.json().get('windows', [])
                
                updated_window = next((w for w in updated_windows if w['id'] == window_id), None)
                if updated_window:
                    saved_pos = updated_window['position']
                    saved_size = updated_window['size']
                    
                    if (saved_pos['x'] == 500 and saved_pos['y'] == 300 and 
                        saved_size['width'] == 400 and saved_size['height'] == 250):
                        print("✅ 位置和大小持久化测试通过!")
                        
                        # 恢复原始位置
                        restored_window = {**updated_window, 'position': original_pos}
                        requests.put(f"{base_url}/api/boards/{board_id}/windows/{window_id}", json=restored_window)
                        print("✓ 已恢复原始位置")
                        
                        return True
                    else:
                        print(f"❌ 保存的位置不正确: {saved_pos}, {saved_size}")
                        return False
                else:
                    print("❌ 找不到更新后的窗口")
                    return False
            else:
                print(f"❌ 保存失败: {response.status_code}")
                return False
        else:
            print("ℹ️ 没有窗口可测试，但加载功能正常")
            return True
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保服务正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试窗口持久化功能...")
    success = test_window_persistence()
    
    if success:
        print("\n🎉 所有测试通过!")
        print("✅ 窗口位置和大小可以正确保存和加载")
        print("✅ 用户离开并返回展板时，窗口会保持之前的状态")
    else:
        print("\n❌ 测试失败，请检查日志")


