"""Step Script -> TTS audio + step_id-aware subtitle track.

输入：一节 step_script section（由 services.step_script_service 生成）。
输出：单个音频文件 + 字幕 list，每条字幕带 (step_id, kind, anchor_page, block_index)。

约定（用户决定）：
- pause_cue：先念 cue 句子，再追加 lesson_plan.steps[i].pause_seconds 秒静默
- 默认 TTS provider：GPT-SoVITS（出 wav，方便用 wave 标准库注入静默）

设计要点：
- 复用 tts_service.generate(sentence)，逐句出音频片段
- 第一个 wav 段落的参数 (nchannels/sampwidth/framerate) 作为静默段的模板
- 非 wav 输出回退到 ffmpeg anullsrc 生成同采样率静默
- 字幕单位是"句"，对齐前端"句级高亮"的现状
"""

from __future__ import annotations

import io
import json
import wave
import uuid
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from logger import info, error


# ------------------ wav helpers ------------------


def _wav_params(path: Path) -> Optional[wave._wave_params]:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getparams()
    except Exception:
        return None


def _make_silence_wav(out_path: Path, params, seconds: float) -> bool:
    """按给定 wav params 写一段静默到 out_path。"""
    try:
        frames = max(1, int(round(params.framerate * max(0.0, seconds))))
        silence = b"\x00" * frames * params.sampwidth * params.nchannels
        with wave.open(str(out_path), "wb") as w:
            w.setparams(params)
            w.writeframes(silence)
        return True
    except Exception as e:
        error(f"[step_audio] 生成静默 wav 失败: {e}")
        return False


def _make_silence_ffmpeg(out_path: Path, seconds: float, sample_rate: int = 44100, ext: str = "mp3") -> bool:
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=mono:sample_rate={sample_rate}",
                "-t", f"{max(0.05, seconds):.3f}",
                "-q:a", "9",
                str(out_path),
            ],
            capture_output=True, text=True, check=True,
        )
        return True
    except Exception as e:
        error(f"[step_audio] ffmpeg 静默生成失败: {e}")
        return False


def _audio_duration(path: Path) -> float:
    """优先 wave 标准库，失败回退 ffprobe。"""
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                return frames / float(rate) if rate else 0.0
        except Exception:
            pass
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, check=True,
        )
        return float((result.stdout or "0").strip() or 0.0)
    except Exception as e:
        error(f"[step_audio] 读取时长失败 {path}: {e}")
        return 0.0


def _concat_wav(segment_paths: List[Path], out_path: Path) -> bool:
    """全 wav 拼接走标准库（不依赖 ffmpeg），更快更稳。"""
    try:
        writer = None
        try:
            for sp in segment_paths:
                with wave.open(str(sp), "rb") as r:
                    if writer is None:
                        writer = wave.open(str(out_path), "wb")
                        writer.setparams(r.getparams())
                    writer.writeframes(r.readframes(r.getnframes()))
        finally:
            if writer is not None:
                writer.close()
        return True
    except Exception as e:
        error(f"[step_audio] wav 拼接失败: {e}")
        return False


def _concat_ffmpeg(segment_paths: List[Path], out_path: Path) -> bool:
    if not segment_paths:
        return False
    concat_list = out_path.parent / f"_concat_{uuid.uuid4().hex}.txt"
    try:
        lines = []
        for sp in segment_paths:
            escaped = str(sp).replace("'", "'\\''")
            lines.append(f"file '{escaped}'\n")
        concat_list.write_text("".join(lines), encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(out_path),
            ],
            capture_output=True, text=True, check=True,
        )
        return True
    except Exception as e:
        error(f"[step_audio] ffmpeg 拼接失败: {e}")
        return False
    finally:
        if concat_list.exists():
            try:
                concat_list.unlink()
            except Exception:
                pass


# ------------------ subtitle types ------------------


@dataclass
class _Segment:
    path: Path
    duration: float
    is_silence: bool
    subtitle: Optional[Dict[str, Any]]  # None for silence-only padding-less segments


# ------------------ core ------------------


async def synthesize_step_section(
    *,
    section: Dict[str, Any],
    tts_service,
    temp_dir: Path,
    add_silence_after_pause_cue: bool = True,
    progress_callback=None,  # 可选：(done_sentences, total_sentences, current_step_id, current_kind) -> None
) -> Dict[str, Any]:
    """合成一节 step_script -> {audio_bytes, extension, subtitles, duration, ...}

    Args:
        section: 一个 step_script section，含 'blocks'（每个 block 有 kind/step_id/anchor_page/script/sentences）
        tts_service: 实例化好的 TTSService，将复用 .generate(text)
        temp_dir: 用于落 tts 临时片段（通常 DATA_DIR/temp/audio）
        add_silence_after_pause_cue: pause_cue 后是否插静默（约定 True）
        progress_callback: 可选回调，每完成一句调用

    Returns:
        {
            "audio_bytes": bytes,
            "extension": "wav"|"mp3",
            "subtitles": [...],
            "duration_seconds": float,
            "sentence_count": int,
            "pause_seconds_total": float,
            "warnings": [...],
        }
    """
    section_num = int(section.get("section_number") or 0)
    blocks = section.get("blocks") or []
    if not blocks:
        raise ValueError(f"section {section_num} 没有 blocks，无法合成")

    temp_dir.mkdir(parents=True, exist_ok=True)

    # 先把所有 sentence 摊平
    flat: List[Tuple[int, Dict[str, Any], int, str]] = []
    total_sentences = 0
    for bidx, block in enumerate(blocks):
        sentences = block.get("sentences") or []
        if not sentences:
            # fallback：若没拆，整个 script 当一句（前端不会很好看，但能跑）
            script = (block.get("script") or "").strip()
            if script:
                sentences = [script]
        for sidx, sent in enumerate(sentences):
            s = (sent or "").strip()
            if not s:
                continue
            flat.append((bidx, block, sidx, s))
            total_sentences += 1

    if not flat:
        raise ValueError(f"section {section_num} blocks 无可用句子")

    info(f"[step_audio] §{section_num} 待合成 {total_sentences} 句 / {len(blocks)} blocks")

    segments: List[_Segment] = []
    cursor = 0.0
    subtitles: List[Dict[str, Any]] = []
    warnings: List[str] = []
    first_wav_params = None  # type: Optional[wave._wave_params]
    extension: Optional[str] = None  # 取首个 segment 的扩展名

    sentence_done = 0
    last_block_index: Optional[int] = None

    for (bidx, block, sidx, sent) in flat:
        kind = block.get("kind") or "main"
        step_id = block.get("step_id")
        anchor_page = block.get("anchor_page")
        block_index = bidx

        # --- TTS 单句合成 ---
        res = await tts_service.generate(sent)
        if not res or not res.get("success"):
            warning_msg = f"§{section_num} b{bidx} s{sidx} TTS 失败: {(res or {}).get('error', 'unknown')}"
            warnings.append(warning_msg)
            error(f"[step_audio] {warning_msg}")
            continue

        url = res.get("audio_url") or ""
        rel = url.replace("/static/files/", "").lstrip("/")
        # tts_service 把临时文件放在 data_dir/temp/audio/<name>
        seg_path = tts_service.data_dir / rel if not Path(rel).is_absolute() else Path(rel)
        if not seg_path.exists():
            # 兜底尝试用 temp_dir 拼
            alt = temp_dir / Path(rel).name
            if alt.exists():
                seg_path = alt
            else:
                warnings.append(f"§{section_num} b{bidx} s{sidx} 找不到生成文件: {seg_path}")
                continue

        seg_ext = seg_path.suffix.lower().lstrip(".") or "wav"
        if extension is None:
            extension = seg_ext
        elif seg_ext != extension:
            warnings.append(f"§{section_num} 音频扩展名混杂 {extension} vs {seg_ext}，已强制忽略")
            # 不混拼，跳过这个 segment（实际中 GPT-SoVITS 单提供商场景不会触发）
            continue

        if first_wav_params is None and seg_ext == "wav":
            first_wav_params = _wav_params(seg_path)

        duration = _audio_duration(seg_path)
        sub = {
            "start": round(cursor, 4),
            "end": round(cursor + duration, 4),
            "text": sent,
            "step_id": step_id,
            "kind": kind,
            "anchor_page": anchor_page,
            "block_index": block_index,
            "sentence_index": sidx,
        }
        subtitles.append(sub)
        segments.append(_Segment(path=seg_path, duration=duration, is_silence=False, subtitle=sub))
        cursor += duration

        sentence_done += 1
        last_block_index = bidx
        if progress_callback is not None:
            try:
                progress_callback(sentence_done, total_sentences, step_id, kind)
            except Exception:
                pass

    if not segments:
        raise RuntimeError(f"§{section_num} 没有可用 TTS 片段")

    # --- 在每个 pause_cue block 末尾插入静默 ---
    pause_seconds_total = 0.0
    if add_silence_after_pause_cue:
        # 重新走一遍 blocks，找出 pause_cue 的位置（block index），在该 block 最后一句字幕后插静默
        pause_inserts: List[Tuple[int, float, Dict[str, Any]]] = []
        for bidx, block in enumerate(blocks):
            if block.get("kind") != "pause_cue":
                continue
            pause_s = float(block.get("pause_seconds") or 0.0)
            if pause_s <= 0:
                continue
            pause_inserts.append((bidx, pause_s, block))

        if pause_inserts:
            # 我们要重排 segments 列表 & subtitles，让静默插在对应 block 的最后一句之后。
            # 现有 segments 已经按时间顺序排好（因为我们就是顺序生成的）。
            # 简化处理：在 subtitles 顺序里找到每个 pause block 的最后一条字幕，插入 silence。
            # segments 也同步插入对应文件（用同 wav params 或 ffmpeg 生成）。

            new_segments: List[_Segment] = []
            new_subtitles: List[Dict[str, Any]] = []
            cursor2 = 0.0
            pause_by_bidx = {bidx: (sec, block) for (bidx, sec, block) in pause_inserts}
            # group segments by block_index, but preserve order
            grouped: Dict[int, List[_Segment]] = {}
            order: List[int] = []
            for seg in segments:
                bidx = seg.subtitle["block_index"] if seg.subtitle else -1
                if bidx not in grouped:
                    grouped[bidx] = []
                    order.append(bidx)
                grouped[bidx].append(seg)

            for bidx in order:
                segs = grouped[bidx]
                # 重新算时间戳（cursor2）
                for seg in segs:
                    duration = seg.duration
                    if seg.subtitle is not None:
                        new_sub = dict(seg.subtitle)
                        new_sub["start"] = round(cursor2, 4)
                        new_sub["end"] = round(cursor2 + duration, 4)
                        new_subtitles.append(new_sub)
                        new_segments.append(_Segment(
                            path=seg.path, duration=duration,
                            is_silence=False, subtitle=new_sub,
                        ))
                    cursor2 += duration

                if bidx in pause_by_bidx:
                    pause_s, pblock = pause_by_bidx[bidx]
                    silence_path = temp_dir / f"step_silence_{uuid.uuid4().hex}.{extension}"
                    ok = False
                    if extension == "wav" and first_wav_params is not None:
                        ok = _make_silence_wav(silence_path, first_wav_params, pause_s)
                    if not ok:
                        # 回退用 ffmpeg
                        ok = _make_silence_ffmpeg(silence_path, pause_s, sample_rate=(first_wav_params.framerate if first_wav_params else 44100), ext=extension or "wav")
                    if not ok:
                        warnings.append(f"§{section_num} b{bidx} pause_cue 静默生成失败，跳过")
                        continue
                    silence_duration = _audio_duration(silence_path)
                    silence_sub = {
                        "start": round(cursor2, 4),
                        "end": round(cursor2 + silence_duration, 4),
                        "text": f"[pause {int(round(pause_s))}s]",
                        "step_id": pblock.get("step_id"),
                        "kind": "silence",
                        "anchor_page": pblock.get("anchor_page"),
                        "block_index": bidx,
                        "sentence_index": None,
                        "pause_seconds": pause_s,
                    }
                    new_subtitles.append(silence_sub)
                    new_segments.append(_Segment(
                        path=silence_path, duration=silence_duration,
                        is_silence=True, subtitle=silence_sub,
                    ))
                    cursor2 += silence_duration
                    pause_seconds_total += silence_duration

            segments = new_segments
            subtitles = new_subtitles
            cursor = cursor2

    # --- 拼接 ---
    final_path = temp_dir / f"step_section_{section_num:03d}_{uuid.uuid4().hex}.{extension}"
    if extension == "wav":
        ok = _concat_wav([s.path for s in segments], final_path)
    else:
        ok = _concat_ffmpeg([s.path for s in segments], final_path)
    if not ok or not final_path.exists():
        raise RuntimeError(f"§{section_num} 音频拼接失败")

    try:
        audio_bytes = final_path.read_bytes()
    finally:
        try:
            final_path.unlink()
        except Exception:
            pass

    return {
        "audio_bytes": audio_bytes,
        "extension": extension or "wav",
        "subtitles": subtitles,
        "duration_seconds": round(cursor, 3),
        "sentence_count": sum(1 for s in segments if not s.is_silence),
        "silence_count": sum(1 for s in segments if s.is_silence),
        "pause_seconds_total": round(pause_seconds_total, 3),
        "block_count": len(blocks),
        "warnings": warnings,
    }
