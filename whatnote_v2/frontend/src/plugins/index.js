/**
 * 插件系统入口
 * 统一导出所有插件和注册表
 */

import { pluginRegistry } from './registry';
import wordCountPlugin from './core/word-count-plugin';
import stickyNotePlugin from './core/sticky-note-plugin';

// 注册所有内置插件
export function initializePlugins() {
  console.log('[插件系统] 初始化插件系统...');
  
  // 注册工具栏功能插件
  pluginRegistry.register(wordCountPlugin);
  console.log('[插件系统] 已注册字数统计插件');
  
  // 注册窗口类型插件
  pluginRegistry.register(stickyNotePlugin);
  console.log('[插件系统] 已注册便签窗口插件');
  
  const allPlugins = pluginRegistry.getAll();
  const enabledPlugins = pluginRegistry.getEnabled();
  
  console.log(`[插件系统] 已注册 ${allPlugins.length} 个插件:`, allPlugins.map(p => p.id));
  console.log(`[插件系统] 已启用 ${enabledPlugins.length} 个插件:`, enabledPlugins.map(p => p.id));
  
  // 验证插件是否正确注册
  const wordCount = pluginRegistry.get('word-count');
  if (wordCount) {
    console.log('[插件系统] ✓ 字数统计插件已正确注册');
  } else {
    console.error('[插件系统] ✗ 字数统计插件注册失败');
  }
}

// 导出注册表供其他模块使用
export { pluginRegistry };

// 导出插件（供参考）
export { wordCountPlugin, stickyNotePlugin };

