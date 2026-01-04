import React, { useEffect, useMemo, useState, useCallback } from 'react';
import './CalendarPlannerWindow.css';
import { useLanguage } from '../i18n/LanguageContext';

// 星期数组将在组件内部根据语言动态生成

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

// formatDateLabel 将在组件内部根据语言动态生成

const formatDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// 已移除 loadInitialPlannerData，改为从后端加载

function CalendarPlannerWindow({ initialDate }) {
  const { t, language } = useLanguage();
  const [currentDate, setCurrentDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [selectedDate, setSelectedDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [plannerData, setPlannerData] = useState({});
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskTime, setNewTaskTime] = useState('');
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editTaskTitle, setEditTaskTitle] = useState('');
  const [editTaskTime, setEditTaskTime] = useState('');

  // 根据语言动态生成星期数组（用于日历表头显示，单字或缩写）
  const WEEKDAYS = useMemo(() => [
    t('calendar_weekday_0'),
    t('calendar_weekday_1'),
    t('calendar_weekday_2'),
    t('calendar_weekday_3'),
    t('calendar_weekday_4'),
    t('calendar_weekday_5'),
    t('calendar_weekday_6')
  ], [t]);

  // 根据语言动态生成完整星期名称数组（用于显示选中日期的星期）
  const FULL_WEEKDAYS = useMemo(() => [
    t('calendar_weekday_full_0'),
    t('calendar_weekday_full_1'),
    t('calendar_weekday_full_2'),
    t('calendar_weekday_full_3'),
    t('calendar_weekday_full_4'),
    t('calendar_weekday_full_5'),
    t('calendar_weekday_full_6')
  ], [t]);

  const today = useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);

  // 根据语言格式化日期标签
  const formatDateLabel = useCallback((date) => {
    if (language.startsWith('en')) {
      // 英文格式: January 1, 2024
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    } else if (language.startsWith('ja')) {
      // 日文格式: 2024年1月1日
      return `${date.getFullYear()}${t('date_format_year')}${date.getMonth() + 1}${t('date_format_month')}${date.getDate()}${t('date_format_day')}`;
    } else {
      // 中文格式: 2024年1月1日
      return `${date.getFullYear()}${t('date_format_year')}${date.getMonth() + 1}${t('date_format_month')}${date.getDate()}${t('date_format_day')}`;
    }
  }, [t, language]);

  // 根据语言格式化月份标签
  const formatMonthLabel = useCallback((date) => {
    if (language.startsWith('en')) {
      // 英文格式: January 2024
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });
    } else if (language.startsWith('ja')) {
      // 日文格式: 2024年1月
      return `${date.getFullYear()}${t('date_format_year')}${date.getMonth() + 1}${t('date_format_month')}`;
    } else {
      // 中文格式: 2024年1月
      return `${date.getFullYear()}${t('date_format_year')}${date.getMonth() + 1}${t('date_format_month')}`;
    }
  }, [t, language]);

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
          <button className="calendar-nav-btn" onClick={handlePrevMonth} aria-label={t('calendar_prev_month')}>◀</button>
          <div className="calendar-header-title">
            <div className="calendar-month-label">{formatMonthLabel(currentDate)}</div>
            <div className="calendar-subtitle">{t('calendar_subtitle')}</div>
          </div>
          <button className="calendar-nav-btn" onClick={handleNextMonth} aria-label={t('calendar_next_month')}>▶</button>
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
          <button className="calendar-footer-btn" onClick={handleToday}>{t('calendar_back_to_today')}</button>
        </div>
      </div>

      <div className="planner-panel">
        <div className="planner-header">
          <div>
            <div className="planner-selected-date">{formatDateLabel(selectedDate)}</div>
            <div className="planner-selected-weekday">{FULL_WEEKDAYS[selectedDate.getDay()]}</div>
          </div>
          <div className="planner-actions" onKeyDown={handleFormKeyDown}>
            <input
              className="planner-input planner-input-title"
              type="text"
              placeholder={t('planner_new_task_placeholder')}
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
              {t('planner_add_task')}
            </button>
          </div>
        </div>

        <div className="planner-content">
          {tasksForSelectedDate.length === 0 ? (
            <div className="planner-placeholder">
              <div className="planner-placeholder-title">{t('planner_no_tasks')}</div>
              <p>{t('planner_no_tasks_desc')}</p>
              <p>{t('planner_no_tasks_desc2')}</p>
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

