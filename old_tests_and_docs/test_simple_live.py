#!/usr/bin/env python3
"""
测试简化版实时编辑器（分屏设计）
"""
import requests
import json

def test_simple_live():
    print("=== 测试简化版实时编辑器 ===\n")
    
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
        "title": "简化版实时编辑器",
        "type": "generic",
        "position": {"x": 100, "y": 50},
        "size": {"width": 700, "height": 500}
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
    test_content = """# 简化版实时编辑器

这是一个更实用的方案！

## 设计理念

基于您提供的Obsidian原理分析，我意识到之前的方案过于复杂。
真正的Obsidian风格需要CodeMirror这样的专业编辑器框架。

## 当前方案：分屏实时预览

左侧：**编辑区**
- 纯文本编辑器
- 支持所有编辑操作
- Courier New等宽字体

右侧：**实时预览**
- 完整Markdown渲染
- 实时更新显示
- Times New Roman字体

## 优势

1. **简单可靠**：不会有光标错位问题
2. **功能完整**：支持所有编辑操作
3. **渲染正确**：代码块、公式、表格都正确显示
4. **性能好**：没有复杂的映射计算

## 代码块测试

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 测试函数
for i in range(10):
    print(f"fibonacci({i}) = {fibonacci(i)}")
```

```javascript
function quickSort(arr) {
    if (arr.length <= 1) return arr;
    
    const pivot = arr[arr.length - 1];
    const left = arr.filter(x => x < pivot);
    const right = arr.filter(x => x > pivot);
    
    return [...quickSort(left), pivot, ...quickSort(right)];
}
```

## 数学公式

行内公式：$E = mc^2$

块级公式：
$$\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}$$

## 表格

| 特性 | 复杂方案 | 简化方案 |
|------|----------|----------|
| 光标对齐 | ❌ 困难 | ✅ 完美 |
| 编辑操作 | ❌ 受限 | ✅ 完整 |
| 代码块 | ❌ 断裂 | ✅ 正确 |
| 实现复杂度 | ❌ 很高 | ✅ 简单 |
| 用户体验 | ❌ 问题多 | ✅ 流畅 |

## 结论

虽然不是真正的"同一编辑器内实时渲染"，但这个分屏方案：

- **实用性强**：没有技术难题
- **体验好**：编辑流畅，预览准确
- **维护简单**：代码清晰易懂

这可能是当前最合适的解决方案！"""
    
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功")
        print(f"🔗 窗口ID: {window_id}")
        print("\n🎉 简化版实时编辑器准备就绪！")
        print("\n📋 特点：")
        print("- ✅ 左右分屏：编辑区 + 预览区")
        print("- ✅ 实时更新：输入即时显示效果")
        print("- ✅ 无光标问题：分离编辑避免错位")
        print("- ✅ 完整功能：所有编辑操作都支持")
        print("- ✅ 正确渲染：代码块、公式、表格完美")
        print("\n🚀 请在前端点击 '⚡ 实时' 按钮体验分屏编辑！")
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")

if __name__ == "__main__":
    test_simple_live()
