#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend 包 · 共享状态与基础资源路径（单例模块）
============================================
集中存放所有跨模块共享的可变/不可变全局：
- 资源路径函数（resource_path / exe_dir / _user_dict_path）
- .env 加载与 LLM / 讯飞 配置常量
- 识别就绪标志（ASR_READY / LLM_READY / DEMO_MODE / OFFLINE_*）
- 词库数据与加速索引（DICT_* / _DICT_*）
- 懒加载的模型句柄（_FUNASR_MODEL / _OFFLINE_ENGINE）
- 受保护的第三方依赖（pypinyin / websocket / funasr / requests）

其它子模块统一通过 `from . import _state` 读写 `_state.X`，
避免 `from ._state import X` 造成的「绑定副本」陷阱（global 重赋值不回写模块）。
"""
import os
import sys
import glob
import json
import hashlib
import hmac
import base64
import datetime
import tempfile

import requests
from dotenv import load_dotenv

try:
    from pypinyin import pinyin, Style
except Exception:
    pinyin = None

try:
    import websocket
except Exception:
    websocket = None

try:
    import funasr
except Exception:
    funasr = None


# ----------------------------- 资源路径 -----------------------------
# 包内 __file__ 为 backend/_state.py，故项目根目录需取 backend/ 的父目录，
# 否则开发模式下 resource_path 会指向 backend/ 子目录而找不到 dialect_dict*.json / assets。
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(rel):
    """PyInstaller 打包后用 _MEIPASS 临时目录；源码/开发运行时用项目根目录。"""
    base = getattr(sys, "_MEIPASS", _PROJECT_ROOT)
    return os.path.join(base, rel)


def exe_dir():
    """可执行文件所在目录（用于读取用户可配置的 .env）。"""
    return os.path.dirname(os.path.abspath(sys.executable))


def _user_dict_path() -> str:
    """用户自定义词库存放路径（exe 同目录，持久化、可写）。"""
    return os.path.join(exe_dir(), "user_dict.json")


# .env：优先 exe 同目录（发布场景），否则项目根目录（开发场景）
_env_path = os.path.join(exe_dir(), ".env")
if not os.path.exists(_env_path):
    _env_path = os.path.join(_PROJECT_ROOT, ".env")
load_dotenv(_env_path)

# ----------------------------- 配置读取 -----------------------------
XF_APPID = os.getenv("XF_APPID", "")
XF_API_KEY = os.getenv("XF_API_KEY", "")
XF_API_SECRET = os.getenv("XF_API_SECRET", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

ASR_READY = bool(XF_APPID and XF_API_KEY and XF_API_SECRET and websocket)
LLM_READY = bool(LLM_API_KEY)
DEMO_MODE = not (ASR_READY and LLM_READY)

OFFLINE_ASR_MODEL = os.getenv("OFFLINE_ASR_MODEL", "")
FUNASR_AVAILABLE = funasr is not None

# 识别引擎选择：offline(onnx, 默认)/ xunfei(云端)/ funasr(torch)/ auto(按可用度自动)
ASR_ENGINE_CHOICE = os.getenv("ASR_ENGINE", "auto").lower()


def _find_offline_model_dir():
    """定位 torch-free 的 FunASR-ONNX 模型目录（需含 *.onnx + tokens.txt + am.mvn）。"""
    env = os.getenv("OFFLINE_ASR_MODEL_DIR", "").strip()
    if env and os.path.isdir(env):
        return env
    base = resource_path("assets/asr_models")
    if os.path.isdir(base):
        for d in sorted(glob.glob(os.path.join(base, "*"))):
            if os.path.isdir(d) and glob.glob(os.path.join(d, "*.onnx")) \
               and os.path.exists(os.path.join(d, "tokens.txt")) \
               and os.path.exists(os.path.join(d, "am.mvn")):
                return d
    return None


OFFLINE_MODEL_DIR = _find_offline_model_dir()
OFFLINE_ONNX_AVAILABLE = OFFLINE_MODEL_DIR is not None

# 可选音色：普通话女声 / 偏北方中性男声（念原句更自然）
TTS_VOICES = {
    "mandarin": "zh-CN-XiaoxiaoNeural",   # 普通话 · 晓晓（女）
    "dialect": "zh-CN-YunyangNeural",     # 偏北方口音 · 云扬（男），念方言原句
}

# ----------------------------- 词库数据与加速索引（由 dictionary 模块填充） -----------------------------
DICT_PHRASES = []
DICT_CITIES = []
DICT_META = {}
DICT_PACKAGES = []
DICT = {"meta": DICT_META, "phrases": DICT_PHRASES, "cities": DICT_CITIES}
_DICT_SORTED = []
_DICT_INDEX = {}
_DIALECT_SET = set()
_BY_LEN = {}

# 懒加载句柄
_FUNASR_MODEL = None
_OFFLINE_ENGINE = None
