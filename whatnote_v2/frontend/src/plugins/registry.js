/**
 * 插件注册表
 * 管理所有插件的注册、启用、禁用
 */

class PluginRegistry {
  constructor() {
    this.plugins = new Map();
    this.enabledPlugins = new Set();
    this.disabledPlugins = new Set(); // 记录用户明确禁用的插件
    this.hasLoadedPreferences = false;
    this.loadUserPreferences();
    this.hasLoadedPreferences = true;
  }

  /**
   * 注册插件
   * @param {Object} plugin - 插件对象
   */
  register(plugin) {
    if (this.plugins.has(plugin.id)) {
      console.warn(`[插件系统] 插件 ${plugin.id} 已存在，将被覆盖`);
    }

    this.plugins.set(plugin.id, plugin);
    console.log(`[插件系统] 已注册插件: ${plugin.name} (${plugin.id})`);

    // 如果用户偏好中已明确启用，则启用
    if (this.enabledPlugins.has(plugin.id)) {
      this.enable(plugin.id, false); // false 表示不保存（因为已经在 enabledPlugins 中）
    } else if (this.hasLoadedPreferences) {
      // 如果已加载用户偏好，且插件不在启用列表中，说明用户已禁用或未启用
      // 只有在 enabledByDefault !== false 且用户偏好中没有记录时才默认启用
      // 但这里我们保守一点：如果用户偏好已加载，且插件不在启用列表中，就不启用
      // 这样可以确保用户禁用的插件不会因为刷新而重新启用
      if (plugin.enabledByDefault !== false && !this.disabledPlugins.has(plugin.id)) {
        // 首次安装的插件，默认启用
        this.enable(plugin.id, true); // 保存偏好
      }
    } else {
      // 如果还没有加载用户偏好，使用默认值
      if (plugin.enabledByDefault !== false) {
        this.enable(plugin.id, false); // 不保存（因为偏好还没加载）
      }
    }
  }

  /**
   * 启用插件
   * @param {string} pluginId - 插件ID
   * @param {boolean} savePreferences - 是否保存用户偏好（默认 true）
   */
  enable(pluginId, savePreferences = true) {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) {
      console.warn(`[插件系统] 插件 ${pluginId} 不存在`);
      return false;
    }

    if (plugin.onEnable) {
      try {
        plugin.onEnable(this.getContext());
      } catch (error) {
        console.error(`[插件系统] 启用插件 ${pluginId} 时出错:`, error);
        return false;
      }
    }

    this.enabledPlugins.add(pluginId);
    if (savePreferences) {
    this.saveUserPreferences();
    }
    console.log(`[插件系统] 已启用插件: ${plugin.name}`);
    return true;
  }

  /**
   * 禁用插件
   * @param {string} pluginId - 插件ID
   */
  disable(pluginId) {
    const plugin = this.plugins.get(pluginId);
    if (!plugin) {
      console.warn(`[插件系统] 插件 ${pluginId} 不存在`);
      return false;
    }

    if (plugin.onDisable) {
      try {
        plugin.onDisable(this.getContext());
      } catch (error) {
        console.error(`[插件系统] 禁用插件 ${pluginId} 时出错:`, error);
      }
    }

    this.enabledPlugins.delete(pluginId);
    // 记录用户明确禁用的插件
    if (!this.disabledPlugins) {
      this.disabledPlugins = new Set();
    }
    this.disabledPlugins.add(pluginId);
    this.saveUserPreferences();
    console.log(`[插件系统] 已禁用插件: ${plugin.name}`);
    return true;
  }

  /**
   * 获取插件
   * @param {string} pluginId - 插件ID
   */
  get(pluginId) {
    return this.plugins.get(pluginId);
  }

  /**
   * 获取所有插件
   */
  getAll() {
    return Array.from(this.plugins.values());
  }

  /**
   * 获取所有已启用的插件
   */
  getEnabled() {
    return Array.from(this.enabledPlugins)
      .map(id => this.plugins.get(id))
      .filter(Boolean);
  }

  /**
   * 获取适用于特定窗口类型的工具栏按钮插件
   * @param {string} windowType - 窗口类型
   */
  getToolbarPluginsForWindow(windowType) {
    return this.getEnabled()
      .filter(p => 
        p.type === 'toolbar-feature' && 
          p.targetWindowTypes &&
          p.targetWindowTypes.includes(windowType)
      );
  }

  /**
   * 获取窗口类型插件
   * @param {string} windowType - 窗口类型
   */
  getWindowTypePlugin(windowType) {
    return this.getEnabled()
      .find(p => p.type === 'window-type' && p.windowType === windowType);
  }

  /**
   * 获取所有窗口类型插件
   */
  getAllWindowTypePlugins() {
    return this.getEnabled()
      .filter(p => p.type === 'window-type');
  }

  /**
   * 获取右键菜单项
   * @param {string} menuType - 菜单类型 ('desktop' 或 'icon')
   */
  getContextMenuItems(menuType) {
    const items = [];
    this.getEnabled().forEach(plugin => {
      if (plugin.contextMenuItems && Array.isArray(plugin.contextMenuItems)) {
        plugin.contextMenuItems.forEach(item => {
          if (item.menuType === menuType || item.menuType === 'both') {
            items.push({
              ...item,
              pluginId: plugin.id // 标记来源插件
            });
          }
        });
      }
    });
    return items;
  }

  /**
   * 检查插件是否启用
   * @param {string} pluginId - 插件ID
   */
  isEnabled(pluginId) {
    return this.enabledPlugins.has(pluginId);
  }

  /**
   * 获取插件系统上下文（供插件使用）
   */
  getContext() {
    return {
      // 可以在这里提供一些全局 API
      // 例如：事件总线、API 客户端等
    };
  }

  /**
   * 保存用户偏好到 localStorage
   */
  saveUserPreferences() {
    try {
      localStorage.setItem('whatnote_enabled_plugins', 
        JSON.stringify(Array.from(this.enabledPlugins)));
      // 同时保存已禁用的插件列表（用于区分"未设置"和"已禁用"）
      if (this.disabledPlugins && this.disabledPlugins.size > 0) {
        localStorage.setItem('whatnote_disabled_plugins', 
          JSON.stringify(Array.from(this.disabledPlugins)));
      } else {
        localStorage.removeItem('whatnote_disabled_plugins');
      }
    } catch (error) {
      console.error('[插件系统] 保存用户偏好失败:', error);
    }
  }

  /**
   * 从 localStorage 加载用户偏好
   */
  loadUserPreferences() {
    try {
      const savedEnabled = localStorage.getItem('whatnote_enabled_plugins');
      const savedDisabled = localStorage.getItem('whatnote_disabled_plugins');
      
      if (savedEnabled) {
        const savedIds = JSON.parse(savedEnabled);
        this.enabledPlugins = new Set(savedIds);
        console.log('[插件系统] 已加载用户插件偏好（已启用）:', Array.from(this.enabledPlugins));
      } else {
        this.enabledPlugins = new Set();
      }
      
      if (savedDisabled) {
        const disabledIds = JSON.parse(savedDisabled);
        this.disabledPlugins = new Set(disabledIds);
        console.log('[插件系统] 已加载用户插件偏好（已禁用）:', Array.from(this.disabledPlugins));
      } else {
        this.disabledPlugins = new Set();
      }
    } catch (error) {
      console.error('[插件系统] 加载用户偏好失败:', error);
      this.enabledPlugins = new Set();
      this.disabledPlugins = new Set();
    }
  }
}

// 创建单例
export const pluginRegistry = new PluginRegistry();

