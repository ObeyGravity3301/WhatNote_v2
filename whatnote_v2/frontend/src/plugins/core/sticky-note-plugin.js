/**
 * 便签窗口插件
 * 添加一个简单的便签窗口类型
 */

import React, { useState, useEffect } from 'react';

// 便签窗口组件
const StickyNoteWindow = ({ window: windowData, onContentChange, boardId }) => {
  const [content, setContent] = useState(windowData.content || '');

  useEffect(() => {
    setContent(windowData.content || '');
  }, [windowData.content]);

  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setContent(newContent);
    if (onContentChange) {
      onContentChange(newContent);
    }
  };

  // 随机颜色（便签风格）
  const colors = [
    { bg: '#ffffcc', border: '#ffcc00' }, // 黄色
    { bg: '#ccffcc', border: '#00cc00' }, // 绿色
    { bg: '#ccccff', border: '#0000cc' }, // 蓝色
    { bg: '#ffccff', border: '#cc00cc' }, // 粉色
  ];
  
  // 根据窗口ID选择颜色（确保同一窗口颜色一致）
  const colorIndex = (windowData.id.charCodeAt(0) || 0) % colors.length;
  const color = colors[colorIndex];

  return (
    <div
      style={{
        height: '100%',
        width: '100%',
        backgroundColor: color.bg,
        border: `3px solid ${color.border}`,
        padding: '16px',
        boxShadow: '2px 2px 8px rgba(0,0,0,0.2)',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <div
        style={{
          fontSize: '12px',
          fontFamily: 'MS Sans Serif, sans-serif',
          color: '#666',
          marginBottom: '8px',
          borderBottom: `1px solid ${color.border}`,
          paddingBottom: '4px'
        }}
      >
        📝 便签
      </div>
      <textarea
        value={content}
        onChange={handleContentChange}
        placeholder="在这里输入你的便签内容..."
        style={{
          flex: 1,
          width: '100%',
          border: 'none',
          outline: 'none',
          backgroundColor: 'transparent',
          fontFamily: 'MS Sans Serif, sans-serif',
          fontSize: '13px',
          resize: 'none',
          color: '#333'
        }}
      />
      <div
        style={{
          fontSize: '10px',
          color: '#999',
          marginTop: '8px',
          textAlign: 'right'
        }}
      >
        {content.length} 字符
      </div>
    </div>
  );
};

const stickyNotePlugin = {
  id: 'sticky-note',
  name: '便签窗口',
  description: '添加一个简单的便签窗口类型，用于快速记录',
  version: '1.0.0',
  author: 'WhatNote Team',
  type: 'window-type',
  windowType: 'sticky-note',
  enabledByDefault: true,

  /**
   * 渲染窗口内容
   * @param {Object} props - 包含 window, onContentChange, boardId 等
   */
  renderWindow: (props) => {
    return <StickyNoteWindow {...props} />;
  },

  /**
   * 创建新窗口时的默认配置
   */
  getDefaultWindowConfig: () => {
    return {
      type: 'sticky-note',
      title: '新便签',
      content: '',
      size: { width: 300, height: 250 }
    };
  },

  /**
   * 获取窗口图标（用于桌面图标）
   */
  getWindowIcon: () => {
    return '📝';
  },

  /**
   * 右键菜单项配置
   */
  contextMenuItems: [
    {
      label: '新建便签',
      action: 'plugin:sticky-note:create',
      icon: '📝',
      menuType: 'desktop', // 'desktop', 'icon', 或 'both'
      order: 1 // 排序，数字越小越靠前
    }
  ],

  /**
   * 处理右键菜单项点击
   * @param {string} action - 菜单项 action
   * @param {Object} context - 上下文对象，包含 boardId, createWindow, windows 等
   */
  handleContextMenuAction: async (action, context) => {
    if (action === 'plugin:sticky-note:create') {
      const { boardId, createWindow, windows = [] } = context;
      
      if (!boardId) {
        console.error('[便签插件] boardId 未提供');
        return;
      }

      if (!createWindow) {
        console.error('[便签插件] createWindow 函数未提供');
        return;
      }

      // 使用插件的默认配置创建窗口
      const defaultConfig = stickyNotePlugin.getDefaultWindowConfig();
      
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

      const windowData = {
        ...defaultConfig,
        title: generateUniqueTitle('新便签'),
        position: {
          x: Math.round(100 + Math.random() * 200),
          y: Math.round(100 + Math.random() * 200)
        }
      };

      console.log('[便签插件] 创建便签窗口:', windowData);
      
      // 调用创建窗口函数
      await createWindow(windowData);
    }
  },

  onEnable: (context) => {
    console.log('[便签窗口插件] 已启用');
  },

  onDisable: (context) => {
    console.log('[便签窗口插件] 已禁用');
  }
};

export default stickyNotePlugin;

