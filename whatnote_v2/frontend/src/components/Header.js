import React from 'react';
import './Header.css';

function Header({ isConnected, onToggleConsole }) {
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