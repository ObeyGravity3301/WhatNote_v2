# 路径更新调试指南

## 🔍 调试步骤

### 1. 刷新前端页面
确保使用最新的 Console.js 代码

### 2. 打开浏览器控制台
按 F12 或右键 → 检查 → Console 标签

### 3. 打开工具控制台
开始菜单 → 工具控制台

### 4. 执行 cd 命令
```bash
cd "生态"
```

### 5. 查看浏览器控制台输出
应该看到类似：

```
[Console] 收到响应: {type: "success", content: "已进入课程: 生态\n使用 'boards' 查看展板列表"}
[Console] 收到响应: {type: "text", content: "当前路径: /生态"}
[Console] 路径匹配结果: ["当前路径: /生态", "/生态"]
[Console] 更新路径: / -> /生态
```

### 6. 检查提示符
应该从 `C:\WHATNOTE>` 变成 `/生态>`

---

## ❓ 可能的问题

### 问题 1: 没有看到 pwd 响应
**检查**: 浏览器控制台是否只有一条 "收到响应"
**原因**: 后端的 pwd 命令可能没有发送
**解决**: 检查 setTimeout 是否正常工作

### 问题 2: 路径匹配失败
**检查**: 浏览器控制台显示 "路径匹配结果: null"
**原因**: 正则表达式或格式问题
**解决**: 检查后端返回的确切格式

### 问题 3: 路径更新但提示符没变
**检查**: console.log 显示路径更新了
**原因**: React state 更新延迟
**解决**: 等待下一次渲染，或强制刷新

---

## 🧪 手动测试 pwd

在工具控制台中直接输入：
```bash
pwd
```

应该看到当前路径，并且提示符不会重复显示这行。

---

## 🔧 预期的完整输出

```
C:\WHATNOTE> cd "生态"
已进入课程: 生态
使用 'boards' 查看展板列表

/生态> boards
展板列表 (共 6 个):
============================================================
...

/生态> cd "第一章"
已进入展板: 第一章
现在可以使用窗口工具了

/生态/第一章> get_windows
执行成功: get_windows
------------------------------------------------------------
{
  "board_id": "board-xxx",
  "count": 5,
  ...
}

/生态/第一章> cd ..
已返回课程目录

/生态> cd /
已返回根目录

C:\WHATNOTE>
```

---

## 💡 如果问题依然存在

请在浏览器控制台（F12）粘贴这段代码手动测试：

```javascript
// 检查 currentPath state
const consoleElement = document.querySelector('.console-window');
if (consoleElement) {
  console.log('Console element exists');
  console.log('Current prompt:', document.querySelector('.console-prompt')?.textContent);
}
```

并截图发送调试输出。




