"""根据大纲、细分与讲稿数据生成导出内容"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
import re


CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto/NotoSansSC-Regular.otf",
    "/usr/share/fonts/wenquanyi/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _find_cjk_font() -> fitz.Font:
    for path in CJK_FONT_CANDIDATES:
        if Path(path).exists():
            return fitz.Font(fontfile=path)
    raise FileNotFoundError("未找到可用的中文字体，请安装 noto-fonts-cjk")


def _section_title(section: Dict[str, Any], index: int) -> str:
    return (
        section.get("title")
        or section.get("section_title")
        or f"章节 {index + 1}"
    )


def _page_range_label(start: Optional[int], end: Optional[int]) -> str:
    if start is None and end is None:
        return ""
    if start is None:
        start = end
    if end is None:
        end = start
    if start == end:
        return f"第 {start} 页"
    return f"第 {start}-{end} 页"


def _page_range_markdown(start: Optional[int], end: Optional[int]) -> str:
    if start is None and end is None:
        return ""
    if start is None:
        start = end
    if end is None:
        end = start
    if start == end:
        return f"第 {start} 页"
    return f"第 {start}-{end} 页"


def _wrap_text(text: str, max_chars: int = 42) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    lines: List[str] = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= max_chars:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


class _PdfWriter:
    """使用 TextWriter + 嵌入 CJK 字体，确保中文正常显示"""

    def __init__(self, font: fitz.Font):
        self.font = font
        self.doc = fitz.open()
        self.page_width = 595
        self.page_height = 842
        self.margin_x = 56
        self.margin_top = 56
        self.margin_bottom = 56
        self.y = self.margin_top
        self.page = self.doc.new_page(width=self.page_width, height=self.page_height)
        self._writer = fitz.TextWriter(self.page.rect)

    def _flush_page(self):
        if self._writer:
            self._writer.write_text(self.page)
            self._writer = None

    def _new_page_if_needed(self, needed: float = 24):
        if self.y + needed > self.page_height - self.margin_bottom:
            self._flush_page()
            self.page = self.doc.new_page(width=self.page_width, height=self.page_height)
            self.y = self.margin_top
            self._writer = fitz.TextWriter(self.page.rect)

    def write_line(self, text: str, fontsize: float = 11, indent: float = 0):
        if not text:
            return
        self._new_page_if_needed(fontsize + 8)
        self._writer.append(
            (self.margin_x + indent, self.y),
            text,
            font=self.font,
            fontsize=fontsize,
        )
        self.y += fontsize + 6

    def write_paragraph(self, text: str, fontsize: float = 10, indent: float = 18):
        for line in _wrap_text(text, max_chars=44):
            self.write_line(line, fontsize=fontsize, indent=indent)

    def save_bytes(self) -> bytes:
        self._flush_page()
        buffer = BytesIO()
        self.doc.save(buffer)
        self.doc.close()
        return buffer.getvalue()


def build_toc_pdf(
    outline_data: Dict[str, Any],
    subdivision_data: Dict[str, Any],
    pdf_title: str,
) -> bytes:
    font = _find_cjk_font()
    writer = _PdfWriter(font)

    outline = outline_data.get("outline") or []
    subdivisions = (subdivision_data or {}).get("subdivisions") or []

    writer.write_line("文档目录", fontsize=20)
    writer.write_line(f"来源文档：{pdf_title}", fontsize=11)
    writer.write_line(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=10)
    writer.y += 8
    writer.write_line("—" * 32, fontsize=10)
    writer.y += 6

    for index, section in enumerate(outline):
        section_num = section.get("section_number") or (index + 1)
        title = _section_title(section, index)
        page_label = _page_range_label(section.get("page_start"), section.get("page_end"))
        writer.write_line(f"{section_num}. {title}  ({page_label})", fontsize=13)

        description = (section.get("description") or "").strip()
        if description:
            writer.write_paragraph(f"简介：{description}", fontsize=10, indent=16)

        sub_data = subdivisions[index] if index < len(subdivisions) else None
        if sub_data:
            section_summary = (sub_data.get("section_summary") or sub_data.get("summary") or "").strip()
            if section_summary:
                writer.write_paragraph(f"分段摘要：{section_summary}", fontsize=10, indent=16)

            for sub_index, sub in enumerate(sub_data.get("subdivisions") or [], start=1):
                sub_title = sub.get("title") or f"子分段 {sub_index}"
                sub_pages = _page_range_label(sub.get("page_start"), sub.get("page_end"))
                writer.write_line(
                    f"  {section_num}.{sub_index} {sub_title}  ({sub_pages})",
                    fontsize=11,
                    indent=12,
                )

        writer.y += 6

    return writer.save_bytes()


def build_toc_markdown(
    outline_data: Dict[str, Any],
    subdivision_data: Dict[str, Any],
    pdf_title: str,
) -> str:
    outline = outline_data.get("outline") or []
    subdivisions = (subdivision_data or {}).get("subdivisions") or []

    lines: List[str] = [
        "# 文档目录",
        "",
        f"- 来源文档：{pdf_title}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for index, section in enumerate(outline):
        section_num = section.get("section_number") or (index + 1)
        title = _section_title(section, index)
        page_label = _page_range_markdown(section.get("page_start"), section.get("page_end"))

        lines.extend(
            [
                f"## {section_num}. {title}",
                "",
                f"- 页码：{page_label}",
            ]
        )

        description = (section.get("description") or "").strip()
        if description:
            lines.append(f"- 简介：{description}")

        sub_data = subdivisions[index] if index < len(subdivisions) else None
        if sub_data:
            section_summary = (sub_data.get("section_summary") or sub_data.get("summary") or "").strip()
            if section_summary:
                lines.extend(["", "### 分段摘要", "", section_summary])

            sub_items = sub_data.get("subdivisions") or []
            if sub_items:
                lines.extend(["", "### 子分段", ""])
                for sub_index, sub in enumerate(sub_items, start=1):
                    sub_title = sub.get("title") or f"子分段 {sub_index}"
                    sub_pages = _page_range_markdown(sub.get("page_start"), sub.get("page_end"))
                    lines.append(f"- {section_num}.{sub_index} {sub_title}（{sub_pages}）")

        lines.extend(["", "---", ""])

    return "\n".join(lines).rstrip() + "\n"


def build_toc_agent_markdown(
    outline_data: Dict[str, Any],
    subdivision_data: Dict[str, Any],
    pdf_title: str,
) -> str:
    """生成供 Agent 阅读的精简目录：无简介、无冗余标题，保留页码与分段摘要/子分段。"""
    outline = outline_data.get("outline") or []
    subdivisions = (subdivision_data or {}).get("subdivisions") or []

    lines: List[str] = [
        f"# {pdf_title} — 文档索引",
        "",
        "> 供 Agent 使用：按章节与页码定位原文；每节含分段摘要与子分段页码，不含逐页讲稿。",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # 页码速览表（一节一行，便于大文档快速检索）
    if outline:
        lines.extend(["## 页码速览", ""])
        for index, section in enumerate(outline):
            section_num = section.get("section_number") or (index + 1)
            title = _section_title(section, index)
            page_label = _page_range_markdown(section.get("page_start"), section.get("page_end"))
            lines.append(f"- {page_label}：{section_num}. {title}")
        lines.append("")

    for index, section in enumerate(outline):
        section_num = section.get("section_number") or (index + 1)
        title = _section_title(section, index)
        page_label = _page_range_markdown(section.get("page_start"), section.get("page_end"))

        lines.append(f"## {section_num}. {title}（{page_label}）")

        sub_data = subdivisions[index] if index < len(subdivisions) else None
        section_summary = ""
        if sub_data:
            section_summary = (
                sub_data.get("section_summary") or sub_data.get("summary") or ""
            ).strip()
        if not section_summary:
            section_summary = (section.get("description") or "").strip()

        if section_summary:
            lines.append(f"摘要：{section_summary}")

        sub_items = (sub_data or {}).get("subdivisions") or []
        for sub_index, sub in enumerate(sub_items, start=1):
            sub_title = sub.get("title") or f"子分段 {sub_index}"
            sub_pages = _page_range_markdown(sub.get("page_start"), sub.get("page_end"))
            lines.append(f"- {section_num}.{sub_index} {sub_title}（{sub_pages}）")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"\[(.*?)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    return text


def build_script_markdown(
    page_annotations: List[Dict[str, Any]],
    pdf_title: str,
) -> str:
    lines: List[str] = [
        "# 文档讲稿",
        "",
        f"- 来源文档：{pdf_title}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for item in page_annotations:
        page_num = item.get("page")
        content = (item.get("content") or "").strip() or "*暂无讲稿内容*"
        lines.extend(
            [
                f"## 第 {page_num} 页",
                "",
                content,
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def build_script_pdf(
    page_annotations: List[Dict[str, Any]],
    pdf_title: str,
) -> bytes:
    font = _find_cjk_font()
    writer = _PdfWriter(font)

    writer.write_line("文档讲稿", fontsize=20)
    writer.write_line(f"来源文档：{pdf_title}", fontsize=11)
    writer.write_line(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fontsize=10)
    writer.y += 8
    writer.write_line("—" * 32, fontsize=10)
    writer.y += 6

    for item in page_annotations:
        page_num = item.get("page")
        content = (item.get("content") or "").strip() or "*暂无讲稿内容*"

        writer.write_line(f"第 {page_num} 页", fontsize=14)
        writer.y += 2

        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                writer.y += 4
                continue
            if stripped.startswith("<!--") and stripped.endswith("-->"):
                continue

            clean = _strip_inline_markdown(stripped)
            if stripped.startswith("### "):
                writer.write_line(clean[4:].strip(), fontsize=11, indent=18)
            elif stripped.startswith("## "):
                writer.write_line(clean[3:].strip(), fontsize=12, indent=14)
            elif stripped.startswith("# "):
                writer.write_line(clean[2:].strip(), fontsize=13, indent=10)
            elif stripped.startswith("- ") or stripped.startswith("* "):
                writer.write_paragraph(f"• {clean[2:].strip()}", fontsize=10, indent=22)
            else:
                writer.write_paragraph(clean, fontsize=10, indent=18)

        writer.y += 8
        writer.write_line("—" * 24, fontsize=9)
        writer.y += 6

    return writer.save_bytes()
