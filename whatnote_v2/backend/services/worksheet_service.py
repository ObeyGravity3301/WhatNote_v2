"""Worksheet (学案) — 从 lesson_plan **派生** 而来，零 LLM 调用。

设计原则
========
lesson_plan 是教师视角的结构化学案数据，已经包含了 worksheet 需要的全部信息：

  - section.objective / hook                  → 章首学习目标 + 引入
  - step.key_question                         → 题干
  - step.learning_action                      → "你要做什么"提示
  - step.weight / pause_seconds               → 留白行数
  - step.cognitive_action                     → 题型徽章
  - step.landing_sentence                     → "答案"主语
  - step.reasoning_chain                      → "答案"推理链
  - step.common_mistake                       → "答案"区警示
  - section.assessment                        → 章末自检

所以这一层只做派生 + 渲染，**不再调用 LLM**。下一轮如果需要"题型变体"
或"自定义指令"可以再加 LLM 增强层；目前先把基础形态跑通。

公开 API
========
- render_worksheet_structured(lesson_plan_data)   # 给前端 modal 用
- render_worksheet_markdown(lp_data, show_answers=False)
- _blank_lines_for / _strip_or_none ...           # 内部 helpers，外部不要直接依赖
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ============== 视觉映射 ==============
#
# cognitive_action -> (emoji, 中文短标签) 供前端/MD 显示题型徽章
COGNITIVE_ACTION_META: Dict[str, Dict[str, str]] = {
    "recall":   {"emoji": "🧠", "label_zh": "记忆",   "label_en": "Recall"},
    "compute":  {"emoji": "🧮", "label_zh": "计算",   "label_en": "Compute"},
    "decide":   {"emoji": "⚖️", "label_zh": "判断",   "label_en": "Decide"},
    "connect":  {"emoji": "🔗", "label_zh": "联系",   "label_en": "Connect"},
    "critique": {"emoji": "🔍", "label_zh": "辨析",   "label_en": "Critique"},
    "intro":    {"emoji": "👋", "label_zh": "引入",   "label_en": "Intro"},
    "recap":    {"emoji": "🔁", "label_zh": "回顾",   "label_en": "Recap"},
    "summary":  {"emoji": "📌", "label_zh": "小结",   "label_en": "Summary"},
    "example":  {"emoji": "💡", "label_zh": "例子",   "label_en": "Example"},
}


def cognitive_action_meta(action: Optional[str]) -> Dict[str, str]:
    """容错查询。未知枚举回退到 recall 的视觉。"""
    s = (action or "").strip().lower()
    return COGNITIVE_ACTION_META.get(s, COGNITIVE_ACTION_META["recall"])


# ============== helpers ==============


def _blank_lines_for(weight: Optional[int], pause_seconds: Optional[int]) -> int:
    """根据 weight 和 pause_seconds 决定该 step 留多少行书写空间。

    weight  ->  基础行数
      1     ->  2
      2     ->  4
      3     ->  6
    pause_seconds 加成：
      0-4   ->  +0
      5-14  ->  +1
      15+   ->  +2
    """
    base = {1: 2, 2: 4, 3: 6}.get(int(weight or 2), 3)
    ps = int(pause_seconds or 0)
    if ps >= 15:
        base += 2
    elif ps >= 5:
        base += 1
    return max(1, base)


def _strip_or_none(s: Any) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    return t or None


def _list_or_empty(v: Any) -> List[str]:
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x or "").strip()]


# ============== 结构化输出 ==============


def render_worksheet_structured(lesson_plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """把 lesson_plan_data 转成 worksheet 结构化数据（前端 modal 直接渲染）。

    输出 schema 见模块顶部说明；step 内的 answer 字段是聚合的，前端可一键展开/折叠。
    """
    if not isinstance(lesson_plan_data, dict):
        raise ValueError("lesson_plan_data 必须是 dict")

    sections_in = lesson_plan_data.get("sections") or []
    sections_out: List[Dict[str, Any]] = []

    total_steps = 0
    total_pauses = 0
    total_blank_lines = 0

    for sec in sections_in:
        if not isinstance(sec, dict):
            continue
        steps_in = sec.get("steps") or []
        steps_out: List[Dict[str, Any]] = []
        for s_idx, raw_step in enumerate(steps_in):
            if not isinstance(raw_step, dict):
                continue
            weight = raw_step.get("weight")
            pause_seconds = int(raw_step.get("pause_seconds") or 0)
            blanks = _blank_lines_for(weight, pause_seconds)
            answer_parts = {
                "landing_sentence": _strip_or_none(raw_step.get("landing_sentence")),
                "reasoning_chain": _list_or_empty(raw_step.get("reasoning_chain")),
                "common_mistake": _strip_or_none(raw_step.get("common_mistake")),
                "exam_likelihood": raw_step.get("exam_likelihood"),
            }
            cog = (raw_step.get("cognitive_action") or "").strip().lower() or "recall"
            steps_out.append({
                "step_id": raw_step.get("step_id") or f"s?.{s_idx+1}",
                "step_order": s_idx + 1,
                "step_title": _strip_or_none(raw_step.get("step_title")) or "",
                "cognitive_action": cog,
                "cognitive_meta": cognitive_action_meta(cog),
                "anchor_page": raw_step.get("anchor_page"),
                "anchor_pages": _list_or_empty(raw_step.get("anchor_pages")) or (
                    [str(raw_step.get("anchor_page"))] if raw_step.get("anchor_page") is not None else []
                ),
                "key_question": _strip_or_none(raw_step.get("key_question")) or "",
                "learning_action": _strip_or_none(raw_step.get("learning_action")) or "",
                "weight": int(weight or 2),
                "pause_seconds": pause_seconds,
                "is_pause": pause_seconds > 0,
                "blank_lines": blanks,
                "answer": answer_parts,
            })
            total_steps += 1
            if pause_seconds > 0:
                total_pauses += 1
            total_blank_lines += blanks

        sections_out.append({
            "section_index": sec.get("section_index"),
            "section_number": sec.get("section_number"),
            "section_title": sec.get("section_title") or sec.get("title") or f"Section {len(sections_out) + 1}",
            "page_start": sec.get("page_start"),
            "page_end": sec.get("page_end"),
            "objective": _strip_or_none(sec.get("objective")) or "",
            "hook": _strip_or_none(sec.get("hook")) or "",
            "steps": steps_out,
            "assessment": _list_or_empty(sec.get("assessment")),
        })

    return {
        "schema_version": 1,
        "kind": "worksheet",
        "derived_from": {
            "kind": "lesson_plan",
            "schema_version": lesson_plan_data.get("schema_version"),
            "lesson_plan_created_at": lesson_plan_data.get("created_at"),
            "lesson_plan_updated_at": lesson_plan_data.get("updated_at"),
        },
        "title": lesson_plan_data.get("title") or "学案",
        "sections": sections_out,
        "stats": {
            "section_count": len(sections_out),
            "step_count": total_steps,
            "pause_count": total_pauses,
            "total_blank_lines": total_blank_lines,
        },
    }


# ============== Markdown 渲染（适合复制粘贴打印） ==============


def _md_blank_lines(n: int) -> str:
    """生成 n 条用于书写的下划线。"""
    line = "_" * 60
    return "\n\n".join([line] * max(1, n)) + "\n"


def render_worksheet_markdown(lesson_plan_data: Dict[str, Any], show_answers: bool = False) -> str:
    """把 lesson_plan_data 渲染成可打印的 Markdown。

    Args:
        show_answers: True 时在每个 step 末尾直接展开答案区；False 时把答案
                      塞进 <details> 折叠（Markdown 支持，在 GitHub/常见渲染器
                      中可点开；如果转 PDF 打印则建议 True）。
    """
    ws = render_worksheet_structured(lesson_plan_data)
    out: List[str] = []

    out.append(f"# {ws['title']}")
    stats = ws.get("stats") or {}
    out.append(
        f"\n> 派生自 lesson_plan ({lesson_plan_data.get('created_at', '?')})。"
        f" 共 {stats.get('section_count', 0)} 节 / {stats.get('step_count', 0)} 个 step"
        f" / {stats.get('pause_count', 0)} 处重点停顿。\n"
    )

    for sec in ws["sections"]:
        out.append(f"\n## §{sec['section_number']}. {sec['section_title']}"
                   f"   <small>p.{sec.get('page_start')}–{sec.get('page_end')}</small>\n")
        if sec.get("objective"):
            out.append(f"**📚 学习目标**：{sec['objective']}\n")
        if sec.get("hook"):
            out.append(f"**🪝 课前一问**：{sec['hook']}\n")
        out.append("\n---\n")

        for step in sec["steps"]:
            meta = step["cognitive_meta"]
            stars = "★" * max(1, min(3, int(step.get("weight", 2))))
            stars = stars.ljust(3, "☆")
            ap = step.get("anchor_page")
            ap_str = f"p.{ap}" if ap is not None else ""
            out.append(
                f"\n### ▌ `{step['step_id']}`   "
                f"{meta['emoji']} {meta['label_zh']} · 重要度 {stars}"
                f"{('   ' + ap_str) if ap_str else ''}\n"
            )
            if step.get("step_title"):
                out.append(f"\n_{step['step_title']}_\n")
            if step.get("is_pause"):
                out.append(f"\n> ⏸ **写 {step['pause_seconds']} 秒**\n")

            if step.get("key_question"):
                out.append(f"\n**❓ {step['key_question']}**\n")
            if step.get("learning_action"):
                out.append(f"\n🖊 _你要做_：{step['learning_action']}\n")

            # 书写留白
            out.append("\n" + _md_blank_lines(step.get("blank_lines", 3)))

            # 答案区
            ans = step.get("answer") or {}
            has_answer = any([
                ans.get("landing_sentence"),
                ans.get("reasoning_chain"),
                ans.get("common_mistake"),
            ])
            if has_answer:
                if show_answers:
                    out.append("\n**📖 答案与要点**\n")
                    _emit_answer_block(out, ans)
                else:
                    out.append("\n<details><summary>📖 显示答案</summary>\n")
                    _emit_answer_block(out, ans)
                    out.append("\n</details>\n")
            out.append("\n---\n")

        # 章末自检
        if sec.get("assessment"):
            out.append(f"\n#### ✅ 章末自检\n")
            for i, q in enumerate(sec["assessment"], 1):
                out.append(f"\n{i}. {q}")
                out.append("\n\n" + _md_blank_lines(2))
            out.append("\n")

    return "".join(out)


# ============== HTML 打印渲染 ==============
#
# 用浏览器 Ctrl+P 即可打印。@page 设了 A4 + 17mm margin；
# step 卡片整体 avoid page-break；答案区可全局隐藏（用 details/open 控制）。


def _html_escape(s: Any) -> str:
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _html_blank_lines(n: int) -> str:
    line = '<div class="ws-blank-line"></div>'
    return line * max(1, n)


def render_worksheet_html(lesson_plan_data: Dict[str, Any], show_answers: bool = False) -> str:
    """生成打印友好的 HTML（单文件，可在浏览器里 Ctrl+P 打印 A4）。"""
    ws = render_worksheet_structured(lesson_plan_data)
    title = ws.get("title") or "学案"
    stats = ws.get("stats") or {}

    out: List[str] = []
    out.append("<!DOCTYPE html>")
    out.append('<html lang="zh-CN"><head>')
    out.append('<meta charset="utf-8">')
    out.append(f"<title>{_html_escape(title)} - Worksheet</title>")
    out.append('<style>')
    out.append("""
@page { size: A4; margin: 17mm 15mm 15mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Source Han Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 12pt;
  color: #000;
  background: #fff;
  margin: 0;
  padding: 12mm 8mm;
  line-height: 1.55;
}
.ws-print-toolbar {
  position: sticky; top: 0;
  background: #1d3a6e; color: #fff;
  padding: 8px 12px;
  display: flex; gap: 8px; align-items: center;
  z-index: 50;
  margin: -12mm -8mm 12mm -8mm;
  font-size: 11pt;
}
.ws-print-toolbar button { background: #c0c0c0; color: #000; border: 2px outset #c0c0c0; padding: 4px 10px; cursor: pointer; font-size: 10pt; }
.ws-print-toolbar .spacer { flex: 1; }
.ws-print-toolbar label { color: #fff; user-select: none; }

@media print {
  .ws-print-toolbar { display: none !important; }
  body { padding: 0; }
}

h1.ws-title { margin: 0 0 4mm; font-size: 18pt; }
.ws-meta { color: #555; font-size: 10pt; margin-bottom: 4mm; }

section.ws-section { margin-top: 8mm; page-break-inside: auto; }
section.ws-section h2 { color: #1d3a6e; border-bottom: 2px solid #1d3a6e; padding: 0 0 1mm 0; margin: 0 0 3mm; font-size: 14pt; page-break-after: avoid; }
section.ws-section h2 .ws-page-range { font-size: 9pt; color: #666; font-weight: normal; margin-left: 8px; }

.ws-objective, .ws-hook {
  padding: 2mm 3mm;
  margin-bottom: 2mm;
  font-size: 10.5pt;
  border-left: 3px solid #c9a23c;
  background: #fff7d6;
  page-break-inside: avoid;
}
.ws-hook { background: #e6f0fa; border-left-color: #4a78c0; }

.ws-step {
  margin-top: 5mm;
  padding: 3mm 4mm;
  border: 1px solid #aaa;
  border-left: 4px solid #444;
  page-break-inside: avoid;
}
.ws-step.cog-recall   { border-left-color: #1565c0; }
.ws-step.cog-compute  { border-left-color: #7b1fa2; }
.ws-step.cog-decide   { border-left-color: #bf6e16; }
.ws-step.cog-connect  { border-left-color: #0e7c8c; }
.ws-step.cog-critique { border-left-color: #a02020; }
.ws-step.cog-intro    { border-left-color: #5b8ec9; }
.ws-step.cog-recap    { border-left-color: #7a8aa0; }
.ws-step.cog-summary  { border-left-color: #3aa55a; }
.ws-step.cog-example  { border-left-color: #cc8a00; }

.ws-step-head { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; font-size: 10pt; margin-bottom: 2mm; }
.ws-tag { background: #444; color: #fff; padding: 1px 5px; font-family: 'Courier New', monospace; font-size: 9pt; }
.ws-tag.cog-recall   { background: #1565c0; }
.ws-tag.cog-compute  { background: #7b1fa2; }
.ws-tag.cog-decide   { background: #bf6e16; }
.ws-tag.cog-connect  { background: #0e7c8c; }
.ws-tag.cog-critique { background: #a02020; }
.ws-tag.cog-intro    { background: #5b8ec9; }
.ws-tag.cog-recap    { background: #7a8aa0; }
.ws-tag.cog-summary  { background: #3aa55a; }
.ws-tag.cog-example  { background: #cc8a00; }
.ws-cog-label { color: #555; }
.ws-stars { color: #a07c1d; font-size: 10pt; }
.ws-anchor { color: #666; font-size: 9pt; }
.ws-pause-tag { background: #cc8a00; color: #fff; padding: 1px 5px; font-size: 9pt; }

.ws-step-title { color: #555; font-style: italic; margin-bottom: 1mm; font-size: 10.5pt; }
.ws-key-question { font-weight: bold; font-size: 11.5pt; margin: 2mm 0 1mm; }
.ws-learning-action { color: #555; font-size: 10pt; margin-bottom: 2mm; }

.ws-blank-lines { margin: 2mm 0; }
.ws-blank-line { border-bottom: 1px solid #c0b890; height: 7mm; }

.ws-answer {
  margin-top: 2mm;
  padding: 2mm 3mm;
  background: #f5fff7;
  border: 1px solid #c0d8c5;
  border-left: 3px solid #3aa55a;
  font-size: 10.5pt;
}
.ws-answer .label { font-weight: bold; }
.ws-answer ol { margin: 1mm 0 1mm 5mm; padding: 0; }
.ws-answer .mistake { color: #a02020; }
.ws-answer .exam { color: #666; font-style: italic; }

.ws-assessment {
  margin-top: 5mm;
  padding: 3mm 4mm;
  background: #e8f4ea;
  border: 1px solid #3aa55a;
  border-left: 4px solid #3aa55a;
  page-break-inside: avoid;
}
.ws-assessment h3 { color: #1b6b35; margin: 0 0 2mm; font-size: 12pt; }
.ws-assessment ol { padding-left: 6mm; margin: 0; }
.ws-assessment li { margin-bottom: 3mm; }

/* 全局答案隐藏开关 */
body.hide-answers .ws-answer { display: none; }
""")
    out.append('</style>')
    out.append('</head><body class="' + ('' if show_answers else 'hide-answers') + '">')

    # 顶部工具栏（仅屏幕）
    out.append('<div class="ws-print-toolbar">')
    out.append('<strong>📚 ' + _html_escape(title) + '</strong>')
    out.append('<span class="spacer"></span>')
    out.append('<label><input type="checkbox" id="ws-show-answers"'
               + (' checked' if show_answers else '')
               + ' onchange="document.body.classList.toggle(\'hide-answers\', !this.checked)"> 显示答案</label>')
    out.append('<button onclick="window.print()">🖨 打印 / 保存为 PDF</button>')
    out.append('</div>')

    out.append(f'<h1 class="ws-title">{_html_escape(title)}</h1>')
    out.append(f'<div class="ws-meta">共 {stats.get("section_count", 0)} 节 · '
               f'{stats.get("step_count", 0)} step · '
               f'{stats.get("pause_count", 0)} 处停顿 · '
               f'总留白 {stats.get("total_blank_lines", 0)} 行</div>')

    for sec in ws["sections"]:
        out.append('<section class="ws-section">')
        out.append('<h2>§' + _html_escape(sec.get("section_number")) + '. '
                   + _html_escape(sec.get("section_title")))
        page_start = sec.get("page_start")
        page_end = sec.get("page_end")
        if page_start is not None or page_end is not None:
            out.append(f'<span class="ws-page-range">p.{page_start}–{page_end}</span>')
        out.append('</h2>')

        if sec.get("objective"):
            out.append('<div class="ws-objective"><strong>📚 学习目标：</strong>'
                       + _html_escape(sec["objective"]) + '</div>')
        if sec.get("hook"):
            out.append('<div class="ws-hook"><strong>🪝 课前一问：</strong>'
                       + _html_escape(sec["hook"]) + '</div>')

        for step in sec.get("steps", []):
            cog = step.get("cognitive_action") or "recall"
            meta = step.get("cognitive_meta") or {}
            stars = ("★" * max(1, min(3, int(step.get("weight", 2))))).ljust(3, "☆")
            out.append(f'<div class="ws-step cog-{_html_escape(cog)}">')

            # 头部
            out.append('<div class="ws-step-head">')
            out.append(f'<span class="ws-tag cog-{_html_escape(cog)}">{_html_escape(step.get("step_id"))}</span>')
            out.append(f'<span class="ws-cog-label">{_html_escape(meta.get("emoji", ""))} {_html_escape(meta.get("label_zh", cog))}</span>')
            out.append(f'<span class="ws-stars">重要度 {stars}</span>')
            if step.get("anchor_page") is not None:
                out.append(f'<span class="ws-anchor">p.{_html_escape(step["anchor_page"])}</span>')
            if step.get("is_pause"):
                out.append(f'<span class="ws-pause-tag">⏸ 写 {int(step.get("pause_seconds", 0))} 秒</span>')
            out.append('</div>')

            if step.get("step_title"):
                out.append(f'<div class="ws-step-title">{_html_escape(step["step_title"])}</div>')
            if step.get("key_question"):
                out.append(f'<div class="ws-key-question">❓ {_html_escape(step["key_question"])}</div>')
            if step.get("learning_action"):
                out.append(f'<div class="ws-learning-action">🖊 你要做：{_html_escape(step["learning_action"])}</div>')

            # 留白
            out.append('<div class="ws-blank-lines">' + _html_blank_lines(int(step.get("blank_lines", 3))) + '</div>')

            # 答案区
            ans = step.get("answer") or {}
            has_answer = bool(
                ans.get("landing_sentence")
                or ans.get("reasoning_chain")
                or ans.get("common_mistake")
            )
            if has_answer:
                out.append('<div class="ws-answer">')
                if ans.get("landing_sentence"):
                    out.append(f'<div>📝 <span class="label">关键结论</span>：{_html_escape(ans["landing_sentence"])}</div>')
                chain = ans.get("reasoning_chain") or []
                if chain:
                    out.append('<div>🧩 <span class="label">推理</span>：<ol>')
                    for c in chain:
                        out.append(f'<li>{_html_escape(c)}</li>')
                    out.append('</ol></div>')
                if ans.get("common_mistake"):
                    out.append(f'<div class="mistake">⚠️ <span class="label">常见错误</span>：{_html_escape(ans["common_mistake"])}</div>')
                if ans.get("exam_likelihood") is not None:
                    try:
                        n = int(ans["exam_likelihood"])
                        out.append(f'<div class="exam">🎯 考查可能性：{n}/5</div>')
                    except Exception:
                        pass
                out.append('</div>')
            out.append('</div>')  # /.ws-step

        if sec.get("assessment"):
            out.append('<div class="ws-assessment">')
            out.append('<h3>✅ 章末自检</h3><ol>')
            for q in sec["assessment"]:
                out.append('<li>' + _html_escape(q)
                           + '<div class="ws-blank-lines">' + _html_blank_lines(2) + '</div></li>')
            out.append('</ol></div>')

        out.append('</section>')

    out.append('</body></html>')
    return "".join(out)


def _emit_answer_block(out: List[str], ans: Dict[str, Any]) -> None:
    if ans.get("landing_sentence"):
        out.append(f"\n📝 **关键结论**：{ans['landing_sentence']}\n")
    chain = ans.get("reasoning_chain") or []
    if chain:
        out.append("\n🧩 **推理**：\n")
        for i, step in enumerate(chain, 1):
            out.append(f"   {i}. {step}\n")
    if ans.get("common_mistake"):
        out.append(f"\n⚠️ **常见错误**：{ans['common_mistake']}\n")
    if ans.get("exam_likelihood"):
        try:
            n = int(ans["exam_likelihood"])
            out.append(f"\n🎯 _考查可能性_：{n}/5\n")
        except Exception:
            pass
