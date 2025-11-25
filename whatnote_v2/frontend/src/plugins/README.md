# 插件系统使用指南

## 概述

这是一个轻量级的插件系统，允许你为 WhatNote 添加新功能，而无需修改核心代码。

## 已实现的插件

### 1. 字数统计插件 (`word-count-plugin.js`)
- **类型**: 工具栏功能插件
- **功能**: 在文本窗口工具栏添加字数统计按钮
- **显示信息**: 字符数（含/不含空格）、字数、行数、段落数

### 2. 便签窗口插件 (`sticky-note-plugin.js`)
- **类型**: 窗口类型插件
- **功能**: 添加一个新的窗口类型 "sticky-note"
- **特点**: 彩色便签风格，支持快速记录

## 如何创建新插件

### 工具栏按钮插件示例

```javascript
// plugins/core/my-toolbar-plugin.js
import React, { useState } from 'react';

const myToolbarPlugin = {
  id: 'my-toolbar-plugin',
  name: '我的工具栏插件',
  description: '插件描述',
  version: '1.0.0',
  author: 'Your Name',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'], // 适用的窗口类型
  enabledByDefault: true,

  renderToolbarButton: (props) => {
    const { content, windowId } = props;
    const [isOpen, setIsOpen] = useState(false);

    return (
      <div key="my-plugin" style={{ position: 'relative' }}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '60px'
          }}
        >
          我的按钮
        </button>
        {isOpen && (
          <div style={{ /* 菜单样式 */ }}>
            {/* 你的菜单内容 */}
          </div>
        )}
      </div>
    );
  },

  onEnable: (context) => {
    console.log('插件已启用');
  },

  onDisable: (context) => {
    console.log('插件已禁用');
  }
};

export default myToolbarPlugin;
```

### 窗口类型插件示例

```javascript
// plugins/core/my-window-plugin.js
import React, { useState } from 'react';

const myWindowPlugin = {
  id: 'my-window-plugin',
  name: '我的窗口插件',
  description: '插件描述',
  version: '1.0.0',
  author: 'Your Name',
  type: 'window-type',
  windowType: 'my-window-type', // 窗口类型标识
  enabledByDefault: true,

  renderWindow: (props) => {
    const { window: windowData, onContentChange, boardId } = props;
    const [content, setContent] = useState(windowData.content || '');

    return (
      <div style={{ padding: '16px' }}>
        <h2>我的窗口内容</h2>
        <textarea
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            onContentChange(e.target.value);
          }}
        />
      </div>
    );
  },

  getDefaultWindowConfig: () => {
    return {
      type: 'my-window-type',
      title: '新窗口',
      content: '',
      size: { width: 400, height: 300 }
    };
  },

  getWindowIcon: () => {
    return '🪟'; // 窗口图标
  },

  onEnable: (context) => {
    console.log('窗口插件已启用');
  },

  onDisable: (context) => {
    console.log('窗口插件已禁用');
  }
};

export default myWindowPlugin;
```

## 注册插件

在 `plugins/index.js` 中注册你的插件：

```javascript
import myToolbarPlugin from './core/my-toolbar-plugin';
import myWindowPlugin from './core/my-window-plugin';

export function initializePlugins() {
  // ... 其他插件注册
  
  pluginRegistry.register(myToolbarPlugin);
  pluginRegistry.register(myWindowPlugin);
}
```

## 插件 API

### PluginRegistry 方法

- `register(plugin)`: 注册插件
- `enable(pluginId)`: 启用插件
- `disable(pluginId)`: 禁用插件
- `get(pluginId)`: 获取插件
- `getAll()`: 获取所有插件
- `getEnabled()`: 获取所有已启用的插件
- `getToolbarPluginsForWindow(windowType)`: 获取适用于特定窗口类型的工具栏插件
- `getWindowTypePlugin(windowType)`: 获取窗口类型插件
- `isEnabled(pluginId)`: 检查插件是否启用

### 插件对象属性

- `id`: 插件唯一标识符
- `name`: 插件名称
- `description`: 插件描述
- `version`: 版本号
- `author`: 作者
- `type`: 插件类型 (`'toolbar-feature'` 或 `'window-type'`)
- `targetWindowTypes`: 适用的窗口类型数组（仅工具栏插件）
- `windowType`: 窗口类型标识（仅窗口类型插件）
- `enabledByDefault`: 是否默认启用

### 插件生命周期钩子

- `onEnable(context)`: 插件启用时调用
- `onDisable(context)`: 插件禁用时调用

## 用户偏好

插件的启用/禁用状态会自动保存到 `localStorage`，键名为 `whatnote_enabled_plugins`。

## 注意事项

1. 插件应该保持轻量级，避免影响性能
2. 工具栏按钮插件应该返回 React 组件
3. 窗口类型插件需要实现 `renderWindow` 方法
4. 插件 ID 必须唯一
5. 遵循 Win98 风格设计规范




