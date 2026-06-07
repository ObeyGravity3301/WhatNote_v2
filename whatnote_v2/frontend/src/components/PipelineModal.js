import React, { useEffect, useMemo, useState } from 'react';
import { useLanguage } from '../i18n/LanguageContext';
import { startPipeline, STEP_LABELS } from '../services/pipelineService';

// 「一键生成」流水线 配置 + 启动 入口。
//
// 跑起来后用户可以关闭这个 modal，进度由 GlobalTaskTray 显示。
// 上层在 boardId/windowId/source/pagesInfo 改变时透传更新。

const ALL_STEPS = [
  { id: 'visual_extract',        emoji: '🔍', recommended: true },
  { id: 'outline',               emoji: '📋', recommended: true },
  { id: 'subdivide',             emoji: '✂️', recommended: true },
  { id: 'lesson_plan',           emoji: '📚', recommended: true },
  { id: 'lesson_plan_normalize', emoji: '🧹', recommended: true },
  { id: 'step_script',           emoji: '🎙', recommended: true },
  { id: 'step_audio',            emoji: '🔊', recommended: true },
];

// 选择目标后默认的 step 集合
const TARGET_PRESETS = {
  to_visual_extract: ['visual_extract'],
  to_lesson_plan:    ['visual_extract', 'outline', 'subdivide', 'lesson_plan', 'lesson_plan_normalize'],
  to_step_script:    ['visual_extract', 'outline', 'subdivide', 'lesson_plan', 'lesson_plan_normalize', 'step_script'],
  to_step_audio:     ['visual_extract', 'outline', 'subdivide', 'lesson_plan', 'lesson_plan_normalize', 'step_script', 'step_audio'],
};

const PipelineModal = ({ isOpen, onClose, boardId, windowId, source, pagesInfo }) => {
  const { t } = useLanguage();
  const [target, setTarget] = useState('to_step_audio');
  const [selectedSteps, setSelectedSteps] = useState(new Set(TARGET_PRESETS.to_step_audio));
  const [extractScope, setExtractScope] = useState('unextracted'); // 'unextracted' | 'all' | 'none'
  const [extraInstruction, setExtraInstruction] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState(null);

  // 目标变化时更新默认勾选
  useEffect(() => {
    setSelectedSteps(new Set(TARGET_PRESETS[target] || TARGET_PRESETS.to_step_audio));
  }, [target]);

  const totalPages = useMemo(() => (Array.isArray(pagesInfo) ? pagesInfo.length : 0), [pagesInfo]);
  const unextractedPages = useMemo(() => {
    if (!Array.isArray(pagesInfo)) return [];
    return pagesInfo.filter(p => !p.extracted).map(p => p.page);
  }, [pagesInfo]);

  const pagesToExtract = useMemo(() => {
    if (!selectedSteps.has('visual_extract')) return [];
    if (extractScope === 'all') return (pagesInfo || []).map(p => p.page);
    if (extractScope === 'unextracted') return unextractedPages;
    return [];
  }, [selectedSteps, extractScope, pagesInfo, unextractedPages]);

  const toggleStep = (sid) => {
    setSelectedSteps(prev => {
      const cp = new Set(prev);
      if (cp.has(sid)) cp.delete(sid); else cp.add(sid);
      return cp;
    });
  };

  const handleStart = async () => {
    if (selectedSteps.size === 0) {
      setRunError('请至少勾选一个步骤');
      return;
    }
    setRunError(null);
    // 构造步骤数组（保持 ALL_STEPS 的顺序）
    const steps = [];
    for (const sd of ALL_STEPS) {
      if (!selectedSteps.has(sd.id)) continue;
      const cfg = { id: sd.id };
      if (sd.id === 'visual_extract') {
        cfg.pages = pagesToExtract;
        cfg.dpi = 300;
      } else if (sd.id === 'step_script') {
        if (extraInstruction.trim()) cfg.extra_user_instruction = extraInstruction.trim();
      }
      steps.push(cfg);
    }

    setIsRunning(true);
    try {
      const ctrl = startPipeline({ boardId, windowId, source, steps });
      ctrl.promise.catch(() => {}); // 错误已通过 task-progress 上报，这里吞掉
      // 立即关闭 modal —— 进度由 GlobalTaskTray 接管
      onClose();
    } catch (e) {
      setRunError(e.message || String(e));
    } finally {
      setIsRunning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute', inset: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2100,
    }}>
      <div style={{
        width: 'min(620px, 95%)',
        maxHeight: '90%',
        display: 'flex', flexDirection: 'column',
        backgroundColor: '#c0c0c0',
        border: '2px outset #c0c0c0',
        fontFamily: 'MS Sans Serif, sans-serif',
        fontSize: 11,
      }}>
        <div style={{
          padding: '6px 10px',
          background: '#000080', color: '#fff',
          display: 'flex', alignItems: 'center',
        }}>
          <span style={{ flex: 1, fontWeight: 'bold' }}>
            🚀 {t('pipeline_modal_title') || '一键生成'}
            {source && source.window_title && (
              <span style={{ marginLeft: 6, fontWeight: 'normal', fontSize: 10, opacity: 0.85 }}>
                · {source.window_title}
              </span>
            )}
          </span>
          <button
            onClick={onClose}
            style={{ background: '#c0c0c0', color: '#000', border: '1px outset #fff', padding: '0 8px', cursor: 'pointer' }}
          >✕</button>
        </div>

        <div style={{ padding: 12, overflowY: 'auto', background: '#f4f4f4', color: '#000' }}>
          {/* 目标完成度 */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
              {t('pipeline_target') || '目标完成度'}
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {[
                { id: 'to_visual_extract', label: t('pipeline_target_visual_only') || '仅视觉提取' },
                { id: 'to_lesson_plan',    label: t('pipeline_target_lesson_plan') || '到 Lesson Plan' },
                { id: 'to_step_script',    label: t('pipeline_target_step_script') || '到 Step Script' },
                { id: 'to_step_audio',     label: t('pipeline_target_step_audio') || '到 Step Audio（最完整）' },
              ].map(opt => (
                <button
                  key={opt.id}
                  onClick={() => setTarget(opt.id)}
                  style={{
                    padding: '4px 10px',
                    background: target === opt.id ? '#000080' : '#fff',
                    color: target === opt.id ? '#fff' : '#000',
                    border: target === opt.id ? '2px inset #000080' : '1px outset #c0c0c0',
                    cursor: 'pointer',
                  }}
                >{opt.label}</button>
              ))}
            </div>
          </div>

          {/* 步骤勾选 */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
              {t('pipeline_steps') || '执行步骤'}
              <span style={{ marginLeft: 8, fontSize: 10, color: '#666' }}>
                {t('pipeline_steps_hint') || '（已根据目标自动勾选，可自行调整）'}
              </span>
            </div>
            <div style={{ background: '#fff', border: '1px inset #c0c0c0', padding: 6 }}>
              {ALL_STEPS.map((sd, idx) => (
                <label
                  key={sd.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '3px 4px',
                    background: idx % 2 === 0 ? '#f0f0f0' : '#fff',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedSteps.has(sd.id)}
                    onChange={() => toggleStep(sd.id)}
                    disabled={isRunning}
                  />
                  <span>{sd.emoji}</span>
                  <span style={{ flex: 1 }}>{t(`pipeline_step_${sd.id}`) || STEP_LABELS[sd.id] || sd.id}</span>
                </label>
              ))}
            </div>
          </div>

          {/* 视觉提取范围 */}
          {selectedSteps.has('visual_extract') && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                {t('pipeline_visual_scope') || '视觉提取范围'}
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {[
                  { id: 'unextracted', label: `${t('pipeline_visual_unextracted') || '仅未提取页'} (${unextractedPages.length})` },
                  { id: 'all',         label: `${t('pipeline_visual_all') || '全部页'} (${totalPages})` },
                  { id: 'none',        label: t('pipeline_visual_none') || '不提取（已全部提取过）' },
                ].map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => setExtractScope(opt.id)}
                    style={{
                      padding: '3px 8px',
                      fontSize: 11,
                      background: extractScope === opt.id ? '#000080' : '#fff',
                      color: extractScope === opt.id ? '#fff' : '#000',
                      border: extractScope === opt.id ? '2px inset #000080' : '1px outset #c0c0c0',
                      cursor: 'pointer',
                    }}
                  >{opt.label}</button>
                ))}
              </div>
              {extractScope !== 'none' && pagesToExtract.length === 0 && (
                <div style={{ marginTop: 4, fontSize: 10, color: '#666' }}>
                  {t('pipeline_visual_will_skip') || '当前选项下没有需要提取的页面，视觉提取将被跳过。'}
                </div>
              )}
            </div>
          )}

          {/* 自定义指令（只影响 step_script） */}
          {selectedSteps.has('step_script') && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                {t('pipeline_extra_instruction_step_script') || 'Step Script 额外指令（可选）'}
                <span style={{ marginLeft: 8, fontSize: 10, color: '#666', fontWeight: 'normal' }}>
                  {t('pipeline_extra_instruction_hint') || '会追加在讲稿生成 prompt 末尾，但不会修改输出 schema'}
                </span>
              </div>
              <textarea
                value={extraInstruction}
                onChange={(e) => setExtraInstruction(e.target.value)}
                placeholder={t('pipeline_extra_instruction_placeholder') || '比如：请在每段讲稿末尾追加一句鼓励语；或者：避免使用太多专业术语…'}
                rows={3}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: '#fff', color: '#000',
                  border: '1px inset #c0c0c0', padding: '4px 6px',
                  fontFamily: 'inherit', fontSize: 11,
                  resize: 'vertical',
                }}
              />
            </div>
          )}

          {/* 错误提示 */}
          {runError && (
            <div style={{
              padding: '6px 8px',
              background: '#ffe0e0',
              border: '1px solid #c95c5c',
              color: '#a02020',
              marginBottom: 8,
            }}>{runError}</div>
          )}

          {/* 顶部说明 */}
          <div style={{
            marginTop: 8,
            padding: '6px 8px',
            background: '#fffae6',
            border: '1px solid #e0c060',
            color: '#604000',
            fontSize: 10,
            lineHeight: 1.5,
          }}>
            {t('pipeline_hint') ||
              '开始后该面板会关闭，进度显示在屏幕右上角的任务托盘里。任务结束会自动写入消息中心。'}
          </div>
        </div>

        {/* 底部按钮 */}
        <div style={{
          padding: '8px 12px',
          background: '#c0c0c0',
          borderTop: '1px solid #888',
          display: 'flex', justifyContent: 'flex-end', gap: 6,
        }}>
          <button
            onClick={onClose}
            disabled={isRunning}
            style={{ padding: '4px 14px', cursor: 'pointer', border: '1px outset #c0c0c0', background: '#e0e0e0' }}
          >
            {t('cancel') || '取消'}
          </button>
          <button
            onClick={handleStart}
            disabled={isRunning || selectedSteps.size === 0}
            style={{
              padding: '4px 18px',
              cursor: isRunning ? 'wait' : 'pointer',
              background: '#7b1fa2',
              color: '#fff',
              border: '2px outset #7b1fa2',
              fontWeight: 'bold',
            }}
          >
            🚀 {t('pipeline_start') || '开始'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PipelineModal;
