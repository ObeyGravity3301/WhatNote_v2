"""通义千问 OpenAI 兼容 Chat Completions 常用模型（中国大陆百炼）。"""

from typing import List, Dict

# 纯文本讲稿 / 大纲 / 索引推荐
QWEN_TEXT_MODEL_OPTIONS: List[Dict[str, str]] = [
    {"value": "qwen3.7-max", "label": "Qwen3.7-Max（旗舰，质量最高）"},
    {"value": "qwen3.6-plus", "label": "Qwen3.6-Plus"},
    {"value": "qwen3.5-plus", "label": "Qwen3.5-Plus（推荐）"},
    {"value": "qwen3.5-flash", "label": "Qwen3.5-Flash（快）"},
    {"value": "qwen-plus", "label": "Qwen-Plus（稳定）"},
    {"value": "qwen-flash", "label": "Qwen-Flash"},
    {"value": "qwen-turbo", "label": "Qwen-Turbo（更快）"},
    {"value": "qwen-long", "label": "Qwen-Long（长文本/多页讲稿）"},
]

# 多模态（看图、VL）
QWEN_VL_MODEL_OPTIONS: List[Dict[str, str]] = [
    {"value": "qwen3-vl-plus", "label": "Qwen3-VL-Plus"},
    {"value": "qwen3-vl-flash", "label": "Qwen3-VL-Flash"},
    {"value": "qwen-vl-plus", "label": "Qwen-VL-Plus"},
    {"value": "qwen-vl-max", "label": "Qwen-VL-Max"},
]

DEFAULT_NARRATOR_SCRIPT_MODEL = "qwen-long"
