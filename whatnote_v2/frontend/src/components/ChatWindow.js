import React, { useState, useEffect, useRef, useCallback } from 'react';
import './ChatWindow.css';

function ChatWindow({ 
  boardId, 
  boardName,
  isVisible, 
  onClose, 
  onMinimize,
  onFocus,
  isFocused
}) {
  // 聊天状态
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [conversationTitle, setConversationTitle] = useState('AI助手');
  
  // 工具栏状态
  const [showSettings, setShowSettings] = useState(false);
  const [showFileSelector, setShowFileSelector] = useState(false);
  const [boardFiles, setBoardFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // 引用
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初始化对话
  useEffect(() => {
    if (boardId && isVisible) {
      initializeConversation();
    }
  }, [boardId, isVisible]);

  // 聚焦时focus输入框
  useEffect(() => {
    if (isFocused && isVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isFocused, isVisible]);

  // 发送消息后重置输入框高度
  useEffect(() => {
    if (inputRef.current && inputText === '') {
      const lineHeight = 16;
      const padding = 8;
      const minHeight = lineHeight + padding;
      inputRef.current.style.height = `${minHeight}px`;
      inputRef.current.style.overflowY = 'hidden';
    }
  }, [inputText]);

  const initializeConversation = async () => {
    try {
      // 获取展板已有的对话列表
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations`);
      if (response.ok) {
        const data = await response.json();
        const conversations = data.conversations || [];
        
        if (conversations.length > 0) {
          // 使用最新的对话
          const latestConv = conversations[0];
          setConversationId(latestConv.id);
          setConversationTitle(latestConv.title);
          
          // 加载对话历史
          await loadConversationHistory(latestConv.id);
        } else {
          // 创建新对话
          await createNewConversation();
        }
      } else {
        console.error('获取对话列表失败');
        await createNewConversation();
      }
    } catch (error) {
      console.error('初始化对话失败:', error);
      await createNewConversation();
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `title=${encodeURIComponent('AI助手对话')}`
      });
      
      if (response.ok) {
        const conversation = await response.json();
        setConversationId(conversation.id);
        setConversationTitle(conversation.title);
        setMessages([]);
        console.log('创建新对话成功:', conversation.id);
      } else {
        console.error('创建对话失败');
      }
    } catch (error) {
      console.error('创建对话失败:', error);
    }
  };

  const loadConversationHistory = async (convId) => {
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${convId}`);
      if (response.ok) {
        const conversation = await response.json();
        setMessages(conversation.messages || []);
        console.log('加载对话历史成功:', conversation.messages?.length || 0, '条消息');
      } else {
        console.error('加载对话历史失败');
      }
    } catch (error) {
      console.error('加载对话历史失败:', error);
    }
  };

  const loadBoardFiles = async () => {
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/files`);
      if (response.ok) {
        const data = await response.json();
        setBoardFiles(data.files || []);
        console.log('加载展板文件成功:', data.files?.length || 0, '个文件');
      } else {
        console.error('加载展板文件失败');
      }
    } catch (error) {
      console.error('加载展板文件失败:', error);
    }
  };

  const sendMessage = async () => {
    if ((!inputText.trim() && selectedFiles.length === 0) || !conversationId || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputText.trim() || '发送了文件',
      files: selectedFiles.length > 0 ? selectedFiles : undefined
    };

    // 立即显示用户消息
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setSelectedFiles([]);  // 清空选中的文件
    setIsLoading(true);

    try {
      // 保存用户消息到后端
      await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userMessage)
      });

      // 模拟AI回复（这里可以集成真正的LLM API）
      const aiResponse = await generateAIResponse(userMessage.content);
      const aiMessage = {
        role: 'assistant',
        content: aiResponse
      };

      // 显示AI回复
      setMessages(prev => [...prev, aiMessage]);

      // 保存AI消息到后端
      await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(aiMessage)
      });

    } catch (error) {
      console.error('发送消息失败:', error);
      // 添加错误消息
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，发送消息时出现错误，请稍后重试。'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 模拟AI响应（可以替换为真正的LLM API调用）
  const generateAIResponse = async (userInput) => {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
    
    const responses = [
      `我理解您提到的"${userInput}"。让我为您分析一下这个问题。`,
      `关于"${userInput}"，我可以为您提供以下建议...`,
      `这是一个很好的问题！关于"${userInput}"，我的看法是...`,
      `让我帮您总结一下关于"${userInput}"的要点...`,
      `根据您提到的"${userInput}"，我建议您考虑以下几个方面...`
    ];
    
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // 获取文件类型图标
  const getFileIcon = (fileType) => {
    const icons = {
      'images': '🖼️',
      'videos': '🎬',
      'audios': '🎵',
      'pdfs': '📄',
      'texts': '📝'
    };
    return icons[fileType] || '📄';
  };

  // 自适应高度处理函数
  const handleInputChange = (e) => {
    const textarea = e.target;
    setInputText(textarea.value);
    
    // 重置高度以获取正确的scrollHeight
    textarea.style.height = 'auto';
    
    // 计算实际内容高度
    const scrollHeight = textarea.scrollHeight;
    const lineHeight = 16; // 行高
    const padding = 8; // 上下padding总和 (4px * 2)
    const maxLines = 6;
    const minHeight = lineHeight + padding; // 最小高度（1行 + padding）
    const maxHeight = maxLines * lineHeight + padding; // 最大高度（6行 + padding）
    
    // 计算新高度，确保在最小和最大值之间
    let newHeight = Math.max(minHeight, Math.min(maxHeight, scrollHeight));
    
    // 设置新高度
    textarea.style.height = `${newHeight}px`;
    
    // 如果内容超过最大高度，显示滚动条
    if (scrollHeight > maxHeight) {
      textarea.style.overflowY = 'auto';
    } else {
      textarea.style.overflowY = 'hidden';
    }
  };


  if (!isVisible) return null;

  return (
    <div className="chat-content" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 工具栏 - Windows 98 风格 */}
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          title="聊天设置"
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          title="选择文件发送"
        >
          📎 文件
        </button>
        
        {showSettings && (
          <span style={{
            fontSize: '11px',
            fontFamily: 'MS Sans Serif, sans-serif',
            color: '#000000',
            marginLeft: '8px'
          }}>
            设置面板开发中...
          </span>
        )}
      </div>

      {/* 消息区域 */}
      <div className="messages-container" style={{ flex: 1 }}>
          {messages.length === 0 ? (
            <div className="welcome-message">
              <div className="ai-message">
                <div className="message-avatar">🤖</div>
                <div className="message-bubble ai-bubble">
                  你好！我是AI助手，有什么可以帮助您的吗？
                </div>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={index} className={`message ${message.role === 'user' ? 'user-message' : 'ai-message'}`}>
                <div className="message-avatar">
                  {message.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className={`message-bubble ${message.role === 'user' ? 'user-bubble' : 'ai-bubble'}`}>
                  {message.content}
                  
                  {/* 显示文件附件 */}
                  {message.files && message.files.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      {message.files.map((file, fileIndex) => (
                        <div key={fileIndex} style={{
                          border: '1px solid #ccc',
                          borderRadius: '4px',
                          padding: '8px',
                          margin: '4px 0',
                          backgroundColor: message.role === 'user' ? '#f0f8ff' : '#f8f8f8',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px'
                        }}>
                          <div style={{ fontSize: '16px' }}>
                            {getFileIcon(file.type)}
                          </div>
                          <div style={{ flex: 1, fontSize: '10px' }}>
                            <div style={{ fontWeight: 'bold' }}>{file.name}</div>
                            <div style={{ color: '#666', marginTop: '2px' }}>
                              {file.type} • {(file.size / 1024).toFixed(1)}KB
                            </div>
                          </div>
                          
                          {/* 文件预览 */}
                          {file.type === 'images' && (
                            <img 
                              src={file.url} 
                              alt={file.name}
                              style={{ 
                                maxWidth: '100px', 
                                maxHeight: '100px', 
                                objectFit: 'cover',
                                border: '1px solid #ddd',
                                borderRadius: '2px'
                              }}
                              onClick={() => window.open(file.url, '_blank')}
                            />
                          )}
                          
                          {file.type === 'videos' && (
                            <video 
                              src={file.url}
                              controls
                              style={{ 
                                maxWidth: '150px', 
                                maxHeight: '100px'
                              }}
                            />
                          )}
                          
                          {file.type === 'audios' && (
                            <audio 
                              src={file.url}
                              controls
                              style={{ width: '150px' }}
                            />
                          )}
                          
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
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="ai-message">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble ai-bubble typing">
                <span className="typing-indicator">
                  <span></span><span></span><span></span>
                </span>
                正在思考...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 文件选择面板 */}
        {showFileSelector && (
          <div style={{
            backgroundColor: '#f0f0f0',
            border: '1px inset #c0c0c0',
            maxHeight: '200px',
            overflowY: 'auto',
            padding: '8px',
            margin: '4px 8px',
            fontSize: '11px',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}>
            <div style={{ 
              fontWeight: 'bold', 
              marginBottom: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>选择要发送的文件 ({boardFiles.length}个文件)</span>
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
                      minHeight: '40px',
                      transition: 'all 0.2s ease'
                    }}
                    title={`${file.name} (${(file.size / 1024).toFixed(1)}KB)`}
                    onMouseEnter={(e) => {
                      if (!selectedFiles.find(f => f.path === file.path)) {
                        e.target.style.backgroundColor = '#f5f5f5';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!selectedFiles.find(f => f.path === file.path)) {
                        e.target.style.backgroundColor = '#ffffff';
                      }
                    }}
                  >
                    {/* 文件图标 */}
                    <div style={{ fontSize: '20px', flexShrink: 0 }}>
                      {getFileIcon(file.type)}
                    </div>
                    
                    {/* 文件信息 */}
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
                    
                    {/* 选中状态指示 */}
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
        )}

        {/* 输入区域 */}
        <div className="input-container">
          {/* 已选文件提示 */}
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
                maxHeight: '96px', // 6行 * 16px
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
