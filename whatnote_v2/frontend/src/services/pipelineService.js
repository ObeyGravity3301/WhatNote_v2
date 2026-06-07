// ============================================================
// pipelineService.js — 「一键生成」流水线编排（前端纯逻辑）
// ------------------------------------------------------------
// 顺序执行用户勾选的步骤，每个步骤都是已有的 SSE 接口；
// 通过 window CustomEvent 与 GlobalTaskTray 解耦：
//   • dispatch  'whatnote:task-progress'   报进度
//   • listen    'whatnote:task-abort'      响应中止
//
// 用法：
//   const ctrl = startPipeline({
//     boardId, windowId,
//     source: { board_id, board_name, window_id, window_title },
//     steps: [
//       { id: 'visual_extract', pages: [...], dpi: 300 },
//       { id: 'outline' },
//       { id: 'subdivide' },
//       { id: 'lesson_plan' },
//       { id: 'lesson_plan_normalize' },  // optional
//       { id: 'step_script', extra_user_instruction: '...' },
//       { id: 'step_audio' },
//     ],
//   });
//   // 上层只要监听 task-progress 就行。
//   ctrl.promise.then(result => {...});
// ============================================================

const API_BASE = 'http://localhost:8081';

const STEP_LABELS = {
  visual_extract:        '视觉提取页面',
  outline:               '生成大纲 (Stage 1)',
  subdivide:             '细分分段 (Stage 2)',
  lesson_plan:           '生成 Lesson Plan',
  lesson_plan_normalize: 'Normalize Lesson Plan',
  step_script:           '生成 Step Script',
  step_audio:            '合成 Step Audio',
};

// ============================================================
// SSE 解析助手：读取 ReadableStream 的 text/event-stream 数据
// 返回异步生成器，yield 每个 data 对象（已 JSON.parse）
// ============================================================
async function* readSSE(response, signal) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  try {
    while (true) {
      if (signal && signal.aborted) {
        try { reader.cancel(); } catch {}
        throw new DOMException('aborted', 'AbortError');
      }
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE 帧以 \n\n 分隔
      let idx;
      while ((idx = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;
          try {
            yield JSON.parse(raw);
          } catch (e) {
            // 部分 SSE 用纯文本，忽略
          }
        }
      }
    }
  } finally {
    try { reader.releaseLock(); } catch {}
  }
}

// ============================================================
// 单步执行器（每个 step 一个函数；签名一致）
//   ctx: { boardId, windowId, taskId, source, signal, emit }
//   emit({ overall, sub_label, progress, status })  上报进度
//   抛出 Error  视为失败
// 返回任意 result（写入流水线 result map）
// ============================================================

async function step_visual_extract(ctx, opts) {
  const { boardId, windowId, signal } = ctx;
  const pages = opts.pages || [];
  if (pages.length === 0) {
    ctx.emit({ progress: { completed: 0, total: 0 }, sub_label: '无页面可提取，跳过' });
    return { skipped: true };
  }
  ctx.emit({ progress: { completed: 0, total: pages.length }, sub_label: `准备提取 ${pages.length} 页...` });
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/pages/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pages, dpi: opts.dpi || 300 }),
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  let done = 0;
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress') {
      done = ev.current || done;
      ctx.emit({ progress: { completed: done, total: ev.total || pages.length }, sub_label: `已提取 p.${ev.page || '?'}` });
    } else if (ev.type === 'page_complete' || ev.status === 'page_complete') {
      done += 1;
      ctx.emit({ progress: { completed: done, total: pages.length }, sub_label: `已提取 p.${ev.page_num || ev.page || '?'}` });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: pages.length, total: pages.length }, sub_label: '视觉提取完成' });
    } else if (ev.type === 'error' || ev.error) {
      // 单页错误不阻断
      ctx.emit({ sub_label: `提取 p.${ev.page || '?'} 失败：${ev.error || ev.message || ''}` });
    }
  }
  return { extracted: done };
}

async function step_outline(ctx) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: '生成大纲中（Stage 1）...' });
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress') {
      ctx.emit({ sub_label: ev.message || ev.status || '...' });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: 1, total: 1 }, sub_label: '大纲完成' });
    } else if (ev.type === 'error') {
      throw new Error(ev.error || ev.message || '大纲生成失败');
    }
  }
  return {};
}

async function step_subdivide(ctx) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: '细分分段中（Stage 2）...' });
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  let total = 1, done = 0;
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress') {
      if (typeof ev.total === 'number') total = ev.total;
      if (typeof ev.current === 'number') done = ev.current;
      ctx.emit({ progress: { completed: done, total }, sub_label: ev.message || `${done}/${total}` });
    } else if (ev.type === 'section_complete') {
      done += 1;
      ctx.emit({ progress: { completed: done, total }, sub_label: `分段 ${ev.section_idx || done} 完成` });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: total, total }, sub_label: '细分完成' });
    } else if (ev.type === 'error') {
      throw new Error(ev.error || ev.message || '细分失败');
    }
  }
  return {};
}

async function step_lesson_plan(ctx, opts) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: '生成 Lesson Plan...' });
  const body = { mode: 'full' };
  // 注：lesson_plan 未实现 extra_user_instruction —— 留接口位
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/annotations/batch/lesson-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  let total = 1, done = 0;
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress' || ev.type === 'section_start' || ev.type === 'section_done') {
      if (typeof ev.total === 'number') total = ev.total;
      if (typeof ev.completed === 'number') done = ev.completed;
      else if (typeof ev.current === 'number') done = ev.current;
      ctx.emit({ progress: { completed: done, total }, sub_label: ev.message || `${done}/${total}` });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: total, total }, sub_label: 'Lesson Plan 完成' });
    } else if (ev.type === 'error') {
      throw new Error(ev.error || ev.message || 'Lesson Plan 失败');
    }
  }
  return {};
}

async function step_lesson_plan_normalize(ctx) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: 'Normalize 中...' });
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/annotations/batch/lesson-plan/normalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  // 这个端点通常是一次性 JSON 而非 SSE，直接读
  try {
    const data = await resp.json();
    ctx.emit({ progress: { completed: 1, total: 1 }, sub_label: 'Normalize 完成' });
    return data;
  } catch {
    ctx.emit({ progress: { completed: 1, total: 1 }, sub_label: 'Normalize 完成' });
    return {};
  }
}

async function step_step_script(ctx, opts) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: '生成 Step Script...' });
  const body = { mode: 'full' };
  if (opts.extra_user_instruction && opts.extra_user_instruction.trim()) {
    body.extra_user_instruction = opts.extra_user_instruction.trim();
  }
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/annotations/batch/step-script`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  let total = 1, done = 0;
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress' || ev.type === 'section_start' || ev.type === 'section_done') {
      if (typeof ev.total === 'number') total = ev.total;
      if (typeof ev.completed === 'number') done = ev.completed;
      else if (typeof ev.current === 'number') done = ev.current;
      ctx.emit({ progress: { completed: done, total }, sub_label: ev.message || `${done}/${total}` });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: total, total }, sub_label: 'Step Script 完成' });
    } else if (ev.type === 'error') {
      throw new Error(ev.error || ev.message || 'Step Script 失败');
    }
  }
  return {};
}

async function step_step_audio(ctx) {
  const { boardId, windowId, signal } = ctx;
  ctx.emit({ progress: { completed: 0, total: 1 }, sub_label: '合成 Step Audio...' });
  const resp = await fetch(`${API_BASE}/api/boards/${boardId}/windows/${windowId}/narrator/step-audio/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
    signal,
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status} ${await resp.text().catch(() => '')}`.slice(0, 200));
  let total = 1, done = 0;
  for await (const ev of readSSE(resp, signal)) {
    if (ev.type === 'progress' || ev.type === 'section_start' || ev.type === 'section_done') {
      if (typeof ev.total === 'number') total = ev.total;
      if (typeof ev.completed === 'number') done = ev.completed;
      else if (typeof ev.current === 'number') done = ev.current;
      ctx.emit({ progress: { completed: done, total }, sub_label: ev.message || `合成中 ${done}/${total}` });
    } else if (ev.type === 'complete' || ev.type === 'done') {
      ctx.emit({ progress: { completed: total, total }, sub_label: 'Step Audio 完成' });
    } else if (ev.type === 'error') {
      throw new Error(ev.error || ev.message || 'Step Audio 失败');
    }
  }
  return {};
}

const STEP_RUNNERS = {
  visual_extract:        step_visual_extract,
  outline:               step_outline,
  subdivide:             step_subdivide,
  lesson_plan:           step_lesson_plan,
  lesson_plan_normalize: step_lesson_plan_normalize,
  step_script:           step_step_script,
  step_audio:            step_step_audio,
};

// ============================================================
// 主入口
// ============================================================
export function startPipeline({ boardId, windowId, source, steps, taskId }) {
  if (!boardId || !windowId) throw new Error('boardId/windowId required');
  if (!Array.isArray(steps) || steps.length === 0) throw new Error('steps required');

  const tid = taskId || `pipeline-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  const ac = new AbortController();
  const totalSteps = steps.length;

  // 监听全局中止
  const abortHandler = (evt) => {
    if (evt && evt.detail && evt.detail.task_id === tid) {
      ac.abort();
    }
  };
  window.addEventListener('whatnote:task-abort', abortHandler);

  const title = `🚀 一键生成${source && source.window_title ? ` · ${source.window_title}` : ''}`;

  const emitOverall = (overrides) => {
    window.dispatchEvent(new CustomEvent('whatnote:task-progress', {
      detail: {
        task_id: tid,
        title,
        can_abort: true,
        source,
        ...overrides,
      }
    }));
  };

  const promise = (async () => {
    const results = {};
    try {
      for (let i = 0; i < steps.length; i++) {
        if (ac.signal.aborted) throw new DOMException('aborted', 'AbortError');
        const step = steps[i];
        const runner = STEP_RUNNERS[step.id];
        if (!runner) {
          throw new Error(`未知步骤: ${step.id}`);
        }
        const stepLabel = STEP_LABELS[step.id] || step.id;
        emitOverall({
          status: 'running',
          step_label: stepLabel,
          overall: { current: i + 1, total: totalSteps },
          progress: { completed: 0, total: 1 },
        });
        const ctx = {
          boardId, windowId, taskId: tid, source,
          signal: ac.signal,
          emit: (sub) => {
            emitOverall({
              status: 'running',
              step_label: sub.sub_label ? `[${stepLabel}] ${sub.sub_label}` : stepLabel,
              overall: { current: i + 1, total: totalSteps },
              progress: sub.progress || undefined,
            });
          },
        };
        results[step.id] = await runner(ctx, step);
      }
      emitOverall({
        status: 'done',
        step_label: `全部完成（${totalSteps} 步）`,
        overall: { current: totalSteps, total: totalSteps },
        progress: { completed: totalSteps, total: totalSteps },
      });
      return { ok: true, results };
    } catch (e) {
      const isAbort = e && (e.name === 'AbortError' || ac.signal.aborted);
      emitOverall({
        status: isAbort ? 'aborted' : 'failed',
        step_label: isAbort ? '已中止' : '失败',
        error: isAbort ? '用户中止' : (e && e.message) || String(e),
        overall: undefined,
      });
      throw e;
    } finally {
      window.removeEventListener('whatnote:task-abort', abortHandler);
    }
  })();

  return { taskId: tid, abort: () => ac.abort(), promise };
}

export { STEP_LABELS };
