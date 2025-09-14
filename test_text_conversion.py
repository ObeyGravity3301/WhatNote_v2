#!/usr/bin/env python3
"""
测试文字转换功能
"""
import requests
import json
import time

def test_text_conversion():
    print("=== 测试文字转换功能 ===\n")
    
    base_url = "http://localhost:8081"
    
    # 1. 获取现有板块
    print("1. 获取现有板块...")
    courses_response = requests.get(f"{base_url}/api/courses")
    if not courses_response.ok:
        print(f"❌ 获取课程失败: {courses_response.status_code}")
        return
    
    courses = courses_response.json().get("courses", [])
    if not courses:
        print("❌ 没有找到课程")
        return
    
    course_id = courses[0]["id"]
    print(f"使用课程: {course_id}")
    
    # 获取板块
    boards_response = requests.get(f"{base_url}/api/courses/{course_id}/boards")
    if not boards_response.ok:
        print(f"❌ 获取板块失败: {boards_response.status_code}")
        return
    
    boards = boards_response.json().get("boards", [])
    if not boards:
        print("❌ 没有找到板块")
        return
    
    board_id = boards[0]["id"]
    print(f"使用板块: {board_id}\n")
    
    # 2. 创建通用窗口
    print("2. 创建通用窗口...")
    window_data = {
        "title": "测试文字转换",
        "type": "generic",
        "position": {"x": 200, "y": 200},
        "size": {"width": 500, "height": 400}
    }
    
    create_response = requests.post(
        f"{base_url}/api/boards/{board_id}/windows",
        json=window_data
    )
    
    if not create_response.ok:
        print(f"❌ 创建窗口失败: {create_response.status_code}")
        print(f"响应: {create_response.text}")
        return
    
    window = create_response.json()
    window_id = window["id"]
    print(f"✅ 创建通用窗口成功: {window_id}\n")
    
    # 3. 转换为文本窗口
    print("3. 转换为文本窗口...")
    convert_response = requests.post(
        f"{base_url}/api/windows/{window_id}/convert-to-text"
    )
    
    if not convert_response.ok:
        print(f"❌ 转换失败: {convert_response.status_code}")
        print(f"响应: {convert_response.text}")
        return
    
    convert_result = convert_response.json()
    print(f"✅ 转换成功: {convert_result['message']}\n")
    
    # 4. 检查转换结果
    print("4. 检查转换结果...")
    time.sleep(1)  # 等待文件系统同步
    
    windows_response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
    if not windows_response.ok:
        print(f"❌ 获取窗口数据失败: {windows_response.status_code}")
        return
    
    windows_data = windows_response.json()
    windows = windows_data.get("windows", [])
    
    converted_window = None
    for w in windows:
        if w["id"] == window_id:
            converted_window = w
            break
    
    if not converted_window:
        print(f"❌ 找不到转换后的窗口: {window_id}")
        return
    
    print(f"窗口类型: {converted_window.get('type')}")
    print(f"窗口标题: {converted_window.get('title')}")
    print(f"文件路径: {converted_window.get('file_path')}")
    print(f"内容预览: {converted_window.get('content', '')[:100]}...")
    
    if converted_window.get('type') == 'text':
        print("✅ 窗口成功转换为文本类型\n")
    else:
        print(f"❌ 窗口类型不正确: {converted_window.get('type')}\n")
        return
    
    # 5. 测试内容更新
    print("5. 测试内容更新...")
    test_content = """# 测试Markdown文档

这是一个测试文档，用于验证Markdown编辑器功能。

## 功能特性

- **粗体文本**
- *斜体文本*
- `代码片段`

### 代码块

```python
def hello_world():
    print("Hello, World!")
```

### 数学公式

行内公式：$E = mc^2$

块级公式：
$$\\sum_{i=1}^{n} x_i = \\frac{n(n+1)}{2}$$

### 表格

| 功能 | 状态 |
|------|------|
| 编辑 | ✅ |
| 预览 | ✅ |
| 保存 | ✅ |

> 这是一个引用块
> 
> 支持多行内容
"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if not update_response.ok:
        print(f"❌ 更新内容失败: {update_response.status_code}")
        print(f"响应: {update_response.text}")
        return
    
    update_result = update_response.json()
    print(f"✅ 内容更新成功: {update_result['message']}\n")
    
    # 6. 验证内容保存
    print("6. 验证内容保存...")
    time.sleep(1)  # 等待文件写入
    
    final_windows_response = requests.get(f"{base_url}/api/boards/{board_id}/windows")
    if final_windows_response.ok:
        final_windows_data = final_windows_response.json()
        final_windows = final_windows_data.get("windows", [])
        
        final_window = None
        for w in final_windows:
            if w["id"] == window_id:
                final_window = w
                break
        
        if final_window and final_window.get('content'):
            content_preview = final_window['content'][:200]
            print(f"✅ 内容已保存，预览:\n{content_preview}...\n")
        else:
            print("❌ 内容保存验证失败\n")
    
    print("🎉 文字转换功能测试完成！")
    print(f"🔗 可以在前端查看窗口: {window_id}")

if __name__ == "__main__":
    test_text_conversion()
