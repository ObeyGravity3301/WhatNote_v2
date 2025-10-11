#!/usr/bin/env python3
"""
测试实时Markdown渲染功能
"""
import requests
import json
import time

def test_live_markdown():
    print("=== 测试实时Markdown渲染功能 ===\n")
    
    base_url = "http://localhost:8081"
    
    # 1. 获取现有板块
    print("1. 获取现有板块...")
    courses_response = requests.get(f"{base_url}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{base_url}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    print(f"使用板块: {board_id}\n")
    
    # 2. 创建通用窗口
    print("2. 创建通用窗口...")
    window_data = {
        "title": "实时Markdown测试",
        "type": "generic",
        "position": {"x": 150, "y": 150},
        "size": {"width": 600, "height": 500}
    }
    
    create_response = requests.post(
        f"{base_url}/api/boards/{board_id}/windows",
        json=window_data
    )
    
    window = create_response.json()
    window_id = window["id"]
    print(f"✅ 创建窗口: {window_id}\n")
    
    # 3. 转换为文本窗口
    print("3. 转换为文本窗口...")
    convert_response = requests.post(
        f"{base_url}/api/windows/{window_id}/convert-to-text"
    )
    
    if convert_response.ok:
        print("✅ 转换成功\n")
    else:
        print(f"❌ 转换失败: {convert_response.status_code}")
        return
    
    # 4. 添加测试内容
    print("4. 添加测试内容...")
    test_content = """# 实时Markdown渲染测试

这是一个**实时渲染**的测试文档。

## 功能特性

- 光标所在行显示原码
- 其他行显示渲染结果
- 实时切换，无延迟

### 代码示例

```python
def hello_obsidian():
    print("Hello, Obsidian-style editing!")
```

### 数学公式

行内公式：$E = mc^2$

### 列表

1. 第一项
2. 第二项
   - 子项目
   - 另一个子项目

### 引用

> 这是一个引用块
> 支持多行内容

### 表格

| 模式 | 描述 | 状态 |
|------|------|------|
| 编辑 | 纯文本编辑 | ✅ |
| 实时 | Obsidian风格 | ✅ |
| 预览 | 完整渲染 | ✅ |

**测试完成！**请在前端点击"⚡ 实时"按钮体验效果。"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功\n")
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")
        return
    
    print("🎉 实时Markdown渲染功能准备就绪！")
    print(f"🔗 窗口ID: {window_id}")
    print("\n📋 使用说明：")
    print("1. 在前端打开这个文本窗口")
    print("2. 点击工具栏中的 '⚡ 实时' 按钮")
    print("3. 移动光标到不同行，观察实时渲染效果")
    print("4. 光标所在行显示原码，其他行显示渲染结果")
    print("5. 享受Obsidian风格的编辑体验！")

if __name__ == "__main__":
    test_live_markdown()
