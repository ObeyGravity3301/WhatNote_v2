import React from 'react';
import './Header.css';

function Header({ isConnected, onToggleConsole, onOpenMessageCenter, unreadCount = 0 }) {
  return (
    <header className="header">
      <div className="header-left">
        <h1 className="logo">WhatNote V2</h1>
      </div>
      
      <div className="header-center">
        <div className="connection-status">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
          <span className="status-text">
            {isConnected ? '已连接' : '未连接'}
          </span>
        </div>
      </div>
      
      <div className="header-right">
        <button 
          className="message-center-btn"
          onClick={onOpenMessageCenter}
          title="消息中心"
        >
          📬 消息
          {unreadCount > 0 && (
            <span className="message-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>
          )}
        </button>
        <button 
          className="console-toggle"
          onClick={onToggleConsole}
          title="切换控制台 (Ctrl+Shift+C)"
        >
          🖥️ 控制台
        </button>
      </div>
    </header>
  );
}

export default Header; 