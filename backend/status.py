#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行状态与数据查询接口（供导航栏/页面展示）。"""
from . import _state
from .asr import resolve_asr_engine


def get_status() -> dict:
    if _state.ASR_READY:
        mode = "云端模式：已接入讯飞 ASR 与大模型。"
    elif _state.OFFLINE_ONNX_AVAILABLE:
        mode = "离线模式：本地 FunASR-ONNX 识别（零上传、纯 CPU），释义走演示词库。"
    elif _state.FUNASR_AVAILABLE:
        mode = "离线模式：本地 FunASR(torch) 识别（隐私零上传），释义走演示词库。"
    else:
        mode = "演示模式：未配置密钥，使用内置词库兜底。"
    return {
        "asr": _state.ASR_READY,
        "llm": _state.LLM_READY,
        "demo": _state.DEMO_MODE,
        "offline_asr": _state.FUNASR_AVAILABLE or _state.OFFLINE_ONNX_AVAILABLE,
        "offline_onnx": _state.OFFLINE_ONNX_AVAILABLE,
        "asr_engine": resolve_asr_engine(),
        "message": mode,
    }
