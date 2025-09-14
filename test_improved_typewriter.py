#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的打字机模式测试脚本
测试精确的行映射算法，解决不同高度元素导致的偏离问题
"""

import requests
import json
import time

def test_improved_typewriter_mode():
    """测试改进的打字机模式"""
    
    print("🚀 开始测试改进的打字机模式...")
    
    base_url = "http://localhost:8081"
    board_id = "board-1756987954946"
    
    # 创建测试窗口
    print("\n📝 创建测试窗口...")
    create_response = requests.post(
        f"{base_url}/api/boards/{board_id}/windows",
        json={
            "type": "text",
            "title": "改进的打字机模式测试",
            "content": "",
            "position": {"x": 100, "y": 100},
            "size": {"width": 800, "height": 600}
        }
    )
    
    if not create_response.ok:
        print(f"❌ 创建窗口失败: {create_response.status_code}")
        return
    
    window_data = create_response.json()
    window_id = window_data.get('id')
    print(f"✅ 窗口创建成功，ID: {window_id}")
    
    # 测试内容 - 包含各种不同高度的Markdown元素
    test_content = """# 改进的打字机模式测试

这是一个测试改进的打字机模式的文档。

## 测试目标

解决之前版本中由于渲染元素高度不同导致的行映射偏离问题。

### 主要改进

1. **精确映射算法**：根据内容类型智能匹配预览元素
2. **内容分析**：识别标题、列表、代码块等不同类型
3. **容错处理**：提供后备映射机制

#### 测试场景

- 普通段落文本
- 各级标题
- 列表项目
- 代码块
- 数学公式

##### 列表测试

- 第一个列表项
- 第二个列表项
  - 嵌套列表项
  - 另一个嵌套项
- 第三个列表项

###### 有序列表

1. 第一项
2. 第二项
3. 第三项

## 代码块测试

```python
def test_function():
    print("这是一个测试函数")
    return "测试完成"
```

```javascript
function testTypewriter() {
    console.log("测试打字机模式");
    return true;
}
```

## 数学公式测试

行内公式：$E = mc^2$

块级公式：
$$
\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}
$$

## 引用块测试

> 这是一个引用块
> 
> 用于测试引用内容的映射

## 表格测试

| 功能 | 状态 | 说明 |
|------|------|------|
| 基础映射 | ✅ | 已实现 |
| 精确映射 | ✅ | 新增功能 |
| 容错处理 | ✅ | 已优化 |

## 长段落测试

这是一个很长的段落，用于测试当段落内容很长时，打字机模式是否能正确定位到对应的预览位置。这个段落包含了很多文字，目的是验证长文本的映射准确性。当光标在这个段落的不同位置时，预览应该能够准确滚动到对应的位置，而不会出现偏离。

## 混合内容测试

下面是一个包含多种元素的复杂区域：

### 子标题

这是子标题下的段落。

- 列表项1
- 列表项2

```bash
echo "命令行示例"
ls -la
```

**粗体文本** 和 *斜体文本* 的测试。

## 结论

如果打字机模式工作正常，当您在左侧编辑区移动光标到任何一行时：

1. 右侧预览会平滑滚动
2. 对应的内容会居中显示
3. 不会出现越往下偏离越大的问题
4. 各种类型的内容都能准确映射

**测试完成！享受改进的打字机模式体验！**"""
    
    # 更新窗口内容
    print("\n📄 添加测试内容...")
    update_response = requests.put(
        f"{base_url}/api/windows/{window_id}/content",
        json={"content": test_content}
    )
    
    if update_response.ok:
        print("✅ 内容添加成功")
        print(f"🔗 窗口ID: {window_id}")
        print("\n🎉 改进的打字机模式测试准备就绪！")
        print("\n📋 测试步骤：")
        print("1. 找到 '改进的打字机模式测试' 窗口")
        print("2. 点击 '⚡ 实时 (关)' 按钮进入分屏模式")
        print("3. 点击 '📝 打字机模式 (关)' 按钮启用打字机模式")
        print("4. 在左侧编辑区移动光标到不同类型的内容行")
        print("5. 观察右侧预览的精确滚动效果")
        
        print("\n🎯 预期改进效果：")
        print("✨ **精确映射**：标题、列表、代码块等都能准确对应")
        print("✨ **无偏离问题**：即使在文档末尾也能准确定位")
        print("✨ **智能识别**：不同类型的内容使用不同的匹配策略")
        print("✨ **平滑体验**：居中显示，平滑滚动动画")
        
        print("\n🔧 关键改进：")
        print("• 内容类型分析（标题、列表、代码块、段落）")
        print("• 智能元素匹配（根据内容和标签类型）")
        print("• 容错机制（找不到精确匹配时的后备策略）")
        print("• 实时映射重建（内容变化时自动更新映射关系）")
        
        print("\n🧪 测试重点：")
        print("1. 移动到标题行 - 应该准确定位到对应的h1-h6元素")
        print("2. 移动到列表行 - 应该定位到对应的li元素")
        print("3. 移动到代码块 - 应该定位到pre/code元素")
        print("4. 移动到表格行 - 应该定位到table相关元素")
        print("5. 在文档末尾测试 - 不应该再有偏离问题")
        
    else:
        print(f"❌ 内容添加失败: {update_response.status_code}")

if __name__ == "__main__":
    test_improved_typewriter_mode()

