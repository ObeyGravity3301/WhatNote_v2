from pydantic import BaseModel
from typing import Optional

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    text_lang: str = "zh"
    ref_audio_path: Optional[str] = None
    prompt_text: Optional[str] = None
    prompt_lang: Optional[str] = "zh"
    top_k: int = 5
    top_p: float = 1
    temperature: float = 1
    text_split_method: str = "cut5"
    batch_size: int = 1
    batch_threshold: float = 0.75
    split_bucket: bool = True
    speed_factor: float = 1.0
    fragment_interval: float = 0.3
    seed: int = -1
    media_type: str = "wav"
    streaming_mode: bool = False
    parallel_infer: bool = True
    repetition_penalty: float = 1.35


