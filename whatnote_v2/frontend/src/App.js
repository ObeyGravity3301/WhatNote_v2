import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// 导入组件
import CourseExplorer from './components/CourseExplorer';
import BoardCanvas from './components/BoardCanvas';
import Console from './components/Console';
import Header from './components/Header';
import Sidebar from './components/Sidebar';

function App() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [showConsole, setShowConsole] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  // 开始菜单相关状态
  const [showStartMenu, setShowStartMenu] = useState(false);
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [showCreateBoard, setShowCreateBoard] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDesc, setNewCourseDesc] = useState('');
  const [newBoardName, setNewBoardName] = useState('');
  const [courseBoards, setCourseBoards] = useState({});
  
  // 回收站相关状态
  const [showTrash, setShowTrash] = useState(false);
  const [trashItems, setTrashItems] = useState([]);
  const [trashSize, setTrashSize] = useState(0);
  
  // 窗口管理状态
  const [currentBoardWindows, setCurrentBoardWindows] = useState([]);
  const [minimizedWindows, setMinimizedWindows] = useState(new Set());
  const [hiddenWindows, setHiddenWindows] = useState(new Set());
  const [focusedWindowId, setFocusedWindowId] = useState(null);

  // WebSocket连接
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8081/ws/logs');
    
    ws.onopen = () => {
      console.log('WebSocket连接已建立');
      setIsConnected(true);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('收到消息:', data);
    };
    
    ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  // 加载课程列表
  useEffect(() => {
    fetchCourses();
  }, []);

  // 获取课程的展板列表
  useEffect(() => {
    const fetchCourseBoards = async () => {
      if (!courses || courses.length === 0) return;
      
      const boardsData = {};
      for (const course of courses) {
        try {
          const response = await fetch(`http://localhost:8081/api/courses/${course.id}/boards`);
          if (response.ok) {
            const data = await response.json();
            boardsData[course.id] = data.boards || [];
          }
        } catch (error) {
          console.error(`获取课程 ${course.id} 的展板失败:`, error);
          boardsData[course.id] = [];
        }
      }
      setCourseBoards(boardsData);
    };

    fetchCourseBoards();
  }, [courses]);

  const fetchCourses = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/courses');
      const data = await response.json();
      setCourses(data.courses || []);
    } catch (error) {
      console.error('获取课程失败:', error);
    }
  };

  const handleCreateCourse = async (name, description) => {
    try {
      const response = await fetch(`http://localhost:8081/api/courses?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        await fetchCourses();
      }
    } catch (error) {
      console.error('创建课程失败:', error);
    }
  };

  const handleCreateBoard = async (courseId, boardName) => {
    try {
      const response = await fetch(`http://localhost:8081/api/courses/${courseId}/boards?board_name=${encodeURIComponent(boardName)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        await fetchCourses();
      }
    } catch (error) {
      console.error('创建展板失败:', error);
    }
  };

  // 开始菜单处理函数
  const handleStartMenuCreateCourse = async () => {
    if (newCourseName.trim()) {
      await handleCreateCourse(newCourseName.trim(), newCourseDesc.trim());
      setNewCourseName('');
      setNewCourseDesc('');
      setShowCreateCourse(false);
    }
  };

  const handleStartMenuCreateBoard = async () => {
    if (newBoardName.trim() && selectedCourse) {
      await handleCreateBoard(selectedCourse.id, newBoardName.trim());
      setNewBoardName('');
      setShowCreateBoard(false);
    }
  };

  // 窗口管理函数
  const handleWindowMinimize = (windowId) => {
    setMinimizedWindows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(windowId)) {
        newSet.delete(windowId); // 恢复窗口
        setFocusedWindowId(windowId); // 恢复后设为焦点
      } else {
        newSet.add(windowId); // 最小化窗口
        if (focusedWindowId === windowId) {
          setFocusedWindowId(null); // 清除焦点
        }
      }
      return newSet;
    });
  };

  const handleWindowFocus = (windowId) => {
    setFocusedWindowId(windowId);
    // 如果窗口是最小化的，先恢复它
    if (minimizedWindows.has(windowId)) {
      handleWindowMinimize(windowId);
    }
  };

  const handleWindowClose = (windowId) => {
    console.log('App: 处理窗口关闭（隐藏）:', windowId);
    // 添加到隐藏列表
    setHiddenWindows(prev => {
      const newSet = new Set(prev);
      newSet.add(windowId);
      return newSet;
    });
    // 从最小化列表中移除
    setMinimizedWindows(prev => {
      const newSet = new Set(prev);
      newSet.delete(windowId);
      return newSet;
    });
    // 如果关闭的是当前聚焦的窗口，清除焦点
    if (focusedWindowId === windowId) {
      setFocusedWindowId(null);
    }
  };

  const handleWindowShow = (windowId) => {
    console.log('App: 处理窗口显示（恢复）:', windowId);
    // 从隐藏列表中移除
    setHiddenWindows(prev => {
      const newSet = new Set(prev);
      newSet.delete(windowId);
      return newSet;
    });
  };

  const handleWindowHide = (windowId) => {
    console.log('App: 处理窗口隐藏（设置隐藏状态）:', windowId);
    // 添加到隐藏列表
    setHiddenWindows(prev => {
      const newSet = new Set(prev);
      newSet.add(windowId);
      return newSet;
    });
  };

  const handleBatchWindowHide = (windowIds) => {
    console.log('App: 批量设置隐藏状态:', windowIds);
    setHiddenWindows(prev => {
      const newSet = new Set(prev);
      windowIds.forEach(id => newSet.add(id));
      return newSet;
    });
  };

  const handleClearHiddenWindows = () => {
    console.log('App: 清空隐藏窗口状态');
    setHiddenWindows(new Set());
  };

  // 回收站处理函数
  const loadTrashItems = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/trash');
      if (response.ok) {
        const data = await response.json();
        setTrashItems(data.items || []);
      }
    } catch (error) {
      console.error('加载回收站失败:', error);
    }
  };

  const loadTrashSize = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/trash/size');
      if (response.ok) {
        const data = await response.json();
        setTrashSize(data.size || 0);
      }
    } catch (error) {
      console.error('获取回收站大小失败:', error);
    }
  };

  const handleRestoreFromTrash = async (trashId) => {
    try {
      const response = await fetch(`http://localhost:8081/api/trash/${trashId}/restore`, {
        method: 'POST'
      });
      if (response.ok) {
        await loadTrashItems();
        await loadTrashSize();
        alert('文件恢复成功！');
      } else {
        alert('文件恢复失败！');
      }
    } catch (error) {
      console.error('恢复文件失败:', error);
      alert('文件恢复失败！');
    }
  };

  const handlePermanentDelete = async (trashId) => {
    if (window.confirm('确定要永久删除这个文件吗？此操作无法撤销！')) {
      try {
        const response = await fetch(`http://localhost:8081/api/trash/${trashId}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          await loadTrashItems();
          await loadTrashSize();
          alert('文件已永久删除！');
        } else {
          alert('删除失败！');
        }
      } catch (error) {
        console.error('永久删除失败:', error);
        alert('删除失败！');
      }
    }
  };

  const handleEmptyTrash = async () => {
    if (window.confirm('确定要清空回收站吗？此操作将永久删除所有文件，无法撤销！')) {
      try {
        const response = await fetch('http://localhost:8081/api/trash', {
          method: 'DELETE'
        });
        if (response.ok) {
          await loadTrashItems();
          await loadTrashSize();
          alert('回收站已清空！');
        } else {
          alert('清空回收站失败！');
        }
      } catch (error) {
        console.error('清空回收站失败:', error);
        alert('清空回收站失败！');
      }
    }
  };

  // 当显示回收站时加载数据
  useEffect(() => {
    if (showTrash) {
      loadTrashItems();
      loadTrashSize();
    }
  }, [showTrash]);

  const handleWindowDelete = (windowId) => {
    // 从最小化列表中移除
    setMinimizedWindows(prev => {
      const newSet = new Set(prev);
      newSet.delete(windowId);
      return newSet;
    });
    // 从隐藏列表中移除
    setHiddenWindows(prev => {
      const newSet = new Set(prev);
      newSet.delete(windowId);
      return newSet;
    });
    // 如果删除的是当前聚焦的窗口，清除焦点
    if (focusedWindowId === windowId) {
      setFocusedWindowId(null);
    }
    // 从当前窗口列表中移除
    setCurrentBoardWindows(prev => prev.filter(w => w.id !== windowId));
  };

  // 监听选中展板变化，重置窗口状态（不清空隐藏状态，避免闪烁）
  useEffect(() => {
    if (selectedBoard) {
      setCurrentBoardWindows([]);
      setMinimizedWindows(new Set());
      setFocusedWindowId(null);
      // 不在这里清空隐藏状态，让BoardCanvas在适当时机处理
    }
  }, [selectedBoard]);

  // 快捷键处理
  useEffect(() => {
    const handleKeyPress = (event) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'C') {
        setShowConsole(!showConsole);
      }
    };
    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [showConsole]);

  // 点击外部关闭开始菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showStartMenu && !event.target.closest('.start-menu') && !event.target.closest('.start-button')) {
        setShowStartMenu(false);
      }
    };

    if (showStartMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showStartMenu]);

  return (
    <div className="app">
      <Header 
        isConnected={isConnected} 
        onToggleConsole={() => setShowConsole(!showConsole)} 
      />
      <div className="main-content">
                {/* 侧边栏已移植到开始菜单，暂时隐藏 */}
        {/* <Sidebar 
          courses={courses}
          selectedCourse={selectedCourse}
          selectedBoard={selectedBoard}
          onSelectCourse={setSelectedCourse}
          onSelectBoard={setSelectedBoard}
          onCreateCourse={handleCreateCourse}
          onCreateBoard={handleCreateBoard}
        /> */}
        <div className="content-area">
          {selectedBoard ? (
            <BoardCanvas 
              boardId={selectedBoard.id} 
              boardName={selectedBoard.name}
              onWindowsChange={setCurrentBoardWindows}
              minimizedWindows={minimizedWindows}
              hiddenWindows={hiddenWindows}
              focusedWindowId={focusedWindowId}
              onWindowMinimize={handleWindowMinimize}
              onWindowFocus={handleWindowFocus}
              onWindowClose={handleWindowClose}
              onWindowShow={handleWindowShow}
              onWindowHide={handleWindowHide}
              onBatchWindowHide={handleBatchWindowHide}
              onClearHiddenWindows={handleClearHiddenWindows}
              onWindowDelete={handleWindowDelete}
            />
          ) : (
            <div className="welcome-screen">
              <h2>欢迎使用 WhatNote V2</h2>
              <p>请选择一个展板开始工作</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Win98风格任务栏 - 始终显示 */}
      <div className="taskbar">
        <div className="taskbar-content">
          {/* Win98开始按钮 */}
          <button 
            className="start-button"
            onClick={() => setShowStartMenu(!showStartMenu)}
          >
            <span className="start-icon">🏠</span>
            <span className="start-text">开始</span>
          </button>
          
          <div className="taskbar-separator"></div>
          
          {selectedBoard ? (
            <>
              {currentBoardWindows.filter(window => !hiddenWindows.has(window.id)).length > 0 ? (
                <>
                  <span className="taskbar-label">窗口:</span>
                  {currentBoardWindows.filter(window => !hiddenWindows.has(window.id)).map(window => {
                    const isMinimized = minimizedWindows.has(window.id);
                    const isFocused = focusedWindowId === window.id;
                    return (
                      <button
                        key={window.id}
                        className={`taskbar-item ${isMinimized ? 'minimized' : ''} ${isFocused && !isMinimized ? 'focused' : ''}`}
                        onClick={() => {
                          if (isMinimized) {
                            handleWindowMinimize(window.id);
                          } else {
                            handleWindowFocus(window.id);
                          }
                        }}
                        title={isMinimized ? `恢复: ${window.title}` : `聚焦: ${window.title}`}
                      >
                        <span className="taskbar-icon">{getWindowIcon(window.type)}</span>
                        <span className="taskbar-text">{window.title}</span>
                      </button>
                    );
                  })}
                </>
              ) : (
                <span className="taskbar-label">当前展板: {selectedBoard.name}</span>
              )}
            </>
          ) : (
            <span className="taskbar-label">WhatNote V2 - 请通过开始菜单选择展板</span>
          )}
        </div>
      </div>
      
      {/* Win98风格开始菜单 */}
      {showStartMenu && (
        <div className="start-menu">
          <div className="start-menu-header">
            <div className="start-menu-title">
              <span className="start-menu-icon">🏠</span>
              <span>WhatNote V2</span>
            </div>
          </div>
          
          <div className="start-menu-content">
            <div className="start-menu-section">
              <div className="section-header">
                <span>📚 课程管理</span>
                <button 
                  className="start-menu-btn"
                  onClick={() => setShowCreateCourse(true)}
                >
                  + 新建课程
                </button>
              </div>
              
              <div className="courses-list">
                {courses && courses.length > 0 ? (
                  courses.map(course => (
                    <div key={course.id} className="course-item">
                      <div 
                        className={`course-header ${selectedCourse?.id === course.id ? 'selected' : ''}`}
                        onClick={() => setSelectedCourse(course)}
                      >
                        <span className="course-name">📖 {course.name || '未命名课程'}</span>
                        <button 
                          className="create-board-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCourse(course);
                            setShowCreateBoard(true);
                          }}
                        >
                          + 展板
                        </button>
                      </div>
                      
                      {selectedCourse?.id === course.id && (
                        <div className="boards-list">
                          {courseBoards[course.id]?.map(board => (
                            <div 
                              key={board.id}
                              className={`board-item ${selectedBoard?.id === board.id ? 'selected' : ''}`}
                              onClick={() => {
                                setSelectedBoard(board);
                                setShowStartMenu(false); // 选择展板后关闭开始菜单
                              }}
                            >
                              📋 {board.name || '未命名展板'}
                            </div>
                          ))}
                          {(!courseBoards[course.id] || courseBoards[course.id].length === 0) && (
                            <div className="no-boards">
                              暂无展板
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="no-courses">
                    暂无课程，请创建第一个课程
                  </div>
                )}
              </div>
            </div>
            
            {/* 系统工具部分 */}
            <div className="start-menu-section">
              <div className="section-header">
                <span>🛠️ 系统工具</span>
              </div>
              
              <div className="system-tools">
                <div 
                  className="tool-item"
                  onClick={() => {
                    setShowTrash(true);
                    setShowStartMenu(false);
                  }}
                >
                  🗑️ 回收站
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* 创建课程弹窗 */}
      {showCreateCourse && (
        <div className="modal-overlay" onClick={() => setShowCreateCourse(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>创建新课程</h3>
            <input
              type="text"
              placeholder="课程名称"
              value={newCourseName}
              onChange={(e) => setNewCourseName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleStartMenuCreateCourse()}
            />
            <textarea
              placeholder="课程描述（可选）"
              value={newCourseDesc}
              onChange={(e) => setNewCourseDesc(e.target.value)}
            />
            <div className="modal-buttons">
              <button onClick={handleStartMenuCreateCourse}>创建</button>
              <button onClick={() => setShowCreateCourse(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
      
      {/* 创建展板弹窗 */}
      {showCreateBoard && (
        <div className="modal-overlay" onClick={() => setShowCreateBoard(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>创建新展板</h3>
            <input
              type="text"
              placeholder="展板名称"
              value={newBoardName}
              onChange={(e) => setNewBoardName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleStartMenuCreateBoard()}
            />
            <div className="modal-buttons">
              <button onClick={handleStartMenuCreateBoard}>创建</button>
              <button onClick={() => setShowCreateBoard(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
      
      {/* 回收站弹窗 */}
      {showTrash && (
        <div className="modal-overlay" onClick={() => setShowTrash(false)}>
          <div className="trash-modal" onClick={(e) => e.stopPropagation()}>
            <div className="trash-header">
              <h3>🗑️ 回收站</h3>
              <div className="trash-info">
                <span>项目数: {trashItems.length}</span>
                <span>大小: {(trashSize / 1024).toFixed(2)} KB</span>
              </div>
              <button className="close-btn" onClick={() => setShowTrash(false)}>✕</button>
            </div>
            
            <div className="trash-content">
              {trashItems.length > 0 ? (
                <div className="trash-items">
                  {trashItems.map(item => (
                    <div key={item.id} className="trash-item">
                      <div className="item-info">
                        <div className="item-name">{item.original_name}</div>
                        <div className="item-details">
                          <span>删除时间: {new Date(item.deleted_at).toLocaleString()}</span>
                          <span>大小: {(item.file_size / 1024).toFixed(2)} KB</span>
                          <span className={`file-status ${item.file_exists ? 'exists' : 'missing'}`}>
                            {item.file_exists ? '✓ 文件完整' : '✗ 文件丢失'}
                          </span>
                        </div>
                      </div>
                      <div className="item-actions">
                        <button 
                          className="restore-btn"
                          onClick={() => handleRestoreFromTrash(item.id)}
                          disabled={!item.file_exists}
                        >
                          恢复
                        </button>
                        <button 
                          className="delete-btn"
                          onClick={() => handlePermanentDelete(item.id)}
                        >
                          永久删除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-trash">
                  <p>回收站为空</p>
                </div>
              )}
            </div>
            
            {trashItems.length > 0 && (
              <div className="trash-footer">
                <button 
                  className="empty-trash-btn"
                  onClick={handleEmptyTrash}
                >
                  清空回收站
                </button>
              </div>
            )}
          </div>
        </div>
      )}
      
      {showConsole && (
        <Console onClose={() => setShowConsole(false)} />
      )}
    </div>
  );
}

// 窗口图标辅助函数
const getWindowIcon = (type) => {
  const typeIcons = {
    'text': '📝',
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵',
    'pdf': '📄'
  };
  return typeIcons[type] || '🪟';
};

export default App; 