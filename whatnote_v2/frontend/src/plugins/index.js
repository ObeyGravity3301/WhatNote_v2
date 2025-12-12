/**
 * 插件系统入口 - 测试版本
 * 使用动态 import 支持运行时加载，可以测试插件文件缺失的情况
 * 
 * 使用方法：
 * 1. 临时将 index.js 重命名为 index.prod.js
 * 2. 将 index.test.js 重命名为 index.js
 * 3. 测试完成后恢复
 */

import { pluginRegistry } from './registry';

// 使用动态 import 来安全地加载插件
// 如果插件文件缺失，不会导致构建失败
let wordCountPlugin = null;
let stickyNotePlugin = null;
let ttsPlugin = null;
let webAppPlugin = null;
let pdfNarratorPlugin = null;
let cyberIRCPlugin = null;
let pluginsLoaded = false;

// 异步加载所有插件
async function loadPlugins() {
  if (pluginsLoaded) return;
  
  console.log('[插件系统] 开始动态加载插件...');
  
  // 加载字数统计插件
  try {
    const wordCountModule = await import('./core/word-count-plugin');
    wordCountPlugin = wordCountModule?.default || wordCountModule;
    console.log('[插件系统] ✓ 字数统计插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ 字数统计插件加载失败:', error.message);
    wordCountPlugin = null;
  }
  
  // 加载便签窗口插件
  try {
    const stickyNoteModule = await import('./core/sticky-note-plugin');
    stickyNotePlugin = stickyNoteModule?.default || stickyNoteModule;
    console.log('[插件系统] ✓ 便签窗口插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ 便签窗口插件加载失败:', error.message);
    stickyNotePlugin = null;
  }
  
  // 加载 TTS 语音生成插件
  try {
    const ttsModule = await import('./core/tts-plugin');
    ttsPlugin = ttsModule?.default || ttsModule;
    console.log('[插件系统] ✓ TTS 语音生成插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ TTS 语音生成插件加载失败:', error.message);
    ttsPlugin = null;
  }
  
  // 加载 Web 应用集成插件
  try {
    const webAppModule = await import('./core/web-app-plugin');
    webAppPlugin = webAppModule?.default || webAppModule;
    console.log('[插件系统] ✓ Web 应用集成插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ Web 应用集成插件加载失败:', error.message);
    webAppPlugin = null;
  }

  // 加载 PPT 智能讲解员插件
  try {
    const pdfNarratorModule = await import('./core/pdf-narrator-plugin');
    pdfNarratorPlugin = pdfNarratorModule?.default || pdfNarratorModule;
    console.log('[插件系统] ✓ PPT 智能讲解员插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ PPT 智能讲解员插件加载失败:', error.message);
    pdfNarratorPlugin = null;
  }

  // 加载 CyberIRC 插件
  try {
    const cyberIRCModule = await import('./core/cyber-irc-plugin');
    cyberIRCPlugin = cyberIRCModule?.default || cyberIRCModule;
    console.log('[插件系统] ✓ CyberIRC 插件加载成功');
  } catch (error) {
    console.warn('[插件系统] ⚠️ CyberIRC 插件加载失败:', error.message);
    cyberIRCPlugin = null;
  }

  // 加载快捷键设置插件
  try {
    const shortcutSettingsModule = await import('./core/shortcut-settings-plugin');
    const shortcutSettingsPlugin = shortcutSettingsModule?.default || shortcutSettingsModule;
    if (shortcutSettingsPlugin) {
      pluginRegistry.register(shortcutSettingsPlugin);
      console.log('[插件系统] ✓ 快捷键设置插件加载成功');
    }
  } catch (error) {
    console.warn('[插件系统] ⚠️ 快捷键设置插件加载失败:', error.message);
  }
  
  pluginsLoaded = true;
}

// 注册所有内置插件（兼容同步调用）
export function initializePlugins() {
  console.log('[插件系统] 初始化插件系统（测试模式）...');
  
  // 异步加载插件，加载完成后注册
  loadPlugins().then(() => {
    // 插件加载完成后注册
    registerLoadedPlugins();
  }).catch(error => {
    console.error('[插件系统] 插件加载过程出错:', error);
    // 即使加载失败，也尝试注册已加载的插件
    registerLoadedPlugins();
  });
  
  // 注意：由于是异步加载，插件可能在初始化时还未加载完成
  // 但系统会继续运行，插件会在加载完成后自动注册
}

// 注册已加载的插件
function registerLoadedPlugins() {
  
  let registeredCount = 0;
  let skippedCount = 0;
  
  // 注册工具栏功能插件
  if (wordCountPlugin) {
    try {
      pluginRegistry.register(wordCountPlugin);
      console.log('[插件系统] ✓ 已注册字数统计插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册字数统计插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ 字数统计插件未加载，跳过注册');
    skippedCount++;
  }
  
  // 注册便签窗口插件
  if (stickyNotePlugin) {
    try {
      pluginRegistry.register(stickyNotePlugin);
      console.log('[插件系统] ✓ 已注册便签窗口插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册便签窗口插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ 便签窗口插件未加载，跳过注册');
    skippedCount++;
  }
  
  // 注册 TTS 语音生成插件
  if (ttsPlugin) {
    try {
      pluginRegistry.register(ttsPlugin);
      console.log('[插件系统] ✓ 已注册 TTS 语音生成插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册 TTS 语音生成插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ TTS 语音生成插件未加载，跳过注册');
    skippedCount++;
  }
  
  // 注册 Web 应用集成插件
  if (webAppPlugin) {
    try {
      pluginRegistry.register(webAppPlugin);
      console.log('[插件系统] ✓ 已注册 Web 应用集成插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册 Web 应用集成插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ Web 应用集成插件未加载，跳过注册');
    skippedCount++;
  }

  // 注册 PPT 智能讲解员插件
  if (pdfNarratorPlugin) {
    try {
      pluginRegistry.register(pdfNarratorPlugin);
      console.log('[插件系统] ✓ 已注册 PPT 智能讲解员插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册 PPT 智能讲解员插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ PPT 智能讲解员插件未加载，跳过注册');
    skippedCount++;
  }

  // 注册 CyberIRC 插件
  if (cyberIRCPlugin) {
    try {
      pluginRegistry.register(cyberIRCPlugin);
      console.log('[插件系统] ✓ 已注册 CyberIRC 插件');
      registeredCount++;
    } catch (error) {
      console.error('[插件系统] ✗ 注册 CyberIRC 插件失败:', error);
      skippedCount++;
    }
  } else {
    console.warn('[插件系统] ⚠️ CyberIRC 插件未加载，跳过注册');
    skippedCount++;
  }
  
  const allPlugins = pluginRegistry.getAll();
  const enabledPlugins = pluginRegistry.getEnabled();
  
  console.log(`[插件系统] 初始化完成: 已注册 ${allPlugins.length} 个插件 (成功: ${registeredCount}, 跳过: ${skippedCount})`);
  console.log(`[插件系统] 已启用 ${enabledPlugins.length} 个插件:`, enabledPlugins.map(p => p.id));
  
  if (skippedCount > 0) {
    console.warn(`[插件系统] ⚠️ 有 ${skippedCount} 个插件未能加载，系统将继续运行`);
  }
  
  return { registeredCount, skippedCount };
}

// 导出注册表供其他模块使用
export { pluginRegistry };

// 导出插件（供参考，可能是 null）
export { wordCountPlugin, stickyNotePlugin, ttsPlugin, webAppPlugin, pdfNarratorPlugin, cyberIRCPlugin };
