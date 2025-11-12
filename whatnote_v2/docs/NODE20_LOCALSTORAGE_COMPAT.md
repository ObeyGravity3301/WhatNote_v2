## Node 20+ `localStorage` 兼容问题排查与修复说明

### 背景

- 2025-11-12 起，Arch Linux 系统自动升级 Node.js 至 20+ 版本。
- Node 20 引入 WebStorage 安全策略：在未通过 `--localstorage-file` 指定存储路径的情况下，访问 `globalThis.localStorage`/`sessionStorage` 会抛出 `SecurityError`。
- `react-scripts`（CRA）在构建阶段使用 `html-webpack-plugin` 生成模板时会读取 `localStorage`，导致开发服务器启动失败。

### 典型报错

```
SecurityError: Cannot initialize local storage without a `--localstorage-file` path
  - webstorage:28 Object.get [as localStorage]
  - util:660 get localStorage
  - index.js:636 HtmlWebpackPlugin.evaluateCompilationResult
```

### 临时规避方案（不推荐长期依赖）

- 降级 Node 至 18 LTS 或 16 LTS。
- 或者使用 `node --localstorage-file=/tmp/node-localstorage.json` 启动。

这两种方式都要求手动维护 Node 版本/启动命令，不利于团队协作与 CI 环境统一。

### 已采用的项目级修复

1. **内存版 WebStorage Polyfill（Node 环境）**
   - 新增 `frontend/scripts/setupLocalStoragePolyfill.js`，在 Node 运行时通过内存对象模拟 `localStorage`/`sessionStorage`。
   - 所有 CRA 脚本（start/build/test/eject）改为执行自定义入口，先加载 polyfill 再调用官方脚本。
2. **Craco 兜底处理**
   - `frontend/craco.config.js` 保留了在打包阶段注入空实现的逻辑，防止后续切换到 craco 时遗漏 polyfill。
3. **组件懒加载优化**
   - `BoardCanvas` 等组件不再在初始化时直接访问 `localStorage`，而是在 `useEffect` 中判定浏览器环境后读取，源头上降低构建期访问风险。

### 操作步骤（开发者常用流程）

| 场景 | 指令 | 说明 |
| --- | --- | --- |
| 本地开发 | `npm start` | 自动加载 polyfill，Node 20+ 可直接运行 |
| 构建发布 | `npm run build` | 同上，生成产物不受影响 |
| 单元测试 | `npm test` | Jest 环境同样会预加载 polyfill |
| 异常排查 | 查看 `frontend/scripts/`、`frontend/craco.config.js` | 确认 polyfill 未被误删 |

### 后续维护建议

1. **固定 Node 版本范围**：在 `.nvmrc` / Dockerfile 中注明“>=20.0.0”，并保留以上 polyfill，确保任何新环境启动都一致。
2. **组件开发规范**：若在 React 组件中访问浏览器 API，优先在 `useEffect` 内进行，并加上 `typeof window !== 'undefined'` 检测。
3. **依赖升级检查**：未来如迁移至 Vite、Webpack 5 原生配置或其他脚手架，需确认其对 Node 20 的处理方式，如果不再需要该 polyfill，可在发布说明中移除。
4. **文档标注**：在团队 Wiki / README 中引用本文件，提醒协作者注意 Node 20 的行为变更。

### 参考资料

- [Node.js 20.0.0 Release Notes](https://nodejs.org/en/blog/release/v20.0.0/)
- [WHATWG Web Storage 标准实现说明](https://html.spec.whatwg.org/multipage/webstorage.html)
- CRA 社区讨论：<https://github.com/facebook/create-react-app/issues/13556>

