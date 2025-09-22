import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  // 聊天状态
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessageId, setStreamingMessageId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [conversationTitle, setConversationTitle] = useState('AI助手');
  
  // 工具栏状态
  const [showSettings, setShowSettings] = useState(false);
  const [showFileSelector, setShowFileSelector] = useState(false);
  const [boardFiles, setBoardFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // 滚动控制状态
  const [isAutoScrolling, setIsAutoScrolling] = useState(false);
  const scrollAnimationRef = useRef(null);
  
  // LLM API设置状态
  const [apiProvider, setApiProvider] = useState('openai'); // 默认OpenAI
  const [apiConfigs, setApiConfigs] = useState({
    openai: { apiKey: '', model: 'gpt-4', baseUrl: 'https://api.openai.com/v1' },
    anthropic: { apiKey: '', model: 'claude-3-5-sonnet-20241022', baseUrl: 'https://api.anthropic.com' },
    gemini: { apiKey: '', model: 'gemini-1.5-pro', baseUrl: 'https://generativelanguage.googleapis.com/v1' },
    qwen: { apiKey: '', model: 'qwen-plus', baseUrl: 'https://dashscope.aliyuncs.com/api/v1' }
  });
  
  // 引用
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);

  // 确保文本选择功能正常
  useEffect(() => {
    const enableTextSelection = () => {
      if (messagesContainerRef.current) {
        const container = messagesContainerRef.current;
        
        // 为消息容器添加事件监听器，阻止父级干扰
        const handleMouseEvent = (e) => {
          // 只在文本选择区域内阻止事件冒泡
          if (e.target.closest('.message-content, .ai-message-block, .user-bubble')) {
            e.stopPropagation();
          }
        };
        
        container.addEventListener('mousedown', handleMouseEvent, true);
        container.addEventListener('mouseup', handleMouseEvent, true);
        
        return () => {
          container.removeEventListener('mousedown', handleMouseEvent, true);
          container.removeEventListener('mouseup', handleMouseEvent, true);
        };
      }
    };
    
    // 延迟执行确保DOM已渲染
    const timer = setTimeout(enableTextSelection, 100);
    return () => clearTimeout(timer);
  }, [messages]);

  // 用户交互检测 - 打断平滑滚动
  useEffect(() => {
    const handleUserInteraction = (e) => {
      console.log('🖱️ User interaction detected:', e.type);
      // 停止自定义滚动动画
      if (isAutoScrolling) {
        console.log('🛑 Stopping scroll animation');
        setIsAutoScrolling(false);
        if (scrollAnimationRef.current) {
          cancelAnimationFrame(scrollAnimationRef.current);
          scrollAnimationRef.current = null;
        }
      }
    };

    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      container.addEventListener('wheel', handleUserInteraction, { passive: true });
      container.addEventListener('touchstart', handleUserInteraction, { passive: true });
      container.addEventListener('mousedown', handleUserInteraction);
      
      return () => {
        if (container) {
          container.removeEventListener('wheel', handleUserInteraction);
          container.removeEventListener('touchstart', handleUserInteraction);
          container.removeEventListener('mousedown', handleUserInteraction);
        }
      };
    }
  }, [isAutoScrolling]);

  // 手动滚动到底部（带动画效果）
  const scrollToBottom = (smooth = false) => {
    console.log('🔄 ScrollToBottom called, smooth:', smooth);
    
    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      console.log('📏 Container info:', {
        scrollTop: container.scrollTop,
        scrollHeight: container.scrollHeight,
        clientHeight: container.clientHeight
      });
      
      // 停止之前的动画
      if (scrollAnimationRef.current) {
        cancelAnimationFrame(scrollAnimationRef.current);
        scrollAnimationRef.current = null;
      }
      setIsAutoScrolling(false);
      
      if (smooth) {
        // 使用自定义可中断的平滑滚动
        setIsAutoScrolling(true);
        const startTop = container.scrollTop;
        const targetTop = container.scrollHeight - container.clientHeight;
        const distance = targetTop - startTop;
        const duration = Math.min(1000, Math.max(500, Math.abs(distance) / 3));
        
        let startTime = null;
        
        const animateScroll = (currentTime) => {
          // 检查动画是否被取消
          if (!scrollAnimationRef.current) {
            console.log('🛑 Animation cancelled');
            return;
          }
          
          if (startTime === null) startTime = currentTime;
          const timeElapsed = currentTime - startTime;
          const progress = Math.min(timeElapsed / duration, 1);
          
          // 使用easeOutCubic缓动函数
          const easeOutCubic = 1 - Math.pow(1 - progress, 3);
          container.scrollTop = startTop + (distance * easeOutCubic);
          
          if (progress < 1) {
            scrollAnimationRef.current = requestAnimationFrame(animateScroll);
          } else {
            setIsAutoScrolling(false);
            scrollAnimationRef.current = null;
            console.log('✅ Smooth scroll completed');
          }
        };
        
        scrollAnimationRef.current = requestAnimationFrame(animateScroll);
        console.log('✨ Custom smooth scroll initiated');
      } else {
        // 立即滚动到底部
        container.scrollTop = container.scrollHeight;
        console.log('⚡ Instant scroll completed');
      }
    } else {
      console.error('❌ Messages container not found');
    }
  };

  // 移除自动滚动，不再在消息更新时自动滚动到底部
  // useEffect(() => {
  //   scrollToBottom();
  // }, [messages]);

  // 初始化对话
  useEffect(() => {
    if (boardId && isVisible) {
      initializeConversation();
    }
  }, [boardId, isVisible]);

  // 加载API配置
  useEffect(() => {
    loadApiConfig();
  }, []);

  // 从后端加载API配置
  const loadApiConfig = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/llm/config');
      if (response.ok) {
        const config = await response.json();
        setApiProvider(config.current_provider || 'openai');
        
        // 转换后端配置格式到前端格式
        const frontendConfigs = {};
        Object.entries(config.providers || {}).forEach(([provider, providerConfig]) => {
          frontendConfigs[provider] = {
            apiKey: providerConfig.configured ? '***已配置***' : '',
            model: providerConfig.model || '',
            baseUrl: providerConfig.baseUrl || ''
          };
        });
        setApiConfigs(frontendConfigs);
        
        console.log('加载API配置成功');
      } else {
        console.error('加载API配置失败');
      }
    } catch (error) {
      console.error('加载API配置失败:', error);
    }
  };

  // 保存API配置到后端
  const saveApiConfig = async (provider, configs) => {
    try {
      // 更新服务商配置
      const response = await fetch(`http://localhost:8081/api/llm/config/${provider}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(configs[provider])
      });
      
      if (response.ok) {
        console.log(`保存${provider}配置成功`);
      } else {
        console.error(`保存${provider}配置失败`);
      }
      
      // 设置当前服务商
      const providerResponse = await fetch(`http://localhost:8081/api/llm/provider/${provider}`, {
        method: 'POST'
      });
      
      if (providerResponse.ok) {
        console.log(`设置当前服务商成功: ${provider}`);
      } else {
        console.error(`设置当前服务商失败: ${provider}`);
      }
    } catch (error) {
      console.error('保存API配置失败:', error);
    }
  };

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

  // 点击外部关闭设置面板
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showSettings) {
        // 检查点击是否在设置面板内部
        const settingsPanel = document.querySelector('.settings-panel');
        const settingsButton = document.querySelector('.settings-button');
        
        // 如果点击的不是设置面板内部和设置按钮，则关闭面板
        if (settingsPanel && 
            !settingsPanel.contains(event.target) && 
            settingsButton && 
            !settingsButton.contains(event.target)) {
          setShowSettings(false);
        }
      }
    };
    
    if (showSettings) {
      // 使用 capture 阶段确保事件能被正确捕获
      document.addEventListener('mousedown', handleClickOutside, true);
      return () => document.removeEventListener('mousedown', handleClickOutside, true);
    }
  }, [showSettings]);

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
      id: Date.now(),
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

      // 创建AI消息占位符，用于流式更新
      const aiMessageId = Date.now();
      const aiMessage = {
        id: aiMessageId,
        role: 'assistant',
        content: ''
      };

      // 立即显示空的AI消息
      setMessages(prev => [...prev, aiMessage]);

      // 开始流式输出，停止显示"正在思考..."
      setIsLoading(false);
      setIsStreaming(true);
      setStreamingMessageId(aiMessageId);

      // 调用流式AI回复
      await generateStreamingAIResponse(userMessage.content, aiMessageId);

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

  // 流式AI回复函数
  const generateStreamingAIResponse = async (userInput, aiMessageId) => {
    try {
      // 准备消息历史（包括当前对话上下文）
      const conversationMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        files: msg.files // 包含文件信息
      }));
      
      // 添加当前用户消息
      const currentUserMessage = {
        role: 'user',
        content: userInput
      };
      
      // 如果当前消息包含文件，添加文件信息
      const currentMessage = messages[messages.length - 1];
      if (currentMessage && currentMessage.files && currentMessage.files.length > 0) {
        currentUserMessage.files = currentMessage.files;
        console.log(`添加文件信息到当前消息: ${currentMessage.files.length} 个文件`);
      }
      
      conversationMessages.push(currentUserMessage);
      
      // 调试信息：检查发送的数据
      console.log('发送给LLM的消息:', JSON.stringify(conversationMessages, null, 2));
      
      // 特别检查文件信息
      conversationMessages.forEach((msg, index) => {
        if (msg.files && msg.files.length > 0) {
          console.log(`消息 ${index} 包含 ${msg.files.length} 个文件:`, msg.files);
        }
      });
      
      // 调用流式API
      const response = await fetch('http://localhost:8081/api/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: conversationMessages
        })
      });
      
      if (!response.ok) {
        throw new Error(`API调用失败: ${response.status}`);
      }
      
      // 处理流式响应
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
              // 流式响应完成，停止流式状态
              setIsStreaming(false);
              setStreamingMessageId(null);
              
              // 流式响应完成，保存完整消息到后端
              const finalMessage = {
                role: 'assistant',
                content: fullResponse
              };
              
              await fetch(`http://localhost:8081/api/boards/${boardId}/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify(finalMessage)
              });
              
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullResponse += parsed.content;
                
                // 实时更新消息内容
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
      // 停止流式状态
      setIsStreaming(false);
      setStreamingMessageId(null);
      
      // 更新消息为错误信息
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: `❌ API调用失败: ${error.message}\n\n请检查:\n1. API配置是否正确\n2. 网络连接是否正常\n3. API密钥是否有效` }
          : msg
      ));
    }
  };

  // 调用真正的LLM API（保留用于兼容性）
  const generateAIResponse = async (userInput) => {
    try {
      // 准备消息历史（包括当前对话上下文）
      const conversationMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      // 添加当前用户消息
      conversationMessages.push({
        role: 'user',
        content: userInput
      });
      
      // 调用流式API
      const response = await fetch('http://localhost:8081/api/llm/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: conversationMessages
        })
      });
      
      if (!response.ok) {
        throw new Error(`API调用失败: ${response.status}`);
      }
      
      // 处理流式响应
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
              return fullResponse;
            }
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullResponse += parsed.content;
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
      
      return fullResponse || '抱歉，API返回了空响应';
      
    } catch (error) {
      console.error('LLM API调用失败:', error);
      return `❌ API调用失败: ${error.message}\n\n请检查:\n1. API配置是否正确\n2. 网络连接是否正常\n3. API密钥是否有效`;
    }
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

  // 获取服务商名称
  const getProviderName = (provider) => {
    const names = {
      'openai': 'OpenAI',
      'anthropic': 'Anthropic',
      'gemini': 'Google Gemini',
      'qwen': '阿里云通义千问'
    };
    return names[provider] || provider;
  };

  // 获取模型选项
  const getModelOptions = (provider) => {
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
          className="settings-button"
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
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
            
            {/* API服务商选择 */}
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
            
            {/* API配置表单 */}
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
                  
                  // 只有在用户实际输入内容时才保存（避免保存占位符）
                  if (e.target.value && e.target.value !== '***已配置***') {
                    saveApiConfig(apiProvider, newConfigs);
                  }
                }}
                onFocus={(e) => {
                  // 清空占位符，让用户输入真实密钥
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
            
            {/* 模型选择 */}
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
            
            {/* API端点 */}
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
            
            {/* 状态显示 */}
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

      {/* 消息区域 */}
      <div className="messages-container" ref={messagesContainerRef} style={{ flex: 1 }}>
          {messages.length === 0 ? (
            <div className="welcome-message">
              <div className="ai-message-block">
                <div className="message-header">
                  <div className="message-avatar">🤖</div>
                  <div className="message-sender">AI助手</div>
                </div>
                <div className="message-content">
                  你好！我是AI助手，有什么可以帮助您的吗？
                </div>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              message.role === 'user' ? (
                // 用户消息 - 保持原有气泡样式
                <div key={message.id || index} className="message user-message">
                  <div className="message-avatar">👤</div>
                  <div className="message-bubble user-bubble">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        p: ({ children }) => <p style={{ margin: '4px 0', fontSize: '11px', lineHeight: '1.4' }}>{children}</p>,
                        code: ({ children, className, node }) => {
                          // 检查是否是代码块中的代码（有className）还是行内代码
                          const isCodeBlock = className && className.includes('language-');
                          if (isCodeBlock) {
                            // 代码块中的代码，不需要边框和背景，由pre标签统一处理
                            return <code style={{ 
                              fontSize: '10px',
                              fontFamily: 'Courier New, monospace'
                            }}>{children}</code>;
                          } else {
                            // 行内代码，保持原有样式但移除边框
                            return <code style={{ 
                              backgroundColor: '#f0f0f0', 
                              padding: '1px 2px', 
                              fontSize: '10px',
                              fontFamily: 'Courier New, monospace'
                            }}>{children}</code>;
                          }
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
                            borderRadius: '0px' // Windows 98风格，无圆角
                          }}>{children}</pre>
                        )
                      }}
                    >
                      {normalizeLatexDelimiters(message.content)}
                    </ReactMarkdown>
                    
                    {/* 显示文件 - 图片直接在气泡中显示，其他文件作为附件 */}
                    {message.files && message.files.length > 0 && (
                      <div style={{ marginTop: '8px' }}>
                        {message.files.map((file, fileIndex) => {
                          if (file.type === 'images') {
                            // 图片直接在气泡中显示
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
                                      // 尝试打开对应的桌面窗口
                                      onOpenWindow(file.name);
                                    } else {
                                      // 回退到打开新窗口查看大图
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
                          } else {
                            // 其他文件类型作为附件显示
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
                                <div style={{ fontSize: '16px' }}>
                                  {getFileIcon(file.type)}
                                </div>
                                <div style={{ flex: 1, fontSize: '10px' }}>
                                  <div style={{ fontWeight: 'bold' }}>{file.name}</div>
                                  <div style={{ color: '#666', marginTop: '2px' }}>
                                    {file.type} • {(file.size / 1024).toFixed(1)}KB
                                  </div>
                                </div>
                                
                                {/* 视频和音频预览 */}
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
                            );
                          }
                        })}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                // AI消息 - 使用新的居中直接文本样式
                <div key={message.id || index} className="ai-message-block">
                  <div className="message-header">
                    <div className="message-avatar">🤖</div>
                    <div className="message-sender">AI助手</div>
                  </div>
                  <div className="message-content">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      // 自定义组件样式，保持Windows 98风格
                      p: ({ children }) => <p style={{ margin: '4px 0', fontSize: '11px', lineHeight: '1.4' }}>{children}</p>,
                      h1: ({ children }) => <h1 style={{ fontSize: '14px', fontWeight: 'bold', margin: '8px 0 4px 0' }}>{children}</h1>,
                      h2: ({ children }) => <h2 style={{ fontSize: '13px', fontWeight: 'bold', margin: '6px 0 3px 0' }}>{children}</h2>,
                      h3: ({ children }) => <h3 style={{ fontSize: '12px', fontWeight: 'bold', margin: '4px 0 2px 0' }}>{children}</h3>,
                      strong: ({ children }) => <strong style={{ fontWeight: 'bold' }}>{children}</strong>,
                      em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
                      code: ({ children, className, node }) => {
                        // 检查是否是代码块中的代码（有className）还是行内代码
                        const isCodeBlock = className && className.includes('language-');
                        if (isCodeBlock) {
                          // 代码块中的代码，不需要边框和背景，由pre标签统一处理
                          return <code style={{ 
                            fontSize: '10px',
                            fontFamily: 'Courier New, monospace'
                          }}>{children}</code>;
                        } else {
                          // 行内代码，保持原有样式但移除边框
                          return <code style={{ 
                            backgroundColor: '#f0f0f0', 
                            padding: '1px 2px', 
                            fontSize: '10px',
                            fontFamily: 'Courier New, monospace'
                          }}>{children}</code>;
                        }
                      },
                      pre: ({ children, className, node }) => {
                        return <pre style={{ 
                          backgroundColor: '#f0f0f0', 
                          padding: '8px', 
                          fontSize: '10px',
                          fontFamily: 'Courier New, monospace',
                          border: '1px solid #ccc',
                          overflow: 'auto',
                          margin: '4px 0',
                          borderRadius: '0px' // Windows 98风格，无圆角
                        }}>{children}</pre>;
                      },
                      ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: '16px' }}>{children}</ol>,
                      li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
                      blockquote: ({ children }) => <blockquote style={{ 
                        borderLeft: '3px solid #ccc', 
                        margin: '4px 0', 
                        paddingLeft: '8px',
                        fontStyle: 'italic'
                      }}>{children}</blockquote>,
                      table: ({ children }) => <table style={{ 
                        borderCollapse: 'collapse', 
                        margin: '4px 0',
                        fontSize: '10px'
                      }}>{children}</table>,
                      th: ({ children }) => <th style={{ 
                        border: '1px solid #ccc', 
                        padding: '2px 4px',
                        backgroundColor: '#f0f0f0',
                        fontWeight: 'bold'
                      }}>{children}</th>,
                      td: ({ children }) => <td style={{ 
                        border: '1px solid #ccc', 
                        padding: '2px 4px'
                      }}>{children}</td>
                    }}
                  >
                    {normalizeLatexDelimiters(message.content)}
                  </ReactMarkdown>
                  
                  {/* 流式输出指示器 */}
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
              )
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

        {/* 文件选择面板 */}
        {showFileSelector && (
          <div style={{
            backgroundColor: '#f0f0f0',
            border: '1px inset #c0c0c0',
            maxHeight: '200px',
            margin: '4px 8px',
            fontSize: '11px',
            fontFamily: 'MS Sans Serif, sans-serif',
            position: 'relative'
          }}>
            {/* 固定的标题栏和关闭按钮 */}
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
            {/* 可滚动的文件列表 */}
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
