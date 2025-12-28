import React, { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import { LanguageProvider, useLanguage } from './i18n/LanguageContext';

// 导入组件
import CourseExplorer from './components/CourseExplorer';
import BoardCanvas from './components/BoardCanvas';
import Console from './components/Console';
// import Header from './components/Header'; // 移除顶部标题栏
import Sidebar from './components/Sidebar';

function App() {
  const [globalSettings, setGlobalSettings] = useState(null);

  useEffect(() => {
    const fetchGlobalSettings = async () => {
      try {
        // 使用一个通用的 board_id 或者专门的全局接口，这里暂时用 'system'
        const response = await fetch(`http://localhost:8081/api/personalization/settings/system`);
        if (response.ok) {
          const data = await response.json();
          setGlobalSettings(data);
        }
      } catch (err) {
        console.error('Failed to fetch global settings:', err);
      }
    };
    fetchGlobalSettings();
  }, []);

  return (
    <LanguageProvider initialSettings={globalSettings}>
      <Router>
        <AppContent />
      </Router>
    </LanguageProvider>
  );
}

function AppContent() {
  const { t, language, theme, updateLanguage } = useLanguage();
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [showConsole, setShowConsole] = useState(false);
  const [consoleInitialPath, setConsoleInitialPath] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // 系统时间状态
  const [currentTime, setCurrentTime] = useState(new Date());
  
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
  
  // 重命名相关状态
  const [editingItemId, setEditingItemId] = useState(null);
  const [editingItemName, setEditingItemName] = useState('');
  
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
  const taskbarMenuRef = useRef(null);
  const startMenuContextRef = useRef(null);

  useLayoutEffect(() => {
    // Taskbar Menu
    if (showTaskbarContextMenu && taskbarMenuRef.current) {
      const menu = taskbarMenuRef.current;
      const rect = menu.getBoundingClientRect();
      const { innerWidth, innerHeight } = window;

      if (rect.bottom > innerHeight) {
        menu.style.top = 'auto';
        menu.style.bottom = `${innerHeight - taskbarMenuPosition.y}px`;
      } else {
        menu.style.bottom = 'auto';
        menu.style.top = `${taskbarMenuPosition.y}px`;
      }

      if (rect.right > innerWidth) {
        menu.style.left = 'auto';
        menu.style.right = `${innerWidth - taskbarMenuPosition.x}px`;
      } else {
        menu.style.right = 'auto';
        menu.style.left = `${taskbarMenuPosition.x}px`;
      }
    }

    // Start Menu Context Menu
    if (startMenuContextMenu.visible && startMenuContextRef.current) {
      const menu = startMenuContextRef.current;
      const rect = menu.getBoundingClientRect();
      const { innerWidth, innerHeight } = window;

      if (rect.bottom > innerHeight) {
        menu.style.top = 'auto';
        menu.style.bottom = `${innerHeight - startMenuContextMenu.y}px`;
      } else {
        menu.style.bottom = 'auto';
        menu.style.top = `${startMenuContextMenu.y}px`;
      }

      if (rect.right > innerWidth) {
        menu.style.left = 'auto';
        menu.style.right = `${innerWidth - startMenuContextMenu.x}px`;
      } else {
        menu.style.right = 'auto';
        menu.style.left = `${startMenuContextMenu.x}px`;
      }
    }
  }, [showTaskbarContextMenu, taskbarMenuPosition, startMenuContextMenu]);
  
  // 子菜单激活状态
  const [activeCourseId, setActiveCourseId] = useState(null);
  const [submenuPosition, setSubmenuPosition] = useState({ top: 0 });
  const [draggedItem, setDraggedItem] = useState(null); // 用于拖拽排序
  const [dragOverInfo, setDragOverInfo] = useState({ id: null, position: null }); // { id, position: 'top' | 'bottom' }
  
  const toastTypeConfig = {
    success: { icon: 'win98-icon-success', title: '操作成功' },
    error: { icon: 'win98-icon-error', title: '操作失败' },
    info: { icon: 'win98-icon-info', title: '提示' }
  };

  useEffect(() => {
    courseBoardsRef.current = courseBoards;
  }, [courseBoards]);

  // 全局禁用默认右键菜单，统一系统风格
  useEffect(() => {
    const handleGlobalContextMenu = (e) => {
      // 检查点击的是否是输入框或文本域，暂时允许这些地方的原生菜单以方便复制粘贴
      const isInput = e.target.tagName === 'INPUT' || 
                      e.target.tagName === 'TEXTAREA' || 
                      e.target.isContentEditable ||
                      e.target.closest('input') ||
                      e.target.closest('textarea');
      
      if (isInput) return;

      // 屏蔽其他所有地方的浏览器默认菜单
      e.preventDefault();
    };

    window.addEventListener('contextmenu', handleGlobalContextMenu);
    return () => window.removeEventListener('contextmenu', handleGlobalContextMenu);
  }, []);
  
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
    
    // 获取子菜单的预估高度（基于内容，但受限于 CSS 的 max-height）
    const submenuElement = document.querySelector('.start-menu-submenu');
    const contentHeight = submenuElement ? submenuElement.scrollHeight : 200;
    
    // 获取实际显示高度（受 CSS 70vh 限制）
    const maxAllowedHeight = window.innerHeight * 0.7;
    const estimatedHeight = Math.min(contentHeight, maxAllowedHeight);
    
    console.log('📍 子菜单高度计算:', {
      contentHeight,
      maxAllowedHeight,
      estimatedHeight
    });
    
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
      // 注意：这里的底部对齐是指子菜单的底部边缘与主菜单底部对齐
      const bottomAlignedTop = startMenuHeight - estimatedHeight;
      const result = { top: bottomAlignedTop }; 
      console.log('✅ 使用底部对齐 (子菜单高度 >= 可用空间):', {
        startMenuHeight,
        estimatedHeight,
        bottomAlignedTop,
        finalTop: result.top
      });
      return result;
    }
  };
  
  // 拖拽排序处理
  const handleDragStart = (e, type, item) => {
    setDraggedItem({ type, item });
    e.dataTransfer.effectAllowed = 'move';
    e.currentTarget.classList.add('dragging');
  };

  const handleDragEnd = (e) => {
    e.currentTarget.classList.remove('dragging');
    setDraggedItem(null);
    setDragOverInfo({ id: null, position: null });
  };

  const handleDragOver = (e, id) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    if (!draggedItem || draggedItem.item.id === id) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const midY = rect.top + rect.height / 2;
    const position = e.clientY < midY ? 'top' : 'bottom';
    
    if (dragOverInfo.id !== id || dragOverInfo.position !== position) {
      setDragOverInfo({ id, position });
    }
  };

  const handleDragLeave = (e) => {
    // 只有当离开整个元素时才清除，防止子元素触发
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverInfo({ id: null, position: null });
    }
  };

  const handleDrop = async (e, type, targetItem) => {
    e.preventDefault();
    const position = dragOverInfo.position;
    setDragOverInfo({ id: null, position: null });

    if (!draggedItem || draggedItem.type !== type || draggedItem.item.id === targetItem.id) {
      return;
    }

    if (type === 'course') {
      const newCourses = [...courses];
      const draggedIndex = newCourses.findIndex(c => c.id === draggedItem.item.id);
      newCourses.splice(draggedIndex, 1);
      
      const targetIndex = newCourses.findIndex(c => c.id === targetItem.id);
      // 根据落点位置决定插入到目标项之前还是之后
      const finalIndex = position === 'top' ? targetIndex : targetIndex + 1;
      
      newCourses.splice(finalIndex, 0, draggedItem.item);
      setCourses(newCourses);
      
      // 保存到后端
      try {
        await fetch(`http://localhost:8081/api/courses/reorder`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newCourses.map(c => c.id))
        });
      } catch (err) {
        console.error('保存课程排序失败:', err);
      }
    } else if (type === 'board') {
      const courseId = activeCourseId;
      const boards = [...courseBoards[courseId]];
      const draggedIndex = boards.findIndex(b => b.id === draggedItem.item.id);
      boards.splice(draggedIndex, 1);
      
      const targetIndex = boards.findIndex(b => b.id === targetItem.id);
      const finalIndex = position === 'top' ? targetIndex : targetIndex + 1;
      
      boards.splice(finalIndex, 0, draggedItem.item);
      setCourseBoards({
        ...courseBoards,
        [courseId]: boards
      });
      
      // 保存到后端
      try {
        await fetch(`http://localhost:8081/api/courses/${courseId}/boards/reorder`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(boards.map(b => b.id))
        });
      } catch (err) {
        console.error('保存展板排序失败:', err);
      }
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

  const handleStartMenuContextMenuAction = async (action) => {
    const { targetType, targetData } = startMenuContextMenu;
    console.log('👉 [App] handleStartMenuContextMenuAction triggered:', { action, targetType, targetData });
    
    // 关闭菜单
    setStartMenuContextMenu({
      visible: false,
      x: 0,
      y: 0,
      targetType: null,
      targetData: null,
    });

    if (!targetData) {
      console.warn('⚠️ [App] No targetData found in startMenuContextMenu');
      return;
    }

    // 统一处理数据结构：展板的数据在 targetData.board 中
    const actualData = targetType === 'board' ? targetData.board : targetData;
    console.log('👉 [App] actualData:', actualData);

    if (action === 'open-folder') {
      try {
        const response = await fetch(`http://localhost:8081/api/boards/${actualData.id}/open-folder`, {
          method: 'POST'
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || '无法打开文件夹');
        }
      } catch (error) {
        console.error('打开文件夹失败:', error);
        showToast(`打开文件夹失败: ${error.message}`, 'error');
      }
    } else if (action === 'rename') {
      const actualData = targetType === 'board' ? targetData.board : targetData;
      setEditingItemId(actualData.id);
      setEditingItemName(actualData.name);
    } else if (action === 'delete') {
      const confirmTitle = targetType === 'course' ? '删除课程' : '删除展板';
      const confirmMsg = targetType === 'course' 
        ? `确定要删除课程 "${actualData.name}" 吗？这会删除该课程下的所有展板和文件！`
        : `确定要删除展板 "${actualData.name}" 吗？`;
        
      const confirmed = await openConfirmDialog({
        title: confirmTitle,
        message: confirmMsg,
        icon: 'win98-icon-warning'
      });
        
      if (confirmed) {
        try {
          const url = targetType === 'course'
            ? `http://localhost:8081/api/courses/${actualData.id}`
            : `http://localhost:8081/api/boards/${actualData.id}`;
            
          console.log(`🚀 [App] Sending ${targetType} delete request to:`, url);
          const response = await fetch(url, { method: 'DELETE' });
          if (response.ok) {
            showToast('删除成功', 'success');
            
            // 如果回收站窗口开着，立即刷新
            loadTrashItems();
            loadTrashSize();
            
            // 如果删除的是当前选中的展板，需要清空选中状态
            if (targetType === 'board' && selectedBoard && selectedBoard.id === actualData.id) {
              setSelectedBoard(null);
            }
            
            await fetchCourses();
            
            // 如果是展板，刷新列表
            if (targetType === 'board') {
              const courseId = actualData.course_id || (targetData.course ? targetData.course.id : null);
              if (courseId) {
                const event = new CustomEvent('refresh-boards', { detail: { courseId } });
                window.dispatchEvent(event);
              }
            }
          } else {
            const errorText = await response.text();
            console.error('❌ [App] Delete failed:', errorText);
            showToast('删除失败', 'error');
          }
        } catch (error) {
          console.error('❌ [App] Delete request error:', error);
          showToast('操作失败，请检查网络', 'error');
        }
      }
    }
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

  // 将 showToast 暴露给全局，方便其他组件调用
  window.showToast = showToast;

  const hideToast = () => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
      toastTimeoutRef.current = null;
    }
    setToast(prev => ({ ...prev, visible: false }));
  };

  // 格式化文件大小
  const formatSize = (bytes) => {
    if (bytes === 0 || bytes === null || isNaN(bytes)) return '0 字节';
    const k = 1024;
    const sizes = ['字节', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  const openConfirmDialog = ({ title, message, confirmText = t('ok'), cancelText = t('cancel'), icon = 'win98-icon-warning' }) => {
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
  const [selectedTrashId, setSelectedTrashId] = useState(null);
  const [trashSortConfig, setTrashSortConfig] = useState({
    field: 'deleted_at', // name, created_at, deleted_at, type
    order: 'desc' // asc, desc
  });
  const [showTrashViewMenu, setShowTrashViewMenu] = useState(false);
  const [showTrashProperties, setShowTrashProperties] = useState(false);
  const [propertiesItem, setPropertiesItem] = useState(null);
  const [trashContextMenu, setTrashContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    targetId: null
  });
  
  // 窗口管理状态
  const [currentBoardWindows, setCurrentBoardWindows] = useState([]);
  const [minimizedWindows, setMinimizedWindows] = useState(new Set());
  const [hiddenWindows, setHiddenWindows] = useState(new Set());
  const [focusedWindowId, setFocusedWindowId] = useState(null);

  // 系统时间更新
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);

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

  const handleStartMenuRenameSubmit = async (targetType, targetId) => {
    if (editingItemName && editingItemName.trim()) {
      try {
        const url = targetType === 'course' 
          ? `http://localhost:8081/api/courses/${targetId}/rename?new_name=${encodeURIComponent(editingItemName.trim())}`
          : `http://localhost:8081/api/boards/${targetId}/rename?new_name=${encodeURIComponent(editingItemName.trim())}`;
          
        const response = await fetch(url, { method: 'PUT' });
        if (response.ok) {
          showToast('重命名成功', 'success');
          await fetchCourses();
          if (targetType === 'board') {
            // 刷新当前课程的展板列表
            if (activeCourseId) {
              const event = new CustomEvent('refresh-boards', { detail: { courseId: activeCourseId } });
              window.dispatchEvent(event);
            }
          }
        } else {
          showToast('重命名失败', 'error');
        }
      } catch (error) {
        console.error('重命名操作失败:', error);
        showToast('操作失败', 'error');
      }
    }
    setEditingItemId(null);
    setEditingItemName('');
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
        // 关键：恢复后立即刷新课程和展板列表，无需手动刷新浏览器
        await fetchCourses();
        showToast('项目恢复成功！', 'success');
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
      title: t('confirm_delete_title'),
      message: t('confirm_delete_msg'),
      icon: 'win98-icon-warning'
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
      title: t('confirm_empty_trash_title'),
      message: t('confirm_empty_trash_msg'),
      icon: 'win98-icon-warning'
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

  // 回收站右键菜单处理
  const handleTrashContextMenu = (e, targetId = null) => {
    e.preventDefault();
    e.stopPropagation();
    setTrashContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      targetId: targetId
    });
    if (targetId) {
      setSelectedTrashId(targetId);
    }
  };

  const closeTrashContextMenu = () => {
    setTrashContextMenu(prev => ({ ...prev, visible: false }));
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

      if (showStartMenu && !clickedInsideStartMenu && !clickedStartButton && !clickedContextMenu) {
        setShowStartMenu(false);
        setShowCreateCourseInput(false); // 重置输入框状态
        setNewCourseName(''); // 清空输入内容
        setShowCreateBoardInput(false); // 重置新建展板输入框状态
        setNewBoardName(''); // 清空展板输入内容
        setActiveCourseId(null);
        setEditingItemId(null);
        setEditingItemName('');
        setStartMenuContextMenu({ visible: false, x: 0, y: 0, targetType: null, targetData: null });
      } else if (startMenuContextMenu.visible && !clickedContextMenu) {
        setStartMenuContextMenu({ visible: false, x: 0, y: 0, targetType: null, targetData: null });
      }
      
      // 关闭任务栏右键菜单
      if (showTaskbarContextMenu && !event.target.closest('.taskbar-context-menu')) {
        setShowTaskbarContextMenu(false);
      }

      // 关闭回收站右键菜单
      if (trashContextMenu.visible && !event.target.closest('.trash-context-menu')) {
        closeTrashContextMenu();
      }
    };

    if (showStartMenu || showTaskbarContextMenu || startMenuContextMenu.visible || trashContextMenu.visible) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showStartMenu, showTaskbarContextMenu, startMenuContextMenu.visible, trashContextMenu.visible]);

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
              setShowStartMenu={setShowStartMenu}
              showStartMenu={showStartMenu} // Add this prop
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
            <span className="start-text">{t('start')}</span>
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
          <div className="taskbar-separator" style={{ marginLeft: 'auto' }}></div>
          <div className="taskbar-tray" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
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
                  title={t('ai_assistant_chat')}
                  style={{ minWidth: 'auto', width: '80px' }}
                >
                  <span className="taskbar-icon win98-icon win98-icon-chat"></span>
                  <span className="taskbar-text">{t('ai_assistant')}</span>
                </button>
                
                <button 
                  className="taskbar-item message-center-taskbar-btn"
                  onClick={() => {
                    const event = new CustomEvent('toggleMessageCenter');
                    if (typeof window !== 'undefined') {
                      window.dispatchEvent(event);
                    }
                  }}
                  title={t('message_center')}
                  style={{ minWidth: 'auto', width: '90px' }}
                >
                  <span className="taskbar-icon win98-icon win98-icon-mail"></span>
                  <span className="taskbar-text">{t('message')}</span>
                </button>
              </>
            )}
            
            {/* 连接状态指示器 */}
            <div className="connection-status" style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '2px 8px' }}>
              <span className={`win98-icon ${isConnected ? 'win98-icon-connected' : 'win98-icon-disconnected'}`}></span>
              <span className="status-text" style={{ fontSize: '11px', color: 'black' }}>
                {isConnected ? t('connected') : t('disconnected')}
              </span>
            </div>
            
            {/* 系统时间显示 */}
            <div 
              className="taskbar-clock" 
              title={currentTime.toLocaleString('zh-CN')}
              onClick={() => {
                const event = new CustomEvent('togglePlannerWindow');
                if (typeof window !== 'undefined') {
                  window.dispatchEvent(event);
                }
              }}
              style={{ cursor: 'pointer' }}
            >
              <div className="clock-time">
                {currentTime.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })}
              </div>
              <div className="clock-date">
                {currentTime.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '/')}
              </div>
            </div>

          </div>
        </div>
      </div>
      
      {/* 任务栏右键菜单 */}
      {showTaskbarContextMenu && (
        <div 
          ref={taskbarMenuRef}
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
                  <span className="menu-text">{t('create_course')}</span>
                </div>
              ) : (
                <div className="start-menu-item start-menu-input-container">
                  <input
                    type="text"
                    placeholder={t('course_name_placeholder')}
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
                    className={`start-menu-item ${activeCourseId === course.id ? 'active' : ''} ${dragOverInfo.id === course.id ? `drag-over-${dragOverInfo.position}` : ''}`}
                    onClick={(e) => handleCourseClick(course.id, e)}
                    onContextMenu={(e) => handleStartMenuContextMenuOpen(e, 'course', course)}
                    draggable
                    onDragStart={(e) => handleDragStart(e, 'course', course)}
                    onDragEnd={handleDragEnd}
                    onDragOver={(e) => handleDragOver(e, course.id)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, 'course', course)}
                  >
                    <span className="menu-icon win98-icon win98-icon-folder"></span>
                    {editingItemId === course.id ? (
                      <div className="start-menu-input-container" onClick={(e) => e.stopPropagation()}>
                        <input
                          autoFocus
                          className="start-menu-input"
                          value={editingItemName}
                          onChange={(e) => setEditingItemName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleStartMenuRenameSubmit('course', course.id);
                            if (e.key === 'Escape') setEditingItemId(null);
                          }}
                          onBlur={() => handleStartMenuRenameSubmit('course', course.id)}
                        />
                      </div>
                    ) : (
                      <span className="menu-text">{course.name || t('unnamed_course')}</span>
                    )}
                    <span className="menu-arrow">▶</span>
                  </div>
                ))
              )}
              {(!courses || courses.length === 0) && (
                <div className="start-menu-item" style={{ color: '#999', fontStyle: 'italic' }}>
                  <span className="menu-text">{t('no_courses')}（调试：courses={JSON.stringify(courses)}）</span>
                </div>
              )}
              
              {/* 分界线 */}
              <div className="menu-separator"></div>
              
              {/* 回收站 */}
              <div 
                className="start-menu-item"
                onClick={() => {
                  loadTrashItems();
                  loadTrashSize();
                  setShowTrash(true);
                  setShowStartMenu(false);
                }}
              >
                <span className="menu-icon win98-icon win98-icon-recycle"></span>
                <span className="menu-text">{t('recycle_bin')}</span>
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
                <span className="menu-text">{t('console')}</span>
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
                      <span className="submenu-text">{t('create_board')}</span>
                    </div>
                  ) : (
                    <div className="submenu-item start-menu-input-container">
                      <input
                        type="text"
                        placeholder={t('board_name_placeholder')}
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
                      className={`submenu-item ${dragOverInfo.id === board.id ? `drag-over-${dragOverInfo.position}` : ''}`}
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
                      draggable
                      onDragStart={(e) => handleDragStart(e, 'board', board)}
                      onDragEnd={handleDragEnd}
                      onDragOver={(e) => handleDragOver(e, board.id)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, 'board', board)}
                    >
                      <span className="submenu-icon win98-icon win98-icon-clipboard"></span>
                      {editingItemId === board.id ? (
                        <div className="start-menu-input-container" onClick={(e) => e.stopPropagation()}>
                          <input
                            autoFocus
                            className="start-menu-input"
                            value={editingItemName}
                            onChange={(e) => setEditingItemName(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleStartMenuRenameSubmit('board', board.id);
                              if (e.key === 'Escape') setEditingItemId(null);
                            }}
                            onBlur={() => handleStartMenuRenameSubmit('board', board.id)}
                          />
                        </div>
                      ) : (
                        <span className="submenu-text">{board.name || t('unnamed_board')}</span>
                      )}
                    </div>
                  ))}
                  
                  {(!courseBoards[activeCourseId] || courseBoards[activeCourseId].length === 0) && (
                    <div className="submenu-empty">
                      {t('no_boards')}
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
          ref={startMenuContextRef}
          className="start-menu-context-menu"
          style={{ left: `${startMenuContextMenu.x}px`, top: `${startMenuContextMenu.y}px` }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {startMenuContextMenu.targetType === 'board' && (
            <>
              <div className="context-menu-item" onClick={() => handleStartMenuContextMenuAction('open-folder')}>
                <span className="menu-icon win98-icon win98-icon-folder"></span>
                <span className="menu-text">{t('open_in_explorer')}</span>
              </div>
              <div className="context-menu-separator"></div>
            </>
          )}
          <div className="context-menu-item" onClick={() => handleStartMenuContextMenuAction('rename')}>
            <span className="menu-icon win98-icon win98-icon-edit"></span>
            <span className="menu-text">{t('rename')}</span>
          </div>
          <div className="context-menu-item" onClick={() => handleStartMenuContextMenuAction('delete')}>
            <span className="menu-icon win98-icon win98-icon-delete"></span>
            <span className="menu-text">{t('delete')}</span>
          </div>
        </div>
      )}
      
      {/* 回收站弹窗 (2D 图标排列) */}
      {showTrash && (
        <div className="modal-overlay" onClick={() => {
          setShowTrash(false);
          setSelectedTrashId(null);
        }}>
          <div className="trash-modal" onClick={(e) => {
            e.stopPropagation();
            if (!e.target.closest('.trash-grid-item')) {
              setSelectedTrashId(null);
            }
          }} onContextMenu={(e) => handleTrashContextMenu(e)}>
            <div className="trash-header">
              <h3>
                <span className="win98-icon win98-icon-recycle" style={{transform: 'scale(0.8)'}}></span>
                {t('recycle_bin')}
              </h3>
              <button className="win98-msgbox-close" onClick={() => {
                setShowTrash(false);
                setSelectedTrashId(null);
              }}>×</button>
            </div>

            <div className="trash-toolbar">
              <button className="trash-toolbar-btn" onClick={handleEmptyTrash}>
                {t('empty_trash')}
              </button>
              <div style={{position: 'relative', zIndex: 32000}}>
                <button 
                  className={`trash-toolbar-btn ${showTrashViewMenu ? 'active' : ''}`}
                  onClick={() => setShowTrashViewMenu(!showTrashViewMenu)}
                >
                  {t('view')}
                </button>
                {showTrashViewMenu && (
                  <div className="trash-view-menu" onClick={(e) => e.stopPropagation()}>
                    <div className={`context-menu-item ${trashSortConfig.field === 'name' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, field: 'name'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.field === 'name' ? '• ' : ''}{t('sort_name')}</span>
                    </div>
                    <div className={`context-menu-item ${trashSortConfig.field === 'created_at' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, field: 'created_at'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.field === 'created_at' ? '• ' : ''}{t('sort_created')}</span>
                    </div>
                    <div className={`context-menu-item ${trashSortConfig.field === 'deleted_at' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, field: 'deleted_at'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.field === 'deleted_at' ? '• ' : ''}{t('sort_deleted')}</span>
                    </div>
                    <div className={`context-menu-item ${trashSortConfig.field === 'type' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, field: 'type'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.field === 'type' ? '• ' : ''}{t('sort_type')}</span>
                    </div>
                    <div className="menu-separator"></div>
                    <div className={`context-menu-item ${trashSortConfig.order === 'asc' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, order: 'asc'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.order === 'asc' ? '• ' : ''}{t('sort_asc')}</span>
                    </div>
                    <div className={`context-menu-item ${trashSortConfig.order === 'desc' ? 'active' : ''}`}
                         onClick={() => { setTrashSortConfig(prev => ({...prev, order: 'desc'})); setShowTrashViewMenu(false); }}>
                      <span className="menu-text">{trashSortConfig.order === 'desc' ? '• ' : ''}{t('sort_desc')}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="trash-content" onClick={() => setShowTrashViewMenu(false)}>
              {trashItems.filter(item => !item.parent_id).length > 0 ? (
                trashItems.filter(item => !item.parent_id).sort((a, b) => {
                  let valA, valB;
                  const config = trashSortConfig;
                  
                  if (config.field === 'name') {
                    const getDisplayName = (item) => {
                      const windowData = item.window_data || {};
                      return (['course', 'board'].includes(windowData.type) && windowData.data?.name) 
                        ? windowData.data.name 
                        : item.original_name;
                    };
                    valA = getDisplayName(a);
                    valB = getDisplayName(b);
                  } else if (config.field === 'type') {
                    valA = a.window_data?.type || 'file';
                    valB = b.window_data?.type || 'file';
                  } else if (config.field === 'created_at') {
                    valA = a.window_data?.data?.created_at || 0;
                    valB = b.window_data?.data?.created_at || 0;
                  } else {
                    valA = a.deleted_at;
                    valB = b.deleted_at;
                  }

                  if (valA < valB) return config.order === 'asc' ? -1 : 1;
                  if (valA > valB) return config.order === 'asc' ? 1 : -1;
                  return 0;
                }).map(item => {
                  const windowData = item.window_data || {};
                  const isSpecialItem = ['course', 'board'].includes(windowData.type);
                  const displayName = isSpecialItem && windowData.data?.name 
                    ? windowData.data.name
                    : item.original_name;
                  
                  // 使用系统已有的图标类
                  let iconClass = "win98-icon ";
                  if (windowData.type === 'course') {
                    iconClass += "win98-icon-folder";
                  } else if (windowData.type === 'board') {
                    iconClass += "win98-icon-clipboard";
                  } else {
                    // 根据文件名后缀判断
                    const ext = item.original_name.toLowerCase().split('.').pop();
                    if (ext === 'pdf') {
                      iconClass += "win98-icon-pdf";
                    } else if (['md', 'json', 'txt'].includes(ext)) {
                      iconClass += "win98-icon-text";
                    } else {
                      iconClass += "win98-icon-default";
                    }
                  }

                  return (
                    <div 
                      key={item.id} 
                      className={`trash-grid-item ${selectedTrashId === item.id ? 'selected' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTrashId(item.id);
                      }}
                      onDoubleClick={() => handleRestoreFromTrash(item.id)}
                      onContextMenu={(e) => handleTrashContextMenu(e, item.id)}
                    >
                      <div className={`trash-icon-img ${iconClass}`}></div>
                      <div className="trash-icon-label">{displayName}</div>
                    </div>
                  );
                })
              ) : (
                <div className="empty-trash-watermark" style={{
                  position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                  opacity: 0.1, pointerEvents: 'none', textAlign: 'center'
                }}>
                  <div className="win98-icon win98-icon-recycle" style={{width: '64px', height: '64px'}}></div>
                  <p>回收站为空</p>
                </div>
              )}
            </div>

            <div className="trash-statusbar">
              <div className="status-field count">
                {trashItems.filter(item => !item.parent_id).length} 个对象
              </div>
              <div className="status-field size">
                {formatSize(trashSize)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 回收站右键菜单 */}
      {trashContextMenu.visible && (
        <div 
          className="start-menu-context-menu trash-context-menu"
          style={{ left: `${trashContextMenu.x}px`, top: `${trashContextMenu.y}px` }}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          {trashContextMenu.targetId ? (
            <>
              <div className="context-menu-item" onClick={() => {
                handleRestoreFromTrash(trashContextMenu.targetId);
                closeTrashContextMenu();
              }}>
                <span className="menu-text">还原(R)</span>
              </div>
              <div className="menu-separator"></div>
              <div className="context-menu-item" onClick={() => {
                handlePermanentDelete(trashContextMenu.targetId);
                closeTrashContextMenu();
              }}>
                <span className="menu-text">删除(D)</span>
              </div>
              <div className="context-menu-item" onClick={() => {
                const item = trashItems.find(i => i.id === trashContextMenu.targetId);
                if (item) {
                  setPropertiesItem(item);
                  setShowTrashProperties(true);
                }
                closeTrashContextMenu();
              }}>
                <span className="menu-text">属性(P)</span>
              </div>
            </>
          ) : (
            <>
              <div className="context-menu-item" onClick={() => {
                handleEmptyTrash();
                closeTrashContextMenu();
              }}>
                <span className="menu-text">清空回收站(B)</span>
              </div>
              <div className="menu-separator"></div>
              <div className="context-menu-item" onClick={() => {
                loadTrashItems();
                loadTrashSize();
                closeTrashContextMenu();
              }}>
                <span className="menu-text">刷新(E)</span>
              </div>
            </>
          )}
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
              <span className={`win98-dialog-icon win98-icon ${confirmDialog.icon || 'win98-icon-warning'}`}></span>
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

      {/* 回收站属性对话框 */}
      {showTrashProperties && propertiesItem && (
        <div className="win98-modal-overlay" style={{zIndex: 35000, display: 'flex', alignItems: 'center', justifyContent: 'center'}} onClick={() => setShowTrashProperties(false)}>
          <div className="win98-properties-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="win98-msgbox-header">
              <span className="win98-msgbox-title">属性</span>
              <button className="win98-msgbox-close" onClick={() => setShowTrashProperties(false)}>×</button>
            </div>
            <div className="properties-tabs">
              <div className="properties-tab active">常规</div>
            </div>
            
            <div className="properties-content">
              <div className="properties-header">
                <div className={`win98-icon ${
                  propertiesItem.window_data?.type === 'course' ? 'win98-icon-folder' : 
                  propertiesItem.window_data?.type === 'board' ? 'win98-icon-clipboard' : 
                  propertiesItem.original_name.toLowerCase().endsWith('.pdf') ? 'win98-icon-pdf' : 'win98-icon-default'
                }`} style={{width: '32px', height: '32px'}}></div>
                <div style={{fontWeight: 'bold', fontSize: '12px'}}>
                  {propertiesItem.window_data?.data?.name || propertiesItem.original_name}
                </div>
              </div>
              
              <div className="properties-row">
                <div className="properties-label">类型:</div>
                <div className="properties-value">
                  {propertiesItem.window_data?.type === 'course' ? '课程文件夹' : 
                   propertiesItem.window_data?.type === 'board' ? '展板文件夹' : '文件'}
                </div>
              </div>
              
              <div className="properties-row">
                <div className="properties-label">原始位置:</div>
                <div className="properties-value">{propertiesItem.original_path}</div>
              </div>
              
              <div className="menu-separator" style={{margin: '10px 0'}}></div>
              
              <div className="properties-row">
                <div className="properties-label">创建时间:</div>
                <div className="properties-value">
                  {propertiesItem.window_data?.data?.created_at ? 
                    new Date(propertiesItem.window_data.data.created_at).toLocaleString() : '未知'}
                </div>
              </div>
              
              <div className="properties-row">
                <div className="properties-label">删除时间:</div>
                <div className="properties-value">
                  {new Date(propertiesItem.deleted_at).toLocaleString()}
                </div>
              </div>
              
              <div className="menu-separator" style={{margin: '10px 0'}}></div>
              
              <div className="properties-row">
                <div className="properties-label">大小:</div>
                <div className="properties-value">
                  {formatSize(propertiesItem.file_size)} ({propertiesItem.file_size.toLocaleString()} 字节)
                </div>
              </div>
            </div>
            
            <div className="properties-footer">
              <button className="win98-msgbox-btn" style={{minWidth: '75px'}} onClick={() => setShowTrashProperties(false)}>确定</button>
            </div>
          </div>
        </div>
      )}

      {/* 全局通知弹窗 (Win98 风格中心对话框) */}
      {toast.visible && (
        <div className="win98-modal-overlay">
          <div className="win98-msgbox">
            <div className="win98-msgbox-header">
              <span className="win98-msgbox-title">WhatNote</span>
              <button className="win98-msgbox-close" onClick={hideToast}>×</button>
            </div>
            <div className="win98-msgbox-body">
              <div className={`win98-msgbox-icon ${toast.type}`}></div>
              <div className="win98-msgbox-content">
                <div className="win98-msgbox-message">{toast.message}</div>
              </div>
            </div>
            <div className="win98-msgbox-footer">
              <button className="win98-msgbox-btn" onClick={hideToast}>OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// 窗口图标辅助函数
const getWindowIcon = (type) => {
  return '';
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
    'console': 'win98-icon win98-icon-console',
    'plugin-manager': 'win98-icon win98-icon-plugin'
  };
  return typeIconClass[type] || 'win98-icon win98-icon-default';
};

export default App; 