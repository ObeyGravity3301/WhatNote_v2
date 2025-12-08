from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from typing import List, Dict, Optional
import aiohttp
import json
import shutil
import uuid
import os
from pathlib import Path
from datetime import datetime
from logger import info, error
from .schemas import TTSRequest

router = APIRouter()

# Global dependencies to be injected
content_manager = None
llm_service = None
GPT_SOVITS_URL = "http://127.0.0.1:9880"
DATA_DIR = Path(".")

# Plugin State
_enabled = True

def check_enabled():
    if not _enabled:
        raise HTTPException(status_code=503, detail="Plugin is disabled")

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
    """调用 GPT-SoVITS 生成语音"""
    check_enabled()
    try:
        info(f"收到 TTS 请求: {request.text[:50]}...")
        
        payload = request.dict()
        
        # 如果没有提供参考音频，使用默认的
        # 这里暂时保留原逻辑，等待 generate_narrator_audio 处理更复杂的 fallback
        
        timeout = aiohttp.ClientTimeout(total=300) 
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {
                "text": request.text,
                "text_lang": request.text_lang,
                "ref_audio_path": request.ref_audio_path or "default_ref.wav", 
                "prompt_text": request.prompt_text or "",
                "prompt_lang": request.prompt_lang,
                "text_split_method": request.text_split_method,
                "batch_size": request.batch_size,
                "media_type": request.media_type,
                "speed_factor": request.speed_factor
            }
            
            try:
                # 尝试调用 GPT-SoVITS API (GET /tts)
                async with session.get(f"{GPT_SOVITS_URL}/tts", params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"GPT-SoVITS Error: {error_text}")
                    
                    audio_data = await response.read()
                    
                    # 保存文件
                    filename = f"tts_{uuid.uuid4()}.{request.media_type}"
                    save_dir = DATA_DIR / "temp" / "audio"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / filename
                    
                    with open(save_path, "wb") as f:
                        f.write(audio_data)
                    
                    audio_url = f"/static/files/temp/audio/{filename}"
                    return {"success": True, "audio_url": audio_url, "duration": 0} 

            except aiohttp.ClientConnectorError:
                raise HTTPException(status_code=503, detail="无法连接到 GPT-SoVITS 服务，请确认服务已启动 (默认端口 9880)")

    except Exception as e:
        error(f"TTS 生成失败: {e}")
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
            "language": meta.get("language", "zh")
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
        
        meta_data = {"text": text, "language": language}
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
            
        return {"success": True, "message": "参考音频已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


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


@router.get("/tts/models")
async def get_tts_models():
    """获取可用的GPT和SoVITS模型列表"""
    check_enabled()
    try:
        cwd = Path.cwd().resolve()
        info(f"当前工作目录: {cwd}")
        
        # 尝试定位 GPT-SoVITS 目录
        candidate_dir = cwd
        base_dir = None
        
        for _ in range(4):
            check_path = candidate_dir / "GPT-SoVITS"
            if check_path.exists() and (check_path / "GPT_weights").exists():
                base_dir = check_path
                break
            
            sibling_path = candidate_dir.parent / "GPT-SoVITS"
            if sibling_path.exists() and (sibling_path / "GPT_weights").exists():
                base_dir = sibling_path
                break
                
            candidate_dir = candidate_dir.parent
            
        if not base_dir:
            # 最后的硬编码尝试
            hardcoded = Path("/home/obeygravity/Projects/GPT-SoVITS")
            if hardcoded.exists():
                base_dir = hardcoded
        
        if not base_dir:
            return {"gpt_weights": [], "sovits_weights": [], "error": f"未找到 GPT-SoVITS 目录 (cwd: {cwd})"}

        info(f"定位到 GPT-SoVITS 目录: {base_dir}")

        gpt_weights = []
        gpt_dir = base_dir / "GPT_weights"
        if gpt_dir.exists():
            gpt_weights = [f.name for f in gpt_dir.glob("*.ckpt")]
            
        sovits_weights = []
        sovits_dir = base_dir / "SoVITS_weights"
        if sovits_dir.exists():
            sovits_weights = [f.name for f in sovits_dir.glob("*.pth")]
            
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
        
        possible_paths = [
            Path("../../GPT-SoVITS"), 
            Path("../GPT-SoVITS"),
            Path("GPT-SoVITS"),
        ]
        base_dir = None
        for p in possible_paths:
            if p.exists() and (p / "GPT_weights").exists():
                base_dir = p.resolve()
                break
        
        # Fallback to hardcoded if not found relative
        if not base_dir:
             hardcoded = Path("/home/obeygravity/Projects/GPT-SoVITS")
             if hardcoded.exists():
                 base_dir = hardcoded

        if not base_dir:
            raise HTTPException(status_code=500, detail="未找到 GPT-SoVITS 目录")

        payload = {}
        if gpt_name:
            payload["gpt_model_path"] = str(base_dir / "GPT_weights" / gpt_name)
        if sovits_name:
            payload["sovits_model_path"] = str(base_dir / "SoVITS_weights" / sovits_name)
            
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

                default_req = "请为每一页撰写一份口语化的演讲稿。\n要求：\n1. 时间控制在 30-60 秒。\n2. 语言自然流畅，适合朗读。\n3. 不要念标题，而是解释核心观点。\n4. 使用第一人称。"
                script_requirement = prompt_template if prompt_template else default_req
                
                prompt = f"""你是一位专业的演讲者。请根据以下PDF分段内容（包含上下文），为指定范围的页面撰写演讲稿。

**分段上下文信息**：
- 分段标题: {section_data.get('title', '未命名')}
- 分段描述: {section_description}
- 完整上下文页码: 第{page_start}页 - 第{page_end}页
{previous_context_text}

**分段完整内容**：
{full_content}

**任务目标**：
请仅为 **第{target_start}页 到 第{target_end}页** 生成演讲稿。
（第{page_start}页到第{target_start-1}页的内容仅供参考，不需要生成讲稿）

**讲稿要求**：
{script_requirement}

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "scripts": [
    {{
      "page": {target_start},
      "script": "第{target_start}页的演讲稿内容..."
    }},
    {{
      "page": {target_start + 1},
      "script": "第{target_start + 1}页的演讲稿内容..."
    }}
  ]
}}
```
请确保scripts数组包含从 **{target_start}** 到 **{target_end}** 的所有页面。
直接输出JSON，不要添加任何额外的说明文字。"""
                
                messages = [{
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                }]
                
                accumulated_content = ""
                
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                
                try:
                    content = accumulated_content.strip()
                    if content.startswith('```'):
                        lines = content.split('\n')
                        if lines[0].startswith('```'): lines = lines[1:]
                        if lines[-1].startswith('```'): lines = lines[:-1]
                        content = '\n'.join(lines)
                    
                    result_data = json.loads(content)
                    scripts = result_data.get('scripts', [])
                    
                    for script_item in scripts:
                        page = script_item.get('page')
                        text = script_item.get('script')
                        if page and text:
                            yield f"data: {json.dumps({'type': 'page_done', 'page': page, 'content': text}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'complete', 'total': len(scripts)}, ensure_ascii=False)}\n\n"
                    
                except json.JSONDecodeError as e:
                    error(f"解析讲稿JSON失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                error(f"批量生成讲稿失败: {e}")
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
            return FileResponse(existing_audio_path, media_type="audio/wav")
        raise HTTPException(status_code=404, detail="语音文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取语音失败: {str(e)}")

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
            
        # 3. 准备 TTS 请求
        ref_audio_path = prompt_audio_path
        prompt_text = request_body.get('prompt_text', '')
        prompt_lang = request_body.get('prompt_lang', 'zh')
        
        # 默认参考音频路径
        ref_dir = DATA_DIR / "ref_audio"
        default_ref_path = ref_dir / "default.wav"
        
        if not ref_audio_path and default_ref_path.exists():
            ref_audio_path = str(default_ref_path.absolute())
            meta_path = ref_dir / "default.json"
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                        if not prompt_text:
                            prompt_text = meta.get('text', '')
                        if not prompt_lang:
                            prompt_lang = meta.get('language', 'zh')
                except:
                    pass
        
        if not ref_audio_path:
             raise HTTPException(status_code=400, detail="未设置参考音频，请在设置中上传一段5-10秒的参考音频")

        # 4. 调用 TTS 服务
        payload = {
            "text": text,
            "text_language": text_language,
            "refer_wav_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_language": prompt_lang,
            "cut_punc": "，。！"
        }
        
        info(f"调用TTS: {GPT_SOVITS_URL}, text len: {len(text)}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{GPT_SOVITS_URL}/", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error(f"TTS API Error: {error_text}")
                    raise HTTPException(status_code=response.status, detail=f"TTS服务错误: {error_text}")
                
                audio_content = await response.read()
                
        # 5. 保存并返回
        saved_path = content_manager.save_narrator_audio(board_id, window_id, page, audio_content)
        
        if saved_path:
            return FileResponse(saved_path, media_type="audio/wav")
        else:
            raise HTTPException(status_code=500, detail="保存音频失败")

    except HTTPException:
        raise
    except Exception as e:
        error(f"生成语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成语音失败: {str(e)}")


