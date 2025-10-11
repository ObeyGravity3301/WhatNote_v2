#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试原位重命名功能（在扩展选中框内编辑）
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_in_place_rename():
    print("✏️ 开始测试原位重命名功能...")
    
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
    
    # 创建专门用于测试原位重命名的文件
    test_cases = [
        {
            "name": "单行重命名测试",
            "title": "单行测试文件",
            "description": "测试单行文件名的原位重命名"
        },
        {
            "name": "多行重命名测试",
            "title": "这是一个多行文件名测试，用来验证原位重命名的扩展选中框效果",
            "description": "测试多行文件名的原位重命名"
        },
        {
            "name": "超长重命名测试",
            "title": "这是一个超级超级长的文件名，专门用来测试在扩展的蓝色选中框内进行原位重命名编辑的功能是否正常工作，应该完全融入选中框的样式",
            "description": "测试超长文件名的原位重命名"
        },
        {
            "name": "英文重命名测试",
            "title": "English filename for testing in-place renaming functionality within the expanded selection box",
            "description": "测试英文文件名的原位重命名"
        },
        {
            "name": "混合文本测试",
            "title": "中英文混合 Mixed Text 测试文件名 for testing 原位重命名功能",
            "description": "测试中英文混合文件名的原位重命名"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 创建测试用例 {i+1}: {test_case['name']}")
        print(f"   初始文件名: {test_case['title']}")
        print(f"   文件名长度: {len(test_case['title'])} 字符")
        print(f"   测试目的: {test_case['description']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"重命名测试{i+1}",
            "content": f"{test_case['description']}的测试内容",
            "position": {"x": 50 + (i % 3) * 120, "y": 50 + (i // 3) * 150},  # 网格布局
            "size": {"width": 300, "height": 200}
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/boards/{board_id}/windows",
            headers={"Content-Type": "application/json"},
            json=window_data
        )
        
        if not create_response.ok:
            print(f"❌ 创建窗口失败: {create_response.status_code}")
            continue
        
        new_window = create_response.json()
        window_id = new_window["id"]
        
        # 重命名为测试文件名
        rename_data = {"new_name": test_case["title"]}
        rename_response = requests.put(
            f"{BASE_URL}/api/boards/{board_id}/windows/{window_id}/rename",
            headers={"Content-Type": "application/json"},
            json=rename_data
        )
        
        if rename_response.ok:
            result = rename_response.json()
            print(f"✅ 创建成功")
            print(f"   窗口ID: {window_id}")
            
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "window_id": window_id,
                "status": "✅ 创建成功"
            })
        else:
            error_text = rename_response.text
            print(f"❌ 重命名失败: {rename_response.status_code} - {error_text}")
            test_results.append({
                "case": test_case["name"],
                "title": test_case["title"],
                "title_length": len(test_case["title"]),
                "window_id": None,
                "status": f"❌ 失败: {rename_response.status_code}"
            })
    
    # 输出测试结果
    print("\n" + "="*80)
    print("📊 原位重命名测试结果:")
    print("="*80)
    
    success_count = 0
    for result in test_results:
        print(f"{result['status']} {result['case']}")
        print(f"   文件名长度: {result['title_length']} 字符")
        if result['window_id']:
            print(f"   窗口ID: {result['window_id']}")
        print()
        
        if "成功" in result['status']:
            success_count += 1
    
    print(f"总计: {success_count}/{len(test_results)} 个测试用例创建成功")
    
    return success_count == len(test_results)

def show_in_place_rename_testing_guide():
    print("\n" + "="*80)
    print("✏️ 原位重命名测试指南:")
    print("="*80)
    print()
    print("📋 测试步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 观察桌面图标的默认显示（截断的文件名）")
    print("3. 右键点击任意图标，选择'重命名'")
    print("4. 观察重命名时的显示效果")
    print("5. 尝试输入新的文件名")
    print("6. 按Enter确认或Esc取消")
    print("7. 观察重命名完成后的状态")
    print()
    print("✅ 预期效果:")
    print("- 开始重命名：图标自动显示蓝色扩展选中框")
    print("- 输入框样式：透明背景，融入选中框")
    print("- 文字效果：白色文字，带阴影，居中对齐")
    print("- 高度自适应：根据文件名长度自动调整")
    print("- 完成重命名：保持选中和扩展状态")
    print()
    print("🎨 视觉特征:")
    print("- 选中框：蓝色背景 (#316ac5) + 白色虚线边框")
    print("- 输入框：透明背景，无独立边框")
    print("- 文字：白色，11px，MS Sans Serif字体")
    print("- 阴影：1px 1px 1px rgba(0, 0, 0, 0.8)")
    print("- 对齐：文本居中，顶部对齐")
    print()
    print("🔧 技术实现:")
    print("- CSS类：.desktop-icon.selected.expanded")
    print("- 输入框：background: transparent, border: none")
    print("- 状态管理：renamingIconId + expanded类")
    print("- 高度：自动调整，与扩展框一致")

def show_rename_interaction_flow():
    print("\n" + "="*80)
    print("🔄 重命名交互流程:")
    print("="*80)
    print()
    print("1️⃣ 开始重命名 (右键 → 重命名):")
    print("   - 设置 renamingIconId = iconId")
    print("   - 设置 selectedIconId = iconId (显示选中框)")
    print("   - 清除 showingFullNameId (避免冲突)")
    print("   - 显示扩展选中框 (expanded类)")
    print("   - 显示透明textarea输入框")
    print()
    print("2️⃣ 输入过程:")
    print("   - textarea融入选中框样式")
    print("   - 高度自动调整")
    print("   - 保持Windows风格外观")
    print()
    print("3️⃣ 完成重命名 (Enter键):")
    print("   - 调用重命名API")
    print("   - 清除 renamingIconId")
    print("   - 保持 selectedIconId (选中状态)")
    print("   - 设置 showingFullNameId (显示完整文件名)")
    print("   - 保持扩展选中框")
    print()
    print("4️⃣ 取消重命名 (Esc键):")
    print("   - 清除所有重命名状态")
    print("   - 清除选中状态")
    print("   - 回到默认显示")
    print()
    print("🎯 核心改进:")
    print("- 重命名时完全融入Windows桌面风格")
    print("- 输入框透明，不破坏选中框外观")
    print("- 交互流程自然，符合用户习惯")
    print("- 状态管理清晰，避免视觉冲突")

if __name__ == "__main__":
    try:
        success = test_in_place_rename()
        show_in_place_rename_testing_guide()
        show_rename_interaction_flow()
        print(f"\n{'🎉 测试窗口创建完成，请按指南进行原位重命名测试' if success else '💥 部分测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

