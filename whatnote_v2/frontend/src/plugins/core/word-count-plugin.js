/**
 * 字数统计插件
 * 在文本窗口工具栏添加字数统计按钮
 */

import React, { useState, useMemo } from 'react';

const wordCountPlugin = {
  id: 'word-count',
  name: '字数统计',
  description: '显示文本的字数、字符数等信息',
  version: '1.0.0',
  author: 'WhatNote Team',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  enabledByDefault: true,

  /**
   * 渲染工具栏按钮
   * @param {Object} props - 包含 windowId, content, onContentChange 等
   * @returns {React.Component} 返回一个 React 组件
   */
  renderToolbarButton: (props) => {
    // 返回一个组件函数，而不是直接调用 Hooks
    return function WordCountButton() {
      const { content = '' } = props;
      const [showStats, setShowStats] = useState(false);

      // 计算统计信息
      const stats = useMemo(() => {
        const text = content || '';
        const chars = text.length;
        const charsNoSpaces = text.replace(/\s/g, '').length;
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        const lines = text.split('\n').length;
        const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim()).length;

        return {
          chars,
          charsNoSpaces,
          words,
          lines,
          paragraphs
        };
      }, [content]);

      const handleClick = () => {
        setShowStats(!showStats);
      };

      return (
        <div key="word-count-plugin" style={{ position: 'relative' }}>
          <button
            onClick={handleClick}
            title="字数统计"
            style={{
              padding: '1px 8px',
              fontSize: '11px',
              backgroundColor: showStats ? '#a0a0a0' : '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '60px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseDown={(e) => {
              e.target.style.border = '2px inset #c0c0c0';
              e.target.style.backgroundColor = '#a0a0a0';
            }}
            onMouseUp={(e) => {
              e.target.style.border = '2px outset #c0c0c0';
              e.target.style.backgroundColor = showStats ? '#a0a0a0' : '#c0c0c0';
            }}
            onMouseLeave={(e) => {
              e.target.style.border = '2px outset #c0c0c0';
              e.target.style.backgroundColor = showStats ? '#a0a0a0' : '#c0c0c0';
            }}
          >
            📊 统计
          </button>

          {showStats && (
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: '24px',
                minWidth: '200px',
                backgroundColor: '#c0c0c0',
                border: '2px outset #c0c0c0',
                boxShadow: '2px 2px 4px rgba(0,0,0,0.3)',
                zIndex: 1000,
                padding: '8px',
                fontFamily: 'MS Sans Serif, sans-serif',
                fontSize: '11px'
              }}
            >
              <div style={{ fontWeight: 'bold', marginBottom: '6px', borderBottom: '1px solid #808080', paddingBottom: '4px' }}>
                字数统计
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>字符数（含空格）：</span>
                  <strong>{stats.chars}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>字符数（不含空格）：</span>
                  <strong>{stats.charsNoSpaces}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>字数：</span>
                  <strong>{stats.words}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>行数：</span>
                  <strong>{stats.lines}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>段落数：</span>
                  <strong>{stats.paragraphs}</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    };
  },

  onEnable: (context) => {
    console.log('[字数统计插件] 已启用');
  },

  onDisable: (context) => {
    console.log('[字数统计插件] 已禁用');
  }
};

export default wordCountPlugin;

