
@app.get("/api/tts/models")
async def get_tts_models():
    """获取可用的GPT和SoVITS模型列表"""
    try:
        # 假设运行在 whatnote_v2 目录下，GPT-SoVITS 在 ../../GPT-SoVITS
        # 这是一个相对路径猜测，为了稳健，我们尝试几个可能的位置
        possible_paths = [
            Path("../../GPT-SoVITS"), # 从 whatnote_v2 运行
            Path("../GPT-SoVITS"),    # 从 whatnote 运行
            Path("GPT-SoVITS"),       # 同级
        ]
        
        base_dir = None
        for p in possible_paths:
            if p.exists() and (p / "GPT_weights").exists():
                base_dir = p
                break
        
        if not base_dir:
            return {"gpt_weights": [], "sovits_weights": [], "error": "未找到 GPT-SoVITS 目录"}

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

@app.post("/api/tts/set_model")
async def set_tts_model(request: Request):
    """切换GPT-SoVITS模型"""
    try:
        data = await request.json()
        gpt_name = data.get("gpt_model")
        sovits_name = data.get("sovits_model")
        
        # 重新定位 base_dir (同上)
        possible_paths = [
            Path("../../GPT-SoVITS"), 
            Path("../GPT-SoVITS"),
            Path("GPT-SoVITS"),
        ]
        base_dir = None
        for p in possible_paths:
            if p.exists() and (p / "GPT_weights").exists():
                base_dir = p.resolve() # 获取绝对路径
                break
        
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






