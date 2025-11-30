# 插件系统测试指南

## 测试插件文件移除后的系统行为

本指南说明如何测试在移除插件文件后，系统是否能正常工作。

### 方法一：使用测试脚本（推荐）

我们提供了一个自动化测试脚本：

```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2
./test_plugin_removal.sh
```

脚本功能：
1. 自动备份插件文件
2. 提供交互式菜单选择要移除的插件
3. 测试完成后可以一键恢复

### 方法二：手动测试

#### 步骤 1: 备份插件文件

```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2/frontend/src/plugins/core
mkdir -p ../core.backup
cp *.js ../core.backup/
```

#### 步骤 2: 移除插件文件进行测试

**测试场景 1: 移除字数统计插件**

```bash
mv word-count-plugin.js word-count-plugin.js.backup
```

**测试场景 2: 移除便签窗口插件**

```bash
mv sticky-note-plugin.js sticky-note-plugin.js.backup
```

**测试场景 3: 移除所有插件**

```bash
mv *.js *.js.backup
```

#### 步骤 3: 重新构建并测试

```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2/frontend
npm start
```

**预期行为：**
- ❌ **构建时**：如果使用静态 import，webpack 会报错（文件不存在）
- ✅ **运行时**：如果构建成功，应用应该能正常启动，但相关功能不可用

#### 步骤 4: 检查功能

1. **应用启动**
   - 应用应该能正常启动
   - 控制台应该显示插件加载警告

2. **字数统计插件测试**
   - 打开文本编辑器窗口
   - 工具栏中**不应该**显示字数统计按钮
   - 插件管理器中应该显示插件未加载

3. **便签窗口插件测试**
   - 桌面右键菜单中**不应该**显示"创建便签"选项
   - 插件管理器中应该显示插件未加载

4. **插件管理器测试**
   - 打开插件管理器窗口
   - 应该显示插件列表（即使插件未加载）
   - 未加载的插件应该显示警告信息

#### 步骤 5: 恢复插件

```bash
cd /home/obeygravity/Projects/whatnote/whatnote_v2/frontend/src/plugins/core
mv *.js.backup *.js
# 或者从备份目录恢复
cp ../core.backup/*.js .
```

### 方法三：使用条件导入（高级）

如果你想测试运行时动态加载，可以临时修改 `index.js`：

```javascript
// 临时测试代码：使用动态 import
let wordCountPlugin = null;
let stickyNotePlugin = null;

// 动态加载插件
import('./core/word-count-plugin')
  .then(module => {
    wordCountPlugin = module.default || module;
    console.log('字数统计插件加载成功');
  })
  .catch(error => {
    console.warn('字数统计插件加载失败:', error);
  });

import('./core/sticky-note-plugin')
  .then(module => {
    stickyNotePlugin = module.default || module;
    console.log('便签窗口插件加载成功');
  })
  .catch(error => {
    console.warn('便签窗口插件加载失败:', error);
  });

// 注意：需要修改 initializePlugins 为异步函数
export async function initializePlugins() {
  // 等待插件加载完成
  await Promise.all([
    import('./core/word-count-plugin').catch(() => null),
    import('./core/sticky-note-plugin').catch(() => null)
  ]);
  
  // ... 注册逻辑
}
```

### 测试检查清单

- [ ] 应用能正常启动（无崩溃）
- [ ] 控制台显示插件加载警告（如果插件缺失）
- [ ] 插件管理器能正常打开
- [ ] 缺失的插件在插件管理器中显示为"未加载"
- [ ] 其他核心功能正常工作
- [ ] 没有 JavaScript 错误
- [ ] 恢复插件后功能正常

### 预期结果

**正常情况（所有插件存在）：**
- ✅ 应用正常启动
- ✅ 所有插件正常加载和注册
- ✅ 所有功能可用

**插件缺失情况：**
- ✅ 应用仍能正常启动
- ⚠️ 控制台显示警告信息
- ❌ 相关功能不可用（按钮不显示、菜单项缺失）
- ✅ 其他功能正常工作
- ✅ 插件管理器显示插件状态

### 注意事项

1. **构建时检查**：使用静态 `import` 时，如果文件不存在，webpack 会在构建时报错。这是**预期的行为**，帮助我们及早发现问题。

2. **运行时检查**：即使构建成功，如果插件文件在运行时被删除，系统应该优雅地处理这种情况，显示警告但继续运行。

3. **错误处理**：插件系统已经实现了错误处理，即使插件加载失败，也不会导致整个应用崩溃。

4. **恢复测试**：测试完成后，记得恢复插件文件，确保系统恢复正常状态。

### 故障排除

**问题：构建失败，提示找不到模块**
- **原因**：插件文件不存在，静态 import 无法解析
- **解决**：这是预期的，说明文件确实缺失。使用动态 import 或恢复文件。

**问题：应用启动后功能缺失但没有警告**
- **原因**：错误处理可能有问题
- **解决**：检查控制台日志，确认插件初始化是否正常执行

**问题：恢复插件后功能仍不可用**
- **原因**：可能需要重新构建或清除缓存
- **解决**：清除 `node_modules/.cache` 并重新构建





