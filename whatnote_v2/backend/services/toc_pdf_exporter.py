"""根据大纲与细分数据生成 PDF 目录"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz


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
