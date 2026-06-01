"""Lesson Plan：教学计划层（介于 outline/subdivisions 与 worksheet/script 之间）。

每个 outline section 输出一个 lesson_plan_section：
- objective + hook
- steps[] 含 step_id / cognitive_action / key_question / learning_action /
  reasoning_chain / landing_sentence / anchor_page(s) / weight /
  exam_likelihood / common_mistake / pause_seconds
- assessment[]

lesson_plan 是 worksheet 和 script 共同的 schema 中枢；step_id 是后续同步高亮的坐标。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 认知动作枚举
COGNITIVE_MAIN_ACTIONS = {"recall", "compute", "decide", "connect", "critique"}
COGNITIVE_TRANSITION_ACTIONS = {"intro", "recap", "summary", "example"}
COGNITIVE_ACTIONS = COGNITIVE_MAIN_ACTIONS | COGNITIVE_TRANSITION_ACTIONS

# 字段限制
MAX_OBJECTIVE_CHARS = 300
MAX_HOOK_CHARS = 200
MAX_STEP_TITLE_CHARS = 60
MAX_KEY_QUESTION_CHARS = 200
MAX_LEARNING_ACTION_CHARS = 80
MAX_REASONING_STEP_CHARS = 160
MAX_REASONING_CHAIN_LEN = 5
MAX_LANDING_SENTENCE_CHARS = 200
MAX_COMMON_MISTAKE_CHARS = 200
MAX_ASSESSMENT_CHARS = 200
MAX_ASSESSMENT_ITEMS = 6
MIN_STEPS = 2
MAX_STEPS = 12

# 默认值（用于缺省回填）
DEFAULT_WEIGHT = 2
MIN_WEIGHT = 1
MAX_WEIGHT = 3
DEFAULT_EXAM_LIKELIHOOD = 3
MIN_EXAM_LIKELIHOOD = 1
MAX_EXAM_LIKELIHOOD = 5
DEFAULT_PAUSE_SECONDS = 5
MIN_PAUSE_SECONDS = 0
MAX_PAUSE_SECONDS = 60

# Prompt 段落长度限制（与 agent_index 类似，控制单次 token）
MAX_SECTION_TEXT_CHARS = 22000

# 生成控制
LESSON_PLAN_MAX_ATTEMPTS = 3
LESSON_PLAN_COMPLETION_RETRY_ROUNDS = 2
# 经实测 13 节 / 并发 8 大约 100s 完成。提到 20 后典型一章基本一批跑完，
# 墙钟时间 ≈ 单节最慢响应。qwen-long DashScope 默认 60+ RPM，20 并发安全。
LESSON_PLAN_CONCURRENCY = 20
LESSON_PLAN_SECTION_TIMEOUT_SEC = 360


def _truncate_section_text_for_prompt(text: str) -> str:
    if len(text) <= MAX_SECTION_TEXT_CHARS:
        return text
    head = (MAX_SECTION_TEXT_CHARS * 2) // 3
    tail = MAX_SECTION_TEXT_CHARS - head - 120
    return (
        text[:head]
        + "\n\n[TRUNCATED: middle pages omitted to fit lesson-plan token budget]\n\n"
        + text[-tail:]
    )


def _extract_json_object(raw: str) -> str:
    content = (raw or "").strip()
    if content.startswith("```"):
        lines = content.split("\n")
        start_idx, end_idx = 0, len(lines)
        for i, line in enumerate(lines):
            if "{" in line:
                start_idx = i
                break
        for i in range(len(lines) - 1, -1, -1):
            if "}" in lines[i]:
                end_idx = i + 1
                break
        content = "\n".join(lines[start_idx:end_idx])
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else content


def _repair_json(s: str) -> str:
    if "[Error]" in s:
        s = s.split("[Error]")[0]
    s = s.strip()
    s = re.sub(r"^```json\s*", "", s)
    s = re.sub(r"^```\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    s = s.strip()
    if not s:
        return s
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    open_braces = s.count("{") - s.count("}")
    open_brackets = s.count("[") - s.count("]")
    if open_braces > 0 or open_brackets > 0:
        s = s.rstrip().rstrip(",")
        if s.count('"') % 2 != 0:
            s += '"'
        s += "}" * max(0, open_braces) + "]" * max(0, open_brackets)
    return s


def build_subdivision_anchor(human_section: Optional[Dict[str, Any]]) -> str:
    if not human_section:
        return ""
    subs = human_section.get("subdivisions") or []
    summary = (human_section.get("section_summary") or "").strip()
    lines: List[str] = []
    if summary:
        lines.append(f"**本节概括**：{summary[:400]}")
    if subs:
        lines.append("**已有子分段（作为认知锚点参考，可以重新分步）**：")
        for sub in subs:
            title = sub.get("title") or "子分段"
            ps = sub.get("page_start")
            pe = sub.get("page_end", ps)
            lines.append(f"- {title}（第 {ps}-{pe} 页）")
    return "\n".join(lines)


def build_lesson_plan_prompt(
    pdf_filename: str,
    section_title: str,
    section_number: int,
    page_start: int,
    page_end: int,
    section_full_text: str,
    subdivision_anchor: str = "",
    previous_landing: str = "",
    next_objective_hint: str = "",
    validation_error: str = "",
) -> str:
    """构造 lesson_plan 生成提示词。"""
    anchor_block = f"\n{subdivision_anchor}\n" if subdivision_anchor else ""
    prev_block = (
        f"\n**上一节最后一句结论**：{previous_landing[:160]}\n"
        if previous_landing
        else ""
    )
    next_block = (
        f"\n**下一节将要讲的主题（用于结尾衔接，不必展开）**：{next_objective_hint[:160]}\n"
        if next_objective_hint
        else ""
    )
    retry_block = (
        f"\n**上一次输出未通过校验，请修正后重试**：\n{validation_error}\n"
        if validation_error
        else ""
    )

    return f"""你正在为一个学习软件生成「教学计划（lesson_plan）」JSON。这是后续生成讲稿（口播 narration）和学案（worksheet 留白）的中枢，不会直接给学生看。

**课件文件**：{pdf_filename}
**本节是整章第 {section_number} 节**：section_number = {section_number}
**本节标题**：{section_title}
**页码范围**：{page_start}-{page_end}
{anchor_block}{prev_block}{next_block}
**本节原文（已截断到 token 预算内）**：
{section_full_text}
{retry_block}
**任务**：输出**单个 JSON 对象**（不要包裹 markdown 代码块，不要在 JSON 外加任何文字）。
顶层字段必须含 objective / hook / steps / assessment。

字段说明（严格遵守）：

1. `objective`（≤{MAX_OBJECTIVE_CHARS} 字）：一句话或两句话，描述「学完本节学生**能做什么**」。用动词开头（区分、推导、计算、判断、对比、批判…）。

2. `hook`（≤{MAX_HOOK_CHARS} 字）：开节的一个**小问题**或反直觉现象，用于吸引注意力。不要写"今天我们学…"这种废话。

3. `steps`：长度 {MIN_STEPS}–{MAX_STEPS} 的数组，按讲授顺序排列。**这是核心**。
   每个 step 必须包含（**`step_id` 不要自己写，会被后端按 `s{section_number}.<i>` 自动生成；如果你写了也会被覆盖，所以请省略**）：
   - `step_title`（≤{MAX_STEP_TITLE_CHARS} 字）：步骤标题
   - `cognitive_action`：枚举之一：
       * 主步骤：`recall`（背诵/识记）、`compute`（计算/推导）、`decide`（判断/选择）、`connect`（关联/对比）、`critique`（批判/质疑）
       * 过场：`intro`（段首引入）、`recap`（中段回顾）、`summary`（段尾小结）、`example`（举例/演示）
   - `anchor_page`（int，落在 {page_start}-{page_end}）：该步骤主要对应的 PDF 页
   - `anchor_pages`（int 数组，可与 anchor_page 一致）：该步骤涉及的所有页（跨页/章末串讲时列出全部相关页，否则给单元素数组）
   - `key_question`（≤{MAX_KEY_QUESTION_CHARS} 字）：这一步要让学生回答的小问题（自然语言一句）
   - `learning_action`（≤{MAX_LEARNING_ACTION_CHARS} 字）：学生需要做的**具体动作**，用动宾结构（如 "写下受体家族名称"、"画出信号通路三步"、"对比 ABA 与乙烯的差异"）。**禁止空话**（"理解本节"、"掌握内容"）。过场 step 可写 "听讲并联想前文" 这类。
   - `reasoning_chain`（字符串数组，长度 0–{MAX_REASONING_CHAIN_LEN}）：推理链条，每条 ≤{MAX_REASONING_STEP_CHARS} 字。主步骤建议 2–4 条；过场 step 可为空数组。
   - `landing_sentence`（≤{MAX_LANDING_SENTENCE_CHARS} 字）：这一步**最值得记住的一句话结论**（可背版）。
   - `weight`：1（轻量过场）/ 2（普通）/ 3（重点必考），决定后续讲稿长度和学案空间。
   - `exam_likelihood`：1–5，5 表示几乎必考。
   - `common_mistake`（≤{MAX_COMMON_MISTAKE_CHARS} 字，可空字符串）：学生常犯的错误或误解；若没有则给空字符串。
   - `pause_seconds`：0–{MAX_PAUSE_SECONDS}，学生在听完该步讲解后写答案需要的秒数。简单识记 3–5，推导 8–15，长句作答 15–30。过场 step 给 0。

4. `assessment`：长度 0–{MAX_ASSESSMENT_ITEMS} 的字符串数组，每条 ≤{MAX_ASSESSMENT_CHARS} 字，是节末的小测题/反思题，对应学案末尾的复习区。

**额外纪律**：
- 顺序：steps 必须严格按讲授顺序排列；同一页可有多步，但 anchor_page 不能往回跳（章末 summary 的 anchor_pages 可以跨整节）。
- 过场 step 占 0–2 个，不要喧宾夺主。
- 不要使用省略号 "..."、"etc."、"and so on" 这类填充。
- 不要在 JSON 外说话；不要写注释（`//`）；字符串内不要换行（用空格代替）。
- 数字字段必须是真正的数字，不要写成字符串。

**输出 JSON 结构示例（注意没有 step_id 字段）**：
{{
  "objective": "学生能够区分 ABA 与乙烯在气孔关闭中的不同时间窗口。",
  "hook": "为什么干旱时气孔秒级关闭，机械损伤反而慢得多？",
  "steps": [
    {{
      "step_title": "ABA 的快速响应路径",
      "cognitive_action": "recall",
      "anchor_page": {page_start},
      "anchor_pages": [{page_start}],
      "key_question": "ABA 结合的受体属于哪个家族？",
      "learning_action": "写下受体家族名称",
      "reasoning_chain": ["ABA 结合 PYR/PYL", "抑制 PP2C", "激活 SnRK2"],
      "landing_sentence": "ABA→PYR/PYL⊣PP2C→SnRK2 是干旱秒级响应的关键链。",
      "weight": 3,
      "exam_likelihood": 4,
      "common_mistake": "误以为 PYR/PYL 是离子通道",
      "pause_seconds": 5
    }}
  ],
  "assessment": ["写出 ABA 信号通路三步", "解释为何乙烯响应慢于 ABA"]
}}
"""


def _clip(text: Any, max_len: int) -> str:
    s = str(text or "").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > max_len:
        cut = s[:max_len]
        s = cut.rsplit(" ", 1)[0] if " " in cut[max_len // 2 :] else cut
    return s


def _clamp_int(val: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(val)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _normalize_cognitive_action(val: Any) -> str:
    s = str(val or "").strip().lower()
    if s in COGNITIVE_ACTIONS:
        return s
    # 常见同义
    mapping = {
        "memorize": "recall",
        "memory": "recall",
        "calculate": "compute",
        "derive": "compute",
        "compare": "connect",
        "contrast": "connect",
        "choose": "decide",
        "judge": "decide",
        "evaluate": "critique",
        "review": "recap",
        "conclusion": "summary",
        "wrap-up": "summary",
        "illustrate": "example",
    }
    return mapping.get(s, "recall")


def _normalize_anchor_pages(
    raw_anchor_page: Any,
    raw_anchor_pages: Any,
    page_start: int,
    page_end: int,
) -> Tuple[int, List[int]]:
    pages: List[int] = []
    if isinstance(raw_anchor_pages, list):
        for p in raw_anchor_pages:
            try:
                pi = int(p)
                if page_start <= pi <= page_end and pi not in pages:
                    pages.append(pi)
            except (TypeError, ValueError):
                continue
    try:
        single = int(raw_anchor_page)
        if page_start <= single <= page_end:
            if single not in pages:
                pages.insert(0, single)
        else:
            single = None
    except (TypeError, ValueError):
        single = None
    if not pages:
        # 兜底：用 page_start
        single = page_start
        pages = [page_start]
    if single is None or single not in pages:
        single = pages[0]
    pages.sort()
    return single, pages


def _normalize_step(
    raw_step: Any,
    section_number: int,
    step_index: int,
    page_start: int,
    page_end: int,
    warnings: List[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_step, dict):
        return None

    # step_id 一律由后端按 s{section_number}.{i} 强制生成，忽略 LLM 给的值。
    # 历史上模型经常把第一段写成页码或固定 "1"，导致跨节冲突，干脆完全后端兜底。
    forced_step_id = f"s{section_number}.{step_index + 1}"
    raw_step_id = str(raw_step.get("step_id") or "").strip()
    if raw_step_id and raw_step_id != forced_step_id:
        warnings.append(
            f"step[{step_index}] step_id '{raw_step_id}' 被规范化为 '{forced_step_id}'"
        )
    step_id_raw = forced_step_id

    step_title = _clip(raw_step.get("step_title"), MAX_STEP_TITLE_CHARS) or f"Step {step_index + 1}"
    cognitive_action = _normalize_cognitive_action(raw_step.get("cognitive_action"))
    anchor_page, anchor_pages = _normalize_anchor_pages(
        raw_step.get("anchor_page"),
        raw_step.get("anchor_pages"),
        page_start,
        page_end,
    )
    key_question = _clip(raw_step.get("key_question"), MAX_KEY_QUESTION_CHARS)
    learning_action = _clip(raw_step.get("learning_action"), MAX_LEARNING_ACTION_CHARS)

    reasoning_raw = raw_step.get("reasoning_chain") or []
    if not isinstance(reasoning_raw, list):
        reasoning_raw = [str(reasoning_raw)] if reasoning_raw else []
    reasoning_chain = [
        _clip(item, MAX_REASONING_STEP_CHARS)
        for item in reasoning_raw[:MAX_REASONING_CHAIN_LEN]
        if str(item).strip()
    ]

    landing_sentence = _clip(raw_step.get("landing_sentence"), MAX_LANDING_SENTENCE_CHARS)
    weight = _clamp_int(raw_step.get("weight"), MIN_WEIGHT, MAX_WEIGHT, DEFAULT_WEIGHT)
    exam_likelihood = _clamp_int(
        raw_step.get("exam_likelihood"),
        MIN_EXAM_LIKELIHOOD,
        MAX_EXAM_LIKELIHOOD,
        DEFAULT_EXAM_LIKELIHOOD,
    )
    common_mistake = _clip(raw_step.get("common_mistake"), MAX_COMMON_MISTAKE_CHARS)
    pause_seconds = _clamp_int(
        raw_step.get("pause_seconds"),
        MIN_PAUSE_SECONDS,
        MAX_PAUSE_SECONDS,
        0 if cognitive_action in COGNITIVE_TRANSITION_ACTIONS else DEFAULT_PAUSE_SECONDS,
    )

    # 关键字段校验（缺失则用兜底，给出 warning）
    if not key_question:
        if cognitive_action in COGNITIVE_TRANSITION_ACTIONS:
            key_question = step_title
        else:
            return None  # 主步骤缺 key_question 直接拒收
    if not learning_action:
        if cognitive_action in COGNITIVE_TRANSITION_ACTIONS:
            learning_action = "听讲并联想前文"
        else:
            return None  # 主步骤缺 learning_action 直接拒收
    if not landing_sentence:
        landing_sentence = step_title

    return {
        "step_id": step_id_raw,
        "step_index": step_index,
        "step_title": step_title,
        "cognitive_action": cognitive_action,
        "anchor_page": anchor_page,
        "anchor_pages": anchor_pages,
        "key_question": key_question,
        "learning_action": learning_action,
        "reasoning_chain": reasoning_chain,
        "landing_sentence": landing_sentence,
        "weight": weight,
        "exam_likelihood": exam_likelihood,
        "common_mistake": common_mistake,
        "pause_seconds": pause_seconds,
    }


def validate_and_normalize_lesson_plan(
    data: Dict[str, Any],
    section_number: int,
    page_start: int,
    page_end: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    if not isinstance(data, dict):
        return False, "根对象必须是 JSON object", None

    warnings: List[str] = []
    objective = _clip(data.get("objective"), MAX_OBJECTIVE_CHARS)
    if not objective:
        return False, "objective 不能为空", None
    hook = _clip(data.get("hook"), MAX_HOOK_CHARS)
    if not hook:
        warnings.append("hook 为空，已用空字符串占位")

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or len(raw_steps) < MIN_STEPS:
        return False, f"steps 必须是长度 ≥{MIN_STEPS} 的数组", None
    if len(raw_steps) > MAX_STEPS:
        warnings.append(f"steps 多于 {MAX_STEPS}，已截断")
        raw_steps = raw_steps[:MAX_STEPS]

    steps: List[Dict[str, Any]] = []
    for i, raw_step in enumerate(raw_steps):
        normalized = _normalize_step(
            raw_step,
            section_number,
            i,
            page_start,
            page_end,
            warnings,
        )
        if not normalized:
            return False, f"step[{i}] 缺少 key_question 或 learning_action，请重写", None
        steps.append(normalized)

    # anchor_page 单调性校验：允许同页连续，但不允许大幅回跳
    last_page = 0
    for i, step in enumerate(steps):
        cur = step["anchor_page"]
        if cur < last_page - 0:  # 允许回到之前页（recap/example 偶尔向前指）
            # 不直接拒收，但记录
            warnings.append(f"step[{i}] anchor_page 回跳到 {cur} (上一步 {last_page})")
        last_page = max(last_page, cur)

    assessment_raw = data.get("assessment") or []
    if not isinstance(assessment_raw, list):
        assessment_raw = [str(assessment_raw)] if assessment_raw else []
    assessment = [
        _clip(item, MAX_ASSESSMENT_CHARS)
        for item in assessment_raw[:MAX_ASSESSMENT_ITEMS]
        if str(item).strip()
    ]

    normalized = {
        "objective": objective,
        "hook": hook,
        "steps": steps,
        "assessment": assessment,
    }
    if warnings:
        normalized["_warnings"] = warnings
    return True, "", normalized


def parse_and_validate_response(
    accumulated: str,
    section_number: int,
    page_start: int,
    page_end: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        content = _extract_json_object(accumulated)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = json.loads(_repair_json(content))
        return validate_and_normalize_lesson_plan(
            payload, section_number, page_start, page_end
        )
    except json.JSONDecodeError as exc:
        return False, f"JSON 解析失败: {exc}", None
    except Exception as exc:
        return False, str(exc), None


def normalize_existing_section(
    stored_section: Dict[str, Any],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """对已存盘的 section dict 重跑 normalize（不再请求 LLM）。

    用于修复历史数据里的 step_id 异形等问题。返回与
    `validate_and_normalize_lesson_plan` 同样的 (ok, err, normalized) 三元组。
    成功时 normalized 是仅含 objective/hook/steps/assessment(+_warnings) 的内容部分；
    调用方需自行通过 build_section_result 再叠加 section_index 等元数据。
    """
    if not isinstance(stored_section, dict):
        return False, "section 不是 dict", None
    section_number = stored_section.get("section_number")
    page_start = stored_section.get("page_start")
    page_end = stored_section.get("page_end")
    if section_number is None or page_start is None or page_end is None:
        return False, "section 缺少 section_number / page_start / page_end", None
    payload = {
        "objective": stored_section.get("objective", ""),
        "hook": stored_section.get("hook", ""),
        "steps": stored_section.get("steps", []),
        "assessment": stored_section.get("assessment", []),
    }
    return validate_and_normalize_lesson_plan(
        payload, int(section_number), int(page_start), int(page_end)
    )


async def generate_lesson_plan_section(
    section_idx: int,
    section: Dict[str, Any],
    pdf_filename: str,
    board_id: str,
    window_id: str,
    get_page_contents,
    llm_chat_stream,
    get_subdivision_anchor,
    previous_landing: str = "",
    next_objective_hint: str = "",
    max_attempts: int = LESSON_PLAN_MAX_ATTEMPTS,
    on_chunk=None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    section_num = section.get("section_number", section_idx + 1)
    section_title = section.get("title", f"分段{section_num}")
    page_start = section.get("page_start")
    page_end = section.get("page_end")

    pages: List[Dict[str, Any]] = []
    for page_num in range(page_start, page_end + 1):
        page_content = get_page_contents(board_id, window_id, page_num)
        if page_content and page_content.get("current"):
            pages.append({"page": page_num, "content": page_content["current"]})
    if not pages:
        return None, "分段无页面内容"

    section_full_text = _truncate_section_text_for_prompt(
        "\n\n".join([f"=== Page {p['page']} ===\n{p['content']}" for p in pages])
    )
    subdivision_anchor = get_subdivision_anchor(board_id, window_id, section_idx) or ""

    validation_error = ""
    normalized: Optional[Dict[str, Any]] = None
    accumulated = ""

    for attempt in range(max_attempts):
        prompt = build_lesson_plan_prompt(
            pdf_filename,
            section_title,
            section_num,
            page_start,
            page_end,
            section_full_text,
            subdivision_anchor=subdivision_anchor,
            previous_landing=previous_landing,
            next_objective_hint=next_objective_hint,
            validation_error=validation_error,
        )
        messages = [{"role": "user", "content": prompt}]
        accumulated = ""
        async for chunk in llm_chat_stream(messages):
            if not chunk:
                continue
            if chunk.startswith("[Error]"):
                return None, f"LLM服务错误: {chunk}"
            accumulated += chunk
            if on_chunk:
                maybe = on_chunk(section_num, chunk)
                if hasattr(maybe, "__await__"):
                    await maybe
        ok, err, normalized = parse_and_validate_response(
            accumulated, section_num, page_start, page_end
        )
        if ok:
            break
        validation_error = err

    if not normalized:
        return None, validation_error or "校验失败"

    return build_section_result(section, section_idx, normalized), ""


def build_section_result(
    section: Dict[str, Any],
    section_idx: int,
    normalized: Dict[str, Any],
) -> Dict[str, Any]:
    section_num = section.get("section_number", section_idx + 1)
    # 原始 outline section 用 `title`；已存盘 lesson plan section 用 `section_title`。
    # 两边都接受，避免 normalize 路径把真名抹成 "Section N"。
    title = (
        section.get("section_title")
        or section.get("title")
        or f"Section {section_num}"
    )
    return {
        "section_index": section_idx,
        "section_number": section_num,
        "section_title": title,
        "page_start": section.get("page_start"),
        "page_end": section.get("page_end"),
        **normalized,
    }


def render_lesson_plan_markdown(lesson_plan: Dict[str, Any]) -> str:
    """简洁可读的 Markdown，用于人工 review；不是面向学生的学案。"""
    pdf_title = lesson_plan.get("pdf_filename", "document")
    sections = lesson_plan.get("sections") or []
    lines = [
        f"# Lesson Plan — {pdf_title}",
        "",
        f"- Generated: {lesson_plan.get('created_at', datetime.now().isoformat())}",
        f"- Sections: {lesson_plan.get('completed_sections', 0)}/{lesson_plan.get('total_sections', 0)}",
        "",
    ]
    for sec in sections:
        if not sec:
            continue
        title = sec.get("section_title", "")
        ps, pe = sec.get("page_start"), sec.get("page_end")
        lines.append(f"## {sec.get('section_number')}. {title} (p.{ps}-{pe})")
        lines.append("")
        lines.append(f"**Objective**: {sec.get('objective', '')}")
        if sec.get("hook"):
            lines.append(f"**Hook**: {sec['hook']}")
        lines.append("")
        for step in sec.get("steps", []):
            anchor = step.get("anchor_page")
            badges = (
                f"[{step.get('cognitive_action', '?')}]"
                f"[w{step.get('weight', '?')}]"
                f"[exam{step.get('exam_likelihood', '?')}]"
                f"[p.{anchor}]"
            )
            lines.append(f"### {step.get('step_id')} {step.get('step_title')} {badges}")
            lines.append(f"- Key question: {step.get('key_question', '')}")
            lines.append(f"- Learning action: {step.get('learning_action', '')}")
            chain = step.get("reasoning_chain") or []
            if chain:
                lines.append("- Reasoning:")
                for r in chain:
                    lines.append(f"  - {r}")
            lines.append(f"- Landing: {step.get('landing_sentence', '')}")
            if step.get("common_mistake"):
                lines.append(f"- ⚠ Common mistake: {step['common_mistake']}")
            lines.append(f"- Pause: {step.get('pause_seconds', 0)}s")
            lines.append("")
        assessment = sec.get("assessment") or []
        if assessment:
            lines.append("**Assessment**:")
            for a in assessment:
                lines.append(f"- {a}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
