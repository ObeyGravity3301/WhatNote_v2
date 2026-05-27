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
    "重要",
    "经典",
    "关键",
    "主要",
    "基本",
    "概述",
    "简介",
    "内容",
    "章节",
}

MAX_ONE_LINER_CHARS = 400
MAX_SUB_ONE_LINER_CHARS = 220
MAX_KEYWORDS = 10
MIN_EXAM_HOOKS = 2
MAX_EXAM_HOOKS = 4


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

1. **one_liner**: 1-2 sentences in English. What this section covers + what problem it solves or what conclusion it reaches. Use English syntax but keep original terms/abbreviations (e.g. "ACC synthase (ACS, 1-aminocyclopropane-1-carboxylate synthase)").

2. **core_schema**: object with EXACTLY these 6 keys; each value is ONE short phrase (not a paragraph). Use "UNKNOWN" if missing:
   - "Entities/Objects"
   - "Process/Method"
   - "Key Relation"
   - "Evidence/Example"
   - "Output/Result"
   - "Assumptions/Conditions"

3. **keywords**: array of <=10 strings. Real terms/symbols/formulas/names/algorithms only. NO adjectives like important/classic/significant.

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


def _normalize_core_schema(raw: Any) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if isinstance(raw, dict):
        for key in CORE_SCHEMA_KEYS:
            val = str(raw.get(key, raw.get(key.replace("/", " "), "UNKNOWN"))).strip()
            result[key] = val or "UNKNOWN"
        return result

    if isinstance(raw, list):
        for i, key in enumerate(CORE_SCHEMA_KEYS):
            if i < len(raw):
                if isinstance(raw[i], dict):
                    val = raw[i].get("value") or raw[i].get(key) or "UNKNOWN"
                else:
                    val = str(raw[i])
                result[key] = str(val).strip() or "UNKNOWN"
            else:
                result[key] = "UNKNOWN"
        return result

    for key in CORE_SCHEMA_KEYS:
        result[key] = "UNKNOWN"
    return result


def _normalize_keywords(raw: Any) -> List[str]:
    if isinstance(raw, str):
        items = [k.strip() for k in re.split(r"[,，;；\n]", raw) if k.strip()]
    elif isinstance(raw, list):
        items = [str(k).strip() for k in raw if str(k).strip()]
    else:
        items = []

    cleaned: List[str] = []
    for item in items:
        low = item.lower()
        if low in BANNED_KEYWORDS:
            continue
        if len(item) > 80:
            item = item[:80]
        if item not in cleaned:
            cleaned.append(item)
        if len(cleaned) >= MAX_KEYWORDS:
            break
    return cleaned


def _normalize_exam_hooks(raw: Any) -> List[str]:
    if isinstance(raw, str):
        hooks = [h.strip() for h in re.split(r"\n+", raw) if h.strip()]
    elif isinstance(raw, list):
        hooks = [str(h).strip() for h in raw if str(h).strip()]
    else:
        hooks = []

    hooks = hooks[:MAX_EXAM_HOOKS]
    if len(hooks) < MIN_EXAM_HOOKS:
        return hooks
    return hooks


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
    if not isinstance(data, dict):
        return False, "根对象必须是 JSON object", None

    one_liner = str(data.get("one_liner", "")).strip()
    if not one_liner:
        return False, "one_liner 不能为空", None
    if len(one_liner) > MAX_ONE_LINER_CHARS:
        return False, f"one_liner 超过 {MAX_ONE_LINER_CHARS} 字符", None

    core_schema = _normalize_core_schema(data.get("core_schema"))
    for key in CORE_SCHEMA_KEYS:
        if key not in core_schema:
            return False, f"core_schema 缺少键 {key}", None
        if len(core_schema[key]) > 200:
            core_schema[key] = core_schema[key][:200]

    keywords = _normalize_keywords(data.get("keywords"))
    if len(keywords) < 1:
        return False, "keywords 至少需要 1 个有效术语", None

    exam_hooks = _normalize_exam_hooks(data.get("exam_hooks"))
    if len(exam_hooks) < MIN_EXAM_HOOKS:
        return False, f"exam_hooks 需要 {MIN_EXAM_HOOKS}-{MAX_EXAM_HOOKS} 条", None

    subdivisions = _normalize_subdivisions(data.get("subdivisions"), page_start, page_end)

    normalized = {
        "one_liner": one_liner,
        "core_schema": core_schema,
        "keywords": keywords,
        "exam_hooks": exam_hooks,
        "subdivisions": subdivisions,
    }
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
