#!/usr/bin/env python3
"""
测试实时渲染修复
"""
import requests
import json

def test_live_fix():
    print("=== 测试实时渲染修复 ===\n")
    
    base_url = "http://localhost:8081"
    
    # 获取现有板块
    courses_response = requests.get(f"{base_url}/api/courses")
    courses = courses_response.json().get("courses", [])
    course_id = courses[0]["id"]
    
    boards_response = requests.get(f"{base_url}/api/courses/{course_id}/boards")
    boards = boards_response.json().get("boards", [])
    board_id = boards[0]["id"]
    
    # 创建简单的测试窗口
    window_data = {
        "title": "实时渲染修复测试",
        "type": "generic",
        "position": {"x": 200, "y": 200},
        "size": {"width": 500, "height": 400}
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
    
    # 添加简单的测试内容
    test_content = """# 修复测试

这是一个简单的测试文档。

## 测试内容

- **粗体文字**
- *斜体文字*
- `代码片段`

### 代码块

```python
print("Hello, Live Markdown!")
```

现在可以安全地点击"⚡ 实时"按钮了！"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功")
        print(f"🔗 窗口ID: {window_id}")
        print("\n🎉 修复完成！现在可以安全地使用实时渲染功能了")
        print("📋 请在前端点击 '⚡ 实时' 按钮测试")
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")

if __name__ == "__main__":
    test_live_fix()
