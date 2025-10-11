#!/usr/bin/env python3
"""
测试新版实时渲染
"""
import requests
import json

def test_live_v2():
    print("=== 测试新版实时渲染 ===\n")
    
    base_url = "http://localhost:8081"
    
    # 获取现有板块
    courses_response = requests.get(f"{base_url}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{base_url}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    # 创建测试窗口
    window_data = {
        "title": "新版实时渲染测试",
        "type": "generic",
        "position": {"x": 250, "y": 150},
        "size": {"width": 550, "height": 450}
    }
    
    create_response = requests.post(
        f"{base_url}/api/boards/{board_id}/windows",
        json=window_data
    )
    
    window = create_response.json()
    window_id = window["id"]
    print(f"✅ 创建窗口: {window_id}")
    
    # 转换为文本窗口
    convert_response = requests.post(
        f"{base_url}/api/windows/{window_id}/convert-to-text"
    )
    
    if convert_response.ok:
        print("✅ 转换成功")
    else:
        print(f"❌ 转换失败: {convert_response.status_code}")
        return
    
    # 添加测试内容
    test_content = """# 新版实时渲染测试

欢迎使用改进后的实时Markdown编辑器！

## 新特性

- **逐行编辑**：点击任意行开始编辑
- **清晰显示**：不再有文字重叠问题
- **统一行距**：完美的行间距控制
- **键盘导航**：使用方向键移动

## 使用方法

1. 点击"⚡ 实时"按钮
2. 点击任意行开始编辑
3. 使用Enter键创建新行
4. 使用方向键切换行

## 代码示例

```python
def obsidian_style():
    print("完美的实时渲染！")
```

### 数学公式

行内公式：$f(x) = x^2 + 1$

### 列表测试

- 第一项
- 第二项
  - 嵌套项目
  - 另一个嵌套项目

### 引用测试

> 这是一个引用块
> 现在应该显示得很清楚

**测试完成！享受新的编辑体验吧！**"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功")
        print(f"🔗 窗口ID: {window_id}")
        print("\n🎉 新版实时渲染准备就绪！")
        print("\n📋 改进说明：")
        print("- ✅ 解决了文字重叠问题")
        print("- ✅ 统一了行间距")
        print("- ✅ 改进了编辑体验")
        print("- ✅ 添加了点击编辑功能")
        print("- ✅ 支持键盘导航")
        print("\n🚀 请在前端点击 '⚡ 实时' 按钮体验！")
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")

if __name__ == "__main__":
    test_live_v2()
