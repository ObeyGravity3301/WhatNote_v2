'use strict';

function createMemoryStorage() {
  let data = {};

  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    },
    removeItem(key) {
      delete data[key];
    },
    clear() {
      data = {};
    },
    key(index) {
      const keys = Object.keys(data);
      return index >= 0 && index < keys.length ? keys[index] : null;
    },
    get length() {
      return Object.keys(data).length;
    }
  };
}

function ensureWebStoragePolyfill() {
  try {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    const needsLocalStoragePolyfill = !descriptor || typeof descriptor.get === 'function';

    if (needsLocalStoragePolyfill) {
      const localStorageStub = createMemoryStorage();
      Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        enumerable: true,
        writable: false,
        value: localStorageStub
      });

      if (typeof globalThis.window === 'undefined') {
        globalThis.window = {};
      }
      if (typeof globalThis.window.localStorage === 'undefined') {
        globalThis.window.localStorage = localStorageStub;
      }
    }

    const sessionDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage');
    const needsSessionStoragePolyfill = !sessionDescriptor || typeof sessionDescriptor.get === 'function';

    if (needsSessionStoragePolyfill) {
      const sessionStorageStub = createMemoryStorage();
      Object.defineProperty(globalThis, 'sessionStorage', {
        configurable: true,
        enumerable: true,
        writable: false,
        value: sessionStorageStub
      });

      if (typeof globalThis.window === 'undefined') {
        globalThis.window = {};
      }
      if (typeof globalThis.window.sessionStorage === 'undefined') {
        globalThis.window.sessionStorage = sessionStorageStub;
      }
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn('[whatnote] 初始化 localStorage polyfill 失败:', error);
  }
}

ensureWebStoragePolyfill();

module.exports = {
  ensureWebStoragePolyfill
};

