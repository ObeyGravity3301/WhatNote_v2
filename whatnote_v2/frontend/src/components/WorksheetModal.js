import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useLanguage } from '../i18n/LanguageContext';

// Worksheet 弹窗（独立 modal）
//
// - 数据从 GET /api/boards/.../worksheet-data 派生（无 LLM）
// - 联动：监听 window 自定义事件 'whatnote:step-change' { step_id, board_id, window_id }
//   收到匹配的事件后：切到该节、滚到该 step、加粗边框高亮
// - 「显示答案」全局开关 + 每个 step 单独的折叠按钮
// - 「📥 导出 MD」「📥 导出 MD (含答案)」按钮

const COG_COLORS = {
  intro:    '#5b8ec9',
  recap:    '#7a8aa0',
  summary:  '#3aa55a',
  example:  '#cc8a00',
  recall:   '#1565c0',
  compute:  '#7b1fa2',
  decide:   '#bf6e16',
  connect:  '#0e7c8c',
  critique: '#a02020',
};

const WorksheetModal = ({ isOpen, onClose, boardId, windowId, documentTitle }) => {
  const { t } = useLanguage();

  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [expandedSectionIdx, setExpandedSectionIdx] = useState(0);
  const [showAllAnswers, setShowAllAnswers] = useState(false);
  const [expandedAnswers, setExpandedAnswers] = useState(() => new Set()); // step_id set
  const [highlightedStepId, setHighlightedStepId] = useState(null);
  const stepRefsRef = useRef({}); // step_id -> DOM element
  const contentRef = useRef(null);

  // 加载 worksheet 数据
  const fetchData = useCallback(async () => {
    if (!boardId || !windowId) return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/worksheet-data`);
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const d = await res.json();
      setData(d);
    } catch (e) {
      setLoadError(e.message || String(e));
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [boardId, windowId]);

  useEffect(() => {
    if (isOpen) fetchData();
    else {
      setHighlightedStepId(null);
    }
  }, [isOpen, fetchData]);

  // ====== 联动：监听 narrator step-change 事件 ======
  useEffect(() => {
    if (!isOpen || !data) return;

    const handler = (evt) => {
      const detail = evt && evt.detail;
      if (!detail) return;
      if (detail.board_id && detail.board_id !== boardId) return;
      if (detail.window_id && detail.window_id !== windowId) return;
      const sid = detail.step_id;
      if (!sid) return;

      // 找到 step 所在的 section
      const sections = data.sections || [];
      let targetSectionIdx = -1;
      let targetStep = null;
      for (let i = 0; i < sections.length; i++) {
        const sec = sections[i];
        if (!sec || !sec.steps) continue;
        const found = sec.steps.find(s => s.step_id === sid);
        if (found) { targetSectionIdx = i; targetStep = found; break; }
      }
      if (targetSectionIdx < 0) return;

      if (targetSectionIdx !== expandedSectionIdx) {
        setExpandedSectionIdx(targetSectionIdx);
      }
      setHighlightedStepId(sid);

      // 滚动到 step 元素（稍延迟，让 section 切换后 DOM 重建）
      window.setTimeout(() => {
        const el = stepRefsRef.current[sid];
        if (el && contentRef.current) {
          try {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } catch (e) {
            el.scrollIntoView();
          }
        }
      }, 60);
    };

    window.addEventListener('whatnote:step-change', handler);
    return () => window.removeEventListener('whatnote:step-change', handler);
  }, [isOpen, data, boardId, windowId, expandedSectionIdx]);

  // ====== 导出 MD ======
  const handleDownloadMd = useCallback(async (withAnswers) => {
    try {
      const url = `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/export-worksheet-markdown?show_answers=${withAnswers ? 'true' : 'false'}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = dlUrl;
      const stem = (documentTitle || 'document').replace(/\.pdf$/i, '');
      a.download = `${stem}${withAnswers ? '-worksheet-with-answers' : '-worksheet'}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(dlUrl);
    } catch (e) {
      alert((t('worksheet_download_failed') || '下载失败：') + (e.message || e));
    }
  }, [boardId, windowId, documentTitle, t]);

  const toggleAnswerExpand = (sid) => {
    setExpandedAnswers(prev => {
      const cp = new Set(prev);
      if (cp.has(sid)) cp.delete(sid); else cp.add(sid);
      return cp;
    });
  };

  const currentSection = useMemo(() => {
    if (!data || !data.sections) return null;
    return data.sections[expandedSectionIdx] || null;
  }, [data, expandedSectionIdx]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute', inset: 0,
      backgroundColor: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 2000,
    }}>
      <div style={{
        width: 'min(820px, 96%)',
        height: '92%',
        display: 'flex', flexDirection: 'column',
        backgroundColor: '#f4f0e6',
        border: '2px outset #c0c0c0',
        fontFamily: 'MS Sans Serif, sans-serif',
        fontSize: '12px',
      }}>
        {/* 顶部工具栏 */}
        <div style={{
          padding: '8px 10px',
          backgroundColor: '#c0c0c0',
          borderBottom: '1px solid #888',
          display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap',
        }}>
          <div style={{ fontWeight: 'bold', fontSize: '13px' }}>
            📚 {t('worksheet_modal_title') || '学案'}
            {data && data.stats && (
              <span style={{ marginLeft: '8px', color: '#444', fontWeight: 'normal', fontSize: '11px' }}>
                ({(t('worksheet_stats_template') || '{s} 节 · {n} step · {p} 处停顿')
                  .replace('{s}', data.stats.section_count || 0)
                  .replace('{n}', data.stats.step_count || 0)
                  .replace('{p}', data.stats.pause_count || 0)})
              </span>
            )}
          </div>
          <div style={{ flex: 1 }} />
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
            <input type="checkbox" checked={showAllAnswers} onChange={(e) => setShowAllAnswers(e.target.checked)} />
            <span>{t('worksheet_show_all_answers') || '显示所有答案'}</span>
          </label>
          <button onClick={() => handleDownloadMd(false)} style={btnStyle()}>
            📥 {t('worksheet_export_md') || '导出 MD'}
          </button>
          <button onClick={() => handleDownloadMd(true)} style={btnStyle()}>
            📥 {t('worksheet_export_md_with_answers') || '导出 MD (含答案)'}
          </button>
          <button onClick={onClose} style={{ ...btnStyle(), fontWeight: 'bold', color: '#a00' }}>
            ✕
          </button>
        </div>

        {/* 节选择条 */}
        {data && data.sections && data.sections.length > 0 && (
          <div style={{
            padding: '6px 8px',
            background: '#e6dfc8',
            borderBottom: '1px solid #888',
            display: 'flex', flexWrap: 'wrap', gap: '4px',
          }}>
            {data.sections.map((sec, idx) => {
              if (!sec) return null;
              const isActive = idx === expandedSectionIdx;
              return (
                <button
                  key={idx}
                  onClick={() => setExpandedSectionIdx(idx)}
                  style={{
                    padding: '2px 8px',
                    fontSize: '11px',
                    background: isActive ? '#000080' : '#fff',
                    color: isActive ? '#fff' : '#000',
                    border: isActive ? '2px inset #000080' : '1px outset #c0c0c0',
                    cursor: 'pointer',
                  }}
                  title={sec.section_title}
                >
                  §{sec.section_number} {(sec.section_title || '').slice(0, 12)}
                </button>
              );
            })}
          </div>
        )}

        {/* 主体内容 */}
        <div ref={contentRef} style={{
          flex: 1,
          overflowY: 'auto',
          padding: '14px 18px',
          background: '#fdfdf6',
          lineHeight: 1.55,
          color: '#000',
        }}>
          {isLoading && <div style={{ color: '#666' }}>{t('worksheet_loading') || '加载中…'}</div>}
          {loadError && (
            <div style={{ color: '#a00', padding: '10px', background: '#fee', border: '1px solid #faa' }}>
              {t('worksheet_load_failed') || '加载学案失败：'}{loadError}
              <div style={{ marginTop: '6px', fontSize: '11px', color: '#666' }}>
                {t('worksheet_load_hint') || '需要先生成 lesson_plan，学案是从 lesson_plan 直接派生的。'}
              </div>
            </div>
          )}
          {!isLoading && !loadError && currentSection && (
            <WorksheetSection
              section={currentSection}
              showAllAnswers={showAllAnswers}
              expandedAnswers={expandedAnswers}
              toggleAnswerExpand={toggleAnswerExpand}
              highlightedStepId={highlightedStepId}
              stepRefs={stepRefsRef}
              t={t}
            />
          )}
        </div>
      </div>
    </div>
  );
};

function WorksheetSection({ section, showAllAnswers, expandedAnswers, toggleAnswerExpand, highlightedStepId, stepRefs, t }) {
  return (
    <div>
      <h2 style={{ marginTop: 0, fontSize: '18px', color: '#000080' }}>
        §{section.section_number}. {section.section_title}
        <span style={{ marginLeft: 8, fontSize: '11px', color: '#666', fontWeight: 'normal' }}>
          p.{section.page_start}–{section.page_end}
        </span>
      </h2>
      {section.objective && (
        <div style={{ margin: '6px 0', padding: '6px 10px', background: '#fff8d6', borderLeft: '3px solid #c9a23c' }}>
          <strong>📚 {t('worksheet_objective') || '学习目标'}：</strong>{section.objective}
        </div>
      )}
      {section.hook && (
        <div style={{ margin: '6px 0', padding: '6px 10px', background: '#e6f0fa', borderLeft: '3px solid #4a78c0' }}>
          <strong>🪝 {t('worksheet_hook') || '课前一问'}：</strong>{section.hook}
        </div>
      )}

      <div style={{ marginTop: '16px' }}>
        {(section.steps || []).map((step) => (
          <WorksheetStep
            key={step.step_id}
            step={step}
            showAllAnswers={showAllAnswers}
            isAnswerExpanded={expandedAnswers.has(step.step_id)}
            onToggleAnswer={() => toggleAnswerExpand(step.step_id)}
            highlighted={highlightedStepId === step.step_id}
            refSetter={(el) => { if (el) stepRefs.current[step.step_id] = el; }}
            t={t}
          />
        ))}
      </div>

      {section.assessment && section.assessment.length > 0 && (
        <div style={{
          marginTop: '20px',
          padding: '10px 14px',
          background: '#e8f4ea',
          border: '1px solid #3aa55a',
          borderLeft: '4px solid #3aa55a',
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#1b6b35' }}>
            ✅ {t('worksheet_assessment_title') || '章末自检'}
          </div>
          <ol style={{ paddingLeft: '24px', margin: 0 }}>
            {section.assessment.map((q, i) => (
              <li key={i} style={{ marginBottom: '12px' }}>
                {q}
                <div style={{ marginTop: '4px' }}>
                  {Array.from({ length: 2 }).map((_, k) => (
                    <div key={k} style={{ borderBottom: '1px solid #aaa', height: '20px' }} />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function WorksheetStep({ step, showAllAnswers, isAnswerExpanded, onToggleAnswer, highlighted, refSetter, t }) {
  const cogColor = COG_COLORS[step.cognitive_action] || '#666';
  const stars = '★'.repeat(Math.max(1, Math.min(3, step.weight || 2))).padEnd(3, '☆');
  const meta = step.cognitive_meta || { emoji: '•', label_zh: step.cognitive_action };
  const showAnswer = showAllAnswers || isAnswerExpanded;
  const ans = step.answer || {};
  const hasAnswer = !!(ans.landing_sentence || (ans.reasoning_chain && ans.reasoning_chain.length) || ans.common_mistake);

  return (
    <div
      ref={refSetter}
      style={{
        margin: '12px 0',
        padding: '10px 14px',
        background: '#fff',
        border: highlighted ? '3px solid #c9a23c' : '1px solid #c8c0a8',
        borderLeft: `4px solid ${cogColor}`,
        boxShadow: highlighted ? '0 0 0 3px rgba(201,162,60,0.25)' : 'none',
        transition: 'box-shadow .15s, border-color .15s',
      }}
    >
      {/* 头部：step_id + 认知动作 + 重要度 + anchor_page */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '11px' }}>
        <span style={{ background: cogColor, color: '#fff', padding: '1px 6px', borderRadius: '2px', fontFamily: 'monospace' }}>
          {step.step_id}
        </span>
        <span style={{ color: cogColor }}>{meta.emoji} {meta.label_zh}</span>
        <span style={{ color: '#a07c1d' }}>重要度 {stars}</span>
        {step.anchor_page != null && (
          <span style={{ color: '#666' }}>p.{step.anchor_page}</span>
        )}
        {step.is_pause && (
          <span style={{ background: '#cc8a00', color: '#fff', padding: '1px 6px', borderRadius: '2px' }}>
            ⏸ {t('worksheet_write_seconds_template') ? t('worksheet_write_seconds_template').replace('{s}', step.pause_seconds) : `写 ${step.pause_seconds} 秒`}
          </span>
        )}
      </div>

      {step.step_title && (
        <div style={{ marginTop: '6px', fontStyle: 'italic', color: '#444' }}>{step.step_title}</div>
      )}

      {step.key_question && (
        <div style={{ marginTop: '8px', fontWeight: 'bold', fontSize: '13px' }}>
          ❓ {step.key_question}
        </div>
      )}

      {step.learning_action && (
        <div style={{ marginTop: '4px', color: '#555', fontSize: '11px' }}>
          🖊 <em>{t('worksheet_learning_action_label') || '你要做'}</em>：{step.learning_action}
        </div>
      )}

      {/* 留白书写区 */}
      <div style={{ marginTop: '10px' }}>
        {Array.from({ length: step.blank_lines || 3 }).map((_, i) => (
          <div key={i} style={{ borderBottom: '1px solid #c0b890', height: '22px' }} />
        ))}
      </div>

      {/* 答案区 */}
      {hasAnswer && (
        <div style={{ marginTop: '10px' }}>
          {!showAllAnswers && (
            <button
              onClick={onToggleAnswer}
              style={{
                padding: '2px 8px', fontSize: '10px',
                background: isAnswerExpanded ? '#e8f4ea' : '#fff',
                border: '1px solid #999', cursor: 'pointer',
              }}
            >
              {isAnswerExpanded
                ? (t('worksheet_hide_answer') || '▼ 隐藏答案')
                : (t('worksheet_show_answer') || '▶ 显示答案')}
            </button>
          )}
          {showAnswer && (
            <div style={{
              marginTop: '6px',
              padding: '8px 12px',
              background: '#f5fff7',
              border: '1px solid #c0d8c5',
              borderLeft: '3px solid #3aa55a',
              fontSize: '11px',
              lineHeight: 1.6,
            }}>
              {ans.landing_sentence && (
                <div>📝 <strong>{t('worksheet_answer_landing') || '关键结论'}：</strong>{ans.landing_sentence}</div>
              )}
              {ans.reasoning_chain && ans.reasoning_chain.length > 0 && (
                <div style={{ marginTop: '4px' }}>
                  🧩 <strong>{t('worksheet_answer_chain') || '推理'}：</strong>
                  <ol style={{ paddingLeft: '24px', margin: '2px 0' }}>
                    {ans.reasoning_chain.map((c, i) => <li key={i}>{c}</li>)}
                  </ol>
                </div>
              )}
              {ans.common_mistake && (
                <div style={{ marginTop: '4px', color: '#a02020' }}>
                  ⚠️ <strong>{t('worksheet_answer_mistake') || '常见错误'}：</strong>{ans.common_mistake}
                </div>
              )}
              {ans.exam_likelihood != null && (
                <div style={{ marginTop: '4px', color: '#666' }}>
                  🎯 <em>{t('worksheet_answer_exam_likelihood') || '考查可能性'}</em>：{ans.exam_likelihood}/5
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function btnStyle() {
  return {
    padding: '4px 10px',
    fontSize: '11px',
    backgroundColor: '#dcdcd0',
    border: '1px outset #fff',
    cursor: 'pointer',
  };
}

export default WorksheetModal;
