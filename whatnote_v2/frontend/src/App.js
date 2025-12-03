import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// 导入组件
import CourseExplorer from './components/CourseExplorer';
import BoardCanvas from './components/BoardCanvas';
import Console from './components/Console';
// import Header from './components/Header'; // 移除顶部标题栏
import Sidebar from './components/Sidebar';

function App() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [showConsole, setShowConsole] = useState(false);
  const [consoleInitialPath, setConsoleInitialPath] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // 开始菜单相关状态
  const [showStartMenu, setShowStartMenu] = useState(false);
  const [showCreateCourse, setShowCreateCourse] = useState(false);
  const [showCreateCourseInput, setShowCreateCourseInput] = useState(false);
  const [showCreateBoard, setShowCreateBoard] = useState(false);
  const [showCreateBoardInput, setShowCreateBoardInput] = useState(false);
  const [newCourseName, setNewCourseName] = useState('');
  const [newCourseDesc, setNewCourseDesc] = useState('');
  const [newBoardName, setNewBoardName] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [courseBoards, setCourseBoards] = useState({});
  const courseBoardsRef = useRef({});

  // 系统提示状态
  const [toast, setToast] = useState({ visible: false, message: '', type: 'info' });
  const toastTimeoutRef = useRef(null);

  // 全局确认弹窗状态
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [startMenuContextMenu, setStartMenuContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    targetType: null,
    targetData: null
  });
  
  // 任务栏右键菜单状态
  const [showTaskbarContextMenu, setShowTaskbarContextMenu] = useState(false);
  const [taskbarMenuPosition, setTaskbarMenuPosition] = useState({ x: 0, y: 0 });
  
  // 子菜单激活状态
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [submenuPosition, setSubmenuPosition] = useState({ top: 0 });
  
  const toastTypeConfig = {
    success: { icon: '✅', title: '操作成功' },
    error: { icon: '⚠️', title: '操作失败' },
    info: { icon: 'ℹ️', title: '提示' }
  };

  useEffect(() => {
    courseBoardsRef.current = courseBoards;
  }, [courseBoards]);
  
  // 计算子菜单位置
  const calculateSubmenuPosition = (element) => {
    if (!element) {
      console.log('❌ calculateSubmenuPosition: element is null');
      return { top: 0 };
    }
    
    const rect = element.getBoundingClientRect();
    console.log('📍 文件夹元素位置:', {
      top: rect.top,
      bottom: rect.bottom,
      height: rect.height
    });
    
    const startMenuElement = document.querySelector('.start-menu');
    if (!startMenuElement) {
      console.log('❌ 找不到 .start-menu 元素');
      return { top: 0 };
    }
    
    const startMenuRect = startMenuElement.getBoundingClientRect();
    console.log('📍 开始菜单位置:', {
      top: startMenuRect.top,
      bottom: startMenuRect.bottom,
      height: startMenuRect.height
    });
    
    // 获取子菜单的预估高度（基于内容）
    const submenuElement = document.querySelector('.start-menu-submenu');
    const estimatedHeight = submenuElement ? submenuElement.scrollHeight : 200;
    console.log('📍 子菜单预估高度:', estimatedHeight);
    
    // 计算文件夹顶部到开始菜单底部的距离（可用空间）
    const folderTop = rect.top - startMenuRect.top;
    const startMenuHeight = startMenuRect.bottom - startMenuRect.top;
    const availableSpace = startMenuHeight - folderTop;
    
    console.log('📍 计算数据:', {
      folderTop,
      startMenuHeight,
      availableSpace,
      estimatedHeight,
      comparison: `${estimatedHeight} vs ${availableSpace}`
    });
    
    // 判断子菜单高度与可用空间的关系
    if (estimatedHeight < availableSpace) {
      // 子菜单高度小于可用空间，顶部对齐文件夹顶部
      const result = { top: Math.max(0, folderTop) };
      console.log('✅ 使用顶部对齐 (子菜单高度 < 可用空间):', result);
      return result;
    } else {
      // 子菜单高度大于等于可用空间，底部对齐开始菜单底部
      const bottomAlignedTop = startMenuHeight - estimatedHeight - 5;
      const result = { top: bottomAlignedTop }; // 不使用Math.max，允许负数（超出顶部）
      console.log('✅ 使用底部对齐 (子菜单高度 >= 可用空间):', {
        startMenuHeight,
        estimatedHeight,
        bottomAlignedTop,
        finalTop: result.top,
        note: bottomAlignedTop < 0 ? '子菜单顶部超出开始菜单顶部' : '子菜单完全在开始菜单内'
      });
      return result;
    }
  };
  
  const handleCourseClick = (courseId, event) => {
    const targetElement = event.currentTarget;
    
    if (activeCourseId === courseId) {
      setActiveCourseId(null);
      setShowCreateBoardInput(false);
      setNewBoardName('');
      return;
    }

    setShowCreateBoardInput(false);
    setNewBoardName('');
    setActiveCourseId(courseId);
    
    setTimeout(() => {
      const position = calculateSubmenuPosition(targetElement);
      setSubmenuPosition(position);
    }, 10);
  };
  
  // 任务栏右键菜单处理
  const handleTaskbarContextMenu = (e) => {
    e.preventDefault();
    setTaskbarMenuPosition({ x: e.clientX, y: e.clientY });
    setShowTaskbarContextMenu(true);
  };

  const handleStartMenuContextMenuOpen = (event, targetType, targetData) => {
    event.preventDefault();
    event.stopPropagation();
    setStartMenuContextMenu({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      targetType,
      targetData,
    });
  };

  const handleStartMenuContextMenuAction = (action) => {
    if (startMenuContextMenu.targetData) {
      console.log('[StartMenu ContextMenu]', action, startMenuContextMenu.targetType, startMenuContextMenu.targetData);
    }
    setStartMenuContextMenu({
      visible: false,
      x: 0,
      y: 0,
      targetType: null,
      targetData: null,
    });
  };

  const showToast = (message, type = 'info') => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
    }

    setToast({ visible: true, message, type });

    toastTimeoutRef.current = setTimeout(() => {
      setToast(prev => ({ ...prev, visible: false }));
      toastTimeoutRef.current = null;
    }, 3000);
  };

  const hideToast = () => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
      toastTimeoutRef.current = null;
    }
    setToast(prev => ({ ...prev, visible: false }));
  };
  
  const openConfirmDialog = ({ title, message, confirmText = '确定', cancelText = '取消', icon = '⚠️' }) => {
    return new Promise((resolve) => {
      setConfirmDialog({
        title,
        message,
        confirmText,
        cancelText,
        icon,
        onConfirm: () => {
          setConfirmDialog(null);
          resolve(true);
        },
        onCancel: () => {
          setConfirmDialog(null);
          resolve(false);
        }
      });
    });
  };
  
  const handleTaskbarMenuClose = () => {
    setShowTaskbarContextMenu(false);
  };

  const handleOpenPersonalization = () => {
    setShowTaskbarContextMenu(false);
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('openPersonalization');
      window.dispatchEvent(event);
    }
  };
  
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

  // 加载课程列表（带重试机制）
  useEffect(() => {
    let cancelled = false;
    let retryTimer = null;

    const fetchCoursesWithRetry = async (attempt = 1) => {
      if (cancelled) return;

      try {
        // 先检查后端健康状态
        try {
          const healthResponse = await fetch('http://localhost:8081/api/health');
          if (!healthResponse.ok) {
            throw new Error(`健康检查失败: HTTP ${healthResponse.status}`);
          }
        } catch (healthError) {
          console.log(`[App] 后端未就绪 (尝试 ${attempt}/5)，等待重试...`);
          if (attempt < 5 && !cancelled) {
            const delay = 1000 * attempt; // 1s, 2s, 3s, 4s
            retryTimer = setTimeout(() => {
              if (!cancelled) {
                retryTimer = null;
                fetchCoursesWithRetry(attempt + 1);
              }
            }, delay);
          } else {
            console.error('[App] 后端连接失败，已重试5次');
            showToast('无法连接到后端服务器，请检查后端是否已启动', 'error');
          }
          return;
        }

        // 后端就绪，获取课程列表
        const response = await fetch('http://localhost:8081/api/courses');
        if (response.ok) {
          const data = await response.json();
          console.log('[App] 课程API响应:', data);
          const coursesList = data.courses || [];
          console.log(`[App] 解析后的课程列表:`, coursesList);
          console.log(`[App] 课程数量: ${coursesList.length}`);
          if (!cancelled) {
            setCourses(coursesList);
            console.log(`[App] ✅ 成功加载 ${coursesList.length} 个课程到状态`);
            if (coursesList.length === 0) {
              console.warn('[App] ⚠️ 课程列表为空，可能是后端没有课程数据');
            }
          }
        } else {
          const errorText = await response.text();
          console.error(`[App] 获取课程失败: HTTP ${response.status}`, errorText);
          throw new Error(`获取课程失败: HTTP ${response.status} - ${errorText}`);
        }
      } catch (error) {
        console.error(`[App] 获取课程失败 (尝试 ${attempt}/5):`, error);
        if (attempt < 5 && !cancelled) {
          const delay = 1000 * attempt;
          console.log(`[App] ${delay}ms 后重试获取课程列表...`);
          retryTimer = setTimeout(() => {
            if (!cancelled) {
              retryTimer = null;
              fetchCoursesWithRetry(attempt + 1);
            }
          }, delay);
        } else {
          console.error('[App] 获取课程列表失败，已重试5次');
          showToast('无法加载课程列表，请检查后端服务', 'error');
        }
      }
    };

    fetchCoursesWithRetry();

    return () => {
      cancelled = true;
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
    };
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) {
        clearTimeout(toastTimeoutRef.current);
      }
    };
  }, []);

  // 获取课程的展板列表
  useEffect(() => {
      if (!courses || courses.length === 0) return;
      
    let cancelled = false;
    let retryTimer = null;

    const fetchCourseBoards = async (attempt = 1) => {
      const boardsData = {};
      let hasFailure = false;

      for (const course of courses) {
        const previousBoards = courseBoardsRef.current[course.id] || [];
        try {
          const response = await fetch(`http://localhost:8081/api/courses/${course.id}/boards`);
          if (response.ok) {
            const data = await response.json();
            boardsData[course.id] = data.boards || [];
          } else {
            console.warn(`[App] 获取课程 ${course.id} 的展板失败 (HTTP ${response.status})`);
            boardsData[course.id] = previousBoards;
            hasFailure = true;
          }
        } catch (error) {
          console.error(`获取课程 ${course.id} 的展板失败:`, error);
          boardsData[course.id] = previousBoards;
          hasFailure = true;
        }
      }

      if (cancelled) return;

      setCourseBoards(boardsData);

      if (hasFailure && attempt < 3) {
        const delay = 1500 * attempt;
        console.log(`[App] 展板列表获取部分失败，${delay}ms 后重试 (第 ${attempt + 1} 次)`);
        if (retryTimer) {
          clearTimeout(retryTimer);
        }
        retryTimer = setTimeout(() => {
          if (!cancelled) {
            retryTimer = null;
            fetchCourseBoards(attempt + 1);
          }
        }, delay);
      }
    };

    fetchCourseBoards();

    return () => {
      cancelled = true;
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
    };
  }, [courses]);

  const fetchCourses = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/courses');
      if (response.ok) {
      const data = await response.json();
      setCourses(data.courses || []);
        console.log(`[App] 手动刷新：成功加载 ${(data.courses || []).length} 个课程`);
      } else {
        console.error(`[App] 获取课程失败: HTTP ${response.status}`);
        showToast('获取课程列表失败', 'error');
      }
    } catch (error) {
      console.error('获取课程失败:', error);
      showToast('无法连接到后端服务器', 'error');
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
      await handleCreateCourse(newCourseName.trim(), '');
      setNewCourseName('');
      setShowCreateCourseInput(false);
      setActiveCourseId(null);
      setShowCreateBoardInput(false);
    }
  };

  const handleStartMenuCreateBoard = async () => {
    if (newBoardName.trim() && selectedCourse) {
      await handleCreateBoard(selectedCourse.id, newBoardName.trim());
      setNewBoardName('');
      setShowCreateBoardInput(false);
      setActiveCourseId(null);
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
        showToast('文件恢复成功！', 'success');
      } else {
        showToast('文件恢复失败！', 'error');
      }
    } catch (error) {
      console.error('恢复文件失败:', error);
      showToast('文件恢复失败！', 'error');
    }
  };

  const handlePermanentDelete = async (trashId) => {
    const confirmed = await openConfirmDialog({
      title: '永久删除确认',
      message: '确定要永久删除这个文件吗？此操作无法撤销！',
      icon: '⚠️'
    });

    if (!confirmed) {
      return;
    }

      try {
        const response = await fetch(`http://localhost:8081/api/trash/${trashId}`, {
          method: 'DELETE'
        });
        if (response.ok) {
          await loadTrashItems();
          await loadTrashSize();
        showToast('文件已永久删除！', 'success');
        } else {
        showToast('删除失败！', 'error');
        }
      } catch (error) {
        console.error('永久删除失败:', error);
      showToast('删除失败！', 'error');
    }
  };

  const handleEmptyTrash = async () => {
    const confirmed = await openConfirmDialog({
      title: '清空回收站',
      message: '确定要清空回收站吗？此操作将永久删除所有文件，无法撤销！',
      icon: '⚠️'
    });

    if (!confirmed) {
      return;
    }

      try {
        const response = await fetch('http://localhost:8081/api/trash', {
          method: 'DELETE'
        });
        if (response.ok) {
          await loadTrashItems();
          await loadTrashSize();
        showToast('回收站已清空！', 'success');
        } else {
        showToast('清空回收站失败！', 'error');
        }
      } catch (error) {
        console.error('清空回收站失败:', error);
      showToast('清空回收站失败！', 'error');
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

  // 提供全局方法供 BoardCanvas 调用
  useEffect(() => {
    window.openConsoleAtCurrentBoard = async (courseId, boardId) => {
      console.log('[App] 打开控制台，定位到:', { courseId, boardId });
      
      try {
        // 从当前状态中查找课程和展板信息
        // 优先使用已加载的数据，避免不必要的 API 调用
        const course = courses.find(c => c.id === courseId);
        
        if (course) {
          console.log('[App] 找到课程:', course.name);
          
          // 获取展板列表
          const boardsResponse = await fetch(`http://localhost:8081/api/courses/${courseId}/boards`);
          if (boardsResponse.ok) {
            const boardsData = await boardsResponse.json();
            const board = boardsData.boards.find(b => b.id === boardId);
            
            if (board) {
              // 设置初始路径
              const initialPath = `${course.name}/${board.name}`;
              console.log('[App] 设置初始路径:', initialPath);
              setConsoleInitialPath(initialPath);
              console.log('[App] 打开控制台');
              setShowConsole(true);
              
              console.log('[App] 控制台已打开，路径:', initialPath);
              return;
            } else {
              console.warn('[App] 未找到展板:', boardId);
            }
          } else {
            console.error('[App] 获取展板列表失败');
          }
        } else {
          console.warn('[App] 未找到课程:', courseId);
        }
        
        // 如果获取失败，也打开控制台（不带初始路径）
        console.warn('[App] 无法获取课程/展板信息，打开空白控制台');
        setShowConsole(true);
      } catch (error) {
        console.error('[App] 获取课程/展板信息失败:', error);
        // 即使失败也打开控制台
        setShowConsole(true);
      }
    };
    
    return () => {
      delete window.openConsoleAtCurrentBoard;
    };
  }, [courses]);

  // 监听控制台的切换展板事件
  useEffect(() => {
    const handleSwitchBoard = async (event) => {
      const { courseId, boardId } = event.detail;
      console.log('[App] 控制台切换展板:', { courseId, boardId });
      
      // 查找课程对象
      const course = courses.find(c => c.id === courseId);
      if (course) {
        setSelectedCourse(course);
        
        // 获取展板信息
        try {
          const response = await fetch(`http://localhost:8081/api/courses/${courseId}/boards`);
          if (response.ok) {
            const data = await response.json();
            const board = data.boards.find(b => b.id === boardId);
            if (board) {
              setSelectedBoard(board);
              console.log('[App] 已切换到展板:', board.name);
            }
          }
        } catch (error) {
          console.error('[App] 获取展板信息失败:', error);
        }
      }
    };
    
    const handleSwitchCourse = (event) => {
      const { courseId } = event.detail;
      console.log('[App] 控制台切换课程:', { courseId });
      
      const course = courses.find(c => c.id === courseId);
      if (course) {
        setSelectedCourse(course);
        console.log('[App] 已切换到课程:', course.name);
      }
    };
    
    const handleRefreshCourses = () => {
      console.log('[App] 刷新课程列表');
      fetchCourses();
    };
    
    const handleRefreshBoards = async (event) => {
      const { courseId } = event.detail;
      console.log('[App] 刷新展板列表:', courseId);
      
      // 重新获取该课程的展板列表
      try {
        const response = await fetch(`http://localhost:8081/api/courses/${courseId}/boards`);
        if (response.ok) {
          const data = await response.json();
          setCourseBoards(prev => ({
            ...prev,
            [courseId]: data.boards || []
          }));
          console.log('[App] 展板列表已刷新');
        }
      } catch (error) {
        console.error('[App] 刷新展板列表失败:', error);
      }
    };
    
    window.addEventListener('switchBoard', handleSwitchBoard);
    window.addEventListener('switchCourse', handleSwitchCourse);
    window.addEventListener('refreshCourses', handleRefreshCourses);
    window.addEventListener('refreshBoards', handleRefreshBoards);
    
    return () => {
      window.removeEventListener('switchBoard', handleSwitchBoard);
      window.removeEventListener('switchCourse', handleSwitchCourse);
      window.removeEventListener('refreshCourses', handleRefreshCourses);
      window.removeEventListener('refreshBoards', handleRefreshBoards);
    };
  }, [courses]);

  // 点击外部关闭开始菜单和任务栏右键菜单
  useEffect(() => {
    const handleClickOutside = (event) => {
      const clickedInsideStartMenu = event.target.closest('.start-menu-container');
      const clickedStartButton = event.target.closest('.start-button');
      const clickedContextMenu = event.target.closest('.start-menu-context-menu');

      if (showStartMenu && !clickedInsideStartMenu && !clickedStartButton) {
        setShowStartMenu(false);
        setShowCreateCourseInput(false); // 重置输入框状态
        setNewCourseName(''); // 清空输入内容
        setShowCreateBoardInput(false); // 重置新建展板输入框状态
        setNewBoardName(''); // 清空展板输入内容
        setActiveCourseId(null);
        setStartMenuContextMenu({ visible: false, x: 0, y: 0, targetType: null, targetData: null });
      } else if (startMenuContextMenu.visible && !clickedContextMenu) {
        setStartMenuContextMenu({ visible: false, x: 0, y: 0, targetType: null, targetData: null });
      }
      
      // 关闭任务栏右键菜单
      if (showTaskbarContextMenu && !event.target.closest('.taskbar-context-menu')) {
        setShowTaskbarContextMenu(false);
      }
    };

    if (showStartMenu || showTaskbarContextMenu || startMenuContextMenu.visible) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showStartMenu, showTaskbarContextMenu, startMenuContextMenu.visible]);

  useEffect(() => {
    if (!showStartMenu) {
      setActiveCourseId(null);
      setShowCreateBoardInput(false);
      setNewBoardName('');
      setStartMenuContextMenu({ visible: false, x: 0, y: 0, targetType: null, targetData: null });
    }
  }, [showStartMenu]);

  return (
    <div className="app">
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
              courseId={selectedCourse?.id}
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
              <h2>WhatNote V2</h2>
              <p>请选择一个展板开始工作</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Win98风格任务栏 - 始终显示 */}
      <div className="taskbar" onContextMenu={handleTaskbarContextMenu}>
        <div className="taskbar-content">
          {/* Win98开始按钮 */}
          <button 
            className="start-button"
            onClick={() => setShowStartMenu(!showStartMenu)}
          >
            <span className="start-icon win98-icon win98-icon-start"></span>
            <span className="start-text">开始</span>
          </button>
          
          <div className="taskbar-separator"></div>
          
          {selectedBoard ? (
            <>
              {currentBoardWindows.filter(window => 
                !hiddenWindows.has(window.id) && 
                window.type !== 'chat' && 
                window.type !== 'message-center' &&
                window.type !== 'planner'
              ).length > 0 ? (
                <>
                  {currentBoardWindows.filter(window => 
                    !hiddenWindows.has(window.id) && 
                    window.type !== 'chat' && 
                    window.type !== 'message-center' &&
                    window.type !== 'planner'
                  ).map(window => {
                    const isMinimized = minimizedWindows.has(window.id);
                    const isFocused = focusedWindowId === window.id;
                    const iconClass = getWindowIconClass(window.type);
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
                        <span className={`taskbar-icon${iconClass ? ` ${iconClass}` : ''}`}>
                          {iconClass ? null : getWindowIcon(window.type)}
                        </span>
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
          
          {/* 右侧聊天按钮和连接状态 */}
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px' }}>
            {selectedBoard && (
              <>
                <button 
                  className="taskbar-item"
                  onClick={() => {
                    // 通过事件通知BoardCanvas打开聊天窗口
                    const event = new CustomEvent('toggleChatWindow');
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(event);
                    }
                  }}
                  title="AI助手聊天"
                  style={{ minWidth: 'auto', width: '80px' }}
                >
                  <span className="taskbar-icon">💬</span>
                  <span className="taskbar-text">AI助手</span>
                </button>
                
                <button 
                  className="taskbar-item message-center-taskbar-btn"
                  onClick={() => {
                    // 通过事件通知BoardCanvas打开消息中心
                    const event = new CustomEvent('toggleMessageCenter');
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(event);
                    }
                  }}
                  title="消息中心"
                  style={{ minWidth: 'auto', width: '80px', position: 'relative' }}
                >
                  <span className="taskbar-icon win98-icon win98-icon-mail"></span>
                  <span className="taskbar-text">消息</span>
                </button>

                <button
                  className="taskbar-item planner-taskbar-btn"
                  onClick={() => {
                    const event = new CustomEvent('togglePlannerWindow');
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(event);
                    }
                  }}
                  title="日历与计划"
                  style={{ minWidth: 'auto', width: '90px' }}
                >
                  <span className="taskbar-icon win98-icon win98-icon-calendar"></span>
                  <span className="taskbar-text">日历</span>
                </button>

                <button
                  className="taskbar-item plugin-manager-taskbar-btn"
                  onClick={() => {
                    const event = new CustomEvent('togglePluginManagerWindow');
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(event);
                    }
                  }}
                  title="插件管理器"
                  style={{ minWidth: 'auto', width: '90px' }}
                >
                  <span className="taskbar-icon">🔌</span>
                  <span className="taskbar-text">插件</span>
                </button>
              </>
            )}
            
            {/* 连接状态指示器 */}
            <div className="connection-status" style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '2px 8px' }}>
              <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
              <span className="status-text" style={{ fontSize: '11px', color: 'black' }}>
                {isConnected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* 任务栏右键菜单 */}
      {showTaskbarContextMenu && (
        <div 
          className="taskbar-context-menu"
          style={{
            position: 'fixed',
            left: `${taskbarMenuPosition.x}px`,
            top: `${taskbarMenuPosition.y}px`,
            zIndex: 20000
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="context-menu-item" onClick={handleOpenPersonalization}>
            <span className="menu-icon win98-icon win98-icon-palette"></span>
            <span className="menu-text">个性化</span>
          </div>
        </div>
      )}
      
      {/* Win98风格开始菜单 */}
      {showStartMenu && (
        <div className="start-menu-container" onContextMenu={(e) => e.preventDefault()}>
          <div className="start-menu">
            <div className="start-menu-vertical-title">WhatNote</div>
            <div className="start-menu-content">
            {/* 主菜单 */}
            <div className="start-menu-main">
              {/* 新建课程选项 */}
              {!showCreateCourseInput ? (
                <div 
                  className="start-menu-item"
                  onClick={() => {
                    setShowCreateCourseInput(true);
                    setNewCourseName('');
                  }}
                >
                  <span className="menu-icon win98-icon win98-icon-document-plus"></span>
                  <span className="menu-text">新建课程</span>
                </div>
              ) : (
                <div className="start-menu-item start-menu-input-container">
                  <input
                    type="text"
                    placeholder="课程名称"
                    value={newCourseName}
                    onChange={(e) => setNewCourseName(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !isComposing) {
                        handleStartMenuCreateCourse();
                      } else if (e.key === 'Escape') {
                        setShowCreateCourseInput(false);
                        setNewCourseName('');
                      }
                    }}
                    onCompositionStart={() => setIsComposing(true)}
                    onCompositionEnd={() => setIsComposing(false)}
                    onBlur={() => {
                      if (!isComposing) {
                        setTimeout(() => {
                          if (newCourseName.trim() === '') {
                            setShowCreateCourseInput(false);
                          }
                        }, 200);
                      }
                    }}
                    autoFocus
                    className="start-menu-input"
                  />
                  <button
                    onClick={handleStartMenuCreateCourse}
                    className="start-menu-confirm-btn"
                    disabled={!newCourseName.trim()}
                  >
                    ✓
                  </button>
                </div>
              )}
              
              {/* 分界线 */}
              <div className="menu-separator"></div>
              
              {/* 课程列表 */}
              {(() => {
                console.log('[App] 渲染课程列表，courses状态:', courses);
                console.log('[App] courses类型:', typeof courses, '是否为数组:', Array.isArray(courses));
                console.log('[App] courses长度:', courses?.length);
                return null;
              })()}
              {courses && courses.length > 0 && (
                courses.map(course => (
                  <div 
                    key={course.id} 
                    className={`start-menu-item ${activeCourseId === course.id ? 'active' : ''}`}
                    onClick={(e) => handleCourseClick(course.id, e)}
                    onContextMenu={(e) => handleStartMenuContextMenuOpen(e, 'course', course)}
                  >
                    <span className="menu-icon win98-icon win98-icon-folder"></span>
                    <span className="menu-text">{course.name || '未命名课程'}</span>
                    <span className="menu-arrow">▶</span>
                  </div>
                ))
              )}
              {(!courses || courses.length === 0) && (
                <div className="start-menu-item" style={{ color: '#999', fontStyle: 'italic' }}>
                  <span className="menu-text">暂无课程（调试：courses={JSON.stringify(courses)}）</span>
                </div>
              )}
              
              {/* 分界线 */}
              <div className="menu-separator"></div>
              
              {/* 回收站 */}
              <div 
                className="start-menu-item"
                onClick={() => {
                  setShowTrash(true);
                  setShowStartMenu(false);
                }}
              >
                <span className="menu-icon win98-icon win98-icon-recycle"></span>
                <span className="menu-text">回收站</span>
              </div>
              
              {/* 工具控制台 */}
              <div 
                className="start-menu-item"
                onClick={() => {
                  setShowConsole(true);
                  setShowStartMenu(false);
                }}
              >
                <span className="menu-icon win98-icon win98-icon-console"></span>
                <span className="menu-text">工具控制台</span>
              </div>
            </div>
            
          </div>
          
          {/* 外侧子菜单 */}
          {activeCourseId && (
            <div 
              className="start-menu-submenu"
              style={{ top: `${submenuPosition.top}px` }}
            >
              <div className="submenu-content">
                <div className="submenu-items">
                  {!showCreateBoardInput ? (
                    <div 
                      className="submenu-item"
                      onClick={() => {
                        setSelectedCourse(courses.find(c => c.id === activeCourseId));
                        setShowCreateBoardInput(true);
                        setNewBoardName('');
                      }}
                    >
                      <span className="submenu-icon win98-icon win98-icon-document-plus"></span>
                      <span className="submenu-text">新建展板</span>
                    </div>
                  ) : (
                    <div className="submenu-item start-menu-input-container">
                      <input
                        type="text"
                        placeholder="展板名称"
                        value={newBoardName}
                        onChange={(e) => setNewBoardName(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter' && !isComposing) {
                            handleStartMenuCreateBoard();
                          } else if (e.key === 'Escape') {
                            setShowCreateBoardInput(false);
                            setNewBoardName('');
                          }
                        }}
                        onCompositionStart={() => setIsComposing(true)}
                        onCompositionEnd={() => setIsComposing(false)}
                        onBlur={() => {
                          if (!isComposing) {
                            setTimeout(() => {
                              if (newBoardName.trim() === '') {
                                setShowCreateBoardInput(false);
                                setActiveCourseId(null);
                              }
                            }, 200);
                          }
                        }}
                        autoFocus
                        className="start-menu-input"
                      />
                      <button
                        onClick={handleStartMenuCreateBoard}
                        className="start-menu-confirm-btn"
                        disabled={!newBoardName.trim()}
                      >
                        ✓
                      </button>
                    </div>
                  )}
                  
                  {courseBoards[activeCourseId]?.map(board => (
                    <div 
                      key={board.id}
                      className="submenu-item"
                      onClick={() => {
                        // 找到对应的课程并设置
                        const course = courses.find(c => c.id === activeCourseId);
                        if (course) {
                          setSelectedCourse(course);
                        }
                        setSelectedBoard(board);
                        setShowStartMenu(false);
                        setActiveCourseId(null);
                        setShowCreateBoardInput(false);
                        setNewBoardName('');
                      }}
                      onContextMenu={(e) => handleStartMenuContextMenuOpen(e, 'board', { course: courses.find(c => c.id === activeCourseId), board })}
                    >
                      <span className="submenu-icon win98-icon win98-icon-clipboard"></span>
                      <span className="submenu-text">{board.name || '未命名展板'}</span>
                    </div>
                  ))}
                  
                  {(!courseBoards[activeCourseId] || courseBoards[activeCourseId].length === 0) && (
                    <div className="submenu-empty">
                      暂无展板
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          </div>
        </div>
      )}
      
      {startMenuContextMenu.visible && showStartMenu && (
        <div
          className="start-menu-context-menu"
          style={{ left: `${startMenuContextMenu.x}px`, top: `${startMenuContextMenu.y}px` }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="context-menu-item" onClick={() => handleStartMenuContextMenuAction('rename')}>
            <span className="menu-icon">✏️</span>
            <span className="menu-text">重命名</span>
          </div>
          <div className="context-menu-item" onClick={() => handleStartMenuContextMenuAction('delete')}>
            <span className="menu-icon">🗑️</span>
            <span className="menu-text">删除</span>
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
        <Console 
          onClose={() => {
            setShowConsole(false);
            setConsoleInitialPath(null); // 关闭时清空初始路径
          }} 
          initialPath={consoleInitialPath}
        />
      )}

      {confirmDialog && (
        <div className="win98-dialog-overlay" role="dialog" aria-modal="true">
          <div className="win98-dialog">
            <div className="win98-dialog-titlebar">
              <span className="win98-dialog-icon">{confirmDialog.icon || '⚠️'}</span>
              <span className="win98-dialog-title">{confirmDialog.title || '确认操作'}</span>
            </div>
            <div className="win98-dialog-content">
              {React.isValidElement(confirmDialog.message) ? (
                confirmDialog.message
              ) : (
                <div className="win98-dialog-message">{confirmDialog.message}</div>
              )}
            </div>
            <div className="win98-dialog-actions">
              <button className="win98-btn primary" onClick={confirmDialog.onConfirm}>
                {confirmDialog.confirmText || '确定'}
              </button>
              <button className="win98-btn" onClick={confirmDialog.onCancel}>
                {confirmDialog.cancelText || '取消'}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast.visible && (
        <div className="win98-toast-container">
          <div className={`win98-toast ${toast.type}`}>
            <div className="win98-toast-icon">
              {(toastTypeConfig[toast.type] || toastTypeConfig.info).icon}
            </div>
            <div className="win98-toast-content">
              <div className="win98-toast-title">
                {(toastTypeConfig[toast.type] || toastTypeConfig.info).title}
              </div>
              <div className="win98-toast-message">{toast.message}</div>
            </div>
            <button className="win98-toast-close" onClick={hideToast} aria-label="关闭提示">×</button>
          </div>
        </div>
      )}
    </div>
  );
}

// 窗口图标辅助函数
const getWindowIcon = (type) => {
  const typeIcons = {
    'text': '📝',
    'web': '🌐',
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵',
    'pdf': '📄',
    'chat': '💬',
    'message-center': '📬',
    'personalization': '🎨',
    'planner': '📅'
  };
  return typeIcons[type] || '🪟';
};

const getWindowIconClass = (type) => {
  const typeIconClass = {
    'text': 'win98-icon win98-icon-text',
    'web': 'win98-icon win98-icon-web',
    'image': 'win98-icon win98-icon-image',
    'video': 'win98-icon win98-icon-video',
    'audio': 'win98-icon win98-icon-audio',
    'pdf': 'win98-icon win98-icon-pdf',
    'chat': 'win98-icon win98-icon-chat',
    'message-center': 'win98-icon win98-icon-mail',
    'personalization': 'win98-icon win98-icon-settings',
    'planner': 'win98-icon win98-icon-calendar',
    'console': 'win98-icon win98-icon-console'
  };
  return typeIconClass[type] || null;
};

export default App; 