import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import './ChatWindow.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

// LaTeX 分隔符标准化函数
const normalizeLatexDelimiters = (text) => {
  return text
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$');
};

// 优化的消息组件 - 使用React.memo减少重渲染
const MessageComponent = React.memo(({ message, isStreaming, streamingMessageId, onOpenWindow, getFileIcon }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  
  // 使用useMemo缓存Markdown组件配置
  const markdownComponents = useMemo(() => ({
    p: ({ children }) => <p style={{ margin: '4px 0', fontSize: '11px', lineHeight: '1.4' }}>{children}</p>,
    h1: ({ children }) => <h1 style={{ fontSize: '14px', fontWeight: 'bold', margin: '8px 0 4px 0' }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ fontSize: '13px', fontWeight: 'bold', margin: '6px 0 3px 0' }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ fontSize: '12px', fontWeight: 'bold', margin: '4px 0 2px 0' }}>{children}</h3>,
    strong: ({ children }) => <strong style={{ fontWeight: 'bold' }}>{children}</strong>,
    em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
    code: ({ children, className }) => {
      const isCodeBlock = className && className.includes('language-');
      return <code style={{ 
        fontSize: '10px',
        fontFamily: 'Courier New, monospace',
        backgroundColor: isCodeBlock ? 'transparent' : '#f0f0f0',
        padding: isCodeBlock ? '0' : '1px 2px'
      }}>{children}</code>;
    },
    pre: ({ children }) => (
      <pre style={{ 
        backgroundColor: '#f0f0f0', 
        padding: '8px', 
        fontSize: '10px',
        fontFamily: 'Courier New, monospace',
        border: '1px solid #ccc',
        overflow: 'auto',
        margin: '4px 0',
        borderRadius: '0px'
      }}>{children}</pre>
    ),
    ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ol>,
    li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
    blockquote: ({ children }) => <blockquote style={{ 
      borderLeft: '3px solid #ccc', 
      margin: '4px 0', 
      paddingLeft: '8px',
      fontStyle: 'italic'
    }}>{children}</blockquote>
  }), []);

  // 文件渲染组件
  const FileComponent = useMemo(() => ({ file, fileIndex }) => {
    if (file.type === 'images') {
      return (
        <div key={fileIndex} style={{ margin: '8px 0' }}>
          <img 
            src={file.url} 
            alt={file.name}
            style={{ 
              maxWidth: '200px',
              maxHeight: '150px',
              width: 'auto',
              height: 'auto',
              objectFit: 'contain',
              border: '1px solid #ccc',
              borderRadius: '2px',
              cursor: 'pointer',
              display: 'block'
            }}
            onClick={() => {
              if (onOpenWindow) {
                onOpenWindow(file.name);
      } else {
                window.open(file.url, '_blank');
              }
            }}
            title={`${file.name} - 点击打开桌面窗口`}
          />
          <div style={{ 
            fontSize: '9px', 
            color: '#666', 
            marginTop: '2px',
            textAlign: 'center'
          }}>
            {file.name} ({(file.size / 1024).toFixed(1)}KB)
          </div>
        </div>
      );
    }
    
    return (
      <div key={fileIndex} style={{
        border: '1px solid #ccc',
        borderRadius: '4px',
        padding: '8px',
        margin: '4px 0',
        backgroundColor: '#f0f8ff',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <div style={{ fontSize: '16px' }}>{getFileIcon(file.type)}</div>
        <div style={{ flex: 1, fontSize: '10px' }}>
          <div style={{ fontWeight: 'bold' }}>{file.name}</div>
          <div style={{ color: '#666', marginTop: '2px' }}>
            {file.type} • {(file.size / 1024).toFixed(1)}KB
          </div>
        </div>
        <button
          onClick={() => window.open(file.url, '_blank')}
          style={{
            backgroundColor: '#c0c0c0',
            border: '1px outset #c0c0c0',
            cursor: 'pointer',
            fontSize: '10px',
            padding: '2px 6px',
            borderRadius: '2px'
          }}
          title="打开文件"
        >
          📂
        </button>
      </div>
    );
  }, [onOpenWindow, getFileIcon]);

  // 系统消息渲染
  if (isSystem) {
    const metadata = message.metadata || {};
    const isAnnotationAction = metadata.type === 'annotation_action';
    const isOutlineAction = metadata.type === 'batch_outline_generated';
    const isSectionAnnotationAction = metadata.type === 'batch_section_annotation_generated';
    const isClickable = isAnnotationAction || isOutlineAction || isSectionAnnotationAction;
    const hasThumbnail = metadata.thumbnail_path && metadata.action === 'generate_visual_annotation';
    
    // 获取左边框颜色
    const getBorderColor = () => {
      if (isOutlineAction) return '#4169e1'; // 蓝色 - 大纲
      if (isSectionAnnotationAction) return '#ff8c00'; // 橙色 - 分段注释
      return '#ffd700'; // 金色 - 默认/单页注释
    };
    
    // 点击系统通知的处理
    const handleNotificationClick = () => {
      if (isAnnotationAction && metadata.window_id && metadata.page) {
        // 单页注释：跳转到对应页面
        console.log('📖 点击系统通知，打开PDF页面:', {
          windowId: metadata.window_id,
          page: metadata.page,
          filename: metadata.pdf_filename
        });
        
        const event = new CustomEvent('openPDFPage', {
          detail: {
            windowId: metadata.window_id,
            page: metadata.page,
            filename: metadata.pdf_filename
          }
        });
        if (typeof window !== 'undefined') {
          window.dispatchEvent(event);
        }
      } else if (isOutlineAction && metadata.window_id) {
        // 大纲生成：打开大纲侧栏
        console.log('📚 点击大纲通知，打开大纲侧栏:', {
          windowId: metadata.window_id,
          filename: metadata.pdf_filename
        });
        
        const event = new CustomEvent('openPDFOutline', {
          detail: {
            windowId: metadata.window_id,
            filename: metadata.pdf_filename
          }
        });
        if (typeof window !== 'undefined') {
          window.dispatchEvent(event);
        }
      } else if (isSectionAnnotationAction && metadata.window_id && metadata.page_range) {
        // 分段注释：跳转到该分段的起始页
        const startPage = metadata.page_range[0];
        console.log('⚡ 点击分段注释通知，打开PDF页面:', {
          windowId: metadata.window_id,
          page: startPage,
          filename: metadata.pdf_filename
        });
        
        const event = new CustomEvent('openPDFPage', {
          detail: {
            windowId: metadata.window_id,
            page: startPage,
            filename: metadata.pdf_filename
          }
        });
        if (typeof window !== 'undefined') {
          window.dispatchEvent(event);
        }
      }
    };
    
    return (
      <div 
        style={{
          margin: '8px 0',
          padding: '6px 10px',
          backgroundColor: '#fffacd',
          border: '1px solid #f0e68c',
          borderLeft: `3px solid ${getBorderColor()}`,
          fontSize: '10px',
          fontFamily: 'MS Sans Serif, sans-serif',
          color: '#666',
          borderRadius: '2px',
          cursor: isClickable ? 'pointer' : 'default',
          transition: 'all 0.2s'
        }}
        onClick={handleNotificationClick}
        onMouseEnter={(e) => {
          if (isClickable) {
            e.currentTarget.style.backgroundColor = '#fff8dc';
            e.currentTarget.style.borderLeftColor = '#ffa500';
          }
        }}
        onMouseLeave={(e) => {
          if (isClickable) {
            e.currentTarget.style.backgroundColor = '#fffacd';
            e.currentTarget.style.borderLeftColor = getBorderColor();
          }
        }}
        title={
          isAnnotationAction ? `点击打开PDF《${metadata.pdf_filename}》第${metadata.page}页` :
          isOutlineAction ? `点击打开PDF《${metadata.pdf_filename}》的大纲` :
          isSectionAnnotationAction ? `点击打开PDF《${metadata.pdf_filename}》第${metadata.section_title}分段` :
          ''
        }
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
          <span style={{ fontSize: '12px', marginTop: '2px' }}>ℹ️</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 'bold', marginBottom: '2px' }}>
              {message.content}
              {isClickable && (
                <span style={{ 
                  marginLeft: '6px', 
                  fontSize: '9px', 
                  color: '#0078d4',
                  fontWeight: 'normal'
                }}>
                  (点击打开)
                </span>
              )}
            </div>
            
            {/* 单页注释详情 */}
            {isAnnotationAction && (
              <>
                <div style={{ fontSize: '9px', color: '#888', marginTop: '4px' }}>
                  📄 文件: {metadata.pdf_filename} | 📖 页码: 第{metadata.page}页 | ⏰ {new Date(message.timestamp).toLocaleString('zh-CN')}
                </div>
                {hasThumbnail && (
                  <div style={{ marginTop: '6px' }}>
                    <img 
                      src={`http://localhost:8081/api/media/serve?path=${encodeURIComponent(metadata.thumbnail_path)}`}
                      alt={`第${metadata.page}页缩略图`}
                      style={{
                        maxWidth: '150px',
                        maxHeight: '150px',
                        border: '1px solid #ccc',
                        borderRadius: '2px',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                      }}
                      title={`PDF第${metadata.page}页渲染图像`}
                    />
                  </div>
                )}
              </>
            )}
            
            {/* 大纲生成详情 */}
            {isOutlineAction && (
              <div style={{ fontSize: '9px', color: '#888', marginTop: '4px' }}>
                📄 文件: {metadata.pdf_filename} | 📊 分段数: {metadata.total_sections} | ⏰ {new Date(message.timestamp).toLocaleString('zh-CN')}
                {metadata.sections_summary && metadata.sections_summary.length > 0 && (
                  <div style={{ marginTop: '6px', maxHeight: '100px', overflowY: 'auto' }}>
                    {metadata.sections_summary.slice(0, 5).map((section, idx) => (
                      <div key={idx} style={{ fontSize: '9px', color: '#666', padding: '2px 0' }}>
                        {section.index}. {section.title} (p.{section.pages[0]}-{section.pages[1]})
                      </div>
                    ))}
                    {metadata.sections_summary.length > 5 && (
                      <div style={{ fontSize: '9px', color: '#999', fontStyle: 'italic' }}>
                        ... 还有 {metadata.sections_summary.length - 5} 个分段
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* 分段注释详情 */}
            {isSectionAnnotationAction && (
              <div style={{ fontSize: '9px', color: '#888', marginTop: '4px' }}>
                📄 文件: {metadata.pdf_filename} | 📑 分段: 第{metadata.section_number}节 | 📖 页码: {metadata.page_range[0]}-{metadata.page_range[1]} | 📝 注释数: {metadata.annotation_count} | ⏰ {new Date(message.timestamp).toLocaleString('zh-CN')}
                {metadata.section_summary && (
                  <div style={{ 
                    marginTop: '4px', 
                    padding: '4px', 
                    backgroundColor: '#f8f8f8', 
                    borderRadius: '2px',
                    fontSize: '9px',
                    color: '#555',
                    maxHeight: '60px',
                    overflowY: 'auto'
                  }}>
                    <strong>分段简介：</strong>{metadata.section_summary.substring(0, 100)}{metadata.section_summary.length > 100 ? '...' : ''}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
  
  if (isUser) {
    return (
      <div className="message user-message">
        <div className="message-avatar">👤</div>
        <div className="message-bubble user-bubble">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={markdownComponents}
          >
            {normalizeLatexDelimiters(message.content)}
          </ReactMarkdown>
          
          {message.files && message.files.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              {message.files.map((file, fileIndex) => (
                <FileComponent key={fileIndex} file={file} fileIndex={fileIndex} />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="ai-message-block">
      <div className="message-header">
        <div className="message-avatar">🤖</div>
        <div className="message-sender">Amadeus</div>
      </div>
      <div className="message-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={markdownComponents}
        >
          {normalizeLatexDelimiters(message.content)}
        </ReactMarkdown>
        
        {isStreaming && message.id === streamingMessageId && (
          <span style={{
            display: 'inline-block',
            marginLeft: '4px',
            color: '#666',
            fontSize: '12px',
            animation: 'blink 1s infinite'
          }}>
            ▊
          </span>
        )}
      </div>
    </div>
  );
});

// 优化的工具栏组件
const Toolbar = React.memo(({ 
  showSettings, 
  setShowSettings, 
  showFileSelector, 
  setShowFileSelector,
  loadBoardFiles,
  scrollToBottom,
  apiProvider,
  setApiProvider,
  apiConfigs,
  setApiConfigs,
  saveApiConfig,
  getModelOptions,
  getProviderName
}) => {
  return (
      <div style={{
        backgroundColor: '#c0c0c0',
        borderBottom: '2px outset #c0c0c0',
        padding: '2px 4px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        height: '24px',
        flexShrink: 0
      }}>
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="LLM API 设置"
        >
          ⚙️ 设置
        </button>
        
        <button
          onClick={() => {
            if (!showFileSelector) {
              loadBoardFiles();
            }
            setShowFileSelector(!showFileSelector);
          }}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="选择文件发送"
        >
          📎 文件
        </button>
      
      <button
        onClick={() => scrollToBottom(true)}
        style={{
          padding: '1px 8px',
          fontSize: '11px',
          backgroundColor: '#c0c0c0',
          border: '2px outset #c0c0c0',
          borderRadius: '0px',
          cursor: 'pointer',
          fontFamily: 'MS Sans Serif, sans-serif',
          height: '20px',
          minWidth: '50px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
        title="滚动到最底部"
      >
        ⬇️ 底部
      </button>
        
        {showSettings && (
          <div className="settings-panel" style={{
            position: 'absolute',
          top: '45px',
            left: '4px',
            width: '320px',
            backgroundColor: '#c0c0c0',
            border: '2px outset #c0c0c0',
            padding: '8px',
            fontSize: '11px',
            fontFamily: 'MS Sans Serif, sans-serif',
            zIndex: 1000,
            boxShadow: '2px 2px 4px rgba(0,0,0,0.3)'
          }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', borderBottom: '1px solid #808080', paddingBottom: '4px' }}>
              LLM API 设置
            </div>
            
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                API 服务商:
              </label>
              <select
                value={apiProvider}
                onChange={(e) => {
                  setApiProvider(e.target.value);
                  saveApiConfig(e.target.value, apiConfigs);
                }}
                style={{
                  width: '100%',
                  padding: '2px',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  border: '1px inset #c0c0c0',
                  backgroundColor: '#ffffff'
                }}
              >
                <option value="openai">OpenAI (GPT-4, GPT-3.5)</option>
                <option value="anthropic">Anthropic (Claude-3.5)</option>
                <option value="gemini">Google (Gemini Pro)</option>
                <option value="qwen">阿里云 (通义千问)</option>
              </select>
            </div>
            
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                API 密钥:
              </label>
              <input
                type="password"
                value={apiConfigs[apiProvider]?.apiKey || ''}
                onChange={(e) => {
                  const newConfigs = {
                    ...apiConfigs,
                    [apiProvider]: {
                      ...apiConfigs[apiProvider],
                      apiKey: e.target.value
                    }
                  };
                  setApiConfigs(newConfigs);
                  
                  if (e.target.value && e.target.value !== '***已配置***') {
                    saveApiConfig(apiProvider, newConfigs);
                  }
                }}
                onFocus={(e) => {
                  if (e.target.value === '***已配置***') {
                    const newConfigs = {
                      ...apiConfigs,
                      [apiProvider]: {
                        ...apiConfigs[apiProvider],
                        apiKey: ''
                      }
                    };
                    setApiConfigs(newConfigs);
                  }
                }}
                placeholder="请输入API密钥"
                style={{
                  width: '100%',
                  padding: '2px 4px',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  border: '1px inset #c0c0c0',
                  backgroundColor: '#ffffff',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                模型:
              </label>
              <select
                value={apiConfigs[apiProvider]?.model || ''}
                onChange={(e) => {
                  const newConfigs = {
                    ...apiConfigs,
                    [apiProvider]: {
                      ...apiConfigs[apiProvider],
                      model: e.target.value
                    }
                  };
                  setApiConfigs(newConfigs);
                  saveApiConfig(apiProvider, newConfigs);
                }}
                style={{
                  width: '100%',
                  padding: '2px',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  border: '1px inset #c0c0c0',
                  backgroundColor: '#ffffff'
                }}
              >
                {getModelOptions(apiProvider).map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                API 端点:
              </label>
              <input
                type="text"
                value={apiConfigs[apiProvider]?.baseUrl || ''}
                onChange={(e) => {
                  const newConfigs = {
                    ...apiConfigs,
                    [apiProvider]: {
                      ...apiConfigs[apiProvider],
                      baseUrl: e.target.value
                    }
                  };
                  setApiConfigs(newConfigs);
                  saveApiConfig(apiProvider, newConfigs);
                }}
                style={{
                  width: '100%',
                  padding: '2px 4px',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  border: '1px inset #c0c0c0',
                  backgroundColor: '#ffffff',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            
            <div style={{ 
              marginTop: '8px', 
              padding: '4px', 
              backgroundColor: apiConfigs[apiProvider]?.apiKey ? '#e6f3ff' : '#fff3e6',
              border: '1px solid #ccc',
              fontSize: '10px'
            }}>
              状态: {apiConfigs[apiProvider]?.apiKey ? 
                `✅ ${getProviderName(apiProvider)} 已配置` : 
                `⚠️ 请配置 ${getProviderName(apiProvider)} API密钥`
              }
            </div>
          </div>
        )}
      </div>
  );
});

// 优化的文件选择器组件
const FileSelector = React.memo(({ 
  showFileSelector, 
  setShowFileSelector, 
  boardFiles, 
  selectedFiles, 
  setSelectedFiles, 
  getFileIcon 
}) => {
  if (!showFileSelector) return null;

  return (
          <div style={{
            backgroundColor: '#f0f0f0',
            border: '1px inset #c0c0c0',
            maxHeight: '200px',
            margin: '4px 8px',
            fontSize: '11px',
      fontFamily: 'MS Sans Serif, sans-serif',
      position: 'relative'
          }}>
            <div style={{ 
              fontWeight: 'bold', 
        padding: '8px 8px 4px 8px',
              display: 'flex',
              justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#f0f0f0',
        borderBottom: '1px solid #c0c0c0',
        position: 'sticky',
        top: '0',
        zIndex: 10
            }}>
              <span>选择要发送的文件 ({boardFiles.length}个文件)</span>
              <div style={{ fontSize: '8px', color: '#666', marginTop: '2px' }}>
                调试: boardFiles.length = {boardFiles.length}
              </div>
              <button
                onClick={() => setShowFileSelector(false)}
                style={{
                  backgroundColor: '#c0c0c0',
                  border: '1px outset #c0c0c0',
                  cursor: 'pointer',
                  fontSize: '10px',
                  padding: '1px 4px'
                }}
              >
                ✕
              </button>
            </div>
            
      <div style={{
        maxHeight: '160px',
        overflowY: 'auto',
        padding: '4px 8px 8px 8px'
      }}>
            {boardFiles.length === 0 ? (
              <div style={{ color: '#808080', textAlign: 'center', padding: '16px' }}>
                展板中暂无文件
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {boardFiles.map((file) => (
                  <div
                    key={file.path}
                    onClick={() => {
                      if (selectedFiles.find(f => f.path === file.path)) {
                        setSelectedFiles(prev => prev.filter(f => f.path !== file.path));
                      } else {
                        setSelectedFiles(prev => [...prev, file]);
                      }
                    }}
                    style={{
                      border: selectedFiles.find(f => f.path === file.path) ? '2px solid #0078d4' : '1px solid #808080',
                      backgroundColor: selectedFiles.find(f => f.path === file.path) ? '#e6f3ff' : '#ffffff',
                      padding: '8px',
                      cursor: 'pointer',
                      borderRadius: '2px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                  minHeight: '40px'
                    }}
                    title={`${file.name} (${(file.size / 1024).toFixed(1)}KB)`}
              >
                    <div style={{ fontSize: '20px', flexShrink: 0 }}>
                      {getFileIcon(file.type)}
                    </div>
                    
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ 
                        fontSize: '11px', 
                        fontWeight: 'bold',
                        color: '#000000',
                        marginBottom: '2px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {file.name}
                      </div>
                      <div style={{ 
                        fontSize: '10px', 
                        color: '#666666',
                        display: 'flex',
                        gap: '8px'
                      }}>
                        <span>{file.type}</span>
                        <span>•</span>
                        <span>{(file.size / 1024).toFixed(1)}KB</span>
                      </div>
                    </div>
                    
                    {selectedFiles.find(f => f.path === file.path) && (
                      <div style={{ 
                        fontSize: '14px', 
                        color: '#0078d4',
                        flexShrink: 0
                      }}>
                        ✓
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {selectedFiles.length > 0 && (
              <div style={{ 
                marginTop: '8px', 
                padding: '4px 8px', 
                backgroundColor: '#e6f3ff',
                border: '1px solid #0078d4',
                borderRadius: '2px'
              }}>
                <strong>已选择 {selectedFiles.length} 个文件:</strong>
                <div style={{ marginTop: '4px' }}>
                  {selectedFiles.map(file => (
                    <span key={file.path} style={{ 
                      display: 'inline-block',
                      backgroundColor: '#0078d4',
                      color: 'white',
                      padding: '2px 6px',
                      margin: '2px',
                      borderRadius: '2px',
                      fontSize: '10px'
                    }}>
                      {getFileIcon(file.type)} {file.name.length > 10 ? file.name.substring(0, 8) + '...' : file.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
      </div>
    </div>
  );
});

function ChatWindow({ 
  boardId, 
  boardName,
  isVisible, 
  onClose, 
  onMinimize,
  onFocus,
  isFocused,
  onOpenWindow
}) {
  // 基础状态 - 最小化状态数量
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  
  // 分页加载状态
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  
  // 简化的消息管理状态
  const [displayedMessages, setDisplayedMessages] = useState([]);
  const [isAtTop, setIsAtTop] = useState(false);
  const [shouldPreserveScrollPosition, setShouldPreserveScrollPosition] = useState(false);
  
  // UI状态
  const [showSettings, setShowSettings] = useState(false);
  const [showFileSelector, setShowFileSelector] = useState(false);
  const [boardFiles, setBoardFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // API配置状态
  const [apiProvider, setApiProvider] = useState('openai');
  const [apiConfigs, setApiConfigs] = useState({
    openai: { apiKey: '', model: 'gpt-4', baseUrl: 'https://api.openai.com/v1' },
    anthropic: { apiKey: '', model: 'claude-3-5-sonnet-20241022', baseUrl: 'https://api.anthropic.com' },
    gemini: { apiKey: '', model: 'gemini-1.5-pro', baseUrl: 'https://generativelanguage.googleapis.com/v1' },
    qwen: { apiKey: '', model: 'qwen-plus', baseUrl: 'https://dashscope.aliyuncs.com/api/v1' }
  });
  
  // 引用 - 最小化引用数量
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);
  const ITEMS_PER_PAGE = 20; // 每页加载20条消息

  // 加载更多历史消息 - 手动触发版本，保持滚动位置
  const loadMoreHistory = useCallback(async () => {
    console.log('🔄 点击加载更多按钮:', { isLoadingHistory, hasMoreHistory, conversationId, currentPage });
    
    if (isLoadingHistory || !hasMoreHistory || !conversationId) {
      console.log('❌ 跳过加载:', { isLoadingHistory, hasMoreHistory, conversationId });
      return;
    }

    // 记录当前滚动位置
    const container = messagesContainerRef.current;
    const currentScrollTop = container ? container.scrollTop : 0;
    const currentScrollHeight = container ? container.scrollHeight : 0;
    
    setIsLoadingHistory(true);
    setShouldPreserveScrollPosition(true); // 标记需要保持滚动位置
    console.log('📥 开始加载历史消息...');
    
    try {
      const url = `http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}?page=${currentPage + 1}&limit=${ITEMS_PER_PAGE}`;
      console.log('📡 请求URL:', url);
      
      const response = await fetch(url);
      console.log('📡 API响应状态:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        const newMessages = data.messages || [];
        console.log('📨 收到新消息:', newMessages.length, '条');
        console.log('📊 数据详情:', data);
        
        if (newMessages.length === 0) {
          console.log('📭 没有更多历史消息');
          setHasMoreHistory(false);
        } else {
          const updatedMessages = [...newMessages, ...messages];
          console.log('📊 更新消息列表:', updatedMessages.length, '条');
          
          // 如果消息总数超过100条，只保留最新的100条以控制内存使用
          if (updatedMessages.length > 100) {
            setMessages(updatedMessages.slice(-100));
          } else {
            setMessages(updatedMessages);
          }
          
          setCurrentPage(prev => prev + 1);
          
          // 计算新的滚动位置以保持用户的视觉位置
          setTimeout(() => {
            if (container && shouldPreserveScrollPosition) {
              const newScrollHeight = container.scrollHeight;
              const heightDifference = newScrollHeight - currentScrollHeight;
              const newScrollTop = currentScrollTop + heightDifference;
              container.scrollTop = newScrollTop;
              console.log('📍 保持滚动位置:', { currentScrollTop, newScrollTop, heightDifference });
            }
          }, 100);
        }
      } else {
        console.error('❌ API请求失败:', response.status);
        const errorText = await response.text();
        console.error('❌ 错误详情:', errorText);
      }
    } catch (error) {
      console.error('❌ 加载历史消息失败:', error);
    } finally {
      setIsLoadingHistory(false);
      setShouldPreserveScrollPosition(false); // 重置标记
      console.log('✅ 加载历史消息完成');
    }
  }, [isLoadingHistory, hasMoreHistory, conversationId, currentPage, boardId, messages, shouldPreserveScrollPosition]);

  // 优化的滚动函数 - 使用useCallback避免重复创建
  const scrollToBottom = useCallback((smooth = false) => {
    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      if (smooth) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      } else {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, []);

  // 智能消息管理函数 - 根据消息数量决定显示策略
  const updateDisplayedMessages = useCallback(() => {
    if (messages.length <= 15) {
      // 如果消息总数不超过15条，显示所有消息
      setDisplayedMessages(messages);
    } else {
      // 如果消息总数超过15条，显示所有消息（让用户可以滚动查看）
      setDisplayedMessages(messages);
    }
  }, [messages]);

  // 滚动事件处理 - 检测是否在顶部
  const handleScroll = useCallback((e) => {
    // 阻止事件冒泡，防止桌面被滚动
    e.stopPropagation();
    
    const container = e.target;
    const scrollTop = container.scrollTop;
    
    // 检测是否接近顶部（50px范围内）
    setIsAtTop(scrollTop < 50);
  }, []);

  // 优化的文件加载函数
  const loadBoardFiles = useCallback(async () => {
    try {
      console.log(`正在加载展板文件: ${boardId}`);
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/files`);
      console.log(`文件API响应状态: ${response.status}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`加载到的文件数量: ${data.files ? data.files.length : 0}`);
        console.log(`文件列表:`, data.files);
        setBoardFiles(data.files || []);
      } else {
        console.error('文件API响应失败:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('加载展板文件失败:', error);
    }
  }, [boardId]);

  // 优化的API配置加载
  const loadApiConfig = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8081/api/llm/config');
      if (response.ok) {
        const config = await response.json();
        setApiProvider(config.current_provider || 'openai');
        
        const frontendConfigs = {};
        Object.entries(config.providers || {}).forEach(([provider, providerConfig]) => {
          frontendConfigs[provider] = {
            apiKey: providerConfig.configured ? '***已配置***' : '',
            model: providerConfig.model || '',
            baseUrl: providerConfig.baseUrl || ''
          };
        });
        setApiConfigs(frontendConfigs);
      }
    } catch (error) {
      console.error('加载API配置失败:', error);
    }
  }, []);

  // 优化的API配置保存
  const saveApiConfig = useCallback(async (provider, configs) => {
    try {
      await fetch(`http://localhost:8081/api/llm/config/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configs[provider])
      });
      
      await fetch(`http://localhost:8081/api/llm/provider/${provider}`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('保存API配置失败:', error);
    }
  }, []);

  // 工具函数 - 使用useCallback缓存
  const getFileIcon = useCallback((fileType) => {
    const icons = {
      'images': '🖼️',
      'videos': '🎬',
      'audios': '🎵',
      'pdfs': '📄',
      'texts': '📝'
    };
    return icons[fileType] || '📄';
  }, []);

  const getProviderName = useCallback((provider) => {
    const names = {
      'openai': 'OpenAI',
      'anthropic': 'Anthropic',
      'gemini': 'Google Gemini',
      'qwen': '阿里云通义千问'
    };
    return names[provider] || provider;
  }, []);

  const getModelOptions = useCallback((provider) => {
    const options = {
      'openai': [
        { value: 'gpt-4o', label: 'GPT-4o (多模态推荐)' },
        { value: 'gpt-4-turbo', label: 'GPT-4 Turbo (多模态)' },
        { value: 'gpt-4-vision-preview', label: 'GPT-4 Vision (多模态)' }
      ],
      'anthropic': [
        { value: 'claude-3-5-sonnet-20241022', label: 'Claude-3.5 Sonnet (多模态推荐)' },
        { value: 'claude-3-opus-20240229', label: 'Claude-3 Opus (多模态最强)' },
        { value: 'claude-3-sonnet-20240229', label: 'Claude-3 Sonnet (多模态)' }
      ],
      'gemini': [
        { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro (多模态推荐)' },
        { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (多模态快速)' },
        { value: 'gemini-pro-vision', label: 'Gemini Pro Vision (多模态)' }
      ],
      'qwen': [
        { value: 'qwen-vl-plus', label: '通义千问-VL-Plus (多模态推荐)' },
        { value: 'qwen-long', label: '通义千问-Long (长文本+多模态)' },
        { value: 'qwen-vl-max', label: '通义千问-VL-Max (多模态最强)' }
      ]
    };
    return options[provider] || [];
  }, []);

  // 输入处理函数
  const handleInputChange = useCallback((e) => {
    const textarea = e.target;
    setInputText(textarea.value);
    
    textarea.style.height = 'auto';
    const scrollHeight = textarea.scrollHeight;
    const lineHeight = 16;
    const padding = 8;
    const maxLines = 6;
    const minHeight = lineHeight + padding;
    const maxHeight = maxLines * lineHeight + padding;
    
    let newHeight = Math.max(minHeight, Math.min(maxHeight, scrollHeight));
    textarea.style.height = `${newHeight}px`;
    
    if (scrollHeight > maxHeight) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
  }, []);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, []);

  // 发送消息函数
  const sendMessage = useCallback(async () => {
    if ((!inputText.trim() && selectedFiles.length === 0) || !conversationId || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputText.trim() || '发送了文件',
      files: selectedFiles.length > 0 ? selectedFiles : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setSelectedFiles([]);
    setIsLoading(true);

    try {
      await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userMessage)
      });

      const aiMessageId = Date.now();
      const aiMessage = {
        id: aiMessageId,
        role: 'assistant',
        content: ''
      };

      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
      setIsStreaming(true);
      setStreamingMessageId(aiMessageId);

      await generateStreamingAIResponse(userMessage, aiMessageId);

    } catch (error) {
      console.error('发送消息失败:', error);
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，发送消息时出现错误，请稍后重试。'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [inputText, selectedFiles, conversationId, isLoading, boardId]);

  // 流式AI回复函数
  const generateStreamingAIResponse = useCallback(async (userMessage, aiMessageId) => {
    try {
      // 包含所有消息（包括system消息），让LLM了解用户的操作历史
      const conversationMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        files: msg.files
      }));
      
      console.log('发送给LLM的消息数:', conversationMessages.length);
      console.log('包含system消息，让LLM了解用户操作');
      
      // 直接使用传入的userMessage对象
      const currentUserMessage = {
        role: userMessage.role,
        content: userMessage.content,
        files: userMessage.files
      };
      
      if (userMessage.files && userMessage.files.length > 0) {
        console.log('当前消息包含文件:', userMessage.files);
      } else {
        console.log('当前消息不包含文件');
      }
      
      conversationMessages.push(currentUserMessage);
      
      // 调试：打印发送给LLM的消息
      console.log('=== 发送给LLM的完整消息 ===');
      console.log('消息总数:', conversationMessages.length);
      conversationMessages.forEach((msg, index) => {
        console.log(`--- 消息 ${index} ---`);
        console.log('角色:', msg.role);
        console.log('内容:', msg.content);
        if (msg.files && msg.files.length > 0) {
          console.log(`文件数量: ${msg.files.length}`);
          msg.files.forEach((file, fileIndex) => {
            console.log(`  文件 ${fileIndex}: ${file.name} (${file.type})`);
            console.log(`    路径: ${file.path}`);
            console.log(`    URL: ${file.url}`);
          });
        } else {
          console.log('无文件');
        }
      });
      console.log('=== 完整JSON ===');
      console.log(JSON.stringify(conversationMessages, null, 2));
      
      const response = await fetch('http://localhost:8081/api/llm/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: conversationMessages })
      });
      
      if (!response.ok) {
        throw new Error(`API调用失败: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setIsStreaming(false);
              setStreamingMessageId(null);
              
              const finalMessage = {
                role: 'assistant',
                content: fullResponse
              };
              
              await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalMessage)
              });
              
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullResponse += parsed.content;
                
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, content: fullResponse }
                    : msg
                ));
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
      
    } catch (error) {
      console.error('流式LLM API调用失败:', error);
      setIsStreaming(false);
      setStreamingMessageId(null);
      
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: `❌ API调用失败: ${error.message}\n\n请检查:\n1. API配置是否正确\n2. 网络连接是否正常\n3. API密钥是否有效` }
          : msg
      ));
    }
  }, [messages, boardId, conversationId]);

  // 初始化对话 - 支持分页加载
  const initializeConversation = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations`);
      if (response.ok) {
        const data = await response.json();
        const conversations = data.conversations || [];
        
        if (conversations.length > 0) {
          const latestConv = conversations[0];
          setConversationId(latestConv.id);
          
          // 只加载最新的消息（第一页）
          const historyResponse = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${latestConv.id}?page=0&limit=${ITEMS_PER_PAGE}`);
          if (historyResponse.ok) {
            const conversation = await historyResponse.json();
            const messages = conversation.messages || [];
            const totalMessages = conversation.total_messages || messages.length;
            
            console.log('📊 初始化对话:', { 
              loadedMessages: messages.length, 
              totalMessages, 
              hasMore: conversation.has_more 
            });
            
            setMessages(messages);
            setCurrentPage(0);
            // 根据后端返回的has_more字段或消息数量判断是否有更多历史
            const hasMore = conversation.has_more !== false && totalMessages > messages.length;
            console.log('📊 设置hasMoreHistory:', hasMore, { has_more: conversation.has_more, totalMessages, loadedMessages: messages.length });
            setHasMoreHistory(hasMore);
          }
        } else {
          const newConvResponse = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `title=${encodeURIComponent('AI助手对话')}`
          });
          
          if (newConvResponse.ok) {
            const conversation = await newConvResponse.json();
            setConversationId(conversation.id);
            setMessages([]);
            setCurrentPage(0);
            setHasMoreHistory(false);
          }
        }
      }
    } catch (error) {
      console.error('初始化对话失败:', error);
    }
  }, [boardId]);

  // 效果钩子 - 最小化数量
  useEffect(() => {
    if (boardId && isVisible) {
      initializeConversation();
    }
  }, [boardId, isVisible, initializeConversation]);

  // 初始化显示的消息
  useEffect(() => {
    updateDisplayedMessages();
  }, [updateDisplayedMessages]);

  // 当消息更新时，智能滚动
  useEffect(() => {
    if (messages.length > 0 && !shouldPreserveScrollPosition) {
      // 只有在初次加载或新增消息时才滚动到底部
      // 加载历史消息时不自动滚动，保持用户位置
      if (messages.length <= 20) {
        // 初次加载时滚动到底部
        setTimeout(() => {
          scrollToBottom();
        }, 100);
      } else {
        // 新增消息时滚动到底部
        setTimeout(() => {
          scrollToBottom();
        }, 100);
      }
    }
  }, [messages, scrollToBottom, shouldPreserveScrollPosition]);


  useEffect(() => {
    loadApiConfig();
  }, [loadApiConfig]);

  useEffect(() => {
    if (isFocused && isVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isFocused, isVisible]);

  useEffect(() => {
    if (inputRef.current && inputText === '') {
      const lineHeight = 16;
      const padding = 8;
      const minHeight = lineHeight + padding;
      inputRef.current.style.height = `${minHeight}px`;
      inputRef.current.style.overflowY = 'hidden';
    }
  }, [inputText]);

  // 点击外部关闭设置面板
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showSettings) {
        const settingsPanel = document.querySelector('.settings-panel');
        const settingsButton = document.querySelector('.settings-button');
        
        if (settingsPanel && 
            !settingsPanel.contains(event.target) && 
            settingsButton && 
            !settingsButton.contains(event.target)) {
          setShowSettings(false);
        }
      }
    };
    
    if (showSettings) {
      document.addEventListener('mousedown', handleClickOutside, true);
      return () => document.removeEventListener('mousedown', handleClickOutside, true);
    }
  }, [showSettings]);

  // 监听注释生成完成事件，实时刷新对话
  useEffect(() => {
    const handleRefreshConversation = async (event) => {
      const { conversationId: updatedConvId } = event.detail || {};
      console.log('🔄 收到刷新对话事件:', updatedConvId, '当前对话ID:', conversationId);
      
      if (conversationId && updatedConvId === conversationId) {
        console.log('✅ 对话ID匹配，重新加载最新消息');
        
        try {
          // 重新加载最新的消息（只加载最新的一页）
          const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}?page=0&limit=${ITEMS_PER_PAGE}`);
          if (response.ok) {
            const conversation = await response.json();
            const newMessages = conversation.messages || [];
            
            console.log('🔄 重新加载的消息数:', newMessages.length);
            
            // 更新消息列表
            setMessages(newMessages);
            
            // 滚动到底部以显示新的系统通知
            setTimeout(() => {
              scrollToBottom(true);
            }, 100);
          }
        } catch (error) {
          console.error('重新加载对话失败:', error);
        }
      }
    };
    
    if (typeof window !== 'undefined') {
      window.addEventListener('refreshChatConversation', handleRefreshConversation);
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('refreshChatConversation', handleRefreshConversation);
      }
    };
  }, [conversationId, boardId, scrollToBottom]);

  if (!isVisible) return null;

  return (
    <div className="chat-content" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar 
        showSettings={showSettings}
        setShowSettings={setShowSettings}
        showFileSelector={showFileSelector}
        setShowFileSelector={setShowFileSelector}
        loadBoardFiles={loadBoardFiles}
        scrollToBottom={scrollToBottom}
        apiProvider={apiProvider}
        setApiProvider={setApiProvider}
        apiConfigs={apiConfigs}
        setApiConfigs={setApiConfigs}
        saveApiConfig={saveApiConfig}
        getModelOptions={getModelOptions}
        getProviderName={getProviderName}
      />

      <div 
        className="messages-container" 
        ref={messagesContainerRef} 
        style={{ 
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden'
        }}
        onScroll={handleScroll}
        onWheel={(e) => {
          // 阻止滚轮事件冒泡到桌面
          e.stopPropagation();
        }}
        onTouchMove={(e) => {
          // 阻止触摸滚动事件冒泡到桌面
          e.stopPropagation();
        }}
      >
        
        {/* 调试信息 */}
        {process.env.NODE_ENV === 'development' && (
          <div style={{
            fontSize: '9px',
            color: '#999',
            padding: '2px 8px',
            backgroundColor: '#f9f9f9',
            borderBottom: '1px solid #eee'
          }}>
            🔍 调试: hasMoreHistory={hasMoreHistory.toString()}, messages={messages.length}, currentPage={currentPage}, conversationId={conversationId ? '✓' : '✗'}
          </div>
        )}

        {/* 加载更早记录按钮 - Windows 98风格 */}
        {hasMoreHistory && messages.length > 0 && isAtTop && (
          <div style={{
            textAlign: 'center',
            padding: '6px',
            backgroundColor: '#ffffff', // 与聊天界面背景色一致
            borderBottom: '1px solid #c0c0c0',
            borderTop: '1px solid #c0c0c0',
            fontSize: '11px',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}>
            <button
              onClick={loadMoreHistory}
              disabled={isLoadingHistory}
              style={{
                backgroundColor: isLoadingHistory ? '#a0a0a0' : '#c0c0c0',
                color: isLoadingHistory ? '#666' : '#000',
                border: '2px outset #c0c0c0',
                padding: '2px 8px',
                fontSize: '11px',
                cursor: isLoadingHistory ? 'not-allowed' : 'pointer',
                fontFamily: 'MS Sans Serif, sans-serif',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                margin: '0 auto',
                minWidth: '120px',
                justifyContent: 'center'
              }}
              onMouseDown={(e) => {
                if (!isLoadingHistory) {
                  e.target.style.border = '2px inset #c0c0c0';
                  e.target.style.backgroundColor = '#a0a0a0';
                }
              }}
              onMouseUp={(e) => {
                if (!isLoadingHistory) {
                  e.target.style.border = '2px outset #c0c0c0';
                  e.target.style.backgroundColor = '#c0c0c0';
                }
              }}
              onMouseLeave={(e) => {
                if (!isLoadingHistory) {
                  e.target.style.border = '2px outset #c0c0c0';
                  e.target.style.backgroundColor = '#c0c0c0';
                }
              }}
              title="点击加载更早的聊天记录"
            >
              {isLoadingHistory ? (
                <>
                  <span>⏳</span>
                  正在加载...
                </>
              ) : (
                <>
                  <span>📜</span>
                  加载更早记录
                </>
              )}
            </button>
            <div style={{
              fontSize: '10px',
              color: '#666',
              marginTop: '4px',
              fontWeight: 'normal'
            }}>
              显示 {displayedMessages.length} 条消息 (共 {messages.length} 条) | 页面: {currentPage + 1}
            </div>
          </div>
        )}
        
        {messages.length === 0 ? (
          <div className="welcome-message">
            <div className="ai-message-block">
              <div className="message-header">
                <div className="message-avatar">🤖</div>
                <div className="message-sender">Amadeus</div>
              </div>
              <div className="message-content">
                你好,这是Amadeus，有什么可以帮助您的吗？
              </div>
            </div>
          </div>
        ) : (
          /* 使用智能管理的消息列表 */
          displayedMessages.map((message, index) => (
            <MessageComponent
              key={message.id || index}
              message={message}
              isStreaming={isStreaming}
              streamingMessageId={streamingMessageId}
              onOpenWindow={onOpenWindow}
              getFileIcon={getFileIcon}
            />
          ))
        )}
        
        {isLoading && (
          <div className="ai-message-block">
            <div className="message-header">
              <div className="message-avatar">🤖</div>
              <div className="message-sender">AI助手</div>
            </div>
            <div className="message-content typing">
              <span className="typing-indicator">
                <span></span><span></span><span></span>
              </span>
              正在思考...
            </div>
          </div>
        )}
      </div>

      <FileSelector
        showFileSelector={showFileSelector}
        setShowFileSelector={setShowFileSelector}
        boardFiles={boardFiles}
        selectedFiles={selectedFiles}
        setSelectedFiles={setSelectedFiles}
        getFileIcon={getFileIcon}
      />

        <div className="input-container">
          {selectedFiles.length > 0 && (
            <div style={{
              fontSize: '10px',
              color: '#0078d4',
              padding: '2px 4px',
              backgroundColor: '#f0f8ff',
              border: '1px solid #0078d4',
              borderRadius: '2px',
              margin: '0 4px 4px 4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span>📎 已选择 {selectedFiles.length} 个文件</span>
              <button
                onClick={() => setSelectedFiles([])}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '10px',
                  color: '#0078d4',
                  padding: '0 2px'
                }}
                title="清空选择"
              >
                ✕
              </button>
            </div>
          )}
          
          <div className="input-box">
            <textarea
              ref={inputRef}
              value={inputText}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="输入消息... (Enter发送，Shift+Enter换行)"
              rows="1"
              disabled={isLoading}
              style={{
                resize: 'none',
                minHeight: '16px',
              maxHeight: '96px',
                overflowY: 'hidden',
                transition: 'height 0.1s ease'
              }}
            />
            <button 
              className="send-button"
              onClick={sendMessage}
              disabled={isLoading || !inputText.trim()}
              title="发送消息"
            >
              {isLoading ? '⏳' : '📤'}
            </button>
          </div>
        </div>
    </div>
  );
}

export default ChatWindow;
