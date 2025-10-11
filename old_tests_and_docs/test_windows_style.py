#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Windows风格的选中框扩展功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_windows_style_selection():
    print("🪟 开始测试Windows风格的选中框扩展功能...")
    
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
    
    # 创建专门用于测试Windows风格选中框扩展的文件
    test_cases = [
        {
            "name": "短文件名测试",
            "title": "短文件",
            "description": "测试短文件名的选中框效果"
        },
        {
            "name": "中等长度测试",
            "title": "中等长度的文件名测试",
            "description": "测试中等长度文件名的选中框扩展"
        },
        {
            "name": "长文件名测试",
            "title": "这是一个很长很长的文件名，用来测试Windows风格的选中框扩展功能是否正常工作",
            "description": "测试长文件名的选中框扩展效果"
        },
        {
            "name": "超长文件名测试",
            "title": "这是一个超级超级超级长的文件名，包含了很多很多的文字内容，用来测试Windows桌面风格的选中框向下扩展显示完整文件名的功能实现效果",
            "description": "测试超长文件名的选中框扩展效果"
        },
        {
            "name": "英文长文件名测试",
            "title": "This is a very very long English filename for testing the Windows desktop style selection box expansion functionality that should work properly",
            "description": "测试英文长文件名的选中框扩展"
        }
    ]
    
    test_results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 创建测试用例 {i+1}: {test_case['name']}")
        print(f"   文件名: {test_case['title']}")
        print(f"   文件名长度: {len(test_case['title'])} 字符")
        print(f"   测试目的: {test_case['description']}")
        
        # 创建测试窗口
        window_data = {
            "type": "text",
            "title": f"临时{i+1}",
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
    print("📊 Windows风格选中框扩展测试结果:")
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

def show_windows_style_testing_guide():
    print("\n" + "="*80)
    print("🪟 Windows风格选中框扩展测试指南:")
    print("="*80)
    print()
    print("📋 测试步骤:")
    print("1. 在浏览器中打开 http://localhost:3000")
    print("2. 观察桌面图标的默认显示（应该显示截断的文件名）")
    print("3. 单击任意图标")
    print("4. 观察选中框是否向下扩展显示完整文件名")
    print("5. 再次单击同一图标，选中框应该收缩回原状")
    print("6. 单击其他图标或空白区域，选中框应该收缩")
    print()
    print("✅ 预期效果:")
    print("- 默认状态：显示截断的文件名（带省略号）")
    print("- 选中状态：蓝色虚线框向下扩展，显示完整文件名")
    print("- 扩展框的高度根据文件名长度自动调整")
    print("- 文字不会超出选中框范围")
    print("- 交互流畅，类似Windows桌面体验")
    print()
    print("🎨 视觉特征:")
    print("- 选中框：蓝色背景 (#316ac5) + 白色虚线边框")
    print("- 扩展时：框架向下延伸，包含完整文件名")
    print("- 文字：白色，居中对齐，带阴影效果")
    print("- 高度：自动调整，最小76px")
    print()
    print("🔧 技术实现:")
    print("- CSS类：.desktop-icon.selected.expanded")
    print("- 高度：height: auto, min-height: 76px")
    print("- 文本：移除line-clamp限制，显示完整内容")
    print("- 状态：通过showingFullNameId控制")

def show_comparison_with_old_method():
    print("\n" + "="*80)
    print("🆚 新旧方法对比:")
    print("="*80)
    print()
    print("❌ 旧方法（黑色弹窗）:")
    print("- 独立的黑色半透明弹窗")
    print("- 绝对定位覆盖在图标上方")
    print("- 不符合Windows桌面习惯")
    print("- 视觉突兀，与整体风格不符")
    print()
    print("✅ 新方法（选中框扩展）:")
    print("- 原有选中框向下扩展")
    print("- 保持蓝色背景和虚线边框")
    print("- 完全符合Windows桌面体验")
    print("- 视觉自然，与系统风格一致")
    print()
    print("🎯 改进要点:")
    print("- 移除了.desktop-icon-full-name样式")
    print("- 添加了.desktop-icon.expanded样式")
    print("- 修改了文本显示逻辑")
    print("- 保持了所有交互功能")

if __name__ == "__main__":
    try:
        success = test_windows_style_selection()
        show_windows_style_testing_guide()
        show_comparison_with_old_method()
        print(f"\n{'🎉 测试窗口创建完成，请按指南进行手动测试' if success else '💥 部分测试窗口创建失败'}!")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")

