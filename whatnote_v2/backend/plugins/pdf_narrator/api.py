from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Dict, Optional
import aiohttp
import json
import shutil
import uuid
import os
import wave
import io
import re
import subprocess
from pathlib import Path
from datetime import datetime
from logger import info, error
from config import DATA_DIR
from constants.qwen_models import DEFAULT_NARRATOR_SCRIPT_MODEL, QWEN_TEXT_MODEL_OPTIONS
from .schemas import TTSRequest


def _narrator_script_model() -> str:
    if llm_service and getattr(llm_service, "api_config_manager", None):
        return (
            llm_service.api_config_manager.get_task_model("narrator_script")
            or DEFAULT_NARRATOR_SCRIPT_MODEL
        )
    return DEFAULT_NARRATOR_SCRIPT_MODEL

def _repair_json(s: str) -> str:
    """尝试修复常见的 LLM 生成的 JSON 错误"""
    import re
    # 0. 检查是否存在嵌入的错误消息 (通常由 llm_service 异常产生)
    if "[Error]" in s:
        # 记录错误并截断污染部分
        s = s.split("[Error]")[0]
        
    # 1. 移除可能的前后非 JSON 字符
    s = s.strip()
    # 移除 Markdown 代码块标记
    s = re.sub(r'^```json\s*', '', s)
    s = re.sub(r'^```\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    s = s.strip()
    
    if not s:
        return s

    # 2. 修复字符串内的非法换行符 (JSON 字符串内不能直接换行)
    try:
        def replace_newlines(match):
            content = match.group(1)
            return f'"{content.replace("\n", "\\n").replace("\r", "")}"'
        s = re.sub(r'"((?:[^"\\]|\\.)*)"', replace_newlines, s, flags=re.DOTALL)
    except Exception as e:
        error(f"JSON修复-换行符处理失败: {e}")
    
    # 3. 修复缺失的逗号
    s = re.sub(r'([0-9]|"|}|\])\s*\n?\s*"(?!\s*:)', r'\1, "', s)
    
    # 4. 处理多余的逗号
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r',\s*]', ']', s)
    
    # 5. 处理没有引号的 Key
    s = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', s)
    
    # 6. 处理截断的 JSON (尝试自动闭合)
    open_braces = s.count('{') - s.count('}')
    open_brackets = s.count('[') - s.count(']')
    
    if open_braces > 0 or open_brackets > 0:
        s = s.rstrip().rstrip(',')
        if s.count('"') % 2 != 0:
            s += '"'
        stack = []
        for char in s:
            if char == '{': stack.append('}')
            elif char == '[': stack.append(']')
            elif char == '}': 
                if stack and stack[-1] == '}': stack.pop()
            elif char == ']':
                if stack and stack[-1] == ']': stack.pop()
        while stack:
            s += stack.pop()
            
    return s

router = APIRouter()

# Global dependencies to be injected
content_manager = None
llm_service = None
tts_service = None
conversation_manager = None
GPT_SOVITS_URL = "http://127.0.0.1:9880"

GPT_MODEL_DIR_NAMES = [
    "GPT_weights",
    "GPT_weights_v2",
    "GPT_weights_v2Pro",
    "GPT_weights_v2ProPlus",
    "GPT_weights_v3",
    "GPT_weights_v4",
]

SOVITS_MODEL_DIR_NAMES = [
    "SoVITS_weights",
    "SoVITS_weights_v2",
    "SoVITS_weights_v2Pro",
    "SoVITS_weights_v2ProPlus",
    "SoVITS_weights_v3",
    "SoVITS_weights_v4",
]

# Plugin State
_enabled = True

def check_enabled():
    if not _enabled:
        raise HTTPException(status_code=533, detail="Plugin is disabled")


def _has_any_model_dir(base_dir: Path) -> bool:
    return any((base_dir / dirname).exists() for dirname in [*GPT_MODEL_DIR_NAMES, *SOVITS_MODEL_DIR_NAMES])


def _locate_gpt_sovits_dir() -> Optional[Path]:
    cwd = Path.cwd().resolve()
    candidate_dir = cwd

    for _ in range(4):
        check_path = candidate_dir / "GPT-SoVITS"
        if check_path.exists() and _has_any_model_dir(check_path):
            return check_path

        sibling_path = candidate_dir.parent / "GPT-SoVITS"
        if sibling_path.exists() and _has_any_model_dir(sibling_path):
            return sibling_path

        candidate_dir = candidate_dir.parent

    hardcoded = Path("/home/obeygravity/Projects/GPT-SoVITS")
    if hardcoded.exists() and _has_any_model_dir(hardcoded):
        return hardcoded

    return None


def _collect_model_files(base_dir: Path, dir_names: List[str], pattern: str) -> List[str]:
    collected = []
    seen = set()
    for dirname in dir_names:
        model_dir = base_dir / dirname
        if not model_dir.exists():
            continue
        for file_path in sorted(model_dir.glob(pattern)):
            if file_path.name in seen:
                continue
            collected.append(file_path.name)
            seen.add(file_path.name)
    return collected


def _resolve_model_path(base_dir: Path, filename: str, dir_names: List[str]) -> Optional[Path]:
    for dirname in dir_names:
        model_path = base_dir / dirname / filename
        if model_path.exists():
            return model_path
    return None

@router.post("/narrator/control")
async def control_narrator(request: Request):
    """Start or stop the narrator plugin (enable/disable APIs)."""
    global _enabled
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "start":
            _enabled = True
            info("[PdfNarrator] Plugin enabled via API.")
            return {"status": "success", "message": "Narrator plugin enabled"}
        elif action == "stop":
            _enabled = False
            info("[PdfNarrator] Plugin disabled via API.")
            return {"status": "success", "message": "Narrator plugin disabled"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- TTS API Routes ---

@router.post("/tts/generate")
async def generate_tts(request: TTSRequest):
    """通用 TTS 生成接口，支持多后端"""
    check_enabled()
    try:
        info(f"收到 TTS 请求: {request.text[:50]}...")
        result = await tts_service.generate(request.text, request.voice)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "TTS Failed"))
        return result
    except Exception as e:
        error(f"TTS 生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/voices")
async def list_tts_voices(provider: str = "edge"):
    """获取可用音色列表"""
    check_enabled()
    try:
        voices = await tts_service.list_voices(provider)
        return {"success": True, "voices": voices}
    except Exception as e:
        error(f"获取音色列表失败: {e}")
        return {"success": False, "error": str(e)}

@router.get("/tts/config")
async def get_tts_current_config():
    """获取当前 TTS 配置"""
    check_enabled()
    return tts_service.get_tts_config()

@router.get("/tts/test_connection")
async def test_tts_connection(url: Optional[str] = None):
    """测试 TTS 连接状态"""
    check_enabled()
    return await tts_service.test_sovits_connection(url)

@router.post("/tts/detect_local")
async def detect_local_tts(request: Request):
    """检测本地路径是否包含 GPT-SoVITS"""
    check_enabled()
    data = await request.json()
    path = data.get("path")
    return tts_service.check_local_sovits(path)

@router.post("/tts/start_local")
async def start_local_tts():
    """手动启动本地 GPT-SoVITS 服务"""
    check_enabled()
    return await tts_service.start_local_sovits()

@router.put("/tts/config")
async def update_tts_config(request: Request):
    """更新 TTS 配置"""
    check_enabled()
    try:
        new_config = await request.json()
        full_config = tts_service.api_config_manager.get_config()
        
        # 确保 tts 字典存在
        if "tts" not in full_config:
            full_config["tts"] = {}
            
        full_config["tts"].update(new_config)
        full_config["updated_at"] = datetime.now().isoformat()
        
        # 保存到文件
        config_path = tts_service.api_config_manager.config_file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(full_config, f, ensure_ascii=False, indent=2)
            
        return {"success": True}
    except Exception as e:
        error(f"更新 TTS 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/reference")
async def get_tts_reference():
    """获取当前默认参考音频信息"""
    check_enabled()
    try:
        ref_dir = DATA_DIR / "ref_audio"
        meta_path = ref_dir / "default.json"
        wav_path = ref_dir / "default.wav"
        
        if not meta_path.exists() or not wav_path.exists():
            return {"exists": False}
            
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            
        return {
            "exists": True,
            "text": meta.get("text", ""),
            "language": meta.get("language", "zh"),
            "filename": meta.get("filename", "default.wav")
        }
    except Exception as e:
        error(f"获取参考音频信息失败: {e}")
        return {"exists": False, "error": str(e)}


@router.post("/tts/reference")
async def upload_tts_reference(
    file: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form("zh")
):
    """上传默认参考音频"""
    check_enabled()
    try:
        ref_dir = DATA_DIR / "ref_audio"
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = ref_dir / "default.wav"
        meta_path = ref_dir / "default.json"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        meta_data = {
            "text": text, 
            "language": language,
            "filename": file.filename
        }
        # 如果传入的text是空的，尝试保留旧的text
        if not text and meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    old_meta = json.load(f)
                    if old_meta.get('text'):
                        meta_data['text'] = old_meta['text']
            except:
                pass

        with open(meta_path, "w") as f:
            json.dump(meta_data, f)
            
        return {"success": True, "message": "参考音频已更新", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.put("/tts/reference")
async def update_tts_reference_meta(request: Request):
    """更新参考音频的元数据（文本、语言）而不上传新文件"""
    check_enabled()
    try:
        data = await request.json()
        text = data.get("text")
        language = data.get("language")
        
        ref_dir = DATA_DIR / "ref_audio"
        meta_path = ref_dir / "default.json"
        
        if not meta_path.exists():
             # If no meta file, but maybe directory exists?
             # If completely new, we can't update meta without file.
             # But let's allow creating meta if it's missing but user wants to set it 
             # (though without audio it's useless).
             raise HTTPException(status_code=404, detail="参考音频配置不存在，请先上传音频")
            
        with open(meta_path, 'r') as f:
            meta_data = json.load(f)
            
        if text is not None:
            meta_data["text"] = text
        if language is not None:
            meta_data["language"] = language
            
        with open(meta_path, "w") as f:
            json.dump(meta_data, f)
            
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tts/reference/audio")
async def get_tts_reference_audio():
    """获取参考音频文件进行试听"""
    check_enabled()
    try:
        ref_dir = DATA_DIR / "ref_audio"
        wav_path = ref_dir / "default.wav"
        if wav_path.exists():
            return FileResponse(wav_path, media_type="audio/wav", headers={"Cache-Control": "no-cache"})
        raise HTTPException(status_code=404, detail="No reference audio found")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tts/status")
async def get_tts_status():
    """检查TTS服务状态"""
    # 状态检查即使禁用也允许，或者禁用时返回 disabled
    if not _enabled:
        return {"status": "disabled", "error": "Plugin is disabled"}
        
    try:
        async with aiohttp.ClientSession() as session:
            # 尝试调用 control 接口或直接 ping
            async with session.get(f"{GPT_SOVITS_URL}/control") as response:
                return {"status": "online", "version": "v2"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


@router.get("/narrator/llm-model")
async def get_narrator_llm_model():
    """讲稿生成使用的通义千问模型（与聊天全局模型独立）"""
    check_enabled()
    model = _narrator_script_model()
    return {
        "model": model,
        "default": DEFAULT_NARRATOR_SCRIPT_MODEL,
        "options": QWEN_TEXT_MODEL_OPTIONS,
        "current_provider": (
            llm_service.api_config_manager.get_current_provider()
            if llm_service and getattr(llm_service, "api_config_manager", None)
            else "qwen"
        ),
        "fallback_global_model": (
            (llm_service.api_config_manager.get_current_config() or {}).get("model")
            if llm_service and getattr(llm_service, "api_config_manager", None)
            else None
        ),
    }


@router.post("/narrator/llm-model")
async def set_narrator_llm_model(request: Request):
    """设置讲稿生成专用模型"""
    check_enabled()
    data = await request.json()
    model = (data.get("model") or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="model 不能为空")
    allowed = {o["value"] for o in QWEN_TEXT_MODEL_OPTIONS}
    if model not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模型: {model}。请在 options 列表中选择。",
        )
    if not llm_service or not getattr(llm_service, "api_config_manager", None):
        raise HTTPException(status_code=500, detail="LLM 服务未初始化")
    ok = llm_service.api_config_manager.set_task_model("narrator_script", model)
    if not ok:
        raise HTTPException(status_code=500, detail="保存失败")
    info(f"[PdfNarrator] 讲稿模型已设为: {model}")
    return {"success": True, "model": model}


@router.get("/tts/models")
async def get_tts_models():
    """获取可用的GPT和SoVITS模型列表"""
    check_enabled()
    try:
        cwd = Path.cwd().resolve()
        info(f"当前工作目录: {cwd}")

        base_dir = _locate_gpt_sovits_dir()
        if not base_dir:
            return {"gpt_weights": [], "sovits_weights": [], "error": f"未找到 GPT-SoVITS 目录 (cwd: {cwd})"}

        info(f"定位到 GPT-SoVITS 目录: {base_dir}")

        gpt_weights = _collect_model_files(base_dir, GPT_MODEL_DIR_NAMES, "*.ckpt")
        sovits_weights = _collect_model_files(base_dir, SOVITS_MODEL_DIR_NAMES, "*.pth")

        return {
            "gpt_weights": sorted(gpt_weights),
            "sovits_weights": sorted(sovits_weights)
        }
    except Exception as e:
        error(f"获取模型列表失败: {e}")
        return {"gpt_weights": [], "sovits_weights": [], "error": str(e)}


@router.post("/tts/set_model")
async def set_tts_model(request: Request):
    """切换GPT-SoVITS模型"""
    check_enabled()
    try:
        data = await request.json()
        gpt_name = data.get("gpt_model")
        sovits_name = data.get("sovits_model")

        base_dir = _locate_gpt_sovits_dir()
        if not base_dir:
            raise HTTPException(status_code=500, detail="未找到 GPT-SoVITS 目录")

        payload = {}
        if gpt_name:
            gpt_model_path = _resolve_model_path(base_dir, gpt_name, GPT_MODEL_DIR_NAMES)
            if not gpt_model_path:
                raise HTTPException(status_code=404, detail=f"未找到 GPT 模型: {gpt_name}")
            payload["gpt_model_path"] = str(gpt_model_path)
        if sovits_name:
            sovits_model_path = _resolve_model_path(base_dir, sovits_name, SOVITS_MODEL_DIR_NAMES)
            if not sovits_model_path:
                raise HTTPException(status_code=404, detail=f"未找到 SoVITS 模型: {sovits_name}")
            payload["sovits_model_path"] = str(sovits_model_path)
            
        info(f"切换模型: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{GPT_SOVITS_URL}/set_model", json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"切换失败: {text}")
                return await resp.json()
                
    except Exception as e:
        error(f"切换模型出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Narrator API Routes ---

@router.post("/boards/{board_id}/windows/{window_id}/annotations/batch/generate-script-section")
async def generate_narrator_script_section(
    board_id: str,
    window_id: str,
    request: Request
):
    """批量生成讲稿"""
    check_enabled()
    try:
        request_body = await request.json()
        section_index = request_body.get('section_index', 0)
        section_data = request_body.get('section_data')
        subdivision_data = request_body.get('subdivision_data')
        previous_subdivision = request_body.get('previous_subdivision')
        prompt_template = request_body.get('promptTemplate', '')
        
        info(f"开始为分段 {section_index} 批量生成讲稿")
        
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        page_start = section_data['page_start']
        page_end = section_data['page_end']
        
        target_range = request_body.get('target_range', {})
        target_start = target_range.get('start', page_start)
        target_end = target_range.get('end', page_end)
        
        async def generate_stream():
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在为第 {target_start}-{target_end} 页生成讲稿...'}, ensure_ascii=False)}\n\n"
                
                pages_content = []
                for page in range(page_start, page_end + 1):
                    page_data = content_manager.get_pdf_page_contents(board_id, window_id, page)
                    if page_data and page_data.get('current'):
                        pages_content.append({
                            'page': page,
                            'content': page_data['current']
                        })
                
                if not pages_content:
                    error_msg = f'未找到分段内容，页码范围: {page_start}-{page_end}'
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                    return
                
                full_content = ""
                for page_info in pages_content:
                    full_content += f"\n\n=== 第{page_info['page']}页 ===\n{page_info['content']}"
                
                section_description = ''
                if subdivision_data:
                     section_description = subdivision_data.get('section_summary') or section_data.get('description') or ''

                previous_context_text = ""
                if previous_subdivision:
                    prev_summary = previous_subdivision.get('section_summary', '')
                    prev_title = previous_subdivision.get('title', '')
                    if prev_summary:
                        previous_context_text = f"\n**前情提要（上一分段上下文）**：\n- 上一分段标题: {prev_title}\n- 上一分段主要内容: {prev_summary}\n- 提示：请承接上述内容，保持演讲的连贯性，避免生硬的开场。"

                default_req = """请作为一名专业的老师，根据页面内容撰写自然、口语化的讲稿。
要求：
1. 内容驱动长度：讲稿的长度应直接取决于该页的信息量。简单页面（如标题页、转场页）请言简意赅；复杂页面（如包含核心概念、复杂图表、多项实验数据）请深入浅出地详细讲解。
2. 解析深度一致：保持统一的教学风格。对于知识点，不仅要说出“是什么”，还要解释“为什么”或“意味着什么”，确保整份讲稿的解析深度在不同页面间维持一致。
3. 自然叙事：使用口语化的第一人称。避免生硬的“第一点、第二点”这种阅读式表达，而是使用“我们再来看看...”、“这里有一个细节值得注意...”等衔接词。
4. 严禁念稿：不要直接朗读页面上的原始文字，而是将其转化为你自己的讲解语言。
5. 独立且连贯：每页讲稿需对应其页面内容，但语气上要与前后文保持连贯，像是在进行一场不间断的精彩讲座。"""
                script_requirement = prompt_template if prompt_template else default_req
                
                prompt = f"""你是一位富有经验且充满激情的专业老师。请根据以下PDF分段内容（包含上下文），为指定范围的每一页页面撰写一份**讲解风格一致**的讲稿。

**分段上下文信息**：
- 分段标题: {section_data.get('title', '未命名')}
- 分段描述: {section_description}
- 完整上下文页码: 第{page_start}页 - 第{page_end}页
{previous_context_text}

**分段内容详情**：
{full_content}

**任务目标**：
请仅为 **第{target_start}页 到 第{target_end}页** 分别生成讲稿。
注意：请根据每页实际包含的信息密度来决定讲稿的长短。不要为了凑字数而废话，也不要因为内容多而漏掉核心逻辑。

**讲稿要求**：
{script_requirement}

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "scripts": [
    {{
      "page": {target_start},
      "script": "这里是根据该页内容生成的自然讲解内容..."
    }}
  ]
}}
```
请确保 scripts 数组包含从 **{target_start}** 到 **{target_end}** 的每一页。直接输出 JSON。"""
                
                messages = [{
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                }]
                
                accumulated_content = ""
                
                script_model = _narrator_script_model()
                info(f"[PdfNarrator] 批量讲稿 LLM 模型: {script_model}")
                async for chunk in llm_service.chat_completion(
                    messages, stream=True, override_model=script_model
                ):
                    if chunk:
                        if chunk.startswith('[Error]'):
                            yield f"data: {json.dumps({'type': 'error', 'error': chunk}, ensure_ascii=False)}\n\n"
                            return
                        accumulated_content += chunk
                
                try:
                    content = accumulated_content.strip()
                    if content.startswith('```'):
                        lines = content.split('\n')
                        # 改进：更健壮地提取JSON内容
                        start_idx = 0
                        for i, line in enumerate(lines):
                            if '{' in line:
                                start_idx = i
                                break
                        end_idx = len(lines)
                        for i in range(len(lines) - 1, -1, -1):
                            if '}' in lines[i]:
                                end_idx = i + 1
                                break
                        content = '\n'.join(lines[start_idx:end_idx])
                    
                    try:
                        result_data = json.loads(content)
                    except json.JSONDecodeError:
                        # 备选方案1：尝试修复并再次解析
                        try:
                            repaired_content = _repair_json(content)
                            result_data = json.loads(repaired_content)
                        except json.JSONDecodeError:
                            # 备选方案2：尝试正则表达式提取 JSON 并修复
                            import re
                            json_match = re.search(r'\{.*\}', content, re.DOTALL)
                            if json_match:
                                try:
                                    result_data = json.loads(_repair_json(json_match.group()))
                                except:
                                    error(f"修复后的正则解析仍然失败: {content[:200]}...")
                                    raise
                            else:
                                error(f"无法从内容中找到JSON结构: {content[:200]}...")
                                raise
                            
                    scripts = result_data.get('scripts', [])
                    
                    # 记录统计
                    expected_range = list(range(target_start, target_end + 1))
                    received_pages = [s.get('page') for s in scripts if s.get('page')]
                    missing_pages = [p for p in expected_range if p not in received_pages]
                    
                    info(f"讲稿生成统计 - 预期范围: {target_start}-{target_end} (共{len(expected_range)}页)")
                    info(f"讲稿生成统计 - 收到页面: {received_pages} (共{len(scripts)}页)")
                    if missing_pages:
                        error(f"讲稿生成统计 - 缺失页面: {missing_pages}")
                    else:
                        info("讲稿生成统计 - 所有页面均已收到")
                    
                    processed_count = 0
                    for script_item in scripts:
                        page = script_item.get('page')
                        text = script_item.get('script')
                        if page and text:
                            processed_count += 1
                            yield f"data: {json.dumps({'type': 'page_done', 'page': page, 'content': text}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({
                        'type': 'complete', 
                        'total': processed_count, 
                        'expected_total': len(expected_range),
                        'missing_pages': missing_pages
                    }, ensure_ascii=False)}\n\n"
                    
                except json.JSONDecodeError as e:
                    error_msg = f"解析讲稿JSON失败: {e}\nRaw content preview: {content[:200]}..."
                    error(error_msg)
                    
                    # Log to dedicated file
                    try:
                        log_path = DATA_DIR / "narrator_error.log"
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(f"\n{'='*30}\n[{datetime.now().isoformat()}] JSON Decode Error (Section {section_index}, Target {target_start}-{target_end})\n")
                            f.write(f"Error: {e}\n")
                            f.write(f"Raw Content:\n{accumulated_content}\n")
                            f.write(f"{'='*30}\n")
                    except Exception as log_err:
                        error(f"Failed to write to log file: {log_err}")

                    yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}。详情见 {log_path.name}'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                error(f"批量生成讲稿失败: {e}")
                # Log to dedicated file
                try:
                    log_path = DATA_DIR / "narrator_error.log"
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n{'='*30}\n[{datetime.now().isoformat()}] General Error (Section {section_index})\n")
                        f.write(f"Error: {e}\n")
                        f.write(f"{'='*30}\n")
                except: pass
                
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        error(f"批量生成讲稿接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boards/{board_id}/windows/{window_id}/narrator/scripts/{page}")
async def get_narrator_script(board_id: str, window_id: str, page: int):
    check_enabled()
    try:
        content = content_manager.get_narrator_script(board_id, window_id, page)
        return {"success": True, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/boards/{board_id}/windows/{window_id}/narrator/scripts/{page}")
async def save_narrator_script(board_id: str, window_id: str, page: int, request: Request):
    check_enabled()
    try:
        data = await request.json()
        content = data.get('content', '')
        success = content_manager.save_narrator_script(board_id, window_id, page, content)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/boards/{board_id}/windows/{window_id}/narrator/script-generate/{page}")
async def generate_narrator_script_single(
    board_id: str, 
    window_id: str, 
    page: int, 
    request: Request
):
    """单页讲稿生成（独立接口，不污染注释）"""
    check_enabled()
    try:
        request_body = await request.json()
        custom_prompt = request_body.get('promptTemplate', '')
        previous_script = request_body.get('previous_script', '')
        next_script = request_body.get('next_script', '')
        
        # 获取内容
        page_contents = content_manager.get_pdf_page_contents(board_id, window_id, page)
        if not page_contents.get('current'):
            raise HTTPException(status_code=404, detail="Page content not found")
            
        # 构建 Prompt
        prompt_parts = []
        prompt_parts.append("你是一位专业的演讲者。请根据以下PDF页面内容撰写一份口语化的演讲稿。\n")
        
        # 上一页（参考）
        if page_contents.get('previous'):
            prompt_parts.append(f"【上一页原文内容（第{page-1}页）】\n{page_contents['previous']}\n")
        if previous_script:
            prompt_parts.append(f"【上一页已生成讲稿参考】\n{previous_script}\n")
            
        # 当前页（重点）
        prompt_parts.append(f"【当前页原文内容（第{page}页）】\n{page_contents['current']}\n")
        
        # 下一页（参考）
        if next_script:
            prompt_parts.append(f"【下一页已生成讲稿参考】\n{next_script}\n")
        if page_contents.get('next'):
            prompt_parts.append(f"【下一页原文内容（第{page+1}页）】\n{page_contents['next']}\n")
            
        if page == 1:
            prompt_parts.append("\n注意：这是演示文档的第一页，请直接开始开场白，无需回顾前文。")

        if custom_prompt:
            prompt_parts.append(f"\n{custom_prompt}")
        else:
            prompt_parts.append("\n要求：\n1. 时间控制在 30-60 秒。\n2. 语言自然流畅。\n3. 不要念标题，而是解释核心观点。\n4. 使用第一人称。")
            
        prompt = "\n".join(prompt_parts)
        
        messages = [{
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }]
        
        async def generate_stream():
            accumulated_content = ""
            script_model = _narrator_script_model()
            info(f"[PdfNarrator] 单页讲稿 LLM 模型: {script_model}")
            async for chunk in llm_service.chat_completion(
                messages, stream=True, override_model=script_model
            ):
                if chunk:
                    accumulated_content += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 自动保存到 *讲稿* 文件 (使用 save_narrator_script)
            content_manager.save_narrator_script(board_id, window_id, page, accumulated_content)
            
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as e:
        error(f"生成讲稿失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def get_narrator_audio(
    board_id: str,
    window_id: str,
    page: int
):
    """获取PDF指定页面的语音文件（仅获取，不生成）"""
    check_enabled()
    try:
        existing_audio_path = content_manager.get_narrator_audio_path(board_id, window_id, page)
        if existing_audio_path:
            # 检查实际扩展名
            ext = os.path.splitext(existing_audio_path)[1].lower()
            mime = "audio/wav" if ext == ".wav" else "audio/mpeg"
            return FileResponse(existing_audio_path, media_type=mime)
        raise HTTPException(status_code=404, detail="语音文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取语音失败: {str(e)}")

@router.delete("/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def delete_narrator_audio(
    board_id: str,
    window_id: str,
    page: int
):
    """删除PDF指定页面的语音与字幕文件"""
    check_enabled()
    try:
        success = content_manager.delete_narrator_audio(board_id, window_id, page)
        if success:
            return {"success": True}
        raise HTTPException(status_code=500, detail="删除语音失败")
    except HTTPException:
        raise
    except Exception as e:
        error(f"删除语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除语音失败: {str(e)}")

@router.get("/boards/{board_id}/windows/{window_id}/narrator/subtitles/{page}")
async def get_narrator_subtitles_api(
    board_id: str,
    window_id: str,
    page: int
):
    """获取PDF指定页面的字幕文件"""
    check_enabled()
    try:
        subs = content_manager.get_narrator_subtitles(board_id, window_id, page)
        return {"subtitles": subs or []}
    except Exception as e:
        error(f"获取字幕失败: {e}")
        return {"subtitles": []}



def split_text_smartly(text: str) -> List[str]:
    """智能分句：保留标点符号，同时支持换行符作为分隔"""
    lines = text.split('\n')
    final_sentences = []
    
    pattern = r'([。！？.!?])'
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        parts = re.split(pattern, line)
        current = ""
        for part in parts:
            current += part
            if re.match(pattern, part):
                if len(current.strip()) > 0:
                    final_sentences.append(current)
                current = ""
        
        if current.strip():
            final_sentences.append(current)
            
    return final_sentences


def get_audio_duration_seconds(audio_path: Path) -> float:
    """获取音频时长。WAV 走标准库，其余格式走 ffprobe。"""
    ext = audio_path.suffix.lower()
    if ext == ".wav":
        with wave.open(str(audio_path), "rb") as wav_in:
            frames = wav_in.getnframes()
            rate = wav_in.getframerate()
            return frames / float(rate) if rate else 0.0

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float((result.stdout or "0").strip() or 0.0)


def concat_audio_with_ffmpeg(segment_paths: List[Path], output_ext: str) -> bytes:
    """使用 ffmpeg 正确拼接音频，避免直接二进制拼接导致文件损坏。"""
    if not segment_paths:
        return b""

    concat_file = DATA_DIR / "temp" / "audio" / f"concat_{uuid.uuid4().hex}.txt"
    output_file = DATA_DIR / "temp" / "audio" / f"concat_{uuid.uuid4().hex}.{output_ext}"
    concat_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        concat_lines = []
        for path in segment_paths:
            escaped_path = str(path).replace("'", "'\\''")
            concat_lines.append(f"file '{escaped_path}'\n")
        concat_file.write_text(
            "".join(concat_lines),
            encoding="utf-8"
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_file)
            ],
            capture_output=True,
            text=True,
            check=True
        )

        return output_file.read_bytes()
    finally:
        if concat_file.exists():
            concat_file.unlink()
        if output_file.exists():
            output_file.unlink()

@router.post("/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def generate_narrator_audio(
    board_id: str,
    window_id: str,
    page: int,
    request: Request
):
    """生成PDF指定页面的语音（强制重新生成）"""
    check_enabled()
    try:
        # 1. 获取参数
        request_body = await request.json()
        text = request_body.get('text', '')
        prompt_audio_path = request_body.get('prompt_audio_path', '')
        text_language = request_body.get('text_language', 'zh')
        
        if not text:
            raise HTTPException(status_code=400, detail="缺少文本内容")
            
        # 2. 获取 TTS 配置
        config = tts_service.get_tts_config()
        provider = config.get("provider", "edge")
        
        # 3. 准备分句逻辑
        sentences = split_text_smartly(text)
        info(f"TTS Split ({provider}): {len(sentences)} sentences")
        
        subtitles = []
        current_time = 0.0
        final_audio = b""
        audio_extension = "wav" # 默认合并后输出为 wav，除非实际生成的是其他格式
        segment_paths: List[Path] = []

        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue

            res = await tts_service.generate(cleaned)
            if not res.get("success"):
                error(f"TTS Segment Error ({provider}): {res.get('error')}")
                continue

            audio_url = res["audio_url"]
            temp_file_path = DATA_DIR / audio_url.replace("/static/files/", "")

            try:
                duration = get_audio_duration_seconds(temp_file_path)
                ext = temp_file_path.suffix.lower().replace(".", "") or "wav"
                if segment_paths and ext != audio_extension:
                    raise HTTPException(status_code=500, detail=f"音频分段格式不一致: {audio_extension} -> {ext}")

                audio_extension = ext
                segment_paths.append(temp_file_path)
                subtitles.append({
                    "start": current_time,
                    "end": current_time + duration,
                    "text": cleaned
                })
                current_time += duration
            except HTTPException:
                raise
            except Exception as e:
                error(f"Error processing audio segment: {e}")

        # 5. 完成合并
        if not segment_paths:
            raise HTTPException(status_code=500, detail="未生成任何可用音频片段")

        if len(segment_paths) == 1:
            final_audio = segment_paths[0].read_bytes()
        elif audio_extension == "wav":
            full_audio_buffer = io.BytesIO()
            wave_writer = None
            try:
                for segment_path in segment_paths:
                    with wave.open(str(segment_path), "rb") as wav_in:
                        if wave_writer is None:
                            wave_writer = wave.open(full_audio_buffer, "wb")
                            wave_writer.setparams(wav_in.getparams())
                        wave_writer.writeframes(wav_in.readframes(wav_in.getnframes()))
            finally:
                if wave_writer:
                    wave_writer.close()
            final_audio = full_audio_buffer.getvalue()
        else:
            final_audio = concat_audio_with_ffmpeg(segment_paths, audio_extension)

        if not final_audio:
            raise HTTPException(status_code=500, detail="音频拼接失败")
            
        # 6. 保存并返回
        saved_path = content_manager.save_narrator_audio(board_id, window_id, page, final_audio, extension=audio_extension)
        content_manager.save_narrator_subtitles(board_id, window_id, page, subtitles)
        
        if saved_path:
            return {
                "success": True,
                "audio_url": f"/api/boards/{board_id}/windows/{window_id}/narrator/audio/{page}",
                "subtitles": subtitles
            }
        else:
            raise HTTPException(status_code=500, detail="保存音频失败")

    except HTTPException:
        raise
    except Exception as e:
        error(f"生成语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成语音失败: {str(e)}")


# =============================================================================
# Step Script audio (per-section TTS aligned with lesson_plan.steps)
# =============================================================================

from .step_audio import synthesize_step_section


def _load_step_script_data(board_id: str, window_id: str) -> Optional[Dict]:
    if conversation_manager is None:
        return None
    ss_file = conversation_manager.get_board_conversations_dir(board_id) / f"step-script-{window_id}-data.json"
    if not ss_file.exists():
        return None
    try:
        with open(ss_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        error(f"[step_audio] 读取 step_script 失败: {e}")
        return None


def _resolve_step_section(board_id: str, window_id: str, section_idx: int, body_section: Optional[Dict]) -> Dict:
    """先用 body 里传过来的 section，没有就从磁盘读 step-script-data。section_idx 是 0-based。"""
    if body_section and isinstance(body_section, dict) and body_section.get("blocks"):
        return body_section
    data = _load_step_script_data(board_id, window_id)
    if not data:
        raise HTTPException(status_code=404, detail="未找到 step_script 数据，请先生成 Step Script")
    sections = data.get("sections") or []
    if section_idx < 0 or section_idx >= len(sections):
        raise HTTPException(status_code=404, detail=f"section_idx 越界（0..{len(sections)-1}）")
    sec = sections[section_idx] or {}
    if not sec.get("blocks"):
        raise HTTPException(status_code=400, detail=f"§{section_idx+1} 没有 blocks，无法合成")
    return sec


@router.post("/boards/{board_id}/windows/{window_id}/narrator/step-audio/{section_idx}")
async def generate_step_section_audio(board_id: str, window_id: str, section_idx: int, request: Request):
    """合成一节 step_script 的完整音频 + 带 step_id 的字幕轨。

    Body（可选）:
        { "section": {...}, "add_silence": true }
    若 section 缺省则从磁盘读 step-script-data。
    """
    check_enabled()
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}
        body_section = (body or {}).get("section")
        add_silence = bool((body or {}).get("add_silence", True))

        section = _resolve_step_section(board_id, window_id, section_idx, body_section)
        section_num = int(section.get("section_number") or (section_idx + 1))

        info(f"[step_audio] 开始合成 §{section_num} (board={board_id}, window={window_id})")

        result = await synthesize_step_section(
            section=section,
            tts_service=tts_service,
            temp_dir=DATA_DIR / "temp" / "audio",
            add_silence_after_pause_cue=add_silence,
        )

        saved_path = content_manager.save_step_audio(
            board_id, window_id, section_num,
            result["audio_bytes"], extension=result["extension"],
        )
        if not saved_path:
            raise HTTPException(status_code=500, detail="保存 step audio 失败")
        content_manager.save_step_subtitles(board_id, window_id, section_num, result["subtitles"])

        info(
            f"[step_audio] §{section_num} 合成完成: {result['duration_seconds']:.1f}s "
            f"({result['sentence_count']}句 + {result['silence_count']}静默)"
        )

        return {
            "success": True,
            "section_number": section_num,
            "audio_url": f"/api/boards/{board_id}/windows/{window_id}/narrator/step-audio/{section_num}",
            "subtitles": result["subtitles"],
            "duration_seconds": result["duration_seconds"],
            "sentence_count": result["sentence_count"],
            "silence_count": result["silence_count"],
            "pause_seconds_total": result["pause_seconds_total"],
            "block_count": result["block_count"],
            "extension": result["extension"],
            "warnings": result.get("warnings") or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"step 音频合成失败 §{section_idx + 1}: {e}")
        raise HTTPException(status_code=500, detail=f"step 音频合成失败: {str(e)}")


@router.get("/boards/{board_id}/windows/{window_id}/narrator/step-audio/{section_num}")
async def get_step_section_audio(board_id: str, window_id: str, section_num: int):
    """返回某节已合成的 step 音频二进制。section_num 是 1-based 章节号。"""
    check_enabled()
    try:
        path = content_manager.get_step_audio_path(board_id, window_id, section_num)
        if not path:
            raise HTTPException(status_code=404, detail="step 音频不存在，请先合成")
        ext = os.path.splitext(path)[1].lower()
        mime = "audio/wav" if ext == ".wav" else "audio/mpeg"
        return FileResponse(path, media_type=mime, headers={"Cache-Control": "no-cache"})
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取 step 音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/boards/{board_id}/windows/{window_id}/narrator/step-audio/{section_num}")
async def delete_step_section_audio(board_id: str, window_id: str, section_num: int):
    check_enabled()
    try:
        content_manager.delete_step_audio(board_id, window_id, section_num)
        return {"success": True}
    except Exception as e:
        error(f"删除 step 音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/boards/{board_id}/windows/{window_id}/narrator/step-subtitles/{section_num}")
async def get_step_section_subtitles(board_id: str, window_id: str, section_num: int):
    """返回某节的 step 字幕轨（含 step_id/kind/anchor_page）。"""
    check_enabled()
    try:
        subs = content_manager.get_step_subtitles(board_id, window_id, section_num)
        return {"subtitles": subs or []}
    except Exception as e:
        error(f"获取 step 字幕失败: {e}")
        return {"subtitles": []}


@router.get("/boards/{board_id}/windows/{window_id}/narrator/step-audio")
async def list_step_section_audio(board_id: str, window_id: str):
    """列出已经合成 step audio 的章节号。"""
    check_enabled()
    try:
        nums = content_manager.list_step_audio_sections(board_id, window_id)
        return {"sections": nums}
    except Exception as e:
        error(f"列出 step 音频失败: {e}")
        return {"sections": []}


@router.post("/boards/{board_id}/windows/{window_id}/narrator/step-audio/batch")
async def batch_generate_step_audio(board_id: str, window_id: str, request: Request):
    """SSE 流式批量合成 step audio。

    Body（可选）:
        {
            "mode": "all" | "missing" | "indices",
            "indices": [0,2,5],           # 0-based，仅当 mode=indices
            "add_silence": true,
            "concurrency": 1               # GPT-SoVITS 通常不能并发，默认串行
        }
    """
    check_enabled()
    try:
        body = await request.json() if await request.body() else {}
    except Exception:
        body = {}
    mode = (body or {}).get("mode", "all")
    requested_indices = (body or {}).get("indices") or []
    add_silence = bool((body or {}).get("add_silence", True))
    # 串行：GPT-SoVITS 单进程实例不能并发推理，默认 1。
    concurrency = max(1, min(4, int((body or {}).get("concurrency", 1) or 1)))

    data = _load_step_script_data(board_id, window_id)
    if not data:
        raise HTTPException(status_code=404, detail="未找到 step_script 数据，请先生成 Step Script")
    sections = data.get("sections") or []
    if not sections:
        raise HTTPException(status_code=400, detail="step_script 没有任何 section")

    # 计算 target indices
    existing_nums = set(content_manager.list_step_audio_sections(board_id, window_id))
    target_indices: List[int] = []
    if mode == "indices":
        target_indices = [i for i in requested_indices if 0 <= i < len(sections)]
    elif mode == "missing":
        for i, sec in enumerate(sections):
            if not sec:
                continue
            section_num = int((sec or {}).get("section_number") or (i + 1))
            if section_num not in existing_nums:
                target_indices.append(i)
    else:
        target_indices = list(range(len(sections)))

    if not target_indices:
        async def empty_stream():
            yield f"data: {json.dumps({'type': 'complete', 'message': '没有需要合成的章节'})}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    import asyncio as _asyncio

    async def stream():
        yield f"data: {json.dumps({'type': 'start', 'total': len(target_indices), 'mode': mode, 'concurrency': concurrency})}\n\n"

        sem = _asyncio.Semaphore(concurrency)
        done_count = 0
        results: Dict[int, Dict] = {}

        out_queue: _asyncio.Queue = _asyncio.Queue()

        async def worker(idx: int):
            async with sem:
                sec = sections[idx] or {}
                section_num = int(sec.get("section_number") or (idx + 1))
                title = sec.get("section_title") or f"Section {section_num}"
                try:
                    await out_queue.put({"type": "section_start", "section_num": section_num, "title": title, "idx": idx})
                    if not sec.get("blocks"):
                        raise RuntimeError("section 没有 blocks")
                    result = await synthesize_step_section(
                        section=sec,
                        tts_service=tts_service,
                        temp_dir=DATA_DIR / "temp" / "audio",
                        add_silence_after_pause_cue=add_silence,
                    )
                    saved_path = content_manager.save_step_audio(
                        board_id, window_id, section_num,
                        result["audio_bytes"], extension=result["extension"],
                    )
                    if not saved_path:
                        raise RuntimeError("保存音频失败")
                    content_manager.save_step_subtitles(board_id, window_id, section_num, result["subtitles"])
                    await out_queue.put({
                        "type": "section_done",
                        "section_num": section_num,
                        "title": title,
                        "idx": idx,
                        "duration_seconds": result["duration_seconds"],
                        "sentence_count": result["sentence_count"],
                        "silence_count": result["silence_count"],
                        "warnings": result.get("warnings") or [],
                    })
                    results[idx] = {"ok": True, "section_num": section_num}
                except Exception as e:
                    error(f"[step_audio:batch] §{section_num} 失败: {e}")
                    await out_queue.put({
                        "type": "section_failed",
                        "section_num": section_num,
                        "title": title,
                        "idx": idx,
                        "error": str(e),
                    })
                    results[idx] = {"ok": False, "section_num": section_num, "error": str(e)}

        # 启动所有 worker
        workers = [_asyncio.create_task(worker(idx)) for idx in target_indices]
        gathered = _asyncio.gather(*workers)

        async def heartbeat_loop():
            while not gathered.done():
                await _asyncio.sleep(15)
                if gathered.done():
                    break
                await out_queue.put({"type": "heartbeat", "done": done_count, "total": len(target_indices)})

        hb = _asyncio.create_task(heartbeat_loop())

        try:
            while True:
                try:
                    msg = await _asyncio.wait_for(out_queue.get(), timeout=2.0)
                except _asyncio.TimeoutError:
                    if gathered.done() and out_queue.empty():
                        break
                    continue
                if msg.get("type") in ("section_done", "section_failed"):
                    done_count += 1
                    msg["done"] = done_count
                    msg["total"] = len(target_indices)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                if gathered.done() and out_queue.empty():
                    break
        finally:
            hb.cancel()
            try:
                await hb
            except Exception:
                pass
            try:
                await gathered
            except Exception:
                pass

        ok = sum(1 for r in results.values() if r.get("ok"))
        failed = [r for r in results.values() if not r.get("ok")]
        yield f"data: {json.dumps({'type': 'complete', 'ok': ok, 'failed': failed, 'total': len(target_indices)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
