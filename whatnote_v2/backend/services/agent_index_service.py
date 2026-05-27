"""Agent 索引：提示词、校验与 Markdown 渲染"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

CORE_SCHEMA_KEYS = [
    "Entities/Objects",
    "Process/Method",
    "Key Relation",
    "Evidence/Example",
    "Output/Result",
    "Assumptions/Conditions",
]

BANNED_KEYWORDS = {
    "important",
    "classic",
    "significant",
    "key",
    "main",
    "basic",
    "common",
    "general",
    "various",
    "related",
    "overview",
    "introduction",
    "summary",
    "concept",
    "content",
    "chapter",
    "section",
    "framework",
    "integration",
    "paradigm",
    "structure",
    "function",
    "mechanism",
    "process",
    "system",
    "approach",
    "strategy",
    "network",
    "regulation",
    "signaling",
    "development",
    "interaction",
    "analysis",
    "understanding",
    "fundamental",
    "essential",
    "role",
    "important",
    "重要",
    "经典",
    "关键",
    "主要",
    "基本",
    "概述",
    "简介",
    "内容",
    "章节",
    "框架",
    "整合",
    "机制",
}

# 过宽、多节可复用的词；每节最多保留 2 个
GENERIC_KEYWORDS = {
    "hormones",
    "hormone",
    "transport",
    "transportation",
    "pathway",
    "pathways",
    "metabolism",
    "nutrition",
    "cycle",
    "cycles",
    "plant",
    "plants",
    "root",
    "roots",
    "soil",
    "growth",
    "efficiency",
    "uptake",
    "assimilation",
    "microbes",
    "microbial",
    "bacteria",
    "nitrogen cycle",
    "mineral nutrition",
}

MAX_ONE_LINER_PROMPT_CHARS = 240
MAX_ONE_LINER_CHARS = 260
MAX_ONE_LINER_SENTENCES = 2
MAX_CORE_SCHEMA_CHARS = 80
MAX_CORE_SCHEMA_WORDS = 18
MAX_SUB_ONE_LINER_CHARS = 180
MAX_KEYWORDS = 10
MAX_GENERIC_KEYWORDS = 2
MIN_EXAM_HOOKS = 2
MAX_EXAM_HOOKS = 4

_SCHEMA_CLAUSE_SPLIT = re.compile(
    r"\s*;\s*|\s+which\s+|\s+that\s+|\s+because\s+|\s+including\s+",
    re.IGNORECASE,
)
_ELLIPSIS_RE = re.compile(
    r"\.\.\.|…|\.{3,}|,\s*\.{2,}|(?:^|[\s,])(?:etc\.?|and so on|and others)(?:[\s,.]|$)",
    re.IGNORECASE,
)

AGENT_SECTION_MAX_ATTEMPTS = 4
AGENT_COMPLETION_RETRY_ROUNDS = 2


def _extract_json_object(raw: str) -> str:
    content = (raw or "").strip()
    if content.startswith("```"):
        lines = content.split("\n")
        start_idx = 0
        for i, line in enumerate(lines):
            if "{" in line:
                start_idx = i
                break
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if "}" in lines[i]:
                end_idx = i + 1
                break
        content = "\n".join(lines[start_idx:end_idx])
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return match.group(0) if match else content


def build_human_subdivisions_anchor(human_section: Optional[Dict[str, Any]]) -> str:
    if not human_section:
        return ""
    subs = human_section.get("subdivisions") or []
    if not subs:
        return ""
    lines = ["**参考子分段（可选锚点，页码需与原文一致）**："]
    for sub in subs:
        title = sub.get("title") or "子分段"
        ps = sub.get("page_start")
        pe = sub.get("page_end", ps)
        lines.append(f"- {title}（第 {ps}-{pe} 页）")
    return "\n".join(lines)


def build_agent_subdivision_prompt(
    pdf_filename: str,
    section_title: str,
    page_start: int,
    page_end: int,
    section_full_text: str,
    human_anchor: str = "",
    validation_error: str = "",
) -> str:
    anchor_block = f"\n{human_anchor}\n" if human_anchor else ""
    retry_block = (
        f"\n**上次输出未通过校验，请修正后重试**：\n{validation_error}\n"
        if validation_error
        else ""
    )

    return f"""You are building a machine-readable index for another AI agent (not for human reading).

**Document**: {pdf_filename}
**Section**: {section_title}
**Pages**: {page_start}-{page_end}
{anchor_block}
**Source text**:
{section_full_text}
{retry_block}
**Task** — output ONE JSON object only (no markdown fences, no prose outside JSON):

1. **one_liner** (STRICT — will be rejected if violated):
   - At most {MAX_ONE_LINER_SENTENCES} English sentences
   - At most {MAX_ONE_LINER_PROMPT_CHARS} characters (hard cap {MAX_ONE_LINER_CHARS})
   - State what this section covers + the problem/conclusion in compact form
   - Keep original terms/abbreviations (e.g. "ACC synthase (ACS)")
   - Do NOT write a mini-abstract; stop early rather than exceeding the limit

2. **core_schema**: object with EXACTLY these 6 keys. Each value is a SLOT FILL (not prose):
   - Max {MAX_CORE_SCHEMA_WORDS} words AND max {MAX_CORE_SCHEMA_CHARS} characters per value
   - Use noun phrases, symbols, or arrow relations only (e.g. "NO₃⁻ → NR → NH₄⁺", "NRT1.1, GS1, rhizobia")
   - NO explanatory clauses ("which...", "that...", "because...", lists of 8+ items)
   - NEVER use "...", "…", "etc.", "and so on", "and others" — if too many items, keep 2–4 names only or use UNKNOWN
   - Use "UNKNOWN" if missing
   Keys: "Entities/Objects", "Process/Method", "Key Relation", "Evidence/Example", "Output/Result", "Assumptions/Conditions"

3. **keywords**: array of <=10 strings. Prioritize:
   - Symbols, ions, formulas, gene/protein names, theorem/algorithm names, proper nouns
   - BAN: important, classic, framework, integration, and other vague words any chapter could share
   - Broad terms (hormones, transport, pathway, assimilation) only if unavoidable — max 2 such per section

4. **exam_hooks**: array of 2-4 strings. Each ONE sentence: "<verb>: <task> (→ <CORE_SCHEMA key>)"
   - Course/textbook: verbs define, compare, derive, apply, critique
   - Review/manual/interview: verbs summarize, explain, apply, troubleshoot, critique

5. **subdivisions**: array of light sub-units (do NOT repeat full core_schema). Each item:
   - subdivision_number (int)
   - title (string)
   - page_start, page_end (int, within {page_start}-{page_end})
   - one_liner (<=1 English sentence)

**JSON shape**:
{{
  "one_liner": "...",
  "core_schema": {{
    "Entities/Objects": "...",
    "Process/Method": "...",
    "Key Relation": "...",
    "Evidence/Example": "...",
    "Output/Result": "...",
    "Assumptions/Conditions": "..."
  }},
  "keywords": ["..."],
  "exam_hooks": ["derive: ... (→ Process/Method)"],
  "subdivisions": [
    {{"subdivision_number": 1, "title": "...", "page_start": {page_start}, "page_end": {page_end}, "one_liner": "..."}}
  ]
}}
"""


def _has_forbidden_ellipsis(text: str) -> bool:
    if not text or text.strip().upper() == "UNKNOWN":
        return False
    return bool(_ELLIPSIS_RE.search(text))


def _find_ellipsis_in_payload(payload: Dict[str, Any]) -> Optional[str]:
    one_liner = str(payload.get("one_liner", ""))
    if _has_forbidden_ellipsis(one_liner):
        return "one_liner 不得包含 ... / etc. / and so on"

    core = payload.get("core_schema") or {}
    if isinstance(core, dict):
        for key in CORE_SCHEMA_KEYS:
            val = str(core.get(key, ""))
            if _has_forbidden_ellipsis(val):
                return f"core_schema[{key}] 不得包含 ... / etc. / and so on"

    for i, kw in enumerate(payload.get("keywords") or []):
        if _has_forbidden_ellipsis(str(kw)):
            return f"keywords[{i}] 不得包含省略号或 etc."

    for i, hook in enumerate(payload.get("exam_hooks") or []):
        if _has_forbidden_ellipsis(str(hook)):
            return f"exam_hooks[{i}] 不得包含省略号或 etc."

    for i, sub in enumerate(payload.get("subdivisions") or []):
        if not isinstance(sub, dict):
            continue
        for field in ("title", "one_liner"):
            if _has_forbidden_ellipsis(str(sub.get(field, ""))):
                return f"subdivisions[{i}].{field} 不得包含省略号或 etc."
    return None


def _compress_schema_value(val: str) -> Tuple[str, Optional[str]]:
    val = re.sub(r"\s+", " ", (val or "").strip())
    if not val:
        return "UNKNOWN", None
    if _has_forbidden_ellipsis(val):
        return (
            val,
            "不得使用 .../etc./and so on；只写 2–4 个专名或用 UNKNOWN",
        )
    parts = _SCHEMA_CLAUSE_SPLIT.split(val, maxsplit=1)
    val = parts[0].strip() if parts else val
    words = val.split()
    if len(words) > MAX_CORE_SCHEMA_WORDS:
        val = " ".join(words[:MAX_CORE_SCHEMA_WORDS])
    if len(val) > MAX_CORE_SCHEMA_CHARS:
        return (
            val,
            f"超过 {MAX_CORE_SCHEMA_CHARS} 字符；缩短为更少专名/箭头短语，禁止 ...",
        )
    return val or "UNKNOWN", None


def _normalize_core_schema(raw: Any) -> Tuple[Dict[str, str], Optional[str]]:
    result: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key in CORE_SCHEMA_KEYS:
            val = str(raw.get(key, raw.get(key.replace("/", " "), "UNKNOWN"))).strip()
            compressed, err = _compress_schema_value(val)
            if err:
                return result, f"core_schema[{key}]: {err}"
            result[key] = compressed
        return result, None

    if isinstance(raw, list):
        for i, key in enumerate(CORE_SCHEMA_KEYS):
            if i < len(raw):
                if isinstance(raw[i], dict):
                    val = raw[i].get("value") or raw[i].get(key) or "UNKNOWN"
                else:
                    val = str(raw[i])
                compressed, err = _compress_schema_value(str(val))
            else:
                compressed, err = "UNKNOWN", None
            if err:
                return result, f"core_schema[{key}]: {err}"
            result[key] = compressed
        return result, None

    for key in CORE_SCHEMA_KEYS:
        result[key] = "UNKNOWN"
    return result, None


def _is_specific_keyword(item: str) -> bool:
    low = item.lower().strip()
    if low in BANNED_KEYWORDS or low in GENERIC_KEYWORDS:
        return False
    if re.search(r"[0-9+\-/²³⁻⁺Δ]", item):
        return True
    if re.search(r"\b[A-Z]{2,}[0-9]", item):
        return True
    if "(" in item or ")" in item:
        return True
    if re.search(r"\b[A-Z][a-z]+[0-9]", item):
        return True
    if len(item) >= 10 and re.search(r"[A-Z]{2,}", item):
        return True
    if re.search(r"[\u4e00-\u9fff]", item) and len(item) >= 2:
        return True
    if len(low) >= 12:
        return True
    return False


def _normalize_keywords(raw: Any) -> List[str]:
    if isinstance(raw, str):
        items = [k.strip() for k in re.split(r"[,，;；\n]", raw) if k.strip()]
    elif isinstance(raw, list):
        items = [str(k).strip() for k in raw if str(k).strip()]
    else:
        items = []

    specific: List[str] = []
    generic: List[str] = []
    for item in items:
        low = item.lower()
        if low in BANNED_KEYWORDS:
            continue
        if _has_forbidden_ellipsis(item):
            continue
        if len(item) > 80:
            item = item[:80].rsplit(" ", 1)[0] if " " in item[:80] else item[:80]
        if _is_specific_keyword(item):
            if item not in specific:
                specific.append(item)
        else:
            if low not in {g.lower() for g in generic}:
                generic.append(item)

    cleaned = specific[:MAX_KEYWORDS]
    remaining = MAX_KEYWORDS - len(cleaned)
    if remaining > 0:
        for g in generic[: min(MAX_GENERIC_KEYWORDS, remaining)]:
            if g not in cleaned:
                cleaned.append(g)
    return cleaned


def _count_sentences(text: str) -> int:
    parts = re.split(r"[.!?]+", text)
    return len([p for p in parts if p.strip()])


def _normalize_exam_hooks(raw: Any) -> List[str]:
    if isinstance(raw, str):
        hooks = [h.strip() for h in re.split(r"\n+", raw) if h.strip()]
    elif isinstance(raw, list):
        hooks = [str(h).strip() for h in raw if str(h).strip()]
    else:
        hooks = []

    hooks = hooks[:MAX_EXAM_HOOKS]
    defaults = [
        "summarize: State the main claim of this section (→ Output/Result)",
        "explain: Clarify the core mechanism or argument (→ Process/Method)",
    ]
    for default_hook in defaults:
        if len(hooks) >= MIN_EXAM_HOOKS:
            break
        if default_hook not in hooks:
            hooks.append(default_hook)
    return hooks[:MAX_EXAM_HOOKS]


def _normalize_subdivisions(raw: Any, page_start: int, page_end: int) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    result = []
    for i, sub in enumerate(raw, start=1):
        if not isinstance(sub, dict):
            continue
        ps = int(sub.get("page_start", page_start))
        pe = int(sub.get("page_end", ps))
        ps = max(page_start, min(ps, page_end))
        pe = max(ps, min(pe, page_end))
        one_liner = str(sub.get("one_liner", "")).strip()
        if len(one_liner) > MAX_SUB_ONE_LINER_CHARS:
            one_liner = one_liner[:MAX_SUB_ONE_LINER_CHARS]
        result.append(
            {
                "subdivision_number": sub.get("subdivision_number", i),
                "title": sub.get("title") or f"Sub-unit {i}",
                "page_start": ps,
                "page_end": pe,
                "one_liner": one_liner or "UNKNOWN",
            }
        )
    return result


def validate_and_normalize_agent_payload(
    data: Dict[str, Any],
    page_start: int,
    page_end: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """校验并归一化；超长字段自动截断/补齐，避免因格式细节丢弃整节。"""
    if not isinstance(data, dict):
        return False, "根对象必须是 JSON object", None

    warnings: List[str] = []

    one_liner = str(data.get("one_liner", "")).strip()
    if not one_liner:
        return False, "one_liner 不能为空", None
    if _count_sentences(one_liner) > MAX_ONE_LINER_SENTENCES:
        return (
            False,
            f"one_liner 超过 {MAX_ONE_LINER_SENTENCES} 句，请压缩为最多 2 句、≤{MAX_ONE_LINER_PROMPT_CHARS} 字符",
            None,
        )
    if len(one_liner) > MAX_ONE_LINER_CHARS:
        return (
            False,
            f"one_liner 长度 {len(one_liner)} 超过上限 {MAX_ONE_LINER_CHARS}，请重写为 ≤{MAX_ONE_LINER_PROMPT_CHARS} 字符、最多 2 句",
            None,
        )

    ellipsis_err = _find_ellipsis_in_payload(data)
    if ellipsis_err:
        return False, ellipsis_err, None

    core_schema, schema_err = _normalize_core_schema(data.get("core_schema"))
    if schema_err:
        return False, schema_err, None
    for key in CORE_SCHEMA_KEYS:
        if key not in core_schema:
            core_schema[key] = "UNKNOWN"
            warnings.append(f"core_schema missing {key}, filled UNKNOWN")

    keywords = _normalize_keywords(data.get("keywords"))
    if len(keywords) < 1:
        title_fallback = str(data.get("title") or data.get("section_title") or "").strip()
        if title_fallback:
            keywords = [title_fallback[:60]]
        else:
            keywords = ["UNKNOWN"]
        warnings.append("keywords empty, filled fallback")

    exam_hooks = _normalize_exam_hooks(data.get("exam_hooks"))
    if len(exam_hooks) < MIN_EXAM_HOOKS:
        warnings.append("exam_hooks padded to minimum")

    subdivisions = _normalize_subdivisions(data.get("subdivisions"), page_start, page_end)

    normalized = {
        "one_liner": one_liner,
        "core_schema": core_schema,
        "keywords": keywords,
        "exam_hooks": exam_hooks,
        "subdivisions": subdivisions,
    }
    ellipsis_err = _find_ellipsis_in_payload(normalized)
    if ellipsis_err:
        return False, ellipsis_err, None
    if warnings:
        normalized["_normalization_warnings"] = warnings
    return True, "", normalized


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


def parse_and_validate_agent_response(
    accumulated_content: str,
    page_start: int,
    page_end: int,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        content = _extract_json_object(accumulated_content)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = json.loads(_repair_json(content))
        return validate_and_normalize_agent_payload(payload, page_start, page_end)
    except json.JSONDecodeError as exc:
        return False, f"JSON 解析失败: {exc}", None
    except Exception as exc:
        return False, str(exc), None


async def generate_agent_section_index(
    section_idx: int,
    section: Dict[str, Any],
    pdf_filename: str,
    board_id: str,
    window_id: str,
    get_page_contents,
    llm_chat_stream,
    get_human_anchor,
    max_attempts: int = AGENT_SECTION_MAX_ATTEMPTS,
    on_chunk=None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """生成单节 Agent 索引。返回 (result, error_message)。"""
    section_num = section.get("section_number", section_idx + 1)
    section_title = section.get("title", f"分段{section_num}")
    page_start = section.get("page_start")
    page_end = section.get("page_end")

    section_pages_content = []
    for page_num in range(page_start, page_end + 1):
        page_content = get_page_contents(board_id, window_id, page_num)
        if page_content.get("current"):
            section_pages_content.append({"page": page_num, "content": page_content["current"]})

    if not section_pages_content:
        return None, "分段无页面内容"

    section_full_text = "\n\n".join(
        [f"=== Page {p['page']} ===\n{p['content']}" for p in section_pages_content]
    )
    human_anchor = get_human_anchor(board_id, window_id, section_idx) or ""

    validation_error = ""
    normalized = None
    accumulated_content = ""

    for attempt in range(max_attempts):
        prompt = build_agent_subdivision_prompt(
            pdf_filename,
            section_title,
            page_start,
            page_end,
            section_full_text,
            human_anchor,
            validation_error,
        )
        messages = [{"role": "user", "content": prompt}]
        accumulated_content = ""
        async for chunk in llm_chat_stream(messages):
            if not chunk:
                continue
            if chunk.startswith("[Error]"):
                return None, f"LLM服务错误: {chunk}"
            accumulated_content += chunk
            if on_chunk:
                maybe = on_chunk(section_num, chunk)
                if hasattr(maybe, "__await__"):
                    await maybe

        ok, err, normalized = parse_and_validate_agent_response(
            accumulated_content, page_start, page_end
        )
        if ok:
            break
        validation_error = err

    if not normalized:
        return None, validation_error or "校验失败"

    return build_agent_section_result(section, section_idx, normalized), ""


def build_agent_section_result(
    section: Dict[str, Any],
    section_idx: int,
    normalized: Dict[str, Any],
) -> Dict[str, Any]:
    section_num = section.get("section_number", section_idx + 1)
    return {
        "section_index": section_idx,
        "section_number": section_num,
        "section_title": section.get("title", f"Section {section_num}"),
        "page_start": section.get("page_start"),
        "page_end": section.get("page_end"),
        **normalized,
    }


def render_agent_index_markdown(agent_data: Dict[str, Any]) -> str:
    pdf_title = agent_data.get("pdf_filename", "document")
    sections = agent_data.get("sections") or agent_data.get("subdivisions") or []

    lines = [
        f"# Agent Index — {pdf_title}",
        "",
        f"- Generated: {agent_data.get('created_at', datetime.now().isoformat())}",
        f"- Sections: {agent_data.get('completed_sections', 0)}/{agent_data.get('total_sections', 0)}",
        "",
        "## Page routing",
        "",
    ]

    for item in sections:
        if not item:
            continue
        num = item.get("section_number")
        title = item.get("section_title", "")
        ps, pe = item.get("page_start"), item.get("page_end")
        page = f"p.{ps}" if ps == pe else f"p.{ps}-{pe}"
        lines.append(f"- {page} | {num}. {title} | {item.get('one_liner', '')}")

    lines.append("")

    for item in sections:
        if not item:
            continue
        num = item.get("section_number")
        title = item.get("section_title", "")
        ps, pe = item.get("page_start"), item.get("page_end")
        lines.extend(
            [
                f"## {num}. {title} (p.{ps}-{pe})",
                "",
                f"**ONE_LINER**: {item.get('one_liner', '')}",
                "",
                "**CORE_SCHEMA**:",
            ]
        )
        for key in CORE_SCHEMA_KEYS:
            lines.append(f"- {key}: {item.get('core_schema', {}).get(key, 'UNKNOWN')}")
        lines.append("")
        lines.append(f"**KEYWORDS**: {', '.join(item.get('keywords') or [])}")
        lines.append("")
        lines.append("**EXAM_HOOKS**:")
        for hook in item.get("exam_hooks") or []:
            lines.append(f"- {hook}")
        subs = item.get("subdivisions") or []
        if subs:
            lines.append("")
            lines.append("**Subdivisions**:")
            for sub in subs:
                sp = sub.get("page_start")
                ep = sub.get("page_end")
                lines.append(
                    f"- {sub.get('subdivision_number')}. {sub.get('title')} (p.{sp}-{ep}): {sub.get('one_liner', '')}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
