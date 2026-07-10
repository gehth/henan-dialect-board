#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语音合成 TTS（Edge TTS，需联网）：带磁盘缓存，相同「音色+文本」零重复下载。"""
import os
import hashlib
import tempfile

from . import _state


# 音色表定义在 _state，这里统一再导出供 backend.TTS_VOICES 访问
TTS_VOICES = _state.TTS_VOICES


def _tts_cache_dir():
    """TTS 缓存目录（用户目录，避免 exe 同目录的写权限问题）。"""
    d = os.path.join(os.path.expanduser("~"), ".henan_dialect", "tts_cache")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        return None


def _prune_tts_cache(cache_dir, limit=500):
    """缓存超过上限时清理最旧的文件，防止无限增长。"""
    try:
        files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir)
                 if f.endswith(".mp3")]
        if len(files) > limit:
            files.sort(key=lambda p: os.path.getmtime(p))
            for p in files[: len(files) - limit + 200]:
                try:
                    os.remove(p)
                except Exception:
                    pass
    except Exception:
        pass


def tts_synthesize(text: str, voice_key: str = "mandarin", out_path: str = None) -> str:
    """
    在线语音合成（Edge TTS，需联网）。返回 mp3 本地路径。
    带磁盘缓存：相同「音色+文本」直接复用，避免重复联网下载（秒开、省流量、可离线复用）。
    无 edge_tts 模块或无网络时抛异常，由调用方降级到系统 TTS。
    """
    try:
        import edge_tts
    except Exception:
        raise RuntimeError("未安装 edge_tts（请 pip install edge-tts）")
    if not text:
        raise ValueError("合成文本为空")
    import asyncio
    voice = _state.TTS_VOICES.get(voice_key, _state.TTS_VOICES["mandarin"])

    cache_dir = _tts_cache_dir()
    cached = None
    if cache_dir is not None and out_path is None:
        key = hashlib.md5((voice + "|" + text).encode("utf-8")).hexdigest()
        cached = os.path.join(cache_dir, key + ".mp3")
        if os.path.exists(cached):
            return cached  # 命中缓存：零下载、零联网

    if out_path is None:
        if cached is not None:
            out_path = cached  # 直接下载到缓存路径，无临时文件泄漏
        else:
            fd, out_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

    async def _run():
        comm = edge_tts.Communicate(text, voice)
        await comm.save(out_path)
    asyncio.run(_run())

    if cached is not None:
        _prune_tts_cache(cache_dir)
    return out_path
