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

const loadInitialPlannerData = () => {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const stored = window.localStorage.getItem('whatnotePlannerTasks');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed && typeof parsed === 'object') {
        return parsed;
      }
    }
  } catch (error) {
    console.warn('加载计划数据失败，使用默认数据', error);
  }
  return {};
};

function CalendarPlannerWindow({ initialDate }) {
  const [currentDate, setCurrentDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [selectedDate, setSelectedDate] = useState(() => initialDate ? new Date(initialDate) : new Date());
  const [plannerData, setPlannerData] = useState(() => loadInitialPlannerData());
  const [newTaskName, setNewTaskName] = useState('');
  const [newTaskTime, setNewTaskTime] = useState('');

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

  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem('whatnotePlannerTasks', JSON.stringify(plannerData));
      } catch (error) {
        console.warn('保存计划数据失败', error);
      }
    }
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

  const handleFormKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAddTask();
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
                <label
                  key={task.id}
                  className={`planner-task ${task.completed ? 'completed' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => handleToggleTask(task.id)}
                  />
                  <span className="planner-task-time">{task.time}</span>
                  <span className="planner-task-title">{task.title}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CalendarPlannerWindow;

