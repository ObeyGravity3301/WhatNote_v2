# WhatNote 插件系统规范

## 版本信息

- **规范版本**: 1.0.0
- **最后更新**: 2024
- **兼容性**: WhatNote v2.x

## 目录

1. [概述](#概述)
2. [插件对象规范](#插件对象规范)
3. [插件类型](#插件类型)
4. [API 规范](#api-规范)
5. [生命周期钩子](#生命周期钩子)
6. [上下文对象](#上下文对象)
7. [渲染方法规范](#渲染方法规范)
8. [错误处理](#错误处理)
9. [最佳实践](#最佳实践)
10. [类型定义](#类型定义)

---

## 概述

WhatNote 插件系统是一个轻量级的扩展机制，允许开发者在不修改核心代码的情况下添加新功能。插件通过 JavaScript 模块导出，遵循统一的接口规范。

### 核心原则

1. **单一职责**: 每个插件应该专注于一个功能
2. **松耦合**: 插件之间不应有直接依赖
3. **可扩展性**: 插件系统应该易于扩展新的插件类型
4. **向后兼容**: 新版本应该兼容旧插件（在合理范围内）

---

## 插件对象规范

### 必需属性

每个插件对象必须包含以下属性：

```javascript
{
  id: string,              // 插件唯一标识符（必需）
  name: string,            // 插件显示名称（必需）
  type: string,           // 插件类型（必需）
  version: string,        // 版本号（必需）
}
```

### 可选属性

```javascript
{
  description: string,           // 插件描述
  author: string,                // 作者信息
  enabledByDefault: boolean,      // 是否默认启用（默认: true）
  icon: string,                  // 插件图标（emoji 或 URL）
  homepage: string,              // 插件主页 URL
  repository: string,             // 代码仓库 URL
  license: string,               // 许可证
  dependencies: object,          // 依赖信息（未来扩展）
  minVersion: string,            // 最低系统版本要求
  maxVersion: string,            // 最高系统版本要求
}
```

### 属性详细说明

#### `id` (string, 必需)
- **格式**: 小写字母、数字、连字符，如 `word-count`、`my-plugin-v2`
- **规则**: 
  - 必须唯一
  - 不能包含空格或特殊字符
  - 建议使用 kebab-case
- **示例**: `"word-count"`, `"sticky-note"`

#### `name` (string, 必需)
- **说明**: 插件的显示名称
- **示例**: `"字数统计"`, `"便签窗口"`

#### `type` (string, 必需)
- **可选值**: 
  - `"toolbar-feature"` - 工具栏功能插件
  - `"window-type"` - 窗口类型插件
  - `"context-menu-item"` - 右键菜单插件（未来）
- **说明**: 定义插件的类型，决定插件如何集成到系统中

#### `version` (string, 必需)
- **格式**: 遵循语义化版本 (SemVer): `MAJOR.MINOR.PATCH`
- **示例**: `"1.0.0"`, `"2.1.3"`
- **说明**: 用于版本管理和兼容性检查

#### `enabledByDefault` (boolean, 可选)
- **默认值**: `true`
- **说明**: 插件首次安装时是否自动启用
- **注意**: 如果用户之前禁用过该插件，此设置会被忽略

---

## 插件类型

### 1. 工具栏功能插件 (`toolbar-feature`)

在特定窗口类型的工具栏中添加功能按钮。

#### 必需属性

```javascript
{
  type: 'toolbar-feature',
  targetWindowTypes: string[],  // 适用的窗口类型数组
  renderToolbarButton: function // 渲染工具栏按钮的方法
}
```

#### `targetWindowTypes` (string[], 必需)
- **说明**: 指定插件适用的窗口类型
- **可选值**: `['text']`, `['image']`, `['pdf']`, `['text', 'image']` 等
- **示例**: `['text']` - 仅在文本窗口显示

#### `renderToolbarButton` (function, 必需)
- **签名**: `(props) => React.Component`
- **参数**: 
  ```javascript
  {
    windowId: string,           // 窗口 ID
    content: string,            // 窗口内容
    onContentChange: function,  // 内容变更回调
    boardId: string            // 展板 ID
  }
  ```
- **返回值**: React 组件函数（不是组件实例）
- **注意**: 必须返回一个函数组件，不能直接使用 Hooks

#### 示例

```javascript
const myToolbarPlugin = {
  id: 'my-toolbar',
  name: '我的工具栏',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  version: '1.0.0',
  
  renderToolbarButton: (props) => {
    // 返回组件函数，而不是直接调用 Hooks
    return function MyToolbarButton() {
      const { content, windowId } = props;
      const [isOpen, setIsOpen] = useState(false);
      
      return (
        <button onClick={() => setIsOpen(!isOpen)}>
          我的按钮
        </button>
      );
    };
  }
};
```

### 2. 窗口类型插件 (`window-type`)

添加新的窗口类型，用户可以创建该类型的窗口。

#### 必需属性

```javascript
{
  type: 'window-type',
  windowType: string,              // 窗口类型标识
  renderWindow: function,         // 渲染窗口内容的方法
  getDefaultWindowConfig: function, // 获取默认窗口配置
  getWindowIcon: function          // 获取窗口图标
}
```

#### `windowType` (string, 必需)
- **说明**: 窗口类型的唯一标识符
- **格式**: 小写字母、连字符，如 `sticky-note`
- **注意**: 必须与系统内置窗口类型不冲突

#### `renderWindow` (function, 必需)
- **签名**: `(props) => React.Component`
- **参数**:
  ```javascript
  {
    window: object,              // 窗口数据对象
    onContentChange: function,   // 内容变更回调
    boardId: string              // 展板 ID
  }
  ```
- **返回值**: React 组件函数

#### `getDefaultWindowConfig` (function, 必需)
- **签名**: `() => object`
- **返回值**: 默认窗口配置对象
  ```javascript
  {
    type: string,                // 窗口类型（必须与 windowType 一致）
    title: string,               // 默认标题
    content: string,             // 默认内容
    size: {                      // 默认尺寸
      width: number,
      height: number
    },
    position: {                  // 默认位置（可选）
      x: number,
      y: number
    }
  }
  ```

#### `getWindowIcon` (function, 必需)
- **签名**: `() => string`
- **返回值**: 图标字符串（emoji 或图标标识符）
- **示例**: `"📝"`, `"🪟"`

#### `contextMenuItems` (array, 可选)
- **说明**: 定义右键菜单项，用于快速创建该类型的窗口
- **格式**: 
  ```javascript
  [
    {
      label: string,             // 菜单项标签
      icon: string,              // 图标（可选）
      menuType: string,          // 'desktop' | 'icon' | 'both'
      action: string,            // 动作标识符（如 'plugin:sticky-note:create'）
      order: number              // 排序，数字越小越靠前（可选）
    }
  ]
  ```
- **注意**: `action` 应该是字符串标识符，实际的点击处理由 `handleContextMenuAction` 方法完成

#### `handleContextMenuAction` (function, 可选)
- **签名**: `(action: string, context: object) => Promise<void>`
- **参数**:
  ```javascript
  {
    action: string,              // 菜单项的动作标识符
    context: {                  // 上下文对象
      boardId: string,           // 展板 ID
      createWindow: function,    // 创建窗口的函数
      windows: array            // 当前所有窗口数组
    }
  }
  ```
- **说明**: 处理右键菜单项的点击事件
- **示例**: 见下方完整示例

#### 示例

```javascript
const myWindowPlugin = {
  id: 'my-window',
  name: '我的窗口',
  type: 'window-type',
  windowType: 'my-window-type',
  version: '1.0.0',
  
  renderWindow: (props) => {
    return function MyWindow() {
      const { window: windowData, onContentChange } = props;
      const [content, setContent] = useState(windowData.content || '');
      
      return (
        <div>
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              onContentChange(e.target.value);
            }}
          />
        </div>
      );
    };
  },
  
  getDefaultWindowConfig: () => ({
    type: 'my-window-type',
    title: '新窗口',
    content: '',
    size: { width: 400, height: 300 }
  }),
  
  getWindowIcon: () => '🪟',
  
  contextMenuItems: [
    {
      label: '创建我的窗口',
      icon: '🪟',
      menuType: 'desktop',
      action: 'plugin:my-window:create',
      order: 1
    }
  ],
  
  handleContextMenuAction: async (action, context) => {
    if (action === 'plugin:my-window:create') {
      const { boardId, createWindow, windows = [] } = context;
      
      if (!boardId || !createWindow) {
        console.error('[我的窗口插件] 缺少必要的上下文');
        return;
      }
      
      // 生成唯一标题
      const generateUniqueTitle = (baseTitle) => {
        let title = baseTitle;
        let counter = 1;
        const existingTitles = windows.map(w => w.title);
        while (existingTitles.includes(title)) {
          title = `${baseTitle} ${counter}`;
          counter++;
        }
        return title;
      };
      
      const config = {
        ...myWindowPlugin.getDefaultWindowConfig(),
        title: generateUniqueTitle('新窗口'),
        position: {
          x: Math.round(100 + Math.random() * 200),
          y: Math.round(100 + Math.random() * 200)
        }
      };
      
      await createWindow(config);
    }
  }
};
```

---

## API 规范

### PluginRegistry API

插件系统通过 `pluginRegistry` 单例提供 API。

#### 注册插件

```javascript
pluginRegistry.register(plugin)
```

- **参数**: `plugin` (object) - 插件对象
- **返回值**: 无
- **说明**: 注册插件到系统中，如果插件 ID 已存在，会覆盖旧插件

#### 启用/禁用插件

```javascript
pluginRegistry.enable(pluginId)
pluginRegistry.disable(pluginId)
```

- **参数**: `pluginId` (string) - 插件 ID
- **返回值**: `boolean` - 操作是否成功
- **说明**: 启用/禁用插件，会触发相应的生命周期钩子

#### 查询插件

```javascript
pluginRegistry.get(pluginId)                    // 获取单个插件
pluginRegistry.getAll()                         // 获取所有插件
pluginRegistry.getEnabled()                    // 获取已启用的插件
pluginRegistry.isEnabled(pluginId)             // 检查插件是否启用
pluginRegistry.getToolbarPluginsForWindow(windowType)  // 获取工具栏插件
pluginRegistry.getWindowTypePlugin(windowType)         // 获取窗口类型插件
pluginRegistry.getContextMenuItems(menuType)           // 获取右键菜单项
```

#### 事件监听

```javascript
pluginRegistry.on('pluginStateChanged', callback)
pluginRegistry.off('pluginStateChanged', callback)
```

- **事件**: `pluginStateChanged`
- **回调参数**: `{ pluginId: string, enabled: boolean }`
- **说明**: 监听插件启用/禁用状态变化

---

## 生命周期钩子

### `onEnable(context)`

插件启用时调用。

- **参数**: `context` (object) - 插件上下文对象
- **返回值**: 无
- **用途**: 
  - 初始化插件资源
  - 注册事件监听器
  - 设置全局状态

### `onDisable(context)`

插件禁用时调用。

- **参数**: `context` (object) - 插件上下文对象
- **返回值**: 无
- **用途**: 
  - 清理资源
  - 移除事件监听器
  - 恢复全局状态

#### 示例

```javascript
const myPlugin = {
  // ...
  
  onEnable: (context) => {
    console.log('插件已启用');
    // 初始化工作
    window.addEventListener('custom-event', handleCustomEvent);
  },
  
  onDisable: (context) => {
    console.log('插件已禁用');
    // 清理工作
    window.removeEventListener('custom-event', handleCustomEvent);
  }
};
```

---

## 上下文对象

插件生命周期钩子接收的 `context` 对象（当前版本为空对象，未来会扩展）：

```javascript
{
  // 未来可能包含：
  // eventBus: EventEmitter,      // 事件总线
  // apiClient: APIClient,        // API 客户端
  // storage: Storage,           // 存储接口
  // createWindow: function,      // 创建窗口（窗口类型插件）
  // ...
}
```

---

## 渲染方法规范

### React Hooks 使用规则

**重要**: 插件渲染方法必须返回一个 React 函数组件，不能直接使用 Hooks。

#### ❌ 错误示例

```javascript
renderToolbarButton: (props) => {
  const [state, setState] = useState(false); // ❌ 错误：不能在非组件函数中使用 Hooks
  return <button>按钮</button>;
}
```

#### ✅ 正确示例

```javascript
renderToolbarButton: (props) => {
  return function MyButton() {
    const [state, setState] = useState(false); // ✅ 正确：在组件函数中使用
    return <button>按钮</button>;
  };
}
```

### 组件 Key

如果插件返回多个组件，必须提供唯一的 `key`：

```javascript
renderToolbarButton: (props) => {
  return function MyButtons() {
    return (
      <>
        <button key="button-1">按钮1</button>
        <button key="button-2">按钮2</button>
      </>
    );
  };
}
```

### 样式规范

- **推荐**: 使用内联样式，遵循 Win98 风格
- **可选**: 导入 CSS 文件（webpack 会处理）
- **避免**: 使用全局 CSS 类名（可能冲突）

---

## 错误处理

### 插件加载错误

如果插件加载失败，系统会：
1. 记录警告日志
2. 跳过该插件
3. 继续加载其他插件
4. 应用继续正常运行

### 插件运行时错误

插件应该自行处理运行时错误：

```javascript
renderToolbarButton: (props) => {
  return function MyButton() {
    try {
      // 插件逻辑
      return <button>按钮</button>;
    } catch (error) {
      console.error('插件错误:', error);
      return null; // 或返回错误提示组件
    }
  };
}
```

### 错误边界

建议在插件组件中使用错误边界：

```javascript
class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    console.error('插件错误:', error, errorInfo);
  }
  
  render() {
    if (this.state.hasError) {
      return <div>插件加载失败</div>;
    }
    return this.props.children;
  }
}
```

---

## 最佳实践

### 1. 插件命名

- **ID**: 使用 kebab-case，如 `my-awesome-plugin`
- **名称**: 使用中文描述性名称，如 `"我的超棒插件"`
- **版本**: 遵循 SemVer，如 `1.0.0`

### 2. 性能优化

- 使用 `useMemo` 和 `useCallback` 优化性能
- 避免在渲染方法中执行重计算
- 及时清理事件监听器和定时器

```javascript
renderToolbarButton: (props) => {
  return function OptimizedButton() {
    const expensiveValue = useMemo(() => {
      return computeExpensiveValue(props.content);
    }, [props.content]);
    
    const handleClick = useCallback(() => {
      // 处理点击
    }, []);
    
    return <button onClick={handleClick}>{expensiveValue}</button>;
  };
}
```

### 3. 状态管理

- 优先使用组件内部状态 (`useState`)
- 避免使用全局状态（除非必要）
- 通过 props 传递数据

### 4. 资源管理

- 使用相对路径导入资源
- 合理使用资源文件（CSS、图片等）
- 避免加载过大的资源

### 5. 兼容性

- 检查 API 可用性
- 提供降级方案
- 明确版本要求

```javascript
const myPlugin = {
  minVersion: '2.0.0',
  maxVersion: '3.0.0',
  
  onEnable: (context) => {
    // 检查功能可用性
    if (typeof context.createWindow !== 'function') {
      console.warn('createWindow API 不可用');
      return;
    }
  }
};
```

### 6. 文档

- 提供清晰的插件描述
- 说明插件功能和用法
- 标注依赖和兼容性

---

## 类型定义

### TypeScript 风格类型定义（参考）

```typescript
// 插件基础接口
interface Plugin {
  id: string;
  name: string;
  type: 'toolbar-feature' | 'window-type';
  version: string;
  description?: string;
  author?: string;
  enabledByDefault?: boolean;
  icon?: string;
  homepage?: string;
  repository?: string;
  license?: string;
  minVersion?: string;
  maxVersion?: string;
  onEnable?: (context: PluginContext) => void;
  onDisable?: (context: PluginContext) => void;
}

// 工具栏功能插件
interface ToolbarFeaturePlugin extends Plugin {
  type: 'toolbar-feature';
  targetWindowTypes: string[];
  renderToolbarButton: (props: ToolbarButtonProps) => React.ComponentType;
}

// 窗口类型插件
interface WindowTypePlugin extends Plugin {
  type: 'window-type';
  windowType: string;
  renderWindow: (props: WindowProps) => React.ComponentType;
  getDefaultWindowConfig: () => WindowConfig;
  getWindowIcon: () => string;
  contextMenuItems?: ContextMenuItem[];
}

// Props 类型
interface ToolbarButtonProps {
  windowId: string;
  content: string;
  onContentChange: (content: string) => void;
  boardId: string;
}

interface WindowProps {
  window: WindowData;
  onContentChange: (content: string) => void;
  boardId: string;
}

interface WindowConfig {
  type: string;
  title: string;
  content: string;
  size: { width: number; height: number };
  position?: { x: number; y: number };
}

interface ContextMenuItem {
  label: string;
  icon?: string;
  menuType: 'desktop' | 'icon' | 'both';
  action: (context: PluginContext) => void;
}

interface PluginContext {
  // 未来扩展
}
```

---

## 版本历史

### v1.0.0 (当前版本)
- 初始规范版本
- 支持工具栏功能插件
- 支持窗口类型插件
- 基础生命周期钩子

---

## 附录

### A. 插件检查清单

创建插件时，确保：

- [ ] 插件对象包含所有必需属性
- [ ] 插件 ID 唯一且符合格式要求
- [ ] 版本号遵循 SemVer
- [ ] 渲染方法正确返回 React 组件
- [ ] 正确使用 React Hooks
- [ ] 实现了必要的生命周期钩子
- [ ] 错误处理完善
- [ ] 遵循 Win98 风格设计
- [ ] 性能优化合理
- [ ] 文档完整

### B. 常见问题

**Q: 插件可以依赖其他插件吗？**
A: 当前版本不支持插件依赖，未来可能会支持。

**Q: 插件可以修改核心功能吗？**
A: 不建议，插件应该通过提供的 API 扩展功能。

**Q: 插件可以访问 DOM 吗？**
A: 可以，但建议通过 React 组件操作。

**Q: 插件可以发送网络请求吗？**
A: 可以，使用标准的 `fetch` API。

**Q: 插件如何持久化数据？**
A: 可以使用 `localStorage` 或通过窗口内容保存。

---

## 参考资源

- [插件系统 README](./README.md) - 快速开始指南
- [插件资源文件支持](./PLUGIN_ASSETS.md) - 资源文件使用说明
- [插件测试指南](./TESTING.md) - 测试方法

---

**最后更新**: 2024
**维护者**: WhatNote Team

