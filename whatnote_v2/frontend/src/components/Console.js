import React, { useState, useEffect, useRef } from 'react';
import './Console.css';

function Console({ onClose }) {
  const [logs, setLogs] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  useEffect(() => {
    // 连接WebSocket（与后端 /ws/logs 对齐）
    const ws = new WebSocket('ws://localhost:8081/ws/logs');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket连接已建立');
      setIsConnected(true);
      addLog('🟢 控制台已连接', 'info');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        addLog(`📨 ${data.message || JSON.stringify(data)}`, 'message');
      } catch (error) {
        addLog(`📨 ${event.data}`, 'message');
      }
    };

    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      setIsConnected(false);
      addLog('🔴 控制台连接已断开', 'error');
    };

    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      addLog('❌ WebSocket连接错误', 'error');
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    const newLog = {
      id: Date.now(),
      timestamp,
      message,
      type
    };
    setLogs(prev => [...prev, newLog]);
  };

  // 暴露到全局，便于其他模块快速调试输出
  useEffect(() => {
    window.__whatnoteLog = (msg, type = 'info') => addLog(String(msg), type);
  }, []);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const handleSendMessage = () => {
    if (inputValue.trim() && wsRef.current && isConnected) {
      const message = {
        type: 'console_message',
        content: inputValue.trim()
      };
      wsRef.current.send(JSON.stringify(message));
      addLog(`💬 ${inputValue.trim()}`, 'user');
      setInputValue('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  };

  const clearLogs = () => {
    setLogs([]);
  };

  return (
    <div className="console">
      <div className="console-header">
        <h3>控制台</h3>
        <div className="console-controls">
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '🟢 已连接' : '🔴 未连接'}
          </span>
          <button onClick={clearLogs} className="clear-btn">清空</button>
          <button onClick={onClose} className="close-btn">关闭</button>
        </div>
      </div>
      
      <div className="console-logs">
        {logs.map(log => (
          <div key={log.id} className={`log-entry ${log.type}`}>
            <span className="log-timestamp">[{log.timestamp}]</span>
            <span className="log-message">{log.message}</span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
      
      <div className="console-input">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入消息..."
          disabled={!isConnected}
        />
        <button 
          onClick={handleSendMessage}
          disabled={!isConnected || !inputValue.trim()}
        >
          发送
        </button>
      </div>
    </div>
  );
}

export default Console; 