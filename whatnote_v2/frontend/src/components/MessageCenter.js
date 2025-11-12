import React, { useState, useEffect } from 'react';
import './MessageCenter.css';

const MessageCenter = ({ isOpen, onClose, messages, onClearAll }) => {
  const [selectedMessage, setSelectedMessage] = useState(null);

  if (!isOpen) return null;

  return (
    <div className="message-center-overlay">
      <div className="message-center-window">
        {/* 标题栏 */}
        <div className="message-center-titlebar">
          <span className="message-center-title">📬 消息中心</span>
          <button
            className="message-center-close-btn"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        {/* 内容区 */}
        <div className="message-center-content">
          {messages.length === 0 ? (
            <div className="message-center-empty">
              <span className="message-center-empty-icon"></span>
              <div style={{ color: '#808080' }}>暂无消息</div>
            </div>
          ) : (
            <>
              {/* 消息列表 */}
              <div className="message-center-list">
                {messages.map((msg, index) => (
                  <div
                    key={msg.id || index}
                    className={`message-center-item ${selectedMessage === index ? 'selected' : ''} ${msg.type || 'info'}`}
                    onClick={() => setSelectedMessage(selectedMessage === index ? null : index)}
                  >
                    <div className="message-center-item-header">
                      <span className="message-center-item-icon">
                        {msg.type === 'success' && '✓'}
                        {msg.type === 'error' && '✗'}
                        {msg.type === 'warning' && '⚠'}
                        {msg.type === 'info' && 'ℹ'}
                      </span>
                      <span className="message-center-item-title">{msg.title}</span>
                      <span className="message-center-item-time">{msg.time}</span>
                    </div>
                    
                    {selectedMessage === index && msg.details && (
                      <div className="message-center-item-details">
                        {msg.details}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* 底部按钮 */}
              <div className="message-center-footer">
                <button
                  className="message-center-btn"
                  onClick={onClearAll}
                >
                  清空所有消息
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageCenter;

