import React, { useState, useEffect } from 'react';
import ShortcutManager from '../../utils/ShortcutManager';

const ShortcutSettingsWindow = () => {
  const [actions, setActions] = useState([]);
  const [recordingId, setRecordingId] = useState(null);

  const loadActions = () => {
    setActions(ShortcutManager.getAllActions());
  };

  useEffect(() => {
    loadActions();
    const unsubscribe = ShortcutManager.subscribe(loadActions);
    return unsubscribe;
  }, []);

  const handleRecord = (id) => {
    setRecordingId(id);
  };

  const handleKeyDown = (e) => {
    if (recordingId) {
      e.preventDefault();
      e.stopPropagation();
      
      const keyString = ShortcutManager.getEventKeyString(e);
      if (keyString) {
        if (keyString === 'Escape') {
          setRecordingId(null);
          return;
        }
        if (keyString === 'Backspace' || keyString === 'Delete') {
            ShortcutManager.reset(recordingId);
            setRecordingId(null);
            return;
        }
        
        ShortcutManager.set(recordingId, keyString);
        setRecordingId(null);
      }
    }
  };

  useEffect(() => {
    if (recordingId) {
      window.addEventListener('keydown', handleKeyDown, true); // Capture phase
    } else {
      window.removeEventListener('keydown', handleKeyDown, true);
    }
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [recordingId]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#dcdcdc', padding: '8px' }}>
      <div style={{ 
        flex: 1, 
        backgroundColor: '#fff', 
        border: '2px inset #fff', 
        overflowY: 'auto',
        padding: '8px' 
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #999' }}>
              <th style={{ textAlign: 'left', padding: '4px' }}>功能</th>
              <th style={{ textAlign: 'left', padding: '4px' }}>当前快捷键</th>
              <th style={{ textAlign: 'left', padding: '4px' }}>分类</th>
              <th style={{ width: '60px' }}></th>
            </tr>
          </thead>
          <tbody>
            {actions.map(action => (
              <tr key={action.id} style={{ borderBottom: '1px dotted #ccc' }}>
                <td style={{ padding: '6px 4px' }}>
                  <div style={{ fontWeight: 'bold' }}>{action.label}</div>
                  <div style={{ fontSize: '10px', color: '#666' }}>{action.description}</div>
                </td>
                <td style={{ padding: '6px 4px' }}>
                  {recordingId === action.id ? (
                    <span style={{ backgroundColor: '#000080', color: '#fff', padding: '2px 4px' }}>
                      请按键... (Esc取消)
                    </span>
                  ) : (
                    <kbd style={{ 
                      backgroundColor: '#f0f0f0', 
                      border: '1px solid #999', 
                      borderRadius: '3px', 
                      padding: '2px 6px',
                      fontFamily: 'monospace'
                    }}>
                      {action.currentKey || '未设置'}
                    </kbd>
                  )}
                </td>
                <td style={{ padding: '6px 4px', color: '#666' }}>{action.category}</td>
                <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                  <button 
                    onClick={() => handleRecord(action.id)}
                    disabled={!!recordingId}
                    style={{ fontSize: '10px', cursor: 'pointer', marginRight: '4px' }}
                  >
                    修改
                  </button>
                  <button 
                    onClick={() => ShortcutManager.reset(action.id)}
                    disabled={!!recordingId || !action.currentKey}
                    title="清除快捷键"
                    style={{ 
                      fontSize: '10px', 
                      cursor: 'pointer', 
                      color: 'red',
                      fontWeight: 'bold',
                      padding: '0 4px'
                    }}
                  >
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: '8px', fontSize: '11px', color: '#666' }}>
        * 点击“修改”后按下新快捷键。按 Backspace 或 Delete 可清除。
      </div>
    </div>
  );
};

export const shortcutSettingsPlugin = {
  id: 'shortcut-settings',
  name: '快捷键设置',
  version: '1.0.0',
  type: 'window-type',
  description: '自定义全局快捷键',
  
  // Window Renderer
  renderWindow: (props) => <ShortcutSettingsWindow {...props} />,
  
  // Default Window Config
  defaultConfig: {
    title: '快捷键设置',
    width: 500,
    height: 400,
    resizable: true,
    minimizable: true
  },
  
  // Explicitly define windowType to match the type used in createWindow
  windowType: 'shortcut-settings',
  
  icon: '⌨️',

  contextMenuItems: [
    {
      label: '快捷键设置...',
      action: 'plugin:shortcut-settings:open',
      icon: '⌨️',
      menuType: 'desktop',
      order: 99
    }
  ],

  handleContextMenuAction: async (action, context) => {
    console.log('[ShortcutSettings] handleContextMenuAction called:', action);
    if (action === 'plugin:shortcut-settings:open') {
      const { createWindow, windows = [], focusWindow, restoreWindow, minimizedWindows, hiddenWindows, showWindow } = context;
      
      console.log('[ShortcutSettings] Context windows:', windows.map(w => w.id));
      const existing = windows.find(w => w.type === 'shortcut-settings');
      if (existing) {
         console.log('[ShortcutSettings] Found existing window:', existing.id);
         
         // 1. If hidden, show it first
         if (hiddenWindows && hiddenWindows.has(existing.id) && showWindow) {
             console.log('[ShortcutSettings] Showing hidden window');
             showWindow(existing.id);
         }

         // 2. If minimized, restore it
         if (minimizedWindows && minimizedWindows.has(existing.id) && restoreWindow) {
             console.log('[ShortcutSettings] Restoring minimized window');
             restoreWindow(existing.id);
         }

         // 3. Focus it
         if (focusWindow) {
             console.log('[ShortcutSettings] Focusing window');
             focusWindow(existing.id);
         }
         
         return; 
      }
      
      console.log('[ShortcutSettings] Creating new window...');
      await createWindow({
        id: 'shortcut-settings-window',
        type: 'shortcut-settings',
        title: '快捷键设置',
        content: '',
        position: { x: 300, y: 200 },
        size: { width: 500, height: 400 },
        z_index: 9999
      });
    }
  }
};

export default shortcutSettingsPlugin;

