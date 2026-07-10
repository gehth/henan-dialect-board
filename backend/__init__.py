#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
河南方言语音板 · 后端逻辑包（桌面版，无 Flask）
============================================
把原先 900+ 行的 backend.py「上帝模块」拆分为职责单一的子模块
（_state / pinyin / dictionary / demo / llm / config / tts / correct / asr / status），
本文件仅做统一再导出，外部调用方（main.py / page_*.py / asr/）
仍可用 `import backend` + `backend.xxx` 不变。
"""
from ._state import resource_path  # 资源路径
from .pinyin import pinyin_of
from .dictionary import (
    get_dict, get_dict_packages, get_examples, get_user_words,
    add_custom_word, remove_custom_word, import_custom_dict,
)
from .demo import demo_process
from .llm import llm_process, process_text
from .config import get_llm_config, set_llm_config, save_llm_config_to_env
from .tts import tts_synthesize, TTS_VOICES
from .correct import correct_text
from .asr import (
    set_asr_engine, resolve_asr_engine, get_offline_engine, transcribe_audio,
    xf_asr, wav_bytes_to_pcm16k, ffmpeg_to_pcm16k_mono, ffmpeg_to_wav16k,
    build_xf_url, run_funasr, _get_funasr_model,
)
from .status import get_status

__all__ = [
    # 资源 / 拼音
    "resource_path", "pinyin_of",
    # 词库
    "get_dict", "get_dict_packages", "get_examples", "get_user_words",
    "add_custom_word", "remove_custom_word", "import_custom_dict",
    # 解析
    "demo_process", "llm_process", "process_text",
    # 大模型配置
    "get_llm_config", "set_llm_config", "save_llm_config_to_env",
    # 语音合成
    "tts_synthesize", "TTS_VOICES",
    # 纠错
    "correct_text",
    # ASR
    "set_asr_engine", "resolve_asr_engine", "get_offline_engine", "transcribe_audio",
    "xf_asr", "wav_bytes_to_pcm16k", "ffmpeg_to_pcm16k_mono", "ffmpeg_to_wav16k",
    "build_xf_url", "run_funasr",
    # 状态
    "get_status",
]
