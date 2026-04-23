import json
from pathlib import Path
from typing import Dict, List, Optional
import os
import uuid
import aiohttp
import edge_tts
import asyncio
import subprocess
import platform
from logger import info, error

class TTSService:
    def __init__(self, data_dir: Path, api_config_manager):
        self.data_dir = data_dir
        self.temp_audio_dir = data_dir / "temp" / "audio"
        self.temp_audio_dir.mkdir(parents=True, exist_ok=True)
        self.api_config_manager = api_config_manager
        self._last_status = {"gpt_sovits": False}
        self._sovits_process = None

    def get_tts_config(self) -> Dict:
        """从 api_config.json 获取 TTS 配置"""
        full_config = self.api_config_manager.get_config()
        return full_config.get("tts", {
            "provider": "edge",  # 默认 edge
            "voice": "zh-CN-XiaoxiaoNeural",
            "rate": "+0%",
            "volume": "+0%",
            "sovits_url": "http://127.0.0.1:9880",
            "sovits_path": ""
        })

    async def test_sovits_connection(self, url: Optional[str] = None) -> Dict:
        """测试 GPT-SoVITS 连接状态"""
        if not url:
            config = self.get_tts_config()
            url = config.get("sovits_url", "http://127.0.0.1:9880")
        
        # 确保有协议头
        if url and not url.startswith("http"):
            url = f"http://{url}"
            
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 新版 GPT-SoVITS api.py 没有 /models，这里改用更稳定的 /control 探活。
                async with session.get(f"{url}/control") as response:
                    if response.status == 200:
                        self._last_status["gpt_sovits"] = True
                        return {
                            "success": True,
                            "message": "连接成功"
                        }
                    return {"success": False, "message": f"服务器返回错误: {response.status}"}
        except Exception as e:
            self._last_status["gpt_sovits"] = False
            return {"success": False, "message": f"无法连接: {str(e)}"}

    def check_local_sovits(self, path: str) -> Dict:
        """检查本地路径是否包含 GPT-SoVITS"""
        if not path:
            return {"success": False, "message": "未提供路径"}
            
        p = Path(path)
        if not p.exists():
            return {"success": False, "message": "路径不存在"}
            
        # 检查关键文件
        indicators = ["api_v2.py", "go-webui.bat", "runtime", "GPT_SoVITS"]
        found = [i for i in indicators if (p / i).exists()]
        
        if len(found) >= 2:
            return {
                "success": True, 
                "message": "检测到 GPT-SoVITS",
                "indicators": found
            }
        return {"success": False, "message": "未在该路径下发现 GPT-SoVITS 核心文件"}

    async def start_local_sovits(self) -> Dict:
        """启动本地 GPT-SoVITS 服务"""
        config = self.get_tts_config()
        path = config.get("sovits_path")
        
        if not path:
            return {"success": False, "message": "未配置本地路径"}
            
        p = Path(path)
        if not p.exists():
            return {"success": False, "message": "配置的路径不存在"}
            
        # 检查是否已经在运行
        status = await self.test_sovits_connection()
        if status["success"]:
            return {"success": True, "message": "服务已在运行中"}

        # 准备启动命令
        is_windows = platform.system() == "Windows"
        candidate_paths = []
        if is_windows:
            candidate_paths = [
                p / "venv310" / "Scripts" / "python.exe",
                p / "venv" / "Scripts" / "python.exe",
                p / "runtime" / "python.exe",
            ]
        else:
            candidate_paths = [
                p / "venv310" / "bin" / "python",
                p / "venv" / "bin" / "python",
                p / "runtime" / "bin" / "python",
            ]

        venv_python = next((candidate for candidate in candidate_paths if candidate.exists()), None)

        if not venv_python:
            return {"success": False, "message": "未找到虚拟环境 Python 指释器，请确保路径正确"}

        try:
            info(f"正在尝试启动 GPT-SoVITS: {path}")
            # 使用 subprocess.Popen 启动，不阻塞
            # 注意：api.py 是 GPT-SoVITS 的默认 API 脚本
            self._sovits_process = subprocess.Popen(
                [str(venv_python), "api.py"],
                cwd=str(p),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if is_windows else 0
            )
            
            # 模型加载较慢，给足启动缓冲时间，避免前端误判为离线。
            for _ in range(90):
                await asyncio.sleep(1)
                status = await self.test_sovits_connection()
                if status["success"]:
                    return {"success": True, "message": "服务启动成功"}
            
            return {"success": False, "message": "服务启动超时，请检查控制台或手动启动尝试"}
            
        except Exception as e:
            error(f"启动 GPT-SoVITS 失败: {e}")
            return {"success": False, "message": f"启动失败: {str(e)}"}

    async def generate(self, text: str, voice: Optional[str] = None) -> Dict:
        config = self.get_tts_config()
        provider = config.get("provider", "edge")
        
        if provider == "edge":
            return await self._generate_edge(text, voice or config.get("voice"))
        elif provider == "gpt-sovits":
            return await self._generate_sovits(text, config)
        elif provider == "openai":
            return await self._generate_openai(text, config)
        else:
            raise ValueError(f"不支持的 TTS 服务商: {provider}")

    async def _generate_edge(self, text: str, voice: str) -> Dict:
        """Microsoft Edge TTS 实现"""
        filename = f"edge_{uuid.uuid4()}.mp3"
        save_path = self.temp_audio_dir / filename
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(save_path))
            return {
                "success": True,
                "audio_url": f"/static/files/temp/audio/{filename}",
                "provider": "edge"
            }
        except Exception as e:
            error(f"Edge TTS 生成失败: {e}")
            raise

    async def _generate_sovits(self, text: str, config: Dict) -> Dict:
        """GPT-SoVITS 实现"""
        url = config.get("sovits_url", "http://127.0.0.1:9880")
        if not url.startswith("http"):
            url = f"http://{url}"

        ref_audio_path = config.get("ref_audio_path")
        prompt_text = config.get("prompt_text") or ""
        prompt_language = config.get("prompt_lang", "zh")

        # 如果配置里没有显式写入参考音频，就复用插件上传的默认参考音频。
        if not ref_audio_path:
            default_ref_path = self.data_dir / "ref_audio" / "default.wav"
            default_meta_path = self.data_dir / "ref_audio" / "default.json"
            if default_ref_path.exists():
                ref_audio_path = str(default_ref_path)
                if default_meta_path.exists():
                    try:
                        with open(default_meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        prompt_text = prompt_text or meta.get("text", "")
                        prompt_language = meta.get("language", prompt_language)
                    except Exception as e:
                        error(f"读取默认参考音频元数据失败: {e}")
            
        timeout = aiohttp.ClientTimeout(total=300) 
        async with aiohttp.ClientSession(timeout=timeout) as session:
            params = {
                "text": text,
                "text_language": config.get("text_lang", "zh"),
                "refer_wav_path": ref_audio_path,
                "prompt_text": prompt_text,
                "prompt_language": prompt_language,
                "speed": config.get("speed_factor", 1.0)
            }
            
            try:
                # 兼容新版 GPT-SoVITS api.py，TTS 入口为根路径 /
                async with session.get(f"{url}/", params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {"success": False, "error": f"GPT-SoVITS Error: {error_text}"}
                    
                    audio_data = await response.read()
                    filename = f"sovits_{uuid.uuid4()}.wav"
                    save_path = self.temp_audio_dir / filename
                    
                    with open(save_path, "wb") as f:
                        f.write(audio_data)
                    
                    return {
                        "success": True, 
                        "audio_url": f"/static/files/temp/audio/{filename}",
                        "provider": "gpt-sovits"
                    }
            except aiohttp.ClientConnectorError:
                return {"success": False, "error": "无法连接到 GPT-SoVITS 服务，请检查其 API 是否已启动（默认端口 9880）"}

    async def _generate_openai(self, text: str, config: Dict) -> Dict:
        """OpenAI TTS 实现"""
        from openai import AsyncOpenAI
        import aiofiles
        
        # 统一使用 get_provider_config 以便支持环境变量
        openai_config = self.api_config_manager.get_provider_config("openai")
        if not openai_config:
            return {"success": False, "error": "OpenAI 配置不存在"}
            
        api_key = openai_config.get("apiKey")
        if not api_key:
            return {"success": False, "error": "未配置 OpenAI API Key"}
            
        client = AsyncOpenAI(api_key=api_key, base_url=openai_config.get("baseUrl"))
        
        try:
            filename = f"openai_{uuid.uuid4()}.mp3"
            save_path = self.temp_audio_dir / filename
            
            response = await client.audio.speech.create(
                model=config.get("model", "tts-1"),
                voice=config.get("voice", "alloy"),
                input=text
            )
            
            # 使用 aiofiles 异步写入
            async with aiofiles.open(save_path, "wb") as f:
                await f.write(response.content)
            
            return {
                "success": True,
                "audio_url": f"/static/files/temp/audio/{filename}",
                "provider": "openai"
            }
        except Exception as e:
            error(f"OpenAI TTS 生成失败: {e}")
            return {"success": False, "error": str(e)}

    async def list_voices(self, provider: str) -> List[Dict]:
        """获取音色列表"""
        if provider == "edge":
            try:
                # 简单获取一些常用中文音色，避免每次都扫描
                return [
                    {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女声)"},
                    {"id": "zh-CN-YunxiNeural", "name": "云希 (男声)"},
                    {"id": "zh-CN-YunjianNeural", "name": "云健 (男声)"},
                    {"id": "zh-CN-XiaoyiNeural", "name": "晓依 (女声)"},
                    {"id": "zh-TW-HsiaoChenNeural", "name": "晓臻 (女声-台湾)"},
                    {"id": "zh-HK-HiuGaaiNeural", "name": "晓佳 (女声-香港)"},
                ]
            except Exception as e:
                error(f"获取 Edge TTS 音色列表失败: {e}")
                return []
        elif provider == "gpt-sovits":
            res = await self.test_sovits_connection()
            if res["success"]:
                models = res.get("models", {})
                # 合并 GPT 和 SoVITS 模型
                gpt_models = models.get("gpt_models", [])
                sovits_models = models.get("sovits_models", [])
                return [{"id": m, "name": f"模型: {m}"} for m in list(set(gpt_models + sovits_models))]
            return []
        elif provider == "openai":
            return [
                {"id": "alloy", "name": "Alloy (通用)"},
                {"id": "echo", "name": "Echo (浑厚)"},
                {"id": "fable", "name": "Fable (叙述)"},
                {"id": "onyx", "name": "Onyx (沉稳)"},
                {"id": "nova", "name": "Nova (清亮)"},
                {"id": "shimmer", "name": "Shimmer (柔和)"}
            ]
        return []
