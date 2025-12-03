/**
 * 插件管理器组件
 * 提供插件列表、启用/禁用控制等功能
 */

import React, { useState, useEffect } from 'react';
import { pluginRegistry } from './registry';

const PluginManager = ({ onClose }) => {
  const [plugins, setPlugins] = useState([]);
  const [filter, setFilter] = useState('all'); // 'all', 'enabled', 'disabled'

  useEffect(() => {
    // 加载所有插件
    const allPlugins = pluginRegistry.getAll();
    setPlugins(allPlugins);
  }, []);

  const togglePlugin = (pluginId, enabled) => {
    if (enabled) {
      pluginRegistry.enable(pluginId);
    } else {
      pluginRegistry.disable(pluginId);
    }
    // 更新列表
    setPlugins([...pluginRegistry.getAll()]);
  };

  const filteredPlugins = plugins.filter(plugin => {
    if (filter === 'all') return true;
    if (filter === 'enabled') return pluginRegistry.isEnabled(plugin.id);
    if (filter === 'disabled') return !pluginRegistry.isEnabled(plugin.id);
    return true;
  });

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#c0c0c0',
        fontFamily: 'MS Sans Serif, sans-serif',
        fontSize: '11px',
        display: 'flex',
        flexDirection: 'column',
        padding: '8px'
      }}
    >
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
          borderBottom: '2px solid #808080',
          paddingBottom: '4px'
        }}
      >
        <div style={{ fontWeight: 'bold', fontSize: '12px', display: 'flex', alignItems: 'center' }}>
          <span className="win98-icon win98-icon-plugin" style={{marginRight: '6px'}}></span>
          插件管理器
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: '1px 6px',
              fontSize: '10px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif'
            }}
            onMouseDown={(e) => {
              e.target.style.border = '2px inset #c0c0c0';
            }}
            onMouseUp={(e) => {
              e.target.style.border = '2px outset #c0c0c0';
            }}
          >
            ✕
          </button>
        )}
      </div>

      {/* 筛选器 */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          marginBottom: '8px'
        }}
      >
        <button
          onClick={() => setFilter('all')}
          style={{
            padding: '2px 8px',
            fontSize: '10px',
            backgroundColor: filter === 'all' ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}
        >
          全部 ({plugins.length})
        </button>
        <button
          onClick={() => setFilter('enabled')}
          style={{
            padding: '2px 8px',
            fontSize: '10px',
            backgroundColor: filter === 'enabled' ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}
        >
          已启用 ({plugins.filter(p => pluginRegistry.isEnabled(p.id)).length})
        </button>
        <button
          onClick={() => setFilter('disabled')}
          style={{
            padding: '2px 8px',
            fontSize: '10px',
            backgroundColor: filter === 'disabled' ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}
        >
          已禁用 ({plugins.filter(p => !pluginRegistry.isEnabled(p.id)).length})
        </button>
      </div>

      {/* 插件列表 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          border: '2px inset #c0c0c0',
          backgroundColor: '#ffffff',
          padding: '4px'
        }}
      >
        {filteredPlugins.length === 0 ? (
          <div
            style={{
              padding: '20px',
              textAlign: 'center',
              color: '#808080'
            }}
          >
            没有找到插件
          </div>
        ) : (
          filteredPlugins.map(plugin => {
            const isEnabled = pluginRegistry.isEnabled(plugin.id);
            return (
              <div
                key={plugin.id}
                style={{
                  border: '1px solid #c0c0c0',
                  marginBottom: '6px',
                  padding: '8px',
                  backgroundColor: isEnabled ? '#f0f0f0' : '#e8e8e8',
                  opacity: isEnabled ? 1 : 0.7
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '4px'
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontWeight: 'bold',
                        fontSize: '12px',
                        marginBottom: '2px'
                      }}
                    >
                      {plugin.name}
                    </div>
                    <div
                      style={{
                        fontSize: '10px',
                        color: '#666',
                        marginBottom: '4px'
                      }}
                    >
                      {plugin.description}
                    </div>
                    <div
                      style={{
                        fontSize: '9px',
                        color: '#999',
                        display: 'flex',
                        gap: '8px'
                      }}
                    >
                      <span>版本: {plugin.version}</span>
                      {plugin.author && <span>作者: {plugin.author}</span>}
                      <span>类型: {plugin.type === 'toolbar-feature' ? '工具栏功能' : plugin.type === 'window-type' ? '窗口类型' : plugin.type}</span>
                    </div>
                  </div>
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      cursor: 'pointer',
                      marginLeft: '12px'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={(e) => togglePlugin(plugin.id, e.target.checked)}
                      style={{
                        width: '16px',
                        height: '16px',
                        cursor: 'pointer'
                      }}
                    />
                    <span
                      style={{
                        marginLeft: '4px',
                        fontSize: '10px',
                        color: isEnabled ? '#008000' : '#808080'
                      }}
                    >
                      {isEnabled ? '启用' : '禁用'}
                    </span>
                  </label>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 底部信息 */}
      <div
        style={{
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #808080',
          fontSize: '9px',
          color: '#666',
          textAlign: 'center'
        }}
      >
        共 {plugins.length} 个插件，{plugins.filter(p => pluginRegistry.isEnabled(p.id)).length} 个已启用
      </div>
    </div>
  );
};

export default PluginManager;




