/**
 * Web 应用集成插件示例
 * 演示如何将外部 Web 应用通过 iframe 集成到 WhatNote 中
 * 
 * 使用场景：
 * - 集成第三方工具（如在线编辑器、图表工具等）
 * - 集成自己的其他 Web 应用
 * - 通过 iframe 嵌入外部服务
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';

const WebAppPlugin = {
  id: 'web-app-plugin',
  name: 'Web应用集成',
  type: 'window-type',
  windowType: 'web-app',
  version: '1.0.0',
  description: '将外部 Web 应用集成到 WhatNote',
  enabledByDefault: true,
  icon: '🌐',
  
  // 可配置的 Web 应用列表
  webApps: [
    {
      id: 'example-app',
      name: '示例应用',
      url: 'https://example.com',
      icon: '🌐',
      description: '这是一个示例 Web 应用'
    },
    {
      id: 'drawio',
      name: 'Draw.io',
      url: 'https://app.diagrams.net/',
      icon: '📊',
      description: '在线图表绘制工具'
    },
    // 添加更多应用...
  ],
  
  // 获取默认窗口配置
  getDefaultWindowConfig: () => ({
    type: 'web-app',
    title: 'Web应用',
    content: JSON.stringify({
      appId: 'example-app', // 默认应用 ID
      url: 'https://example.com'
    }),
    size: {
      width: 800,
      height: 600
    }
  }),
  
  // 获取窗口图标
  getWindowIcon: () => '🌐',
  
  // 渲染窗口内容
  renderWindow: (props) => {
    return function WebAppWindow() {
      const { window: windowData, onContentChange } = props;
      const [appConfig, setAppConfig] = useState(() => {
        try {
          const content = windowData.content || '{}';
          return JSON.parse(content);
        } catch {
          return { appId: 'example-app', url: 'https://example.com' };
        }
      });
      const [selectedAppId, setSelectedAppId] = useState(appConfig.appId || 'example-app');
      const [customUrl, setCustomUrl] = useState(appConfig.url || '');
      const [isLoading, setIsLoading] = useState(true);
      const iframeRef = useRef(null);
      
      // 获取当前应用配置
      const currentApp = WebAppPlugin.webApps.find(app => app.id === selectedAppId) || 
                        { url: customUrl, name: '自定义应用' };
      
      // 更新应用配置
      const updateAppConfig = useCallback((newConfig) => {
        const updated = { ...appConfig, ...newConfig };
        setAppConfig(updated);
        onContentChange(JSON.stringify(updated));
      }, [appConfig, onContentChange]);
      
      // 切换应用
      const handleAppChange = useCallback((appId) => {
        setSelectedAppId(appId);
        const app = WebAppPlugin.webApps.find(a => a.id === appId);
        if (app) {
          updateAppConfig({ appId, url: app.url });
        }
      }, [updateAppConfig]);
      
      // 使用自定义 URL
      const handleCustomUrlChange = useCallback((url) => {
        setCustomUrl(url);
        updateAppConfig({ appId: 'custom', url });
      }, [updateAppConfig]);
      
      // iframe 加载完成
      const handleIframeLoad = useCallback(() => {
        setIsLoading(false);
      }, []);
      
      // 与 iframe 通信（如果需要）
      useEffect(() => {
        const handleMessage = (event) => {
          // 安全检查：验证消息来源
          // if (event.origin !== expectedOrigin) return;
          
          console.log('[Web应用插件] 收到来自 iframe 的消息:', event.data);
          
          // 处理来自嵌入应用的消息
          // 例如：保存数据、关闭窗口等
        };
        
        window.addEventListener('message', handleMessage);
        return () => {
          window.removeEventListener('message', handleMessage);
        };
      }, []);
      
      // 向 iframe 发送消息（如果需要）
      const sendMessageToIframe = useCallback((data) => {
        if (iframeRef.current && iframeRef.current.contentWindow) {
          iframeRef.current.contentWindow.postMessage(data, '*'); // 生产环境应该指定具体 origin
        }
      }, []);
      
      return (
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#f0f0f0',
          fontFamily: 'MS Sans Serif, sans-serif'
        }}>
          {/* 工具栏 */}
          <div style={{
            padding: '4px',
            backgroundColor: '#c0c0c0',
            borderBottom: '1px inset #c0c0c0',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexShrink: 0
          }}>
            <label style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span>应用:</span>
              <select
                value={selectedAppId}
                onChange={(e) => handleAppChange(e.target.value)}
                style={{
                  fontSize: '11px',
                  padding: '2px 4px',
                  backgroundColor: '#ffffff',
                  border: '1px inset #c0c0c0',
                  fontFamily: 'MS Sans Serif, sans-serif'
                }}
              >
                {WebAppPlugin.webApps.map(app => (
                  <option key={app.id} value={app.id}>
                    {app.icon} {app.name}
                  </option>
                ))}
                <option value="custom">自定义 URL</option>
              </select>
            </label>
            
            {selectedAppId === 'custom' && (
              <input
                type="text"
                value={customUrl}
                onChange={(e) => handleCustomUrlChange(e.target.value)}
                placeholder="输入 Web 应用 URL"
                style={{
                  flex: 1,
                  fontSize: '11px',
                  padding: '2px 4px',
                  backgroundColor: '#ffffff',
                  border: '1px inset #c0c0c0',
                  fontFamily: 'MS Sans Serif, sans-serif'
                }}
              />
            )}
            
            <button
              onClick={() => {
                if (iframeRef.current) {
                  iframeRef.current.src = iframeRef.current.src; // 重新加载
                }
              }}
              style={{
                padding: '2px 8px',
                fontSize: '11px',
                backgroundColor: '#c0c0c0',
                border: '2px outset #c0c0c0',
                cursor: 'pointer'
              }}
            >
              🔄 刷新
            </button>
          </div>
          
          {/* iframe 容器 */}
          <div style={{
            flex: 1,
            position: 'relative',
            backgroundColor: '#ffffff',
            border: '1px inset #c0c0c0'
          }}>
            {isLoading && (
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '12px',
                color: '#666'
              }}>
                加载中...
              </div>
            )}
            
            <iframe
              ref={iframeRef}
              src={currentApp.url}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                display: isLoading ? 'none' : 'block'
              }}
              onLoad={handleIframeLoad}
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
              // sandbox 属性限制 iframe 的权限，根据需要调整
              title={currentApp.name}
            />
          </div>
          
          {/* 状态栏（可选） */}
          <div style={{
            padding: '2px 4px',
            fontSize: '10px',
            backgroundColor: '#c0c0c0',
            borderTop: '1px inset #c0c0c0',
            color: '#666',
            display: 'flex',
            justifyContent: 'space-between'
          }}>
            <span>{currentApp.name}</span>
            <span>{currentApp.url}</span>
          </div>
        </div>
      );
    };
  },
  
  // 右键菜单项：快速创建 Web 应用窗口
  contextMenuItems: [
    {
      label: '新建 Web 应用窗口',
      icon: '🌐',
      menuType: 'desktop',
      action: 'plugin:web-app:create',
      order: 10
    }
  ],
  
  // 处理右键菜单动作
  handleContextMenuAction: async (action, context) => {
    if (action === 'plugin:web-app:create') {
      const { boardId, createWindow, windows = [] } = context;
      
      if (!boardId || !createWindow) {
        console.error('[Web应用插件] 缺少必要的上下文');
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
        ...WebAppPlugin.getDefaultWindowConfig(),
        title: generateUniqueTitle('Web应用'),
        position: {
          x: Math.round(100 + Math.random() * 200),
          y: Math.round(100 + Math.random() * 200)
        }
      };
      
      await createWindow(config);
    }
  },
  
  // 生命周期钩子
  onEnable: (context) => {
    console.log('[Web应用插件] 已启用');
  },
  
  onDisable: (context) => {
    console.log('[Web应用插件] 已禁用');
  }
};

export default WebAppPlugin;


