import React, { useEffect, useRef, useState, useCallback } from 'react';

// ============================================================
// GlobalTaskTray
// ------------------------------------------------------------
// 跨展板常驻的"持续任务托盘"。
//
// 监听全局事件 'whatnote:task-progress'，集中展示正在进行的耗时任务
// （流水线、批量 TTS、批量翻译等）。
//
// 事件 schema (CustomEvent detail):
//   {
//     task_id: string,                   // 唯一 ID（更新同一任务用同一 ID）
//     title: string,                     // 顶部标题
//     step_label?: string,               // 子步骤标签（一行小字）
//     progress?: { completed, total },   // 子进度（百分比条）
//     overall?: { current, total },      // 整体进度（用 N/M 显示）
//     status: 'running' | 'done' | 'failed' | 'aborted',
//     error?: string,                    // failed 时的简述
//     can_abort?: boolean,               // 是否显示 ✕
//     source?: { board_id, board_name, window_id, window_title },
//   }
//
// 中止：用户点 ✕ → window.dispatchEvent('whatnote:task-abort', {detail:{task_id}})
//      调用方监听该事件后中止本任务。
//
// 任务进入终态（done/failed/aborted）后 4 秒自动 fade out。
// 终态时同时 dispatch 'whatnote:task-summary' 让 BoardCanvas 调用 addMessage
// 把这条任务写入 MessageCenter 留档。
// ============================================================

const FADE_OUT_MS = 4000;

const STATUS_COLORS = {
  running:  { bg: '#dbe7fa', border: '#5b8ec9', accent: '#1565c0' },
  done:     { bg: '#e2f4e7', border: '#3aa55a', accent: '#1b6b35' },
  failed:   { bg: '#fae0e0', border: '#c95c5c', accent: '#a02020' },
  aborted:  { bg: '#eee0c0', border: '#a8842d', accent: '#664a0c' },
};

const GlobalTaskTray = () => {
  const [tasks, setTasks] = useState([]); // 数组保留顺序：先入先显
  const fadeTimers = useRef(new Map());   // task_id -> setTimeout id

  // 清除某任务的 fade timer
  const clearFadeTimer = (taskId) => {
    const tid = fadeTimers.current.get(taskId);
    if (tid) {
      clearTimeout(tid);
      fadeTimers.current.delete(taskId);
    }
  };

  // 安排某任务 fade out
  const scheduleFadeOut = useCallback((taskId) => {
    clearFadeTimer(taskId);
    const tid = setTimeout(() => {
      setTasks(prev => prev.filter(t => t.task_id !== taskId));
      fadeTimers.current.delete(taskId);
    }, FADE_OUT_MS);
    fadeTimers.current.set(taskId, tid);
  }, []);

  // upsert 任务
  const upsertTask = useCallback((detail) => {
    if (!detail || !detail.task_id) return;
    const isTerminal = ['done', 'failed', 'aborted'].includes(detail.status);
    setTasks(prev => {
      const idx = prev.findIndex(t => t.task_id === detail.task_id);
      if (idx === -1) {
        return [...prev, { ...detail, _arrived_at: Date.now() }];
      }
      const next = prev.slice();
      next[idx] = { ...prev[idx], ...detail };
      return next;
    });
    if (isTerminal) {
      scheduleFadeOut(detail.task_id);
      // 同时让 MessageCenter 留档
      try {
        window.dispatchEvent(new CustomEvent('whatnote:task-summary', {
          detail: {
            ...detail,
            time: new Date().toISOString(),
          }
        }));
      } catch (e) {
        // ignore
      }
    } else {
      clearFadeTimer(detail.task_id);
    }
  }, [scheduleFadeOut]);

  useEffect(() => {
    const handler = (evt) => {
      if (!evt || !evt.detail) return;
      upsertTask(evt.detail);
    };
    window.addEventListener('whatnote:task-progress', handler);
    return () => window.removeEventListener('whatnote:task-progress', handler);
  }, [upsertTask]);

  const handleAbort = (task) => {
    try {
      window.dispatchEvent(new CustomEvent('whatnote:task-abort', {
        detail: { task_id: task.task_id }
      }));
    } catch (e) {
      console.warn('dispatch task-abort failed', e);
    }
  };

  const handleDismiss = (taskId) => {
    clearFadeTimer(taskId);
    setTasks(prev => prev.filter(t => t.task_id !== taskId));
  };

  if (tasks.length === 0) return null;

  // 最多直接显示 3 条；剩下显示一个"+N"折叠提示
  const visible = tasks.slice(0, 3);
  const hidden = tasks.length - visible.length;

  return (
    <div
      style={{
        position: 'fixed',
        top: 8,
        right: 8,
        width: 320,
        zIndex: 12000,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        fontFamily: 'MS Sans Serif, sans-serif',
        fontSize: 11,
        pointerEvents: 'none', // 让卡片自己重新拿回 pointer-events
      }}
      aria-live="polite"
    >
      {visible.map(task => (
        <TaskCard
          key={task.task_id}
          task={task}
          onAbort={() => handleAbort(task)}
          onDismiss={() => handleDismiss(task.task_id)}
        />
      ))}
      {hidden > 0 && (
        <div style={{
          alignSelf: 'flex-end',
          padding: '2px 8px',
          background: '#1d1d1d',
          color: '#fff',
          fontSize: 10,
          borderRadius: 10,
          pointerEvents: 'auto',
        }}>
          +{hidden} {hidden === 1 ? '更多任务' : '更多任务'}
        </div>
      )}
    </div>
  );
};

function TaskCard({ task, onAbort, onDismiss }) {
  const palette = STATUS_COLORS[task.status] || STATUS_COLORS.running;
  const isTerminal = ['done', 'failed', 'aborted'].includes(task.status);

  // 子进度百分比
  const pct = (() => {
    const p = task.progress;
    if (!p || !p.total) return null;
    return Math.min(100, Math.round((p.completed || 0) * 100 / p.total));
  })();

  const statusIcon = ({
    running: '⏳',
    done:    '✓',
    failed:  '✗',
    aborted: '■',
  })[task.status] || '⏳';

  return (
    <div
      style={{
        pointerEvents: 'auto',
        background: palette.bg,
        border: `2px solid ${palette.border}`,
        borderLeft: `5px solid ${palette.accent}`,
        boxShadow: '2px 2px 0 rgba(0,0,0,0.15)',
        padding: '6px 8px',
        color: '#000',
        opacity: task.status === 'running' ? 0.97 : 0.92,
        transition: 'opacity 0.3s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ color: palette.accent, fontWeight: 'bold' }}>{statusIcon}</span>
        <span style={{ flex: 1, fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={task.title}>
          {task.title}
        </span>
        {task.overall && task.overall.total && (
          <span style={{ fontSize: 10, color: '#444' }}>
            {task.overall.current}/{task.overall.total}
          </span>
        )}
        {!isTerminal && task.can_abort && (
          <button
            onClick={onAbort}
            title="中止"
            style={{
              background: 'transparent',
              border: '1px solid #888',
              padding: '0 5px',
              cursor: 'pointer',
              fontSize: 10,
              color: '#a02020',
              lineHeight: '14px',
            }}
          >✕</button>
        )}
        {isTerminal && (
          <button
            onClick={onDismiss}
            title="关闭"
            style={{
              background: 'transparent',
              border: '1px solid #888',
              padding: '0 5px',
              cursor: 'pointer',
              fontSize: 10,
              color: '#444',
              lineHeight: '14px',
            }}
          >✕</button>
        )}
      </div>

      {task.step_label && (
        <div style={{ marginTop: 3, color: '#444', fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={task.step_label}>
          {task.step_label}
        </div>
      )}

      {pct != null && (
        <div style={{
          marginTop: 4,
          height: 8,
          background: '#fff',
          border: '1px solid #999',
          position: 'relative',
        }}>
          <div style={{
            width: `${pct}%`,
            height: '100%',
            background: palette.accent,
            transition: 'width 0.2s',
          }} />
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9, fontWeight: 'bold',
            mixBlendMode: 'difference',
            color: '#fff',
          }}>
            {task.progress ? `${task.progress.completed || 0}/${task.progress.total}` : `${pct}%`}
          </div>
        </div>
      )}

      {task.error && task.status === 'failed' && (
        <div style={{
          marginTop: 4,
          color: '#a02020',
          fontSize: 10,
          maxHeight: 40,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }} title={task.error}>
          {task.error}
        </div>
      )}

      {task.source && task.source.board_name && (
        <div style={{ marginTop: 3, fontSize: 9, color: '#777' }}>
          {task.source.board_name}
          {task.source.window_title ? ` / ${task.source.window_title}` : ''}
        </div>
      )}
    </div>
  );
}

export default GlobalTaskTray;
