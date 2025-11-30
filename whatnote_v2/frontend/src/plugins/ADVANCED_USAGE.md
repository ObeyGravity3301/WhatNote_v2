# 高级插件使用指南

## 目录

1. [大型资源文件管理（AI 模型）](#大型资源文件管理ai-模型)
2. [外部 Web 应用集成](#外部-web-应用集成)
3. [插件移除和清理](#插件移除和清理)

---

## 大型资源文件管理（AI 模型）

### 问题场景

当你需要集成大型 AI 模型（如 gpt-sovit、Whisper 等）时，模型文件通常很大（几十 MB 到几 GB），不能直接打包到前端代码中。

### 解决方案

#### 方案 1: 后端 API 服务（推荐）⭐

**优点：**
- 前端不加载大文件，启动速度快
- 模型可以复用，节省内存
- 安全性更好（API Key 等敏感信息在后端）
- 支持 GPU 加速

**实现步骤：**

1. **后端添加 TTS API 端点**

```python
# backend/main.py
@app.post("/api/tts/generate")
async def generate_tts(request: Request):
    data = await request.json()
    text = data.get("text")
    model = data.get("model", "gpt-sovit")
    
    # 加载模型并生成语音
    # ... 模型推理代码 ...
    
    # 返回音频文件
    return FileResponse(audio_path, media_type="audio/wav")
```

2. **前端插件调用后端 API**

```javascript
// plugins/core/tts-plugin.js
const response = await fetch('http://localhost:8081/api/tts/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: content, model: 'gpt-sovit' })
});
const blob = await response.blob();
const audioUrl = URL.createObjectURL(blob);
```

#### 方案 2: 本地模型文件（public 目录）

**适用场景：**
- 模型文件较小（< 50MB）
- 需要离线使用
- 不想依赖后端服务

**实现步骤：**

1. **将模型文件放到 `public/models/` 目录**

```
whatnote_v2/
└── frontend/
    └── public/
        └── models/
            └── gpt-sovit/
                ├── model.onnx
                ├── config.json
                └── vocoder.onnx
```

2. **前端加载模型**

```javascript
// plugins/core/tts-plugin.js
import * as ort from 'onnxruntime-web';

const modelPath = '/models/gpt-sovit/model.onnx';
const session = await ort.InferenceSession.create(modelPath);
// ... 使用模型推理 ...
```

**注意：**
- 需要安装 `onnxruntime-web`: `npm install onnxruntime-web`
- 模型文件不会被 webpack 打包，运行时从服务器加载
- 首次加载可能需要较长时间

#### 方案 3: CDN 远程加载

**适用场景：**
- 模型文件托管在 CDN
- 需要版本管理
- 多用户共享模型

**实现步骤：**

```javascript
// plugins/core/tts-plugin.js
const modelUrl = 'https://your-cdn.com/models/gpt-sovit/v1.0/model.onnx';
const response = await fetch(modelUrl);
const arrayBuffer = await response.arrayBuffer();
const session = await ort.InferenceSession.create(arrayBuffer);
```

### 模型文件存储位置

```
whatnote_v2/
├── backend/
│   └── models/              # 后端模型存储（推荐）
│       └── gpt-sovit/
│           ├── model.onnx
│           └── config.json
└── frontend/
    └── public/
        └── models/          # 前端模型存储（可选）
            └── gpt-sovit/
                └── model.onnx
```

### 插件移除时的清理

当禁用或移除插件时，应该清理已加载的模型：

```javascript
// plugins/core/tts-plugin.js
let modelSession = null;

onEnable: async (context) => {
  // 加载模型
  modelSession = await ort.InferenceSession.create(modelPath);
},

onDisable: (context) => {
  // 清理模型资源
  if (modelSession) {
    modelSession.release();
    modelSession = null;
  }
}
```

---

## 外部 Web 应用集成

### 使用场景

- 集成第三方工具（Draw.io、Excalidraw 等）
- 集成自己的其他 Web 应用
- 通过 iframe 嵌入外部服务

### 实现方式

#### 1. 创建窗口类型插件

参考 `web-app-plugin.js` 示例，创建一个 `window-type` 插件：

```javascript
const WebAppPlugin = {
  id: 'web-app-plugin',
  type: 'window-type',
  windowType: 'web-app',
  
  renderWindow: (props) => {
    return function WebAppWindow() {
      const [appUrl, setAppUrl] = useState('https://example.com');
      
      return (
        <iframe
          src={appUrl}
          style={{ width: '100%', height: '100%', border: 'none' }}
          sandbox="allow-same-origin allow-scripts allow-forms"
        />
      );
    };
  }
};
```

#### 2. iframe 通信

如果需要与嵌入的应用通信：

**从 iframe 接收消息：**

```javascript
useEffect(() => {
  const handleMessage = (event) => {
    // 验证来源
    if (event.origin !== 'https://trusted-domain.com') return;
    
    console.log('收到消息:', event.data);
    // 处理消息
  };
  
  window.addEventListener('message', handleMessage);
  return () => window.removeEventListener('message', handleMessage);
}, []);
```

**向 iframe 发送消息：**

```javascript
const sendMessage = (data) => {
  if (iframeRef.current?.contentWindow) {
    iframeRef.current.contentWindow.postMessage(data, 'https://target-domain.com');
  }
};
```

#### 3. iframe 安全设置

使用 `sandbox` 属性限制 iframe 权限：

```javascript
<iframe
  sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
  // allow-same-origin: 允许同源访问
  // allow-scripts: 允许执行脚本
  // allow-forms: 允许表单提交
  // allow-popups: 允许弹窗
/>
```

**安全建议：**
- 只信任已知域名的应用
- 使用 `sandbox` 限制权限
- 验证 `event.origin` 防止 XSS
- 避免加载不可信的外部内容

#### 4. 配置外部应用列表

在插件中定义可用的 Web 应用：

```javascript
const WebAppPlugin = {
  webApps: [
    {
      id: 'drawio',
      name: 'Draw.io',
      url: 'https://app.diagrams.net/',
      icon: '📊'
    },
    {
      id: 'excalidraw',
      name: 'Excalidraw',
      url: 'https://excalidraw.com/',
      icon: '✏️'
    }
  ]
};
```

### 集成自己的 Web 应用

如果你的 Web 应用需要与 WhatNote 通信：

**1. 在你的应用中监听消息：**

```javascript
// 你的 Web 应用代码
window.addEventListener('message', (event) => {
  // 验证来源
  if (event.origin !== 'http://localhost:3000') return;
  
  if (event.data.type === 'SAVE_DATA') {
    // 保存数据
    const data = event.data.payload;
    // ... 保存逻辑 ...
    
    // 发送确认消息
    window.parent.postMessage({
      type: 'DATA_SAVED',
      success: true
    }, 'http://localhost:3000');
  }
});
```

**2. 在插件中发送消息：**

```javascript
// plugins/core/web-app-plugin.js
const saveDataToApp = (data) => {
  iframeRef.current.contentWindow.postMessage({
    type: 'SAVE_DATA',
    payload: data
  }, 'https://your-app.com');
};
```

---

## 插件移除和清理

### 禁用插件

通过插件管理器禁用插件：

1. 打开插件管理器（任务栏 → 插件）
2. 找到要禁用的插件
3. 点击开关按钮禁用

禁用后：
- 插件功能立即失效
- 调用 `onDisable` 钩子清理资源
- 状态保存到 `localStorage`

### 完全移除插件

#### 方法 1: 删除插件文件（推荐）

```bash
# 删除插件文件
rm whatnote_v2/frontend/src/plugins/core/tts-plugin.js

# 从 index.js 中移除导入（如果使用静态导入）
# 编辑 index.js，删除相关 import 和注册代码
```

#### 方法 2: 重命名为 .backup

```bash
# 重命名插件文件
mv whatnote_v2/frontend/src/plugins/core/tts-plugin.js \
   whatnote_v2/frontend/src/plugins/core/tts-plugin.js.backup
```

**注意：** 如果使用静态 `import`，需要重启开发服务器；如果使用动态 `import`，刷新页面即可。

### 清理插件数据

插件可能存储的数据：

1. **localStorage 数据**

```javascript
// 在浏览器控制台执行
localStorage.removeItem('whatnote_tts_plugin_settings');
```

2. **窗口内容**

如果插件创建了窗口，窗口数据会保存在后端。可以通过删除窗口来清理。

3. **后端模型文件**

如果使用后端 API，需要手动删除模型文件：

```bash
rm -rf whatnote_v2/backend/models/gpt-sovit/
```

### 清理检查清单

- [ ] 禁用插件（通过插件管理器）
- [ ] 删除插件文件（或重命名为 .backup）
- [ ] 从 `index.js` 移除导入（如果使用静态导入）
- [ ] 清理 localStorage 数据
- [ ] 删除后端模型文件（如果使用）
- [ ] 重启开发服务器（如果使用静态导入）

---

## 最佳实践

### 1. 资源文件管理

- ✅ **推荐**: 使用后端 API 提供模型服务
- ⚠️ **谨慎**: 前端加载大文件（影响性能）
- ❌ **避免**: 将大文件打包到 bundle 中

### 2. 外部应用集成

- ✅ **推荐**: 只集成信任的应用
- ✅ **推荐**: 使用 `sandbox` 属性限制权限
- ✅ **推荐**: 验证 `event.origin` 防止 XSS
- ❌ **避免**: 加载不可信的外部内容

### 3. 插件移除

- ✅ **推荐**: 先禁用，再删除文件
- ✅ **推荐**: 使用动态 `import` 便于测试
- ✅ **推荐**: 在 `onDisable` 中清理资源
- ❌ **避免**: 直接删除文件而不清理资源

---

## 示例插件

- **TTS 插件**: `plugins/core/tts-plugin.js` - 演示后端 API 集成
- **Web 应用插件**: `plugins/core/web-app-plugin.js` - 演示 iframe 集成

---

**最后更新**: 2024
**维护者**: WhatNote Team


