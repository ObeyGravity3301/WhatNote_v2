const path = require('path');

(() => {
  try {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    const needsPolyfill = !descriptor || typeof descriptor.get === 'function';

    if (needsPolyfill) {
      const storageData = {};
      const memoryStorage = {
        getItem: key => (Object.prototype.hasOwnProperty.call(storageData, key) ? storageData[key] : null),
        setItem: (key, value) => {
          storageData[key] = String(value);
        },
        removeItem: key => {
          delete storageData[key];
        },
        clear: () => {
          Object.keys(storageData).forEach(k => {
            delete storageData[k];
          });
        },
        key: index => {
          const keys = Object.keys(storageData);
          return index >= 0 && index < keys.length ? keys[index] : null;
        },
        get length() {
          return Object.keys(storageData).length;
        }
      };

      Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        enumerable: true,
        writable: false,
        value: memoryStorage
      });

      if (typeof globalThis.window === 'undefined') {
        globalThis.window = {};
      }
      if (typeof globalThis.window.localStorage === 'undefined') {
        globalThis.window.localStorage = memoryStorage;
      }
    }
  } catch (error) {
    // 记录失败但不阻断构建流程
    console.warn('[craco] 初始化 localStorage polyfill 失败:', error);
  }
})();

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // 解决 localStorage 模板参数访问问题
      webpackConfig.plugins.forEach(plugin => {
        if (plugin.constructor && plugin.constructor.name === 'HtmlWebpackPlugin') {
          plugin.options.templateParameters = {
            ...plugin.options.templateParameters,
            localStorage: {
              getItem: () => null,
              setItem: () => null,
              removeItem: () => null,
              clear: () => null
            }
          };
        }
      });

      webpackConfig.resolve = webpackConfig.resolve || {};

      // Node.js 核心模块 polyfill / 禁用
      webpackConfig.resolve.fallback = Object.assign({}, webpackConfig.resolve.fallback, {
        util: require.resolve('util/'),
        fs: false,
        path: false,
        net: false,
        tls: false,
      });

      // 将 nanoid/non-secure 指向浏览器友好的实现，避免 CJS/ESM 互操作问题
      webpackConfig.resolve.alias = Object.assign({}, webpackConfig.resolve.alias, {
        'nanoid/non-secure': path.resolve(__dirname, 'src/shims/nanoid-non-secure.js'),
      });

      return webpackConfig;
    }
  }
};
