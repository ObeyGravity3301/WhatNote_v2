
@app.post("/api/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def generate_narrator_audio(
    board_id: str,
    window_id: str,
    page: int,
    request: Request
):
    """生成或获取PDF指定页面的语音"""
    try:
        # 1. 检查是否已存在
        existing_audio_path = content_manager.get_narrator_audio_path(board_id, window_id, page)
        if existing_audio_path:
            return FileResponse(existing_audio_path, media_type="audio/wav")
            
        # 2. 获取参数
        request_body = await request.json()
        text = request_body.get('text', '')
        prompt_audio_path = request_body.get('prompt_audio_path', '') # 前端暂未传，预留
        
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
                        prompt_text = meta.get('text', '')
                        prompt_lang = meta.get('language', 'zh')
                except:
                    pass
        
        # 如果还是没有，尝试使用 GPT-SoVITS 目录下的示例音频作为最后的 Fallback
        if not ref_audio_path:
             # 这是一个 hack，让用户第一次能跑通
             # 如果没有 default.wav，我们报错提示用户上传
             raise HTTPException(status_code=400, detail="未设置参考音频，请在设置中上传一段5-10秒的参考音频")

        # 4. 调用 TTS 服务
        payload = {
            "text": text,
            "text_language": "zh",
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

@app.post("/api/tts/reference")
async def upload_tts_reference(
    file: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form("zh")
):
    """上传默认参考音频"""
    try:
        ref_dir = DATA_DIR / "ref_audio"
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = ref_dir / "default.wav"
        meta_path = ref_dir / "default.json"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        with open(meta_path, "w") as f:
            json.dump({"text": text, "language": language}, f)
            
        return {"success": True, "message": "参考音频已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/api/tts/status")
async def get_tts_status():
    """检查TTS服务状态"""
    try:
        async with aiohttp.ClientSession() as session:
            # 尝试调用 control 接口或直接 ping
            async with session.get(f"{GPT_SOVITS_URL}/control") as response:
                # 只要能连通就行，哪怕返回 405 Method Not Allowed
                return {"status": "online", "version": "v2"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}






