import React, { useEffect, useMemo, useState } from 'react';
import './CalendarPlannerWindow.css';

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

const getMonthMatrix = (date) => {
  const year = date.getFullYear();
  const month = date.getMonth();

  const firstDayOfMonth = new Date(year, month, 1);
  const firstWeekday = firstDayOfMonth.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const prevMonthDays = new Date(year, month, 0).getDate();

  const cells = [];
  const totalCells = 42; // 6 行 * 7 列

  for (let i = 0; i < totalCells; i++) {
    const dayOffset = i - firstWeekday;

    if (dayOffset < 0) {
      // 上月日期
      const dateNumber = prevMonthDays + dayOffset + 1;
      const cellDate = new Date(year, month - 1, dateNumber);
      cells.push({
        key: `prev-${dateNumber}`,
        date: cellDate,
        inCurrentMonth: false,
      });
    } else if (dayOffset >= daysInMonth) {
      // 下月日期
      const dateNumber = dayOffset - daysInMonth + 1;
      const cellDate = new Date(year, month + 1, dateNumber);
      cells.push({
        key: `next-${dateNumber}`,
        date: cellDate,
        inCurrentMonth: false,
      });
    } else {
      // 当月日期
      const dateNumber = dayOffset + 1;
      const cellDate = new Date(year, month, dateNumber);
      cells.push({
        key: `current-${dateNumber}`,
        date: cellDate,
        inCurrentMonth: true,
      });
    }
  }

  return cells;
};

const formatDateLabel = (date) => {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
};

const formatDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// 已移除 loadInitialPlannerData，改为从后端加载

function CalendarPlannerWindow({ initialDate }) {
  const [currentDate, setCurrentDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [selectedDate, setSelectedDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [plannerData, setPlannerData] = useState({});
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskTime, setNewTaskTime] = useState('');
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editTaskTitle, setEditTaskTitle] = useState('');
  const [editTaskTime, setEditTaskTime] = useState('');

  const today = useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);

  const monthMatrix = useMemo(() => getMonthMatrix(currentDate), [currentDate]);
  const selectedDateKey = useMemo(() => formatDateKey(selectedDate), [selectedDate]);

  const tasksForSelectedDate = useMemo(() => {
    const tasks = plannerData[selectedDateKey] || [];
    return [...tasks].sort((a, b) => {
      if (a.completed !== b.completed) {
        return a.completed ? 1 : -1;
      }
      return a.time.localeCompare(b.time);
    });
  }, [plannerData, selectedDateKey]);

  // 从后端加载日历数据
  const loadCalendarData = async () => {
    try {
      const response = await fetch('http://localhost:8081/api/calendar/tasks');
      if (response.ok) {
        const data = await response.json();
        setPlannerData(data);
        console.log('[Calendar] 已从后端加载日历数据');
      }
    } catch (error) {
      console.error('[Calendar] 加载日历数据失败:', error);
    }
  };

  useEffect(() => {
    loadCalendarData();
  }, []);

  // 监听控制台刷新日历事件
  useEffect(() => {
    const handleRefreshCalendar = () => {
      console.log('[Calendar] 收到刷新日历事件');
      loadCalendarData();
    };

    window.addEventListener('refreshCalendar', handleRefreshCalendar);

    return () => {
      window.removeEventListener('refreshCalendar', handleRefreshCalendar);
    };
  }, []);

  // 保存到后端（替代 localStorage）
  useEffect(() => {
    const saveCalendarData = async () => {
      try {
        await fetch('http://localhost:8081/api/calendar/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(plannerData)
        });
        console.log('[Calendar] 已保存日历数据到后端');
      } catch (error) {
        console.warn('[Calendar] 保存日历数据失败:', error);
      }
    };
    
    // 防止初始加载时立即保存
    const timer = setTimeout(saveCalendarData, 500);
    return () => clearTimeout(timer);
  }, [plannerData]);

  const isSameDay = (a, b) => {
    return a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();
  };

  const handlePrevMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleToday = () => {
    const now = new Date();
    const normalized = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    setCurrentDate(normalized);
    setSelectedDate(normalized);
    setNewTaskName('');
    setNewTaskTime('');
  };

  const resetForm = () => {
    setNewTaskName('');
    setNewTaskTime('');
  };

  const handleAddTask = () => {
    const trimmedName = newTaskName.trim();
    if (!trimmedName || !newTaskTime) {
      return;
    }

    const newTask = {
      id: Date.now(),
      title: trimmedName,
      time: newTaskTime,
      completed: false,
      createdAt: new Date().toISOString()
    };

    setPlannerData(prev => {
      const existing = prev[selectedDateKey] || [];
      const updatedTasks = [...existing, newTask];
      return {
        ...prev,
        [selectedDateKey]: updatedTasks
      };
    });

    resetForm();
  };

  const handleToggleTask = (taskId) => {
    setPlannerData(prev => {
      const existing = prev[selectedDateKey] || [];
      const updatedTasks = existing.map(task =>
        task.id === taskId ? { ...task, completed: !task.completed, completedAt: !task.completed ? new Date().toISOString() : null } : task
      );
      return {
        ...prev,
        [selectedDateKey]: updatedTasks
      };
    });
  };

  const handleStartEdit = (task) => {
    setEditingTaskId(task.id);
    setEditTaskTitle(task.title);
    setEditTaskTime(task.time);
  };

  const handleSaveEdit = () => {
    if (!editTaskTitle.trim() || !editTaskTime) {
      return;
    }

    setPlannerData(prev => {
      const existing = prev[selectedDateKey] || [];
      const updatedTasks = existing.map(task =>
        task.id === editingTaskId ? { ...task, title: editTaskTitle, time: editTaskTime } : task
      );
      return {
        ...prev,
        [selectedDateKey]: updatedTasks
      };
    });

    setEditingTaskId(null);
    setEditTaskTitle('');
    setEditTaskTime('');
  };

  const handleCancelEdit = () => {
    setEditingTaskId(null);
    setEditTaskTitle('');
    setEditTaskTime('');
  };

  const handleDeleteTask = (taskId) => {
    setPlannerData(prev => {
      const existing = prev[selectedDateKey] || [];
      const updatedTasks = existing.filter(task => task.id !== taskId);
      return {
        ...prev,
        [selectedDateKey]: updatedTasks
      };
    });
  };

  const handleFormKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAddTask();
    }
  };

  const handleEditKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleSaveEdit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      handleCancelEdit();
    }
  };

  return (
    <div className="calendar-planner-window">
      <div className="calendar-panel">
        <div className="calendar-header">
          <button className="calendar-nav-btn" onClick={handlePrevMonth} aria-label="上一月">◀</button>
          <div className="calendar-header-title">
            <div className="calendar-month-label">{currentDate.getFullYear()}年{currentDate.getMonth() + 1}月</div>
            <div className="calendar-subtitle">快速查看当月安排</div>
          </div>
          <button className="calendar-nav-btn" onClick={handleNextMonth} aria-label="下一月">▶</button>
        </div>
        <div className="calendar-weekdays">
          {WEEKDAYS.map(weekday => (
            <div key={weekday} className="calendar-weekday">{weekday}</div>
          ))}
        </div>
        <div className="calendar-grid">
          {monthMatrix.map(cell => {
            const normalizedCell = new Date(cell.date.getFullYear(), cell.date.getMonth(), cell.date.getDate());
            const isTodayCell = isSameDay(normalizedCell, today);
            const isSelected = isSameDay(normalizedCell, selectedDate);

            return (
              <button
                key={cell.key}
                className={[
                  'calendar-cell',
                  cell.inCurrentMonth ? 'current-month' : 'adjacent-month',
                  isTodayCell ? 'is-today' : '',
                  isSelected ? 'is-selected' : ''
                ].join(' ')}
                onClick={() => setSelectedDate(normalizedCell)}
                aria-label={formatDateLabel(cell.date)}
              >
                <span className="calendar-date-number">{cell.date.getDate()}</span>
              </button>
            );
          })}
        </div>
        <div className="calendar-footer">
          <button className="calendar-footer-btn" onClick={handleToday}>回到今天</button>
          <div className="calendar-footer-label">选中日期将在右侧展示，计划功能稍后补充</div>
        </div>
      </div>

      <div className="planner-panel">
        <div className="planner-header">
          <div>
            <div className="planner-selected-date">{formatDateLabel(selectedDate)}</div>
            <div className="planner-selected-weekday">星期{WEEKDAYS[selectedDate.getDay()]}</div>
          </div>
          <div className="planner-actions" onKeyDown={handleFormKeyDown}>
            <input
              className="planner-input planner-input-title"
              type="text"
              placeholder="新增待办名称"
              value={newTaskName}
              onChange={(e) => setNewTaskName(e.target.value)}
            />
            <input
              className="planner-input planner-input-time"
              type="time"
              value={newTaskTime}
              onChange={(e) => setNewTaskTime(e.target.value)}
              step={60}
            />
            <button
              className="planner-action-btn"
              type="button"
              onClick={handleAddTask}
              disabled={!newTaskName.trim() || !newTaskTime}
            >
              添加待办
            </button>
          </div>
        </div>

        <div className="planner-content">
          {tasksForSelectedDate.length === 0 ? (
            <div className="planner-placeholder">
              <div className="planner-placeholder-title">暂未添加待办</div>
              <p>使用上方输入框添加新的计划事项，支持精确到分钟的开始时间。</p>
              <p>勾选事项即可标记完成，完成后的待办会自动移动到列表底部。</p>
            </div>
          ) : (
            <div className="planner-task-list">
              {tasksForSelectedDate.map(task => (
                <div
                  key={task.id}
                  className={`planner-task ${task.completed ? 'completed' : ''} ${editingTaskId === task.id ? 'editing' : ''}`}
                >
                  {editingTaskId === task.id ? (
                    // 编辑模式
                    <div className="planner-task-edit">
                      <input
                        type="time"
                        value={editTaskTime}
                        onChange={(e) => setEditTaskTime(e.target.value)}
                        onKeyDown={handleEditKeyDown}
                        className="planner-edit-time"
                      />
                      <input
                        type="text"
                        value={editTaskTitle}
                        onChange={(e) => setEditTaskTitle(e.target.value)}
                        onKeyDown={handleEditKeyDown}
                        className="planner-edit-title"
                        autoFocus
                      />
                      <button 
                        className="planner-btn planner-btn-save"
                        onClick={handleSaveEdit}
                        title="保存 (Enter)"
                      >
                        ✓
                      </button>
                      <button 
                        className="planner-btn planner-btn-cancel"
                        onClick={handleCancelEdit}
                        title="取消 (Esc)"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    // 显示模式
                    <>
                      <label className="planner-task-content">
                        <input
                          type="checkbox"
                          checked={task.completed}
                          onChange={() => handleToggleTask(task.id)}
                        />
                        <span className="planner-task-time">{task.time}</span>
                        <span className="planner-task-title">{task.title}</span>
                      </label>
                      <div className="planner-task-actions">
                        <button 
                          className="planner-btn planner-btn-edit"
                          onClick={() => handleStartEdit(task)}
                          title="编辑"
                        >
                          ✏️
                        </button>
                        <button 
                          className="planner-btn planner-btn-delete"
                          onClick={() => handleDeleteTask(task.id)}
                          title="删除"
                        >
                          🗑️
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CalendarPlannerWindow;

