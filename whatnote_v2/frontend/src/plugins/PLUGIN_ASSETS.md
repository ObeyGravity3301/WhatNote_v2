# 插件资源文件支持

## 当前状态

**是的，目前插件系统只支持 JS 文件作为插件入口点。**

但是，**插件内部可以导入和使用其他类型的资源文件**（CSS、图片、JSON 等），这得益于 webpack 的资源处理能力。

## 支持的资源类型

### 1. JavaScript 模块（必需）
- 插件的主入口文件必须是 `.js` 文件
- 可以导入其他 JS 模块、React 组件等

### 2. CSS 样式文件（支持）
插件可以在 JS 文件中导入 CSS：

```javascript
// my-plugin.js
import React from 'react';
import './my-plugin.css'; // ✅ 支持导入 CSS

const MyPlugin = {
  // ...
};
```

### 3. 图片资源（支持）
插件可以导入图片：

```javascript
// my-plugin.js
import iconImage from './icon.png'; // ✅ 支持导入图片
import backgroundImage from './background.jpg';

const MyPlugin = {
  renderToolbarButton: () => (
    <div>
      <img src={iconImage} alt="Icon" />
      <div style={{ backgroundImage: `url(${backgroundImage})` }}>
        Content
      </div>
    </div>
  )
};
```

### 4. JSON 配置文件（支持）
插件可以导入 JSON：

```javascript
// my-plugin.js
import config from './config.json'; // ✅ 支持导入 JSON

const MyPlugin = {
  id: config.pluginId,
  name: config.name,
  // ...
};
```

### 5. SVG 图标（支持）
```javascript
// my-plugin.js
import { ReactComponent as MyIcon } from './icon.svg'; // ✅ 支持 SVG 作为组件
// 或者
import iconUrl from './icon.svg'; // 作为 URL

const MyPlugin = {
  renderToolbarButton: () => (
    <div>
      <MyIcon />
      <img src={iconUrl} alt="Icon" />
    </div>
  )
};
```

## 插件目录结构示例

```
plugins/
├── core/
│   ├── my-plugin.js          # 主入口文件（必需）
│   ├── my-plugin.css          # 样式文件（可选）
│   ├── icon.png               # 图标文件（可选）
│   ├── config.json            # 配置文件（可选）
│   └── components/
│       ├── MyComponent.js     # 子组件（可选）
│       └── MyComponent.css    # 子组件样式（可选）
```

## 完整示例：带资源的插件

### 示例 1: 带 CSS 样式的插件

```javascript
// plugins/core/styled-button-plugin.js
import React, { useState } from 'react';
import './styled-button-plugin.css'; // 导入 CSS

const StyledButtonPlugin = {
  id: 'styled-button',
  name: '样式化按钮',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  
  renderToolbarButton: () => {
    return function StyledButton() {
      const [clicked, setClicked] = useState(false);
      
      return (
        <button
          className="styled-plugin-button" // 使用 CSS 类
          onClick={() => setClicked(!clicked)}
        >
          {clicked ? '已点击' : '点击我'}
        </button>
      );
    };
  }
};

export default StyledButtonPlugin;
```

```css
/* plugins/core/styled-button-plugin.css */
.styled-plugin-button {
  padding: 4px 12px;
  background: linear-gradient(to bottom, #4a90e2, #357abd);
  color: white;
  border: 2px outset #4a90e2;
  border-radius: 4px;
  cursor: pointer;
  font-family: 'MS Sans Serif', sans-serif;
  transition: all 0.2s;
}

.styled-plugin-button:hover {
  background: linear-gradient(to bottom, #5ba0f2, #4580cd);
}

.styled-plugin-button:active {
  border: 2px inset #4a90e2;
}
```

### 示例 2: 带图片和图标的插件

```javascript
// plugins/core/icon-button-plugin.js
import React from 'react';
import pluginIcon from './assets/icon.png';
import { ReactComponent as SettingsIcon } from './assets/settings.svg';

const IconButtonPlugin = {
  id: 'icon-button',
  name: '图标按钮',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  
  renderToolbarButton: () => {
    return function IconButton() {
      return (
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <img 
            src={pluginIcon} 
            alt="Plugin Icon" 
            style={{ width: '16px', height: '16px' }}
          />
          <SettingsIcon style={{ width: '16px', height: '16px' }} />
          <span>我的插件</span>
        </div>
      );
    };
  }
};

export default IconButtonPlugin;
```

### 示例 3: 带配置文件的插件

```json
// plugins/core/configurable-plugin/config.json
{
  "pluginId": "configurable",
  "name": "可配置插件",
  "defaultSettings": {
    "theme": "light",
    "maxItems": 10,
    "autoSave": true
  }
}
```

```javascript
// plugins/core/configurable-plugin/index.js
import React from 'react';
import config from './config.json';
import defaultSettings from './default-settings.json';

const ConfigurablePlugin = {
  id: config.pluginId,
  name: config.name,
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  
  renderToolbarButton: () => {
    return function ConfigurableButton() {
      const settings = { ...defaultSettings, ...config.defaultSettings };
      
      return (
        <div>
          <p>主题: {settings.theme}</p>
          <p>最大项数: {settings.maxItems}</p>
        </div>
      );
    };
  }
};

export default ConfigurablePlugin;
```

## 限制和注意事项

### 1. 插件入口必须是 JS 文件
- 插件系统通过 `import` 语句加载插件
- 入口文件必须是 `.js` 或 `.jsx` 文件
- 不能直接加载 `.json`、`.css` 等作为插件入口

### 2. 资源文件路径
- 资源文件应该放在插件文件同一目录或子目录中
- 使用相对路径导入：`import './style.css'`
- webpack 会自动处理这些导入

### 3. 构建时处理
- 所有资源在构建时会被 webpack 处理
- 图片会被转换为 base64 或生成独立文件
- CSS 会被提取或内联到 JS bundle 中

### 4. 运行时动态加载
- 如果使用动态 `import()`，资源也会被正确处理
- 但需要确保资源文件在构建时存在

## 未来扩展方向

### 1. 插件包支持（Plugin Package）
支持包含多个文件的插件包：

```
plugins/
└── packages/
    └── my-plugin-package/
        ├── package.json        # 插件元数据
        ├── index.js            # 入口文件
        ├── styles/
        │   └── main.css
        ├── assets/
        │   ├── icons/
        │   └── images/
        └── components/
```

### 2. 插件清单文件（Manifest）
支持 `plugin.json` 清单文件：

```json
{
  "id": "my-plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "entry": "./index.js",
  "assets": [
    "./styles/main.css",
    "./assets/icon.png"
  ],
  "dependencies": {
    "react": "^18.0.0"
  }
}
```

### 3. 插件市场支持
- 支持从外部 URL 加载插件
- 支持插件版本管理
- 支持插件依赖解析

## 总结

**当前状态：**
- ✅ 插件入口必须是 JS 文件
- ✅ 插件内部可以导入 CSS、图片、JSON 等资源
- ✅ webpack 会自动处理这些资源

**建议：**
- 对于简单插件，继续使用单个 JS 文件 + 内联样式
- 对于复杂插件，使用 JS 文件 + 导入的 CSS/资源文件
- 未来可以考虑支持插件包格式

**最佳实践：**
1. 简单插件：单文件 + 内联样式（如当前的 `word-count-plugin.js`）
2. 中等复杂度：主文件 + CSS 文件（如示例 1）
3. 复杂插件：目录结构 + 多个文件（如示例 3）





