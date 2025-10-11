#!/usr/bin/env python3
"""
测试改进版实时渲染（支持完整编辑和代码块）
"""
import requests
import json

def test_live_v3():
    print("=== 测试改进版实时渲染 ===\n")
    
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
        "title": "完整编辑测试",
        "type": "generic",
        "position": {"x": 300, "y": 100},
        "size": {"width": 600, "height": 500}
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
    
    # 添加包含代码块的测试内容
    test_content = """# 完整编辑功能测试

这个版本支持完整的编辑操作！

## 新特性

- **完整编辑**：支持backspace、delete、粘贴换行文本
- **代码块渲染**：多行代码块正确显示背景
- **透明叠加**：编辑器在上层，预览在下层
- **滚动同步**：编辑和预览同步滚动

## 代码块测试

```python
def hello_world():
    print("Hello, World!")
    
    # 这是一个多行代码块
    for i in range(3):
        print(f"Line {i}")
```

```javascript
function greet(name) {
    console.log(`Hello, ${name}!`);
    
    // 另一个代码块
    return `Welcome, ${name}`;
}
```

## 编辑测试说明

1. **点击"⚡ 实时"按钮**
2. **正常编辑**：
   - 使用backspace删除到上一行
   - 使用delete删除到下一行
   - 粘贴带换行的文本
3. **代码块**：应该有统一的背景色
4. **光标行**：当前行显示原码，其他行显示渲染效果

## 数学公式

行内公式：$E = mc^2$

块级公式：
$$\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}$$

## 列表

- 项目 1
- 项目 2
  - 嵌套项目
  - 另一个嵌套项目

### 引用

> 这是一个引用块
> 支持多行内容
> 
> 还可以有空行

**测试完成！现在应该支持完整的编辑功能了。**"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功")
        print(f"🔗 窗口ID: {window_id}")
        print("\n🎉 改进版实时渲染准备就绪！")
        print("\n📋 主要改进：")
        print("- ✅ 支持完整编辑操作（backspace、delete、粘贴）")
        print("- ✅ 代码块统一背景渲染")
        print("- ✅ 透明叠加设计，避免文字重叠")
        print("- ✅ 滚动同步")
        print("- ✅ 光标行显示原码，其他行实时渲染")
        print("\n🚀 请在前端点击 '⚡ 实时' 按钮体验！")
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")

if __name__ == "__main__":
    test_live_v3()
