import React, { useState, useEffect, useRef } from 'react';
import './Console.css';

const Console = ({ onClose, initialPath }) => {
  const [output, setOutput] = useState([]);
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [connected, setConnected] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [position, setPosition] = useState({ x: window.innerWidth - 670, y: window.innerHeight - 510 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [currentPath, setCurrentPath] = useState('/');
  
  const outputRef = useRef(null);
  const inputRef = useRef(null);
  const windowRef = useRef(null);
  const wsRef = useRef(null);
  const hasInitialized = useRef(false);

  // WebSocket 连接
  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8081/ws/console');
    
    websocket.onopen = () => {
      console.log('控制台 WebSocket 已连接');
      setConnected(true);
    };

    websocket.onmessage = (event) => {
      const response = JSON.parse(event.data);
      handleResponse(response);
    };
    
    websocket.onerror = (error) => {
      console.error('控制台 WebSocket 错误:', error);
      addOutput('错误: 无法连接到后端服务', 'error');
    };

    websocket.onclose = () => {
      console.log('控制台 WebSocket 已断开');
      setConnected(false);
      addOutput('连接已断开', 'error');
    };

    wsRef.current = websocket;

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close();
      }
      wsRef.current = null;
    };
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  // 处理初始路径（自动 cd）
  useEffect(() => {
    console.log('[Console] useEffect 触发:', {
      initialPath,
      connected,
      hasInitialized: hasInitialized.current
    });
    
    if (initialPath && connected && !hasInitialized.current) {
      hasInitialized.current = true;
      
      // 延迟执行，确保 WebSocket 已完全就绪
      setTimeout(() => {
        console.log('[Console] 自动定位到路径:', initialPath);
        sendCommand(`cd "${initialPath}"`);
      }, 500);
    }
  }, [initialPath, connected]);

  // 拖动逻辑
  const handleMouseDown = (e) => {
    if (e.target.closest('.console-titlebar') && !e.target.closest('button')) {
      setIsDragging(true);
      setDragOffset({
        x: e.clientX - position.x,
        y: e.clientY - position.y
      });
    }
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  // 处理后端响应
  const handleResponse = (response) => {
    const { type, content, data, action } = response;
    
    console.log('[Console] 收到响应:', { type, content: content?.substring(0, 100), action });
    
    // 先处理前端同步 action
    if (action) {
      console.log('[Console] 执行前端同步操作:', action);
      switch (action.type) {
        case 'switch_board':
          // 切换到指定展板
          window.dispatchEvent(new CustomEvent('switchBoard', {
            detail: {
              courseId: action.course_id,
              boardId: action.board_id
            }
          }));
          break;
        case 'switch_course':
          // 切换到指定课程
          window.dispatchEvent(new CustomEvent('switchCourse', {
            detail: {
              courseId: action.course_id
            }
          }));
          break;
        case 'refresh_board':
          // 刷新当前展板（重新加载窗口）
          window.dispatchEvent(new CustomEvent('refreshBoard'));
          console.log('[Console] 已发送刷新展板事件');
          break;
        case 'refresh_courses':
          // 刷新课程列表
          window.dispatchEvent(new CustomEvent('refreshCourses'));
          console.log('[Console] 已发送刷新课程列表事件');
          break;
        case 'refresh_boards':
          // 刷新展板列表
          window.dispatchEvent(new CustomEvent('refreshBoards', {
            detail: {
              courseId: action.course_id
            }
          }));
          console.log('[Console] 已发送刷新展板列表事件');
          break;
        case 'refresh_calendar':
          // 刷新日历数据
          window.dispatchEvent(new CustomEvent('refreshCalendar'));
          console.log('[Console] 已发送刷新日历事件');
          break;
        default:
          console.warn('[Console] 未知的 action 类型:', action.type);
      }
    }
    
    // 先提取路径信息（在添加输出之前）
    if (content && content.includes('当前路径:')) {
      const match = content.match(/当前路径:\s*(.+)/);
      console.log('[Console] 路径匹配结果:', match);
      if (match) {
        const newPath = match[1].trim();
        console.log('[Console] 更新路径:', currentPath, '->', newPath);
        setCurrentPath(newPath);
        // pwd 命令的输出不显示在控制台中
        return;
      }
    }
    
    switch (type) {
      case 'welcome':
        addOutput(content, 'info');
        addOutput('', 'empty');
        break;
        
      case 'text':
        addOutput(content, type);
        break;
        
      case 'success':
        addOutput(content, type);
        // 如果是路径相关的成功消息，请求更新路径
        if (content.includes('已进入') || content.includes('已返回')) {
          console.log('[Console] 检测到路径变化，准备发送 pwd 命令');
          console.log('[Console] WebSocket 状态:', wsRef.current?.readyState);
          // 发送 pwd 命令更新路径
          setTimeout(() => {
            console.log('[Console] 正在发送 pwd 命令');
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send('pwd');
              console.log('[Console] pwd 命令已发送');
            } else {
              console.log('[Console] WebSocket 未连接，无法发送 pwd');
            }
          }, 100);
        }
        break;
        
      case 'error':
        addOutput(content, 'error');
        break;
        
      case 'clear':
        setOutput([]);
        break;
        
      case 'exit':
        addOutput('再见!', 'info');
        setTimeout(() => onClose(), 1000);
        break;
        
      case 'empty':
        // 空命令,不输出
        break;
        
      default:
        addOutput(content || JSON.stringify(response), 'text');
    }
  };

  // 添加输出
  const addOutput = (text, type = 'text') => {
    setOutput(prev => [...prev, { text, type, timestamp: Date.now() }]);
  };

  // 发送命令
  const sendCommand = (cmd) => {
    if (!cmd.trim()) return;
    
    // 显示输入的命令（带当前路径）
    const prompt = currentPath === '/' ? 'C:\\WHATNOTE>' : `${currentPath}>`;
    addOutput(`${prompt} ${cmd}`, 'command');
    
    // 发送到后端
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(cmd);
    } else {
      addOutput('错误: 未连接到服务器', 'error');
    }
    
    // 添加到历史
    setHistory(prev => [...prev, cmd]);
    setHistoryIndex(-1);
  };

  // 处理输入提交
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      sendCommand(input);
      setInput('');
    }
  };

  // 处理键盘事件（历史记录导航）
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const newIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setInput(history[newIndex]);
    }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex !== -1) {
        const newIndex = historyIndex + 1;
        if (newIndex >= history.length) {
          setHistoryIndex(-1);
          setInput('');
        } else {
          setHistoryIndex(newIndex);
          setInput(history[newIndex]);
        }
      }
    } else if (e.key === 'Tab') {
      e.preventDefault();
      // TODO: 命令补全
    }
  };

  // 渲染输出行
  const renderOutput = () => {
    return output.map((line, index) => (
      <div key={index} className={`console-line console-line-${line.type}`}>
        {line.text}
      </div>
    ));
  };

  return (
    <div
      ref={windowRef}
      className={`console-window ${isMinimized ? 'minimized' : ''}`}
      style={{ 
        left: `${position.x}px`, 
        top: `${position.y}px`,
        cursor: isDragging ? 'move' : 'default'
      }}
      onMouseDown={handleMouseDown}
    >
      {/* 标题栏 */}
      <div className="console-titlebar">
        <div className="console-titlebar-text">
          <span className="win98-icon win98-icon-console" style={{marginRight: '6px'}}></span>
          <span>WhatNote Tool Console</span>
        </div>
        <div className="console-titlebar-buttons">
          <button 
            className="console-btn-minimize" 
            onClick={(e) => { 
              e.stopPropagation(); 
              setIsMinimized(!isMinimized); 
            }}
          >
            _
          </button>
          <button 
            className="console-btn-close" 
            onClick={(e) => { 
              e.stopPropagation(); 
              onClose(); 
            }}
          >
            ×
          </button>
        </div>
      </div>
      
      {/* 控制台内容 */}
      {!isMinimized && (
        <div className="console-content">
          {/* 输出区域 */}
          <div className="console-output" ref={outputRef}>
            {renderOutput()}
      </div>
      
          {/* 输入区域 */}
          <form className="console-input-form" onSubmit={handleSubmit}>
            <span className="console-prompt">
              {currentPath === '/' ? 'C:\\WHATNOTE>' : `${currentPath}>`}
            </span>
        <input
              ref={inputRef}
          type="text"
              className="console-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={connected ? "输入命令..." : "连接中..."}
              disabled={!connected}
              autoFocus
        />
          </form>

          {/* 状态栏 */}
          <div className="console-statusbar">
            <span className={`console-status ${connected ? 'connected' : 'disconnected'}`}>
              {connected ? '已连接' : '未连接'}
            </span>
            <span className="console-info">
              历史: {history.length} | 使用方向键浏览历史
            </span>
          </div>
      </div>
      )}
    </div>
  );
};

export default Console; 
