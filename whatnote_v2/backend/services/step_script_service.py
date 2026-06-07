"""Step Script：以 lesson_plan 的 step 为单位生成口播讲稿。

每个 outline section 输出一组 blocks（intro_cue + 每个 step 一段 + 可选 pause_cue + outro_cue），
通过 step_id 与 lesson_plan / 后续 worksheet 锁同一坐标系，便于三栏联动。

不取代现有 pdf_narrator 的「按页讲稿」管线，而是平行存在。
将来 TTS 桥接时，把 blocks 平铺为带 step_id 的 sentence 列表喂进现有 TTS。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple


# 字段限制
MAX_SCRIPT_CHARS = 600                # 单个 main block 上限
MAX_CUE_CHARS = 200                   # intro/outro/pause cue 上限
MAX_SENTENCE_CHARS = 240              # 单句切句上限（兜底）
MIN_BLOCKS_PER_SECTION = 2

# 内容驱动长度建议（仅写进 prompt 引导）
WEIGHT_TO_TARGET_CHARS = {
    1: (60, 110),    # 过场 / 轻量
    2: (120, 220),   # 普通主步骤
    3: (200, 360),   # 重点必考
}

# 生成控制
STEP_SCRIPT_MAX_ATTEMPTS = 3
STEP_SCRIPT_COMPLETION_RETRY_ROUNDS = 2
STEP_SCRIPT_CONCURRENCY = 20
STEP_SCRIPT_SECTION_TIMEOUT_SEC = 360

# Prompt 长度上限（lesson_plan 整节已结构化，所以比 lesson_plan 自身的 prompt 更紧）
MAX_PROMPT_SECTION_TEXT_CHARS = 14000

VALID_BLOCK_KINDS = {"intro_cue", "main", "pause_cue", "outro_cue"}


def _truncate_section_text_for_prompt(text: str) -> str:
    if len(text) <= MAX_PROMPT_SECTION_TEXT_CHARS:
        return text
    head = (MAX_PROMPT_SECTION_TEXT_CHARS * 2) // 3
    tail = MAX_PROMPT_SECTION_TEXT_CHARS - head - 120
    return (
        text[:head]
        + "\n\n[TRUNCATED: middle omitted to fit step-script token budget]\n\n"
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


def _clip(text: Any, max_len: int) -> str:
    s = str(text or "").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) > max_len:
        cut = s[:max_len]
        s = cut.rsplit(" ", 1)[0] if " " in cut[max_len // 2 :] else cut
    return s


def _split_sentences(text: str) -> List[str]:
    """智能分句：保留标点；过长的硬切。给 TTS 用。"""
    pattern = r"([。！？；.!?;])"
    raw = text.strip()
    if not raw:
        return []
    lines = raw.split("\n")
    out: List[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = re.split(pattern, line)
        cur = ""
        for p in parts:
            cur += p
            if re.match(pattern, p):
                cur = cur.strip()
                if cur:
                    out.extend(_hard_split_long(cur))
                cur = ""
        if cur.strip():
            out.extend(_hard_split_long(cur.strip()))
    return out


def _hard_split_long(s: str) -> List[str]:
    if len(s) <= MAX_SENTENCE_CHARS:
        return [s]
    # 用逗号断
    chunks = re.split(r"([，,])", s)
    out: List[str] = []
    cur = ""
    for c in chunks:
        if len(cur) + len(c) > MAX_SENTENCE_CHARS and cur:
            out.append(cur.strip())
            cur = c
        else:
            cur += c
    if cur.strip():
        out.append(cur.strip())
    # 还过长就硬切
    final: List[str] = []
    for c in out:
        if len(c) <= MAX_SENTENCE_CHARS:
            final.append(c)
        else:
            for i in range(0, len(c), MAX_SENTENCE_CHARS):
                final.append(c[i : i + MAX_SENTENCE_CHARS])
    return final


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _format_steps_for_prompt(steps: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for st in steps:
        sid = st.get("step_id", "?")
        page = st.get("anchor_page", "?")
        action = st.get("cognitive_action", "?")
        weight = st.get("weight", 2)
        exam = st.get("exam_likelihood", 3)
        pause = st.get("pause_seconds", 0)
        target = WEIGHT_TO_TARGET_CHARS.get(int(weight), (120, 220))
        title = st.get("step_title", "")
        kq = st.get("key_question", "")
        la = st.get("learning_action", "")
        rc = st.get("reasoning_chain") or []
        ls = st.get("landing_sentence", "")
        cm = st.get("common_mistake", "")
        lines.append(
            f"  - step_id={sid}  page={page}  action={action}  weight={weight}  exam={exam}  pause={pause}s  target={target[0]}–{target[1]}字"
        )
        if title:
            lines.append(f"    title: {title}")
        lines.append(f"    key_question: {kq}")
        lines.append(f"    learning_action: {la}")
        if rc:
            lines.append("    reasoning_chain:")
            for r in rc:
                lines.append(f"      - {r}")
        lines.append(f"    landing_sentence: {ls}")
        if cm:
            lines.append(f"    common_mistake: {cm}")
    return "\n".join(lines)


def build_step_script_prompt(
    pdf_filename: str,
    section_number: int,
    section_title: str,
    page_start: int,
    page_end: int,
    objective: str,
    hook: str,
    steps: List[Dict[str, Any]],
    assessment: List[str],
    section_full_text: str,
    previous_landing: str = "",
    next_objective_hint: str = "",
    validation_error: str = "",
    extra_user_instruction: str = "",
) -> str:
    steps_block = _format_steps_for_prompt(steps)
    assessment_block = ""
    if assessment:
        assessment_block = "\n**节末小测/反思（可在 outro_cue 里点一下，不必朗读全部）**：\n" + "\n".join(
            f"- {a}" for a in assessment[:4]
        )
    prev_block = (
        f"\n**上一节最后一句结论（节首可以承接，不要硬开场）**：{previous_landing[:160]}\n"
        if previous_landing
        else ""
    )
    next_block = (
        f"\n**下一节主题（outro 可以暗示）**：{next_objective_hint[:160]}\n"
        if next_objective_hint
        else ""
    )
    retry_block = (
        f"\n**上次输出未通过校验，请修正**：\n{validation_error}\n"
        if validation_error
        else ""
    )
    extra_instruction_block = ""
    if extra_user_instruction and extra_user_instruction.strip():
        # 用户提供的额外要求；schema 与硬性规则不可改写
        trimmed = extra_user_instruction.strip()[:800]
        extra_instruction_block = (
            "\n**用户追加的写作偏好（在不违反硬性规则与输出 schema 的前提下尽量满足）**：\n"
            f"{trimmed}\n"
        )

    return f"""你是一位经验丰富、节奏感强的老师。请把下面这节课的「教学计划（lesson_plan）」改写成**面向耳朵**的逐 step 口播讲稿，输出**单个 JSON 对象**。

**课件**：{pdf_filename}
**本节**：第 {section_number} 节《{section_title}》  pages {page_start}–{page_end}
**学习目标**：{objective}
**节首钩子（hook，仅供你撰写 intro_cue 时参考，可改写）**：{hook}
{prev_block}{next_block}
**教学计划（已切好的 step，按讲授顺序）**：
{steps_block}
{assessment_block}

**本节 PDF 原文（仅用作细节核对，不要照念）**：
{section_full_text}
{retry_block}

------

**输出 schema**（顶层只有 `blocks` 一个字段，按顺序排列）：
```
{{
  "blocks": [
    {{ "kind": "intro_cue",  "anchor_page": <int>, "script": "...一两句开场..." }},
    {{ "kind": "main", "step_id": "s{section_number}.1", "anchor_page": <int>, "script": "...这一步完整口播..." }},
    {{ "kind": "pause_cue", "step_id": "s{section_number}.1", "anchor_page": <int>, "pause_seconds": 5, "script": "...一句具体提示..." }},
    {{ "kind": "main", "step_id": "s{section_number}.2", "anchor_page": <int>, "script": "..." }},
    ...
    {{ "kind": "outro_cue", "anchor_page": <int>, "script": "...一两句小结+预告..." }}
  ]
}}
```

**硬性规则**：
1. **每个 step 必须对应恰好一个 `kind:"main"` block**，`step_id` 与 lesson_plan 一致；顺序与 lesson_plan 一致；不要漏、不要多、不要改 step_id。
2. **`pause_cue` 仅当对应 step 的 `pause_seconds > 0` 时插入**，且紧跟在该 step 的 main block 之后；`step_id` 必须与所跟随的 step 一致；`script` 要写出**具体让学生做什么**（基于该 step 的 learning_action 写一句自然话，不要写「请暂停」「请思考」这种空话）。例：「现在停 5 秒，把临界角公式写下来」「停 8 秒，画出 PYR/PYL → PP2C → SnRK2 三步链」。
3. `intro_cue` 必须是 blocks 的第一项，写**节首引入**：用上节承接（如有）或一句反直觉问题引入，再用一句话告诉学生「这一节要弄清楚 X」。≤{MAX_CUE_CHARS} 字。**不要照念 hook 原文**，可以化用。
4. `outro_cue` 必须是 blocks 的最后一项，做**节末收尾**：一句话回扣 objective，再一句话引出下一节或留个开放问题。≤{MAX_CUE_CHARS} 字。
5. 每个 main block 的 `script` 长度按对应 step 的 weight 控制：weight=1 → 60–110 字；weight=2 → 120–220 字；weight=3 → 200–360 字。**不要超 {MAX_SCRIPT_CHARS} 字**。
6. main block 内部按「先问问题（用 key_question 改写口语化的版本）→ 给最短必要背景 → 走 reasoning_chain → 落到 landing_sentence」的微节奏。**reasoning_chain 不一定每条都念，但顺序不能颠倒**。
7. 过场 step（cognitive_action 是 `intro/recap/summary/example`）的 main block 可以一两句带过，不用走完整微节奏。
8. **anchor_page** 必须落在本节 page 范围内（{page_start}–{page_end}），与对应 step 的 anchor_page 保持一致；intro_cue 用 {page_start}，outro_cue 用 {page_end}。
9. **不要引用 step_id 本身**（不要在讲稿里说「s4.3」「step 3」），它只是数据坐标。
10. 第一人称口语：「我们看…」「这里有一个细节…」「想一想…」；**禁止**「第一点、第二点」「接下来 PPT 显示…」「请看下一页」这类。
11. 不要使用省略号 `...`、`etc.`、`and so on`；字符串内不要换行（用空格替代）；数字字段必须是真正数字。
12. **不要包裹 markdown 代码块**；只输出顶层 JSON。
{extra_instruction_block}
------

下面就开始：
"""


# ---------------------------------------------------------------------------
# Normalize / validate
# ---------------------------------------------------------------------------


def _normalize_block(
    raw: Any,
    section_number: int,
    page_start: int,
    page_end: int,
    expected_step_ids_in_order: List[str],
    warnings: List[str],
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in VALID_BLOCK_KINDS:
        warnings.append(f"block kind '{kind}' 不在 {VALID_BLOCK_KINDS}，已丢弃")
        return None

    step_id_raw = raw.get("step_id")
    step_id = str(step_id_raw).strip() if step_id_raw else None
    if kind in ("intro_cue", "outro_cue"):
        step_id = None  # 强制清空
    elif step_id is None or not step_id:
        warnings.append(f"block kind={kind} 缺 step_id，已丢弃")
        return None

    # anchor_page
    try:
        anchor_page = int(raw.get("anchor_page"))
        if not (page_start <= anchor_page <= page_end):
            anchor_page = page_start if kind == "intro_cue" else page_end if kind == "outro_cue" else page_start
            warnings.append(f"block {kind}/{step_id} anchor_page 越界，已修正为 {anchor_page}")
    except (TypeError, ValueError):
        anchor_page = page_start if kind == "intro_cue" else page_end if kind == "outro_cue" else page_start
        warnings.append(f"block {kind}/{step_id} anchor_page 非数字，已填 {anchor_page}")

    script = _clip(raw.get("script"), MAX_CUE_CHARS if kind != "main" else MAX_SCRIPT_CHARS)
    if not script:
        warnings.append(f"block {kind}/{step_id} script 为空，已丢弃")
        return None

    block: Dict[str, Any] = {
        "kind": kind,
        "step_id": step_id,
        "anchor_page": anchor_page,
        "script": script,
        "sentences": _split_sentences(script),
    }
    if kind == "pause_cue":
        try:
            ps = int(raw.get("pause_seconds") or 5)
        except (TypeError, ValueError):
            ps = 5
        block["pause_seconds"] = max(1, min(60, ps))
    return block


def _expected_step_specs(steps: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
    """返回 [(step_id, pause_seconds), ...]，用于校验 main / pause_cue 期望。"""
    out: List[Tuple[str, int]] = []
    for st in steps:
        sid = st.get("step_id")
        if not sid:
            continue
        ps = st.get("pause_seconds") or 0
        try:
            ps = int(ps)
        except (TypeError, ValueError):
            ps = 0
        out.append((str(sid), ps))
    return out


def validate_and_normalize_step_script(
    data: Dict[str, Any],
    section_number: int,
    page_start: int,
    page_end: int,
    expected_steps: List[Dict[str, Any]],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    if not isinstance(data, dict):
        return False, "根对象必须是 JSON object", None

    raw_blocks = data.get("blocks")
    if not isinstance(raw_blocks, list) or len(raw_blocks) < MIN_BLOCKS_PER_SECTION:
        return False, f"blocks 必须是长度 ≥{MIN_BLOCKS_PER_SECTION} 的数组", None

    expected_specs = _expected_step_specs(expected_steps)
    expected_ids_in_order = [sid for sid, _ in expected_specs]
    expected_pause_map = {sid: ps for sid, ps in expected_specs}

    warnings: List[str] = []
    blocks: List[Dict[str, Any]] = []
    for raw in raw_blocks:
        nb = _normalize_block(raw, section_number, page_start, page_end, expected_ids_in_order, warnings)
        if nb:
            blocks.append(nb)
    if not blocks:
        return False, "所有 block 都未通过规范化", None

    # main block step_id 覆盖度
    main_ids_seen = [b["step_id"] for b in blocks if b["kind"] == "main"]
    missing_main = [sid for sid in expected_ids_in_order if sid not in main_ids_seen]
    extra_main = [sid for sid in main_ids_seen if sid not in expected_ids_in_order]
    if missing_main:
        return False, f"缺失 main block: {missing_main[:5]}", None
    if extra_main:
        warnings.append(f"出现多余 main step_id: {extra_main}，已忽略（保留）")

    # 重排顺序：intro_cue → 按 expected 顺序遍历 step → 每个 step main → pause_cue（如该 step 应有 pause 且模型给了）→ outro_cue
    intro_blocks = [b for b in blocks if b["kind"] == "intro_cue"]
    outro_blocks = [b for b in blocks if b["kind"] == "outro_cue"]
    main_blocks_by_id: Dict[str, Dict[str, Any]] = {}
    pause_blocks_by_id: Dict[str, Dict[str, Any]] = {}
    for b in blocks:
        if b["kind"] == "main":
            # 保留第一次出现的；后续重复丢弃
            main_blocks_by_id.setdefault(b["step_id"], b)
        elif b["kind"] == "pause_cue":
            pause_blocks_by_id.setdefault(b["step_id"], b)

    if not intro_blocks:
        # 自动补一个最简 intro，不致命
        intro_blocks = [
            {
                "kind": "intro_cue",
                "step_id": None,
                "anchor_page": page_start,
                "script": f"我们进入第{section_number}节。",
                "sentences": [f"我们进入第{section_number}节。"],
            }
        ]
        warnings.append("缺 intro_cue，已用最简版补齐")
    if not outro_blocks:
        outro_blocks = [
            {
                "kind": "outro_cue",
                "step_id": None,
                "anchor_page": page_end,
                "script": "这一节就到这里。",
                "sentences": ["这一节就到这里。"],
            }
        ]
        warnings.append("缺 outro_cue，已用最简版补齐")

    ordered: List[Dict[str, Any]] = [intro_blocks[0]]
    for sid in expected_ids_in_order:
        ordered.append(main_blocks_by_id[sid])
        expected_pause = expected_pause_map.get(sid, 0)
        if expected_pause > 0 and sid in pause_blocks_by_id:
            ordered.append(pause_blocks_by_id[sid])
        elif expected_pause > 0:
            warnings.append(f"{sid} 应有 pause_cue (pause={expected_pause}s)，模型未生成")
        elif sid in pause_blocks_by_id:
            warnings.append(f"{sid} 不应出 pause_cue（lesson_plan pause_seconds=0），已丢弃")
    ordered.append(outro_blocks[-1])

    # 给每个 block 一个稳定的 block_index
    for i, b in enumerate(ordered):
        b["block_index"] = i

    normalized = {"blocks": ordered}
    if warnings:
        normalized["_warnings"] = warnings
    return True, "", normalized


def parse_and_validate_response(
    accumulated: str,
    section_number: int,
    page_start: int,
    page_end: int,
    expected_steps: List[Dict[str, Any]],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        content = _extract_json_object(accumulated)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = json.loads(_repair_json(content))
        return validate_and_normalize_step_script(
            payload, section_number, page_start, page_end, expected_steps
        )
    except json.JSONDecodeError as exc:
        return False, f"JSON 解析失败: {exc}", None
    except Exception as exc:
        return False, str(exc), None


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


async def generate_step_script_section(
    section_idx: int,
    section: Dict[str, Any],
    pdf_filename: str,
    board_id: str,
    window_id: str,
    get_page_contents: Callable,
    llm_chat_stream: Callable,
    previous_landing: str = "",
    next_objective_hint: str = "",
    max_attempts: int = STEP_SCRIPT_MAX_ATTEMPTS,
    on_chunk=None,
    override_model: Optional[str] = None,
    extra_user_instruction: str = "",
) -> Tuple[Optional[Dict[str, Any]], str]:
    section_num = section.get("section_number", section_idx + 1)
    section_title = section.get("section_title", f"Section {section_num}")
    page_start = section.get("page_start")
    page_end = section.get("page_end")
    objective = section.get("objective", "")
    hook = section.get("hook", "")
    steps = section.get("steps") or []
    assessment = section.get("assessment") or []

    if not steps:
        return None, "lesson_plan 该节没有 steps"

    pages: List[Dict[str, Any]] = []
    for page_num in range(page_start, page_end + 1):
        page_content = get_page_contents(board_id, window_id, page_num)
        if page_content and page_content.get("current"):
            pages.append({"page": page_num, "content": page_content["current"]})
    section_full_text = _truncate_section_text_for_prompt(
        "\n\n".join([f"=== Page {p['page']} ===\n{p['content']}" for p in pages])
    ) if pages else "(no PDF content available)"

    validation_error = ""
    normalized: Optional[Dict[str, Any]] = None

    for attempt in range(max_attempts):
        prompt = build_step_script_prompt(
            pdf_filename,
            section_num,
            section_title,
            page_start,
            page_end,
            objective,
            hook,
            steps,
            assessment,
            section_full_text,
            previous_landing=previous_landing,
            next_objective_hint=next_objective_hint,
            validation_error=validation_error,
            extra_user_instruction=extra_user_instruction,
        )
        messages = [{"role": "user", "content": prompt}]
        accumulated = ""
        async for chunk in llm_chat_stream(messages, stream=True, override_model=override_model):
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
            accumulated, section_num, page_start, page_end, steps
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
    title = section.get("section_title") or section.get("title") or f"Section {section_num}"
    warnings = normalized.pop("_warnings", []) if isinstance(normalized, dict) else []
    result = {
        "section_index": section_idx,
        "section_number": section_num,
        "section_title": title,
        "page_start": section.get("page_start"),
        "page_end": section.get("page_end"),
        "objective": section.get("objective", ""),
        "hook": section.get("hook", ""),
        **normalized,
    }
    if warnings:
        result["_warnings"] = warnings
    return result


def normalize_existing_section(
    stored_section: Dict[str, Any],
    lesson_plan_section: Dict[str, Any],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """对已存盘的 step_script section 重跑规范化（不调 LLM）。

    需要 lesson_plan_section 提供 expected_steps，用于检验 step_id 覆盖度与 pause 期望。
    """
    if not isinstance(stored_section, dict) or not isinstance(lesson_plan_section, dict):
        return False, "stored_section / lesson_plan_section 不是 dict", None
    page_start = stored_section.get("page_start") or lesson_plan_section.get("page_start")
    page_end = stored_section.get("page_end") or lesson_plan_section.get("page_end")
    section_number = stored_section.get("section_number") or lesson_plan_section.get("section_number")
    if page_start is None or page_end is None or section_number is None:
        return False, "section 缺少 page_start / page_end / section_number", None
    payload = {"blocks": stored_section.get("blocks", [])}
    return validate_and_normalize_step_script(
        payload,
        int(section_number),
        int(page_start),
        int(page_end),
        lesson_plan_section.get("steps") or [],
    )


# ---------------------------------------------------------------------------
# Markdown render（人工 review 用，不是面向学生）
# ---------------------------------------------------------------------------


def render_step_script_markdown(step_script: Dict[str, Any]) -> str:
    pdf_title = step_script.get("pdf_filename", "document")
    sections = step_script.get("sections") or []
    lines = [
        f"# Step Script — {pdf_title}",
        "",
        f"- Generated: {step_script.get('created_at', datetime.now().isoformat())}",
        f"- Sections: {step_script.get('completed_sections', 0)}/{step_script.get('total_sections', 0)}",
        f"- Elapsed: {step_script.get('elapsed_seconds', '?')}s  (concurrency {step_script.get('concurrency', '?')})",
        "",
    ]
    for sec in sections:
        if not sec:
            continue
        title = sec.get("section_title", "")
        ps, pe = sec.get("page_start"), sec.get("page_end")
        lines.append(f"## {sec.get('section_number')}. {title} (p.{ps}-{pe})")
        if sec.get("objective"):
            lines.append(f"_Objective_: {sec['objective']}")
        if sec.get("hook"):
            lines.append(f"_Hook_: {sec['hook']}")
        lines.append("")
        for b in sec.get("blocks", []):
            kind = b.get("kind")
            sid = b.get("step_id") or "—"
            page = b.get("anchor_page")
            if kind == "intro_cue":
                lines.append(f"### ▶ Intro  (p.{page})")
            elif kind == "outro_cue":
                lines.append(f"### ◀ Outro  (p.{page})")
            elif kind == "pause_cue":
                lines.append(f"### ⏸ Pause [{sid}]  (p.{page}, {b.get('pause_seconds', '?')}s)")
            else:
                lines.append(f"### {sid}  (p.{page})")
            lines.append(b.get("script", ""))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
