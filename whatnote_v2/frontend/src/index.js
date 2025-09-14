import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
// 移除 StrictMode 以避免 React 18 开发模式下 useEffect 双执行导致的重复 WebSocket 连接
root.render(
  <App />
);