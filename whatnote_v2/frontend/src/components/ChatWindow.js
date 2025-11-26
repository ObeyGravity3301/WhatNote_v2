import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import './ChatWindow.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import 'katex/dist/katex.min.css';

// LaTeX 分隔符标准化函数
const normalizeLatexDelimiters = (text) => {
  return text
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$');
};

const hasActiveTodos = (status) => {
  if (!status) return false;
  if (typeof status.has_todos === 'boolean') {
    return status.has_todos;
  }
  if (Array.isArray(status.items) && status.items.length > 0) {
    return true;
  }
  if (typeof status.total === 'number' && status.total > 0) {
    return true;
  }
  return false;
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
            rehypePlugins={[rehypeKatex, rehypeRaw]}
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
          rehypePlugins={[rehypeKatex, rehypeRaw]}
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
  getProviderName,
  useTools,
  setUseTools,
  onClearMessages,
  todoStatus,
  showTodoList,
  setShowTodoList,
  isStreaming,
  onStopGeneration
}) => {
  const hasTodos = hasActiveTodos(todoStatus);

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
        
        {hasTodos && (
          <button
            onClick={() => setShowTodoList(!showTodoList)}
            style={{
              padding: '1px 8px',
              fontSize: '11px',
              backgroundColor: showTodoList ? '#0078d4' : '#c0c0c0',
              color: showTodoList ? 'white' : 'black',
              border: showTodoList ? '2px inset #c0c0c0' : '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '50px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="显示/隐藏任务列表"
          >
            📋 Todo
          </button>
        )}
        
        <button
          onClick={() => setUseTools(!useTools)}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: useTools ? '#0078d4' : '#c0c0c0',
            color: useTools ? 'white' : 'black',
            border: useTools ? '2px inset #c0c0c0' : '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title={useTools ? "工具调用已启用（AI 可以创建窗口、查询任务等）" : "工具调用已禁用"}
        >
          🔧 工具{useTools ? ' ✓' : ''}
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
      
      {isStreaming && (
        <button
          onClick={onStopGeneration}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: '#ff4444',
            color: 'white',
            border: '2px outset #ff4444',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="停止生成"
        >
          ⏸️ 停止
        </button>
      )}
      
      <button
        onClick={onClearMessages}
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
        title="清空聊天记录"
      >
        🗑️ 清空
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

// Todo List 选择器组件
const TodoListSelector = React.memo(({ 
  showTodoList, 
  setShowTodoList, 
  todoStatus 
}) => {
  const hasTodos = hasActiveTodos(todoStatus);
  if (!showTodoList || !hasTodos) return null;

  const completedCount = todoStatus.completed_count ?? 0;
  const totalCount = todoStatus.total ?? 0;
  const remainingCount = todoStatus.remaining_count ?? 0;

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
        <span>📋 任务进度 ({completedCount}/{totalCount})</span>
        <button
          onClick={() => setShowTodoList(false)}
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
        {todoStatus.description && (
          <div style={{ 
            color: '#555', 
            marginBottom: '6px', 
            fontSize: '10px',
            fontStyle: 'italic',
            padding: '4px',
            backgroundColor: '#fff',
            border: '1px solid #e0e0e0',
            borderRadius: '2px'
          }}>
            {todoStatus.description}
          </div>
        )}
        
        {todoStatus.items && todoStatus.items.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {todoStatus.items.map(item => (
              <div
                key={item.index}
                style={{
                  border: item.completed ? '1px solid #c8e6c9' : '2px solid #ffe0b2',
                  backgroundColor: item.completed ? '#e8f5e9' : '#fff3e0',
                  padding: '8px',
                  borderRadius: '2px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  minHeight: '40px',
                  opacity: item.completed ? 0.8 : 1
                }}
              >
                <div style={{ fontSize: '16px', flexShrink: 0, marginTop: '2px' }}>
                  {item.completed ? '✅' : '⏳'}
                </div>
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontSize: '11px', 
                    fontWeight: 'bold',
                    marginBottom: '2px',
                    textDecoration: item.completed ? 'line-through' : 'none',
                    color: item.skipped ? '#999' : '#000'
                  }}>
                    {item.task}
                  </div>
                  
                  {(item.skip_reason || item.note) && (
                    <div style={{ 
                      fontSize: '9px', 
                      color: '#666',
                      marginTop: '2px'
                    }}>
                      {item.skip_reason && (
                        <span style={{ color: '#999' }}>
                          跳过: {item.skip_reason}
                        </span>
                      )}
                      {item.note && (
                        <span style={{ color: '#4caf50', fontStyle: 'italic', marginLeft: item.skip_reason ? '8px' : '0' }}>
                          {item.skip_reason ? ' | ' : ''}备注: {item.note}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: '#808080', textAlign: 'center', padding: '16px' }}>
            暂无任务项
          </div>
        )}
        
        <div style={{
          marginTop: '8px',
          paddingTop: '8px',
          borderTop: '1px solid #c0c0c0',
          fontSize: '10px',
          color: '#666',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>
            {todoStatus.all_completed 
              ? '🎉 所有任务已完成' 
              : `进度：已完成 ${completedCount}/${totalCount}，剩余 ${remainingCount}`
            }
          </span>
          {todoStatus.all_completed && (
            <span style={{ color: '#4caf50', fontWeight: 'bold' }}>
              ✓ 完成
            </span>
          )}
        </div>
      </div>
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
  
  // 自动滚动控制状态
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  
  // UI状态
  const [showSettings, setShowSettings] = useState(false);
  const [showFileSelector, setShowFileSelector] = useState(false);
  const [showTodoList, setShowTodoList] = useState(false);
  const [boardFiles, setBoardFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // 工具调用状态
  const [useTools, setUseTools] = useState(true);  // 默认启用工具调用
  const [toolCallLogs, setToolCallLogs] = useState([]);
  const [todoStatus, setTodoStatus] = useState(null);  // Todo 追踪状态
  const hasTodos = hasActiveTodos(todoStatus);

  const [expandedTools, setExpandedTools] = useState({});  // 展开的工具调用 {messageId-toolName-index: boolean}
  
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
  const currentAIMessageIdRef = useRef(null);
  const skipToolCallsRef = useRef({});
  const streamingContentRef = useRef('');
  const abortControllerRef = useRef(null);  // 用于中断流式请求
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
        if (Object.prototype.hasOwnProperty.call(data, 'todo_status')) {
          setTodoStatus(data.todo_status);
          console.info('[ChatWindow][TodoDebug] 加载历史后同步待办状态', data.todo_status);
        }
        
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

  const fetchTodoStatusFromServer = useCallback(async (targetConversationId) => {
    if (!boardId || !targetConversationId) return;
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${targetConversationId}/todo-status`);
      if (response.ok) {
        const data = await response.json();
        if (Object.prototype.hasOwnProperty.call(data, 'todo_status')) {
          console.info('[ChatWindow][TodoDebug] 从服务器同步待办状态', data.todo_status);
          setTodoStatus(data.todo_status);
        } else {
          console.info('[ChatWindow][TodoDebug] 服务器返回空待办状态');
          setTodoStatus(null);
        }
      } else if (response.status === 404) {
        console.info('[ChatWindow][TodoDebug] 服务器无待办状态记录，重置为空');
        setTodoStatus(null);
      }
    } catch (error) {
      console.error('从服务器获取待办状态失败:', error);
    }
  }, [boardId]);

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

  // 滚动事件处理 - 检测是否在顶部，并在用户手动滚动时禁用自动滚动
  const handleScroll = useCallback((e) => {
    // 阻止事件冒泡，防止桌面被滚动
    e.stopPropagation();
    
    const container = e.target;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    
    // 检测是否接近顶部（50px范围内）
    setIsAtTop(scrollTop < 50);
    
    // 检测是否接近底部（50px范围内）
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    
    // 如果用户手动滚动离开底部，禁用自动滚动
    if (!isNearBottom && isAutoScrollEnabled) {
      console.log('🛑 用户手动滚动离开底部，停止自动滚动');
      setIsAutoScrollEnabled(false);
    } else if (isNearBottom && !isAutoScrollEnabled && isStreaming) {
      // ⭐ 只有在模型正在输出时才恢复自动滚动
      // 如果用户滚动回底部附近，且模型正在输出，立即恢复自动滚动
      console.log('✅ 用户滚动回底部，恢复自动滚动（模型正在输出）');
      setIsAutoScrollEnabled(true);
    }
    // 如果模型不在输出，即使滚动到底部也不自动恢复滚动
  }, [isAutoScrollEnabled, isStreaming]);

  // 优化的文件加载函数
  const loadBoardFiles = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/files`);
      
      if (response.ok) {
        const data = await response.json();
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
    
    // 发送新消息时，重新启用自动滚动
    setIsAutoScrollEnabled(true);

    try {
      await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userMessage)
      });

      const aiMessageId = Date.now();
      currentAIMessageIdRef.current = aiMessageId;
      skipToolCallsRef.current = {};
      streamingContentRef.current = '';
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

  // 键盘事件处理
  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // 流式AI回复函数
  const generateStreamingAIResponse = useCallback(async (userMessage, aiMessageId) => {
    try {
      streamingContentRef.current = '';
      skipToolCallsRef.current = {};

      // 添加上下文系统消息（如果启用了工具调用）
      const now = new Date();
      const currentDate = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '-');
      const currentTime = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
      const currentDatetime = now.toISOString().slice(0, 19).replace('T', ' ');
      
      const contextMessage = useTools ? {
        role: 'system',
        content: `### 核心行为准则（最高优先级）###
你是一个"操作员"，不是"叙述者"。你的职责是通过工具调用来执行用户的请求，而不是用语言描述你"将要做"或"已经做了"什么。

🚨 强制规则：
1. 判断请求类型：这是查询还是操作？
2. 如果是操作（创建、添加、修改、删除），你必须调用对应的工具
3. 只有在工具调用成功后，你才能说"已完成"
4. 如果你没有调用工具，就绝对不能声称操作已完成
5. 文本输出不会产生任何实际效果，只有工具调用才能改变系统状态

❌ 禁止行为：
- 禁止在文本中"假装"已经完成操作
- 禁止输出"已添加任务 xxx"而不调用 add_task
- 禁止输出"已创建窗口"而不调用 create_window
- 禁止输出"待办列表已更新"而不调用 todo 相关工具

✅ 正确行为：
- 用户说"添加一个任务" → 调用 add_task 工具
- 用户说"创建一个窗口" → 调用 create_window 工具
- 用户说"在 todo 中添加一项" → 调用 add_todo_item 工具
- 工具调用成功后 → 才能描述结果

### 上下文信息 ###
- 展板名称：${boardName || '未命名展板'}
- 展板ID：${boardId}
- 当前日期：${currentDate}（格式：YYYY-MM-DD）
- 当前时间：${currentTime}（格式：HH:MM）
- 完整时间戳：${currentDatetime}

### 操作指南 ###
1. 当需要操作窗口（创建、读取、编辑、搜索等）时，请使用上述 board_id
2. 用户的所有窗口操作都应该在当前展板上进行
3. 如果用户询问"这里"、"当前展板"等，指的就是上述展板
4. 日期格式必须使用 YYYY-MM-DD（例如：${currentDate}）
5. 时间格式必须使用 HH:MM（例如：${currentTime}）
6. 添加任务时，如果用户说"今天"或未指定日期，使用当前日期：${currentDate}

📋 任务追踪系统（谨慎使用）：
todo 系统是为了帮助你在**非常复杂的长任务**中记住后续步骤，避免遗忘。它会消耗额外的工具调用，请谨慎使用。

⚠️ 大多数情况下不需要 todo：
- 简单问答、单一操作、批量操作后统一总结 → 直接执行，不用 todo
- 3-5 步的常规任务 → 直接按顺序执行，不用 todo
- 有把握一次完成的任务 → 直接执行，不用 todo

✅ 仅在以下情况使用 todo：
- 用户明确要求"分步执行"、"每步告诉我进度"
- 任务非常复杂（10步以上），且你担心中途会忘记后续步骤
- 需要在多轮对话中跨越多次请求完成的长期任务

使用方法：
1. 创建待办列表：create_todo_list(["大步骤1", "大步骤2", ...])
   - 只列出主要步骤，不要拆分得太细
2. 标记完成：
   - 单个完成：complete_todo_item(item_index=0)
   - 批量完成（推荐）：complete_todo_items(item_indices=[0, 1, 2]) - 一次性完成多个项，节省时间和 token
   - 可以连续完成多个操作后，再批量标记，不需要每完成一个小操作就立即标记
3. 暂停：pause_execution(reason="...")

示例：
用户: "帮我创建5个窗口，每个写入不同内容"
→ 不用 todo，直接连续创建5个窗口，最后总结

用户: "帮我做一个复杂的PPT，共20页，每页有不同的内容和样式"
→ 使用 todo，因为任务复杂且容易遗忘

用户: "添加3个日历任务"
→ 不用 todo，直接添加，最后总结`
      } : null;
      
      // 包含所有消息（包括system消息），让LLM了解用户的操作历史
      const conversationMessages = [];
      
      // 首先添加上下文消息
      if (contextMessage) {
        conversationMessages.push(contextMessage);
      }
      
      // 如果有活跃的 todo 列表，将其状态添加到上下文中
      // 这样 LLM 不需要每次都调用 get_todo_status 来获取当前状态
      if (hasActiveTodos(todoStatus)) {
        const todoItems = (todoStatus.items || []).map((item, idx) => {
          const status = item.completed ? '✅' : '⏳';
          return `${idx}. ${status} ${item.task}`;
        }).join('\n');
        
        const todoContextMessage = {
          role: 'system',
          content: `### 当前 Todo 列表状态 ###
描述：${todoStatus.description || '无'}
进度：${todoStatus.completed_count}/${todoStatus.total} 已完成，剩余 ${todoStatus.remaining_count} 项

${todoItems}

注意：如需修改此列表，请使用 add_todo_item、complete_todo_item、complete_todo_items 等工具。`
        };
        conversationMessages.push(todoContextMessage);
      }
      
      // 清理消息内容中的工具调用 HTML 格式，避免 LLM 学习并模仿这些格式
      const cleanToolCallContent = (content) => {
        if (!content || typeof content !== 'string') return content;
        
        // 移除 <details> 工具调用块（包含调用参数和执行结果）
        let cleaned = content.replace(/<details class="tool-call-block[^"]*"[\s\S]*?<\/details>/g, '');
        
        // 移除可能残留的工具调用相关标记
        cleaned = cleaned.replace(/\*\*调用参数\*\*：[\s\S]*?```\n/g, '');
        cleaned = cleaned.replace(/\*\*执行结果\*\*：[\s\S]*?```\n/g, '');
        
        // 清理多余的空行
        cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
        
        return cleaned.trim();
      };
      
      // 然后添加历史消息
      messages.forEach(msg => {
        // 对 assistant 消息清理工具调用格式，避免 LLM 模仿
        const cleanedContent = msg.role === 'assistant' 
          ? cleanToolCallContent(msg.content) 
          : msg.content;
        
        conversationMessages.push({
          role: msg.role,
          content: cleanedContent,
          files: msg.files
        });
      });
      
      // 最后添加当前用户消息
      const currentUserMessage = {
        role: userMessage.role,
        content: userMessage.content,
        files: userMessage.files
      };
      
      conversationMessages.push(currentUserMessage);
      
      // 选择 API 端点：根据 useTools 决定是否使用工具调用
      const apiUrl = useTools 
        ? 'http://localhost:8081/api/llm/chat-with-tools'
        : 'http://localhost:8081/api/llm/chat';
      
      // 创建 AbortController 用于中断请求
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: conversationMessages,
          max_iterations: 50,  // 最大工具调用轮数
          board_id: boardId,
          conversation_id: conversationId
        }),
        signal: abortControllerRef.current.signal  // 添加中断信号
      });
      
      if (!response.ok) {
        throw new Error(`API调用失败: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let currentToolLogs = [];
      
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
              fullResponse = streamingContentRef.current || fullResponse;
              
              // ⭐ 将所有剩余的未完成状态标记改为"已完成"（对话结束时）
              fullResponse = fullResponse.replace(
                /(<span class="tool-status">)\[(?:执行中\.\.\.|等待LLM响应)\](<\/span>)/g,
                '$1[已完成]$2'
              );
              
              // 最后更新一次显示
              setMessages(prev => prev.map(msg => 
                msg.id === aiMessageId 
                  ? { ...msg, content: fullResponse }
                  : msg
              ));
              
              // ⭐ 模型停止输出后，禁用自动滚动（除非用户手动滚动到底部）
              // 这样用户可以自由浏览历史消息，不会被"吸"在底部
              setIsAutoScrollEnabled(false);
              
              const finalMessage = {
                role: 'assistant',
                content: fullResponse
              };
              
              await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalMessage)
              });
              
              currentAIMessageIdRef.current = null;
              skipToolCallsRef.current = {};
              streamingContentRef.current = '';
              
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              fullResponse = streamingContentRef.current || fullResponse;
              
              // 处理工具调用事件
              if (useTools && parsed.type) {
                if (parsed.type === 'thinking') {
                  // 🤔 LLM 正在思考
                  // 显示思考动画（可选）
                  console.log('[ChatWindow] LLM 正在推理...');
                  
                } else if (parsed.type === 'tool_call') {
                  // 🔧 工具调用开始
                  const toolLog = {
                    type: 'tool_call',
                    tool_name: parsed.tool_name,
                    arguments: parsed.arguments,
                    content: parsed.content
                  };
                  currentToolLogs.push(toolLog);
                  setToolCallLogs(prev => [...prev, toolLog]);
                  
                  // ⭐ 如果有之前的工具状态，先标记为"已完成"
                  fullResponse = fullResponse.replace(
                    /(<span class="tool-status">)\[(?:执行中\.\.\.|等待LLM响应)\](<\/span>)/g,
                    '$1[已完成]$2'
                  );
                  streamingContentRef.current = fullResponse;
                  
                  // 在消息中显示工具标签 - 使用 details 标签实现点击展开
                  // 状态：[执行中...] 表示工具正在执行
                  const toolCallId = `tool-${Date.now()}-${parsed.tool_name}`;
                  const argsStr = JSON.stringify(parsed.arguments, null, 2);
                  skipToolCallsRef.current[toolCallId] = false;
                  
                  fullResponse += `\n<details class="tool-call-block tool-call-real" data-tool-id="${toolCallId}" data-skipped="false">
<summary>🔧 <code>${parsed.tool_name}</code> <span class="tool-status">[执行中...]</span> <span class="tool-source">【系统调用】</span></summary>
<div class="tool-call-actions">
  <button type="button" class="tool-skip-button" data-tool-id="${toolCallId}" data-tool-name="${parsed.tool_name}">跳过等待</button>
</div>

**调用参数**：
\`\`\`json
${argsStr}
\`\`\`
</details>\n`;
                  streamingContentRef.current = fullResponse;
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'tool_result') {
                  // ✅ 工具执行完成
                  const resultLog = {
                    type: 'tool_result',
                    tool_name: parsed.tool_name,
                    result: parsed.tool_result,
                    content: parsed.content
                  };
                  currentToolLogs.push(resultLog);
                  setToolCallLogs(prev => [...prev, resultLog]);
                  
                  const toolSuccess = parsed.tool_result?.status === 'success' || parsed.tool_result?.window_id;
                  const toolDebugPayload = {
                    tool_name: parsed.tool_name,
                    result: parsed.tool_result,
                    success: toolSuccess
                  };
                  if (toolSuccess) {
                    console.info('[ChatWindow][ToolDebug] 工具执行成功', toolDebugPayload);
                  } else {
                    console.warn('[ChatWindow][ToolDebug] 工具执行失败或返回异常', toolDebugPayload);
                  }
                  
                  // 特殊处理：create_todo_list 的结果不应该直接更新 todo 状态
                  // 应该等待 todo_status 事件来更新状态
                  if (parsed.tool_name === 'create_todo_list' && toolSuccess) {
                    const resultData = parsed.tool_result;
                    console.info(
                      '[ChatWindow][TodoDebug] 收到 create_todo_list 工具结果，但不直接更新状态，等待 todo_status 事件',
                      { 
                        resultTotal: resultData?.total,
                        resultHasTodos: resultData?.has_todos,
                        currentTodoStatus: todoStatus ? `${todoStatus.completed_count}/${todoStatus.total}` : 'null'
                      }
                    );
                  }
                  
                  // ⭐ 工具执行完成，更新状态并添加执行结果
                  // 状态：[执行中...] -> [等待LLM响应] 表示工具已完成，等待 LLM 继续
                  const resultStr = JSON.stringify(parsed.tool_result, null, 2);
                  
                  // 找到最后一个 </details> 的位置
                  const lastDetailsEndIndex = fullResponse.lastIndexOf('</details>');
                  if (lastDetailsEndIndex !== -1) {
                    // 在 </details> 之前插入执行结果
                    const beforeDetails = fullResponse.substring(0, lastDetailsEndIndex);
                    const afterDetails = fullResponse.substring(lastDetailsEndIndex);
                    
                    // 替换状态：[执行中...] -> [等待LLM响应]
                    const updatedBefore = beforeDetails.replace(
                      /(<span class="tool-status">)\[执行中\.\.\.\](<\/span>)(?![\s\S]*\[执行中\.\.\.\])/,
                      '$1[等待LLM响应]$2'
                    );
                    
                    fullResponse = updatedBefore + `\n\n**执行结果**：\n\`\`\`json\n${resultStr}\n\`\`\`\n` + afterDetails;
                    streamingContentRef.current = fullResponse;
                  }
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                  // 如果是窗口操作，触发刷新
                  const windowTools = [
                    'create_window',
                    'create_web_window',
                    'delete_window',
                    'update_window',
                    'update_web_window',
                    'edit_window'
                  ];
                  if (windowTools.includes(parsed.tool_name)) {
                    const isSuccess = parsed.tool_result?.status === 'success' || parsed.tool_result?.window_id || parsed.tool_result?.message;
                    if (isSuccess) {
                      console.info(`[ChatWindow][WindowDebug] 窗口操作成功 (${parsed.tool_name})`, parsed.tool_result);
                    } else {
                      console.warn(`[ChatWindow][WindowDebug] 窗口操作失败或返回空结果 (${parsed.tool_name})`, parsed.tool_result);
                    }
                    if (isSuccess) {
                      // 延迟一点触发，确保后端已保存完成
                      setTimeout(() => {
                        console.info('[ChatWindow][WindowDebug] 触发 refreshBoard 事件');
                        window.dispatchEvent(new CustomEvent('refreshBoard'));
                      }, 300);
                    }
                  }
                  
                  // 如果是日历操作，触发刷新
                  const calendarTools = ['add_task', 'list_tasks', 'toggle_task', 'update_task', 'delete_task', 'search_tasks', 'get_upcoming_tasks'];
                  if (calendarTools.includes(parsed.tool_name)) {
                    console.log('[ChatWindow] 日历操作完成，触发刷新日历');
                    window.dispatchEvent(new CustomEvent('refreshCalendar'));
                  }
                  
                } else if (parsed.type === 'text_start') {
                  // 💬 开始文本输出
                  // 将所有未完成的工具标记为"已完成"
                  fullResponse = fullResponse.replace(
                    /(<span class="tool-status">)\[(?:执行中\.\.\.|等待LLM响应)\](<\/span>)/g,
                    '$1[已完成]$2'
                  );
                  fullResponse += `\n`;
                  streamingContentRef.current = fullResponse;
                  
                } else if (parsed.type === 'text_chunk') {
                  // 💬 流式输出文本
                  fullResponse += parsed.content;
                  streamingContentRef.current = fullResponse;
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'text_complete') {
                  // 💬 文本输出完成
                  streamingContentRef.current = fullResponse;
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'todo_status') {
                  // 📋 Todo 状态更新
                  const status = parsed.content;
                  const oldStatus = todoStatus;
                  
                  if (hasActiveTodos(status)) {
                    const remainingItems = (status.items || []).filter(item => !item.completed).map(item => item.task);
                    console.info(
                      `[ChatWindow][TodoDebug] 收到待办进度更新: ${status.completed_count}/${status.total} 完成，剩余 ${status.remaining_count} 项`,
                      { 
                        oldStatus: oldStatus ? `${oldStatus.completed_count}/${oldStatus.total}` : 'null',
                        newStatus: `${status.completed_count}/${status.total}`,
                        remainingItems, 
                        fullStatus: status 
                      }
                    );
                  } else {
                    console.info(
                      '[ChatWindow][TodoDebug] 收到待办进度更新：当前无活跃待办',
                      { oldStatus, newStatus: status }
                    );
                  }
                  
                  // 强制更新状态
                  setTodoStatus(status);
                  console.info('[ChatWindow][TodoDebug] 已调用 setTodoStatus，状态应已更新', status);
                  
                } else if (parsed.type === 'intermediate_text_start' || parsed.type === 'final_start') {
                  // 兼容旧版本
                  fullResponse += `\n\n`;
                  
                } else if (parsed.type === 'intermediate_text_chunk' || parsed.type === 'final_chunk') {
                  // 兼容旧版本
                  fullResponse += parsed.content;
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'intermediate_text_complete' || parsed.type === 'final_complete') {
                  // 兼容旧版本
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'final') {
                  // 💬 最终回复（兼容旧格式）
                  fullResponse += `\n${parsed.content}`;
                  
                } else if (parsed.type === 'error') {
                  // ❌ 错误
                  fullResponse += `\n\n❌ ${parsed.content}`;
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                  
                } else if (parsed.type === 'warning') {
                  // ⚠️ 警告
                  fullResponse += `\n\n⚠️ ${parsed.content}`;
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                } else if (parsed.type === 'info') {
                  // ℹ️ 信息提示（如暂停提示）
                  fullResponse += `\n\n${parsed.content}`;
                  
                  // 立即更新显示
                  setMessages(prev => prev.map(msg => 
                    msg.id === aiMessageId 
                      ? { ...msg, content: fullResponse }
                      : msg
                  ));
                }
                
              } else if (parsed.content) {
                // 普通流式响应（没有工具调用）
                fullResponse += parsed.content;
                
                setMessages(prev => prev.map(msg => 
                  msg.id === aiMessageId 
                    ? { ...msg, content: fullResponse }
                    : msg
                ));
              }
            } catch (e) {
              console.error('解析事件失败:', e, 'data:', data);
              // 忽略解析错误
            }
          }
        }
      }
      
    } catch (error) {
      console.error('流式LLM API调用失败:', error);
      setIsStreaming(false);
      setStreamingMessageId(null);
      
      // 如果是用户主动中断，显示不同的消息
      if (error.name === 'AbortError') {
        const finalContent = streamingContentRef.current || '';
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { ...msg, content: finalContent + '\n\n⏸️ **用户已停止生成**' }
            : msg
        ));
        console.log('⏸️ 用户已停止生成');
      } else {
        setMessages(prev => prev.map(msg => 
          msg.id === aiMessageId 
            ? { ...msg, content: `❌ API调用失败: ${error.message}\n\n请检查:\n1. API配置是否正确\n2. 网络连接是否正常\n3. API密钥是否有效` }
            : msg
        ));
      }
    }
  }, [messages, boardId, boardName, conversationId, useTools]);

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
          fetchTodoStatusFromServer(latestConv.id);
          
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
            if (Object.prototype.hasOwnProperty.call(conversation, 'todo_status')) {
              setTodoStatus(conversation.todo_status);
              if (hasActiveTodos(conversation.todo_status)) {
                console.info('[ChatWindow][TodoDebug] 初始化同步待办状态', conversation.todo_status);
              } else {
                console.info('[ChatWindow][TodoDebug] 初始化待办状态为空或无待办', conversation.todo_status);
              }
            }
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
            setTodoStatus(null);
            console.info('[ChatWindow][TodoDebug] 新对话创建，待办状态已重置');
            fetchTodoStatusFromServer(conversation.id);
          }
        }
      }
    } catch (error) {
      console.error('初始化对话失败:', error);
    }
  }, [boardId, fetchTodoStatusFromServer]);

  // 效果钩子 - 最小化数量
  useEffect(() => {
    if (boardId && isVisible) {
      initializeConversation();
    }
  }, [boardId, isVisible, initializeConversation]);

  // 监听刷新对话事件（来自批量注释系统消息）
  useEffect(() => {
    const handleRefreshConversation = async (event) => {
      const { conversationId: targetConversationId } = event.detail || {};
      console.log('🔄 收到刷新对话请求:', targetConversationId, '当前对话:', conversationId);
      
      // 如果目标对话是当前对话，刷新消息列表
      if (targetConversationId === conversationId) {
        try {
          const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}?page=0&limit=${ITEMS_PER_PAGE}`);
          if (response.ok) {
            const conversation = await response.json();
            const newMessages = conversation.messages || [];
            console.log('✅ 对话已刷新，新消息数:', newMessages.length);
            setMessages(newMessages);
            if (Object.prototype.hasOwnProperty.call(conversation, 'todo_status')) {
              setTodoStatus(conversation.todo_status);
              console.info('[ChatWindow][TodoDebug] 刷新对话后同步待办状态', conversation.todo_status);
            }
            setCurrentPage(0);
            fetchTodoStatusFromServer(conversationId);
            // 刷新后滚动到底部查看新消息
            setTimeout(() => {
              scrollToBottom();
            }, 100);
          }
        } catch (error) {
          console.error('刷新对话失败:', error);
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
  }, [boardId, conversationId, scrollToBottom, fetchTodoStatusFromServer]);

  // 初始化显示的消息
  useEffect(() => {
    updateDisplayedMessages();
  }, [updateDisplayedMessages]);

  // 当消息更新时，智能滚动（仅当自动滚动启用时）
  useEffect(() => {
    if (messages.length > 0 && !shouldPreserveScrollPosition && isAutoScrollEnabled) {
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
  }, [messages, scrollToBottom, shouldPreserveScrollPosition, isAutoScrollEnabled]);


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
            if (Object.prototype.hasOwnProperty.call(conversation, 'todo_status')) {
              setTodoStatus(conversation.todo_status);
              console.info('[ChatWindow][TodoDebug] 批量刷新事件后同步待办状态', conversation.todo_status);
            }
            fetchTodoStatusFromServer(conversationId);
            
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
  }, [conversationId, boardId, scrollToBottom, fetchTodoStatusFromServer]);

  const applyToolUpdateToCurrentMessage = useCallback((updateFn) => {
    if (!currentAIMessageIdRef.current) {
      return;
    }
    setMessages(prev => prev.map(msg => {
      if (msg.id !== currentAIMessageIdRef.current) {
        return msg;
      }
      const updatedContent = updateFn(msg.content);
      if (!updatedContent || updatedContent === msg.content) {
        return msg;
      }
      streamingContentRef.current = updatedContent;
      return { ...msg, content: updatedContent };
    }));
  }, [setMessages]);

  const handleSkipToolCall = useCallback(async (toolCallId, toolName) => {
    if (!toolCallId) return;
    if (skipToolCallsRef.current[toolCallId]) return;

    skipToolCallsRef.current[toolCallId] = true;

    applyToolUpdateToCurrentMessage((content) => {
      if (!content) return content;
      let updated = content;
      const detailAttrRegex = new RegExp(`(<details class="tool-call-block" data-tool-id="${toolCallId}"[^>]*)data-skipped="false"`, 'i');
      if (detailAttrRegex.test(updated)) {
        updated = updated.replace(detailAttrRegex, `$1data-skipped="true"`);
      }
      const statusRegex = new RegExp(`(<details class="tool-call-block"[^>]*data-tool-id="${toolCallId}"[\\s\\S]*?<span class="tool-status">)\\[[^\\]]+\\]`);
      updated = updated.replace(statusRegex, `$1[已跳过]`);
      const buttonRegex = new RegExp(`(<button[^>]*class="tool-skip-button"[^>]*data-tool-id="${toolCallId}"[^>]*)(>)([\s\S]*?</button>)`);
      updated = updated.replace(buttonRegex, `$1 data-skipped="true" disabled>$2已跳过</button>`);
      if (!new RegExp(`tool-skip-note"[^>]*data-tool-id="${toolCallId}"`).test(updated)) {
        const actionsRegex = new RegExp(`(<div class="tool-call-actions">[\s\S]*?data-tool-id="${toolCallId}"[\s\S]*?</div>)`);
        if (actionsRegex.test(updated)) {
          updated = updated.replace(actionsRegex, `$1\n<div class="tool-skip-note" data-tool-id="${toolCallId}">⚠️ 用户已选择跳过等待工具结果，后续若有结果将自动更新。</div>`);
        } else {
          updated += `\n<div class="tool-skip-note" data-tool-id="${toolCallId}">⚠️ 用户已选择跳过等待工具结果，后续若有结果将自动更新。</div>`;
        }
      }
      return updated;
    });

    const timestamp = new Date().toISOString();
    setToolCallLogs(prev => [...prev, {
      type: 'tool_skip',
      tool_name: toolName,
      tool_call_id: toolCallId,
      timestamp
    }]);

    if (boardId && conversationId) {
      try {
        const skipMessage = {
          role: 'system',
          content: `⚠️ 用户在等待工具 ${toolName || toolCallId} 的执行结果时选择跳过等待，请继续后续响应。`,
          metadata: {
            type: 'tool_skip',
            tool_name: toolName || '',
            tool_call_id: toolCallId,
            skipped_at: timestamp
          }
        };
        await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(skipMessage)
        });
      } catch (error) {
        console.error('上报跳过等待动作失败:', error);
      }
    }
  }, [applyToolUpdateToCurrentMessage, boardId, conversationId, setToolCallLogs]);

  // 停止生成
  const handleStopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
      setStreamingMessageId(null);
      console.log('⏸️ 用户点击停止按钮，中断生成');
    }
  }, []);

  // 清空聊天记录
  const handleClearMessages = useCallback(async () => {
    if (!conversationId || !boardId) {
      console.warn('无法清空：缺少对话ID或展板ID');
      return;
    }

    // 确认对话框
    if (!window.confirm('确定要清空当前展板的所有聊天记录吗？此操作不可恢复。')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
        method: 'DELETE'
      });

      if (response.ok) {
        // 清空前端状态
        setMessages([]);
        setCurrentPage(0);
        setHasMoreHistory(false);
        setTodoStatus(null);
        setToolCallLogs([]);
        streamingContentRef.current = '';
        currentAIMessageIdRef.current = null;
        skipToolCallsRef.current = {};
        
        console.log('✅ 聊天记录已清空');
      } else {
        const errorText = await response.text();
        console.error('清空聊天记录失败:', response.status, errorText);
        alert('清空聊天记录失败，请稍后重试');
      }
    } catch (error) {
      console.error('清空聊天记录失败:', error);
      alert('清空聊天记录失败，请稍后重试');
    }
  }, [conversationId, boardId]);

  useEffect(() => {
    const handleGlobalClick = (event) => {
      const button = event.target.closest('.tool-skip-button');
      if (!button) return;
      const detail = button.closest('.tool-call-block');
      const toolId = button.getAttribute('data-tool-id');
      if (!toolId || skipToolCallsRef.current[toolId]) return;
      if (detail) {
        const statusText = detail.querySelector('.tool-status')?.textContent || '';
        if (statusText.includes('已完成') || statusText.includes('已跳过')) {
          return;
        }
      }
      event.preventDefault();
      const toolName = button.getAttribute('data-tool-name') || '';
      handleSkipToolCall(toolId, toolName);
    };

    document.addEventListener('click', handleGlobalClick);
    return () => {
      document.removeEventListener('click', handleGlobalClick);
    };
  }, [handleSkipToolCall]);

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
        useTools={useTools}
        setUseTools={setUseTools}
        onClearMessages={handleClearMessages}
        todoStatus={todoStatus}
        showTodoList={showTodoList}
        setShowTodoList={setShowTodoList}
        isStreaming={isStreaming}
        onStopGeneration={handleStopGeneration}
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
          
          // 用户使用滚轮，禁用自动滚动
          if (isAutoScrollEnabled) {
            console.log('🛑 检测到滚轮事件，停止自动滚动');
            setIsAutoScrollEnabled(false);
          }
        }}
        onTouchMove={(e) => {
          // 阻止触摸滚动事件冒泡到桌面
          e.stopPropagation();
          
          // 用户触摸滚动，禁用自动滚动
          if (isAutoScrollEnabled) {
            console.log('🛑 检测到触摸滚动，停止自动滚动');
            setIsAutoScrollEnabled(false);
          }
        }}
        onClick={() => {
          // 用户点击消息区域，禁用自动滚动
          if (isAutoScrollEnabled) {
            console.log('🛑 检测到点击事件，停止自动滚动');
            setIsAutoScrollEnabled(false);
          }
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
          <>
            {/* 消息列表 */}
            {displayedMessages.map((message, index) => (
              <MessageComponent
                key={`msg-${message.id}-${index}`}
                message={message}
                isStreaming={isStreaming}
                streamingMessageId={streamingMessageId}
                onOpenWindow={onOpenWindow}
                getFileIcon={getFileIcon}
              />
            ))}
          </>
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

      <TodoListSelector
        showTodoList={showTodoList}
        setShowTodoList={setShowTodoList}
        todoStatus={todoStatus}
      />

      <div className="input-container">
        {/* 折叠的 Todo 显示 */}
        {hasTodos && !showTodoList && (
          <div 
            onClick={() => setShowTodoList(true)}
            style={{
              fontSize: '10px',
              color: '#0078d4',
              padding: '4px 8px',
              backgroundColor: '#f0f8ff',
              border: '1px solid #0078d4',
              borderRadius: '2px',
              margin: '0 4px 4px 4px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
              userSelect: 'none'
            }}
            title="点击展开任务列表"
          >
            <span>📋</span>
            <span>[{todoStatus.completed_count ?? 0}/{todoStatus.total ?? 0} todo]</span>
            {todoStatus.all_completed && (
              <span style={{ color: '#4caf50', fontWeight: 'bold' }}>✓</span>
            )}
          </div>
        )}
        
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
            disabled={isLoading || (!inputText.trim() && selectedFiles.length === 0)}
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